"""Temporary A-only processor. Replace this adapter when B delivers the dataset pipeline."""
from __future__ import annotations

import re
import uuid

SUPPORTED = {".txt", ".md", ".markdown"}


def process_document(filename: str, text: str) -> dict:
    if not filename.lower().endswith(tuple(SUPPORTED)):
        raise ValueError("仅支持 TXT 和 Markdown 文件")
    clean = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not clean:
        raise ValueError("文件内容不能为空")
    chunks = [x.strip() for x in re.split(r"\n\s*\n|(?<=[。！？])", clean) if x.strip()]
    items = []
    tasks = []
    for i, chunk in enumerate(chunks):
        chunk_id = f"{uuid.uuid4().hex[:8]}-{i}"
        title = re.sub(r"^#+\s*", "", chunk).split("：", 1)[0][:32]
        item = {
            "id": str(uuid.uuid4()), "title": title or "未命名知识点",
            "summary": chunk[:240], "source_file": filename,
            "source_quote": chunk[:300], "chunk_id": chunk_id,
            "status": "candidate"
        }
        items.append(item)
        if any(k in chunk for k in ("提交", "截止", "需要", "必须")):
            tasks.append({"text": chunk, "source_file": filename, "chunk_id": chunk_id})
    return {"filename": filename, "chunks": chunks, "knowledge_items": items,
            "tasks": tasks, "similar_items": []}
