import json
import re
from collections import Counter, defaultdict

TOKEN_RE = re.compile(r"[\u4e00-\u9fff]{2,}|[A-Za-z][A-Za-z0-9_+-]{1,}")
TYPE_WEIGHT = {"definition": 2.0, "concept": 1.8, "rule": 1.7, "process": 1.5, "requirement": 1.4, "warning": 1.2, "date": 1.0, "example": 0.8}

def annotate_frequency(rows):
    """Classify importance with coverage, source breadth, confidence and content type."""
    total_docs = max(1, len({r.get("filename") for r in rows if r.get("filename")}))
    records, term_doc_counts = [], Counter()
    for row in rows:
        try:
            keywords = json.loads(row.get("keywords_json") or "[]")
        except (TypeError, json.JSONDecodeError):
            keywords = []
        terms = set(str(x).strip().lower() for x in keywords if str(x).strip())
        terms.update(x.lower() for x in TOKEN_RE.findall(f"{row.get('title','')} {row.get('summary','')}"))
        term_doc_counts.update({(t, row.get("filename") or row.get("id")) for t in terms})
        records.append((row, terms))
    scored = []
    for row, terms in records:
        coverage = max((sum(1 for r, _ in records if t in _ and r.get("filename") == row.get("filename")) for t in terms), default=1)
        breadth = max((sum(1 for r, _ in records if t in _ and r.get("filename")) for t in terms), default=1)
        confidence = float(row.get("confidence") or 0)
        heading = str(row.get("heading") or "").strip()
        heading_focus = 2.5 if heading and (row.get("title") or "").strip() in heading or heading in (row.get("title") or "") else 0.0
        method = str(row.get("extraction_method") or "").lower()
        type_bonus = max((v for k, v in TYPE_WEIGHT.items() if k in method), default=1.0)
        score = round((breadth / total_docs) * 6 + min(coverage, 3) * 0.7 + confidence * 1.5 + type_bonus + heading_focus, 2)
        scored.append((row, score, breadth, confidence))
    values = sorted((score for _, score, _, _ in scored), reverse=True)
    high_cut = values[max(0, len(values)//3 - 1)] if values else 0
    medium_cut = values[max(0, (2*len(values))//3 - 1)] if values else 0
    output = []
    for row, score, breadth, confidence in scored:
        if score >= high_cut:
            level = "高频"
        elif score >= medium_cut:
            level = "中频"
        else:
            level = "低频"
        item = dict(row)
        item["frequency"] = level
        item["frequency_score"] = score
        item["frequency_reason"] = f"章节/小节标题权重 + 跨资料覆盖 {breadth} 份 + 置信度 {confidence:.2f} + 内容类型权重"
        output.append(item)
    return output


