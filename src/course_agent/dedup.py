"""A 负责：本地近似重复提示（只提示、不合并）。

- 输入可为 KnowledgeCandidate（title/summary 属性）、dict（title/summary 键）
  或任意对象（str() 兜底）。
- 返回 [{"indices":[...], "score": 组内最高相似度}]；相似度达到 threshold
  才归组；绝不修改/合并输入项，是否合并由人工确认。
"""
from .similarity import vectors, cosine


def _text_of(item):
    if hasattr(item, "title"):
        return f"{item.title} {item.summary}"
    if isinstance(item, dict):
        return f"{item.get('title', '')} {item.get('summary', '')}"
    return str(item)


def find_similar(items, threshold=0.72):
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) \
            or not 0 <= threshold <= 1:
        raise ValueError("threshold 必须在 0 和 1 之间")
    items = list(items or [])
    if len(items) < 2:
        return []
    vec = vectors([_text_of(x) for x in items])
    groups, used = [], set()

    def _cosine(i, j):
        # 浮点误差：完全相同的文本余弦可能算出 0.9999999999，夹紧并用
        # 容差比较，保证阈值 1.0 的边界行为符合直觉。
        return min(1.0, cosine(vec[i], vec[j]) + 1e-9)

    for i in range(len(items)):
        if i in used:
            continue
        matches = [j for j in range(i + 1, len(items))
                   if j not in used and _cosine(i, j) >= threshold]
        if matches:
            best = max(_cosine(i, j) for j in matches)
            groups.append({"indices": [i] + matches, "score": round(best, 4)})
            used.update(matches)
    return groups
