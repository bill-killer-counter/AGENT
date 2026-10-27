from .adapters import MEMORY, PROCESSOR
from .phase1_service import Phase1Service

class CourseAgent:
    """Backward-compatible facade retained for the original A tests."""
    def __init__(self, repository=None):
        self._service = Phase1Service()
        if repository is not None:
            self._service.repo = repository
    def ingest(self, workspace_id, filename, text): return self._service.ingest(workspace_id, filename, text)
    def ask(self, workspace_id, question, **kwargs): return self._service.ask(workspace_id, question)

def process_document(filename, text): return PROCESSOR(filename, text)
def save_confirmed(workspace_id, item): return MEMORY.save_confirmed(workspace_id, item)
def list_confirmed(workspace_id): return MEMORY.list_confirmed(workspace_id)
def delete_memory(memory_id): return MEMORY.delete(memory_id)
def clear_memory(workspace_id): return MEMORY.clear(workspace_id)
def answer_question(workspace_id, question):
    hits = [x for x in list_confirmed(workspace_id) if any(t in x.get("summary", "") or t in x.get("title", "") for t in question.strip().split())]
    if not hits: return {"answer": "当前资料中没有找到足够依据。", "citations": [], "abstained": True}
    return {"answer": "\n\n".join(x["summary"] for x in hits[:3]), "abstained": False, "citations": [{"filename": x["source_file"], "chunk_id": x["chunk_id"], "quote": x["source_quote"], "score": 1.0} for x in hits[:3]]}
