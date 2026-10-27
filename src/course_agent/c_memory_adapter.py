import json
import re
from pathlib import Path
from .c_memory.memory_store import MemoryStore

class CMemoryAdapter:
    """Member C memory adapter with one confirmed archive per source document."""
    def __init__(self, db_path='data/memory.db'):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _keywords(items):
        values = []
        for item in items:
            raw = item.get('keywords')
            if not raw and item.get('keywords_json'):
                try: raw = json.loads(item['keywords_json'])
                except (TypeError, json.JSONDecodeError): raw = []
            if isinstance(raw, str): raw = [raw]
            values.extend(x.strip() for x in (raw or []) if isinstance(x, str) and x.strip())
            values.extend(re.findall(r"[\u4e00-\u9fff]{2,6}|[A-Za-z]{3,}", item.get('title', '') + ' ' + item.get('summary', '')))
        return list(dict.fromkeys(values))[:12]

    def save_document_archive(self, workspace_id, document_id, filename, items):
        """Upsert all confirmed points from one document as a single memory object."""
        doc_id = str(document_id or '').strip()
        filename = str(filename or '未命名资料').strip()
        if not doc_id:
            # Legacy fallback; new ingestion always supplies the stable document ID.
            doc_id = 'filename:' + filename
        points_by_id = {}
        with MemoryStore(self.db_path, workspace_id=workspace_id) as store:
            existing = next((r for r in store.list_memories(workspace_id)
                             if r.get('kind') == 'course_document_archive'
                             and str(r.get('content', {}).get('document_id')) == doc_id), None)
            if existing:
                for point in existing.get('content', {}).get('knowledge_points', []):
                    key = str(point.get('knowledge_id') or point.get('title') or len(points_by_id))
                    points_by_id[key] = point
            for item in items:
                key = str(item.get('id') or item.get('knowledge_id') or item.get('title') or len(points_by_id))
                point = {
                    'knowledge_id': item.get('id') or item.get('knowledge_id'),
                    'title': item.get('title') or '未命名知识点',
                    'summary': item.get('summary') or '',
                    'keywords': self._keywords([item])[:6],
                    'heading': item.get('heading') or '',
                    'chunk_id': item.get('chunk_id') or '',
                    'quote': item.get('quote') or '',
                }
                points_by_id[key] = point
            points = list(points_by_id.values())
            keywords = list(dict.fromkeys(k for point in points for k in point.get('keywords', [])))[:12]
            content = {
                'archive_type': 'source_document',
                'document_id': doc_id,
                'source_file': filename,
                'title': filename,
                'summary': f'本资料已归档 {len(points)} 个知识点。' + (' 核心主题：' + '、'.join(keywords[:6]) + '。' if keywords else ''),
                'keywords': keywords,
                'knowledge_count': len(points),
                'knowledge_points': points,
            }
            # Keep C's source contract chunk-based while the content document_id groups the archive.
            sources = list(dict.fromkeys(point['chunk_id'] for point in points if point.get('chunk_id'))) or [doc_id]
            if existing:
                if existing.get('content') == content and existing.get('source_ids') == sources:
                    return existing['memory_id']
                store.update_memory(existing['memory_id'], content)
                # Updating revokes confirmation; confirm the revised archive immediately because
                # it is rebuilt only from already-confirmed source knowledge.
                return store.confirm_memory(existing['memory_id'])['memory_id']
            return store.create_memory(workspace_id, 'course_document_archive', content, sources, confirmed=True)

    def save_confirmed(self, workspace_id, item):
        return self.save_document_archive(workspace_id, item.get('document_id'),
                                          item.get('filename') or item.get('source_file'), [item])

    def compact_legacy(self, workspace_id, live_document_ids):
        """Remove old per-point entries and archives for documents deleted from the course."""
        live = {str(x) for x in live_document_ids}
        with MemoryStore(self.db_path, workspace_id=workspace_id) as store:
            for row in store.list_memories(workspace_id):
                content = row.get('content') or {}
                if row.get('kind') == 'confirmed_knowledge':
                    store.delete_memory(row['memory_id'])
                elif row.get('kind') == 'course_document_archive' and str(content.get('document_id')) not in live:
                    store.delete_memory(row['memory_id'])

    def list(self, workspace_id):
        with MemoryStore(self.db_path, workspace_id=workspace_id) as store:
            return store.list_memories(workspace_id)

    def delete(self, workspace_id, memory_id):
        with MemoryStore(self.db_path, workspace_id=workspace_id) as store:
            return store.delete_memory(memory_id)

    def delete_document_archive(self, workspace_id, document_id):
        with MemoryStore(self.db_path, workspace_id=workspace_id) as store:
            for row in store.list_memories(workspace_id):
                if row.get('kind') == 'course_document_archive' and str(row.get('content', {}).get('document_id')) == str(document_id):
                    return store.delete_memory(row['memory_id'])
        return False

    def clear(self, workspace_id):
        with MemoryStore(self.db_path, workspace_id=workspace_id) as store:
            return store.clear_workspace_long_term_memory(workspace_id)

    def add_record(self, workspace_id, kind, content):
        with MemoryStore(self.db_path, workspace_id=workspace_id) as store:
            return store.add_workspace_record(workspace_id, kind, content)

    def list_records(self, workspace_id, kind=None):
        with MemoryStore(self.db_path, workspace_id=workspace_id) as store:
            return store.list_workspace_records(workspace_id, kind)

    def search(self, workspace_id, query):
        with MemoryStore(self.db_path, workspace_id=workspace_id) as store:
            return store.search_memories(workspace_id, query)
