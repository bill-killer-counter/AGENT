"""Shared validation and wire-format definitions (Python 3.10+)."""
from datetime import datetime, timezone
KINDS = {'confirmed_knowledge','course_document_archive','edited_title','edited_summary','course_highlight','preference'}
SESSION_FIELDS = {'current_question','selected_files','page_filters','draft','retrieval_results'}
WORKSPACE_KINDS = {'document','chunk','batch','confirmation','question_summary','operation'}
EXPORT_FIELDS = {'memory_id','workspace_id','scope','kind','content','source_ids','confirmed','created_at','updated_at','deleted_at'}
def now():
    return datetime.now(timezone.utc).isoformat()
def nonempty(value, name):
    if not isinstance(value,str) or not value.strip():
        raise ValueError(f'{name} must be a nonempty string')
    return value
