import hashlib
import json
from pathlib import Path
from .dedup import find_similar
from .extractor import extract_candidates
from .parser import chunk_text, parse_text
from .repository import Repository
from .retrieval import search
from .c_memory_adapter import CMemoryAdapter
from .llm_provider import answer_with_evidence

class Phase1Service:
    def __init__(self, db_path="data/phase1.db", memory_db_path=None):
        self.repo = Repository(db_path)
        self.long_term = CMemoryAdapter(memory_db_path or str(Path(db_path).with_name("memory.db")))

    def workspace(self, name):
        found = next((x for x in self.repo.workspaces() if x["name"] == name), None)
        return found["id"] if found else self.repo.create_workspace(name)

    def ingest(self, workspace_id, filename, text):
        clean = parse_text(filename, text)
        # chunk id 必须跨账号、跨同名文件保持唯一；内容哈希同时保证重复上传可复现。
        chunk_seed = f"{workspace_id}:{filename}:{hashlib.sha256(clean.encode('utf-8')).hexdigest()}"
        chunks = chunk_text(clean, chunk_seed)
        candidates, tasks = extract_candidates(chunks)
        # 同一课程中标题和摘要高度相近的候选不重复写入，保留第一次出现的可追溯来源。
        existing = {f"{item['title'].strip().lower()}|{item['summary'][:80].strip().lower()}" for item in self.repo.knowledge(workspace_id)}
        unique_candidates = []
        for candidate in candidates:
            key = f"{candidate.title.strip().lower()}|{candidate.summary[:80].strip().lower()}"
            if key not in existing:
                unique_candidates.append(candidate)
                existing.add(key)
        candidates = unique_candidates
        doc_id, created = self.repo.add_document(workspace_id, filename, clean, chunks, candidates, tasks)
        if created:
            self.long_term.add_record(workspace_id, "document", {"document_id": doc_id, "filename": filename, "chunk_count": len(chunks)})
            self.repo.audit(workspace_id, "document_ingested", {"document_id": doc_id, "filename": filename, "chunks": len(chunks)})
        return {"document_id": doc_id, "created": created, "chunks": len(chunks), "candidates": len(candidates), "tasks": len(tasks), "similar": find_similar(self.repo.knowledge(workspace_id, "candidate"))}

    def ask(self, workspace_id, question, filename=None, cloud_enhance=False):
        # 短中文问题常只与原文共享一个双字词，例如“栈是什么”与“栈是一种”。
        # 0.03 排除零相似结果，也避免把有来源的短问题误判为拒答。
        hits = [x for x in search(question, workspace_id, self.repo, top_k=5) if x["score"] >= 0.03]
        if filename: hits = [x for x in hits if x["filename"] == filename]
        if not hits:
            return {"answer": "当前资料范围中没有找到足够依据。", "citations": [], "abstained": True, "confidence": 0.0}
        self.long_term.add_record(workspace_id, "question_summary", {"question": question, "filename": filename, "hit_count": len(hits)})
        # 问答优先呈现已经整理过的知识摘要，再附上原文证据，避免只返回零散段落。
        organized = [x for x in self.repo.knowledge(workspace_id, "confirmed") if not filename or x.get("filename") == filename]
        organized = organized[:3]
        summary = "\n".join(f"- {x['title']}：{x['summary']}" for x in organized)
        evidence = "\n\n".join(x["text"] for x in hits[:3])
        local_answer = ("整理后的知识要点：\n" + summary + "\n\n资料原文依据：\n" + evidence) if summary else evidence
        cloud_answer = answer_with_evidence(question, evidence) if cloud_enhance else None
        answer = cloud_answer or local_answer
        return {"answer": answer, "abstained": False, "cloud_enhanced": bool(cloud_answer), "confidence": round(min(1.0, hits[0]["score"] * 1.5), 3), "citations": [{"filename": x["filename"], "chunk_id": x["chunk_id"], "quote": x["text"][:400], "score": round(x["score"], 3)} for x in hits]}

    def confirm(self, knowledge_id, title, summary):
        target = None
        for ws in self.repo.workspaces():
            hit = next((x for x in self.repo.knowledge(ws["id"]) if x["id"] == knowledge_id), None)
            if hit: target = (ws["id"], hit); break
        if not target: return False
        workspace_id, item = target
        ok = self.repo.confirm_knowledge(knowledge_id, title, summary)
        if ok:
            item.update({"title": title, "summary": summary}); self.long_term.save_confirmed(workspace_id, item)
        return ok

    def auto_confirm_workspace(self, workspace_id):
        count = 0
        for item in self.repo.knowledge(workspace_id, "candidate"):
            if item.get("chunk_id") and self.repo.confirm_knowledge(item["id"], item["title"], item["summary"]):
                item["status"] = "confirmed"
                self.long_term.save_confirmed(workspace_id, item)
                count += 1
        return count

    def long_term_memory(self, workspace_id):
        # Migrate the old per-knowledge records once. Future archive changes are written
        # by save_confirmed; a user-deleted archive is not silently recreated on refresh.
        current = self.long_term.list(workspace_id)
        legacy = [row for row in current if row.get("kind") == "confirmed_knowledge"]
        if legacy:
            legacy_ids = {str((row.get("content") or {}).get("knowledge_id")) for row in legacy}
            legacy_files = {(row.get("content") or {}).get("source_file") for row in legacy}
            confirmed = self.repo.knowledge(workspace_id, "confirmed")
            by_document = {}
            for item in confirmed:
                doc_id = item.get("document_id")
                if not doc_id:
                    continue
                if str(item.get("id")) not in legacy_ids and item.get("filename") not in legacy_files:
                    continue
                bucket = by_document.setdefault(str(doc_id), {"filename": item.get("filename") or "未命名资料", "items": {}})
                bucket["items"][str(item["id"])] = item
            for doc_id, bucket in by_document.items():
                self.long_term.save_document_archive(workspace_id, doc_id, bucket["filename"], list(bucket["items"].values()))
            active_document_ids = {d["id"] for d in self.repo.documents(workspace_id)}
            self.long_term.compact_legacy(workspace_id, active_document_ids)
        # The older A repository also wrote one hidden memory row per knowledge point.
        # C's document archive is now the single authoritative long-term memory store.
        self.repo.clear_long_term(workspace_id)
        return self.long_term.list(workspace_id)
    def long_session_memory(self, workspace_id): return self.long_term.list_records(workspace_id)
    def delete_document(self, workspace_id, document_id):
        deleted = self.repo.delete_document(workspace_id, document_id)
        if deleted: self.long_term.delete_document_archive(workspace_id, document_id)
        if deleted: self.repo.audit(workspace_id, "document_deleted", {"document_id": document_id})
        return deleted
    def review_queue(self, workspace_id, limit=20): return self.repo.review_queue(workspace_id, limit)
    def grade_review(self, workspace_id, knowledge_id, remembered): return self.repo.grade_review(workspace_id, knowledge_id, remembered)
    def record_quiz_attempt(self, workspace_id, knowledge_id, question, answer, is_correct):
        return self.repo.record_quiz_attempt(workspace_id, knowledge_id, question, answer, is_correct)
    def quiz_summary(self, workspace_id): return self.repo.quiz_summary(workspace_id)
    def delete_long_term_memory(self, workspace_id, memory_id): return self.long_term.delete(workspace_id, memory_id)
    def clear_long_term_memory(self, workspace_id): return self.long_term.clear(workspace_id)

    def export(self, workspace_id, fmt="md"):
        rows, tasks = self.repo.knowledge(workspace_id), self.repo.tasks(workspace_id)
        if fmt == "json": return json.dumps({"knowledge": rows, "tasks": tasks}, ensure_ascii=False, indent=2)
        lines = ["# 课程知识库", "", "## 知识点"]
        for row in rows: lines += [f"### {row['title']}", "", row["summary"], "", f"来源：{row['filename'] or '未知'} / {row['chunk_id'] or '未知'}", ""]
        return "\n".join(lines + ["## 待办"] + [f"- {x['text']}（截止：{x['due_date'] or '未识别'}；来源：{x['filename'] or '未知'}）" for x in tasks])

    def review(self, workspace_id, query="", status="all"):
        rows = self.repo.knowledge(workspace_id, None if status == "all" else status)
        if query.strip():
            q = query.strip().lower(); rows = [x for x in rows if q in (x["title"] + x["summary"] + (x["filename"] or "")).lower()]
        return rows





