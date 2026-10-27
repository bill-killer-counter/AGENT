"""A 负责：TXT/Markdown 规范化与带溯源的分块（parser-v2）。

溯源约定（对下游 B/C 的承诺）：
- chunk 的 start_offset/end_offset 是相对 ``parse_text`` 返回的规范化文本的
  字符偏移（Python str 索引），``text[start_offset:end_offset] == chunk.text``。
- chunk.id 由 (document_id, ordinal, 偏移, 文本) 经 uuid5 确定性生成：
  同一文档同一内容重复解析会得到完全相同的 chunk id，可跨次溯源。
- 标题块自身成为一个 chunk；其后所有 chunk 的 ``heading`` 携带最近一个
  Markdown 标题（含标题行本身所在段）。
"""
import re
import uuid
from pathlib import Path

from .models import Chunk

SUPPORTED = {".txt", ".md", ".markdown", ".docx", ".pptx", ".pdf"}

_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "course_agent/parser-v2")
_HEADING = re.compile(r"^#{1,6}\s+(.+)")
_SENT_END = re.compile(r"[。！？!?；;]")


def parse_text(filename, text):
    """接受 txt/md/markdown/docx/pptx 的已提取文本；规范化换行、BOM、NUL 与行尾空白，去除首尾空白。"""
    if Path(filename).suffix.lower() not in SUPPORTED:
        raise ValueError("支持 TXT、Markdown、Word（DOCX）、PowerPoint（PPTX）和 PDF 文件。")
    if not isinstance(text, str) or not text or not text.strip():
        raise ValueError("文件内容为空。")
    text = text.replace("\ufeff", "").replace("\x00", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    return text.strip()


def _split_long(para, start, max_chars, overlap, heading):
    """超长段落：尽量在句号/问号处断开，断不开按窗口硬切，带 overlap。"""
    pieces = []
    pos = 0
    while pos < len(para):
        end = min(len(para), pos + max_chars)
        if end < len(para):
            # 在窗口后半段找最后一个句末标点，避免切断句子
            cut = -1
            for m in _SENT_END.finditer(para, pos + max_chars // 2, end):
                cut = m.end()
            if cut > pos + overlap:
                end = cut
        pieces.append((para[pos:end], start + pos, start + end, heading))
        if end >= len(para):
            break
        pos = max(pos + 1, end - overlap)  # 保证前进，防 overlap 过大死循环
    return pieces


def chunk_text(text, document_id, max_chars=800, overlap=100):
    if not document_id or not isinstance(document_id, str):
        raise ValueError("document_id 必须是非空字符串（用于稳定溯源）。")
    if max_chars <= 0 or overlap < 0 or overlap >= max_chars:
        raise ValueError("需满足 max_chars > overlap >= 0。")
    text = text.strip() if isinstance(text, str) else ""
    if not text:
        return []

    pieces = []  # (片段文本, 起偏移, 止偏移, 标题)
    cursor = 0
    heading = None
    for para in re.split(r"\n\s*\n", text):
        start = text.find(para, cursor)
        cursor = start + len(para)
        stripped = para.strip()
        m = _HEADING.match(stripped)
        if m:
            heading = m.group(1).strip()
        if len(para) <= max_chars:
            pieces.append((para, start, start + len(para), heading))
            continue
        pieces.extend(_split_long(para, start, max_chars, overlap, heading))

    out = []
    for ordinal, (part, a, b, part_heading) in enumerate(pieces):
        if not part.strip():
            continue
        cid = uuid.uuid5(_NAMESPACE, f"{document_id}|{ordinal}|{a}-{b}|{part}")
        out.append(Chunk(str(cid), document_id, ordinal, part, part_heading, a, b))
    return out

