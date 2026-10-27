"""A 负责：基于可解释规则的候选/待办抽取（rules-v1）。

约定：
- 返回 (list[KnowledgeCandidate], list[task dict])；候选必须带
  source_chunk_ids（至少含来源 chunk 的 id），task dict 含
  id/text/due_date/source_chunk_id。
- 纯规则、离线；只产候选，不做任何合并决策（合并属人工确认）。
- 局限：只识别显式定义句式（是指/定义为/包括/包含等）与显式日期，
  隐式知识、跨句推理、英文待办动词均不覆盖；同一文档内标题前缀
  相同的句子只保留首条，可能漏掉后文细化定义。
"""
import re
import uuid

from .models import KnowledgeCandidate

STOP = {
    "这个", "那个", "我们", "你们", "他们", "因此", "例如", "以及", "进行",
    "通过", "课程", "内容", "需要", "可以", "其中", "关于", "如果", "因为",
    "一个", "一些", "就是", "什么", "怎样", "如何", "以下", "如下", "时候",
}

# 定义句式：主语（2~40 字）+ 定义词 + 谓语部分（3~100 字）
DEFINITION = re.compile(
    r"(.{1,40}?)(?:是指|指的是|定义为|称为|叫做|所谓|包括|包含)([^。！？\n]{3,100})"
)
DATE = re.compile(
    r"\d{4}年\d{1,2}月\d{1,2}日|\d{1,2}月\d{1,2}日[前之前]?|\d{4}[-/.]\d{1,2}[-/.]\d{1,2}"
)
TASK_HINT = ("需", "需要", "应当", "必须", "请于", "截止", "提交", "待办",
             "TODO", "todo", "作业", "deadline", "Deadline", "完成")
# 标题前缀清理：序号、项目符号
LEADING_NOISE = re.compile(r"^[\s#>*\-•]*?(?:\d{1,2}[、.．)）]|[一二三四五六七八九十]{1,3}[、.．])\s*")


def _title_from(sentence, match):
    if match:
        title = match.group(1).strip()
    else:
        title = re.split(r"[：:，,。；;]", sentence, maxsplit=1)[0].strip()
    title = LEADING_NOISE.sub("", title).strip(" #\t：:，,。；;—-")
    return title[:48]


def _keywords(text):
    found = re.findall(r"[\u4e00-\u9fff]{2,6}|[A-Za-z]{3,}", text)
    keep = [x for x in found if x not in STOP]
    return list(dict.fromkeys(keep))[:8]


def extract_candidates(chunks):
    items, tasks, seen = [], [], set()
    for c in chunks or []:
        for sentence in re.split(r"(?<=[。！？!?])\s*|\n+", c.text):
            s = sentence.strip(" #\t*-•")
            if len(s) < 8:
                continue
            match = DEFINITION.search(s)
            title = _title_from(s, match)
            if len(title) < 2:
                title = s[:24]
            if title.lower() not in seen:
                seen.add(title.lower())
                items.append(KnowledgeCandidate(
                    str(uuid.uuid4()), title, s[:240], _keywords(s), [c.id],
                    extraction_method="rules-v1",
                    confidence=0.72 if match else 0.48,
                ))
            if any(h in s for h in TASK_HINT):
                dm = DATE.search(s)
                tasks.append({
                    "id": str(uuid.uuid4()),
                    "text": s[:200],
                    "due_date": dm.group(0) if dm else None,
                    "source_chunk_id": c.id,
                })
    return items, tasks
