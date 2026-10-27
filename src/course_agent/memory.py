class SessionMemory:
 """Short-term state lives only in Streamlit session_state."""
 @staticmethod
 def empty():return {"selected_document":None,"drafts":{},"filters":{},"recent_question":None}
class WorkspaceMemory:
 """Long-session, workspace-scoped data persisted in SQLite."""
 def __init__(self,repository):self.repo=repository
 def recent_confirmed(self,workspace_id,limit=20):return self.repo.memory(workspace_id,"workspace")[:limit]
class LongTermMemory:
 """Persistent course facts; only explicit confirmations become long-term."""
 def __init__(self,repository):self.repo=repository
 def confirmed(self,workspace_id):return [m for m in self.repo.memory(workspace_id,"long_term") if m["confirmed"]]
 def forget(self,workspace_id):self.repo.clear_long_term(workspace_id)
