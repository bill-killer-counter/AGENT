"""Offline extraction for common course document formats."""
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

SUPPORTED_UPLOAD = {".txt", ".md", ".markdown", ".docx", ".pptx", ".pdf"}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 5000
MAX_ARCHIVE_RATIO = 100
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
_P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"


def _xml_text(data, tags):
    root = ET.fromstring(data)
    return "\n".join("".join(node.itertext()).strip() for node in root.iter() if node.tag in tags and "".join(node.itertext()).strip())


def extract_text(filename, raw):
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_UPLOAD:
        raise ValueError("支持 TXT、Markdown、Word（DOCX）和 PowerPoint（PPTX）文件。")
    if not raw:
        raise ValueError("文件内容为空。")
    if isinstance(raw, bytes) and len(raw) > MAX_UPLOAD_BYTES:
        raise ValueError("文件超过 20 MB 上限，请拆分后上传。")
    if suffix in {".txt", ".md", ".markdown"}:
        return raw.decode("utf-8-sig") if isinstance(raw, bytes) else raw
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise ValueError("PDF 解析组件尚未安装，请执行 pip install -r requirements.txt。") from exc
        try:
            reader = PdfReader(__import__("io").BytesIO(raw))
            text = "\n\n".join((page.extract_text() or "").strip() for page in reader.pages).strip()
            if not text:
                raise ValueError("PDF 未提取到可复制文本；扫描件需要在后续 OCR 模式中处理。")
            return text
        except Exception as exc:
            raise ValueError(f"无法读取 PDF：{exc}") from exc
    try:
        with ZipFile(__import__("io").BytesIO(raw)) as archive:
            infos = archive.infolist()
            if len(infos) > MAX_ARCHIVE_MEMBERS:
                raise ValueError("Office 文件包含过多内部文件，已拒绝解析。")
            compressed = sum(info.compress_size for info in infos) or 1
            if sum(info.file_size for info in infos) / compressed > MAX_ARCHIVE_RATIO:
                raise ValueError("Office 文件压缩比例异常，已拒绝解析。")
            if suffix == ".docx":
                names = sorted(n for n in archive.namelist() if n.startswith("word/document") and n.endswith(".xml"))
                return _xml_text(archive.read(names[0]), {_W + "p", _W + "tbl"}) if names else ""
            slides = sorted(n for n in archive.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml"))
            parts = []
            for number, name in enumerate(slides, 1):
                text = _xml_text(archive.read(name), {_A + "t"})
                if text: parts.append(f"## 幻灯片 {number}\n{text}")
            return "\n\n".join(parts)
    except (OSError, KeyError, ValueError, ET.ParseError) as exc:
        raise ValueError(f"无法读取 {suffix} 文件：{exc}") from exc
