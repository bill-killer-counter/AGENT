from dataclasses import dataclass, field
from typing import Optional
@dataclass
class Chunk:
    id: str
    document_id: str
    ordinal: int
    text: str
    heading: Optional[str] = None
    start_offset: int = 0
    end_offset: int = 0
@dataclass
class KnowledgeCandidate:
    id: str
    title: str
    summary: str
    keywords: list[str] = field(default_factory=list)
    source_chunk_ids: list[str] = field(default_factory=list)
    extraction_method: str = "rules-v1"
    confidence: float = 0.5
@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    filename: str
    text: str
    score: float
@dataclass
class MemoryEntry:
    id: str
    workspace_id: str
    scope: str
    kind: str
    content: str
    source_ids: list[str] = field(default_factory=list)
    confirmed: bool = False
