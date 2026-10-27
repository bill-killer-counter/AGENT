"""SQLite repository. Bind workspace_id for every web request; unbound is trusted admin mode."""
import json
import sqlite3
from copy import deepcopy
from pathlib import Path
from uuid import uuid4
from .memory_models import KINDS, SESSION_FIELDS, WORKSPACE_KINDS, now, nonempty

class MemoryStore:
    def __init__(self, db_path, workspace_id=None):
        self.workspace_id = nonempty(workspace_id,'workspace_id') if workspace_id is not None else None
        if str(db_path) != ':memory:':
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(db_path), timeout=10)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(Path(__file__).with_name('sqlite_schema.sql').read_text())
        self._sessions = {}
    def close(self):
        self.db.close()
    def __enter__(self): return self
    def __exit__(self, *args): self.close()
    def _workspace(self, workspace_id):
        nonempty(workspace_id,'workspace_id')
        if self.workspace_id is not None and workspace_id != self.workspace_id:
            raise PermissionError('workspace mismatch')
        return workspace_id
    def create_session_state(self, session_id=None, **state):
        session_id = session_id or str(uuid4())
        nonempty(session_id,'session_id')
        if session_id in self._sessions: raise ValueError('session already exists')
        self._sessions[session_id] = {}
        try: self.update_session_state(session_id, **state)
        except Exception:
            del self._sessions[session_id]
            raise
        return session_id
    def update_session_state(self, session_id, **state):
        if session_id not in self._sessions: raise KeyError(session_id)
        if set(state)-SESSION_FIELDS: raise ValueError('unknown session field')
        self._sessions[session_id].update(deepcopy(state))
        return self.get_session_state(session_id)
    def get_session_state(self, session_id):
        return deepcopy(self._sessions.get(session_id))
    def clear_session_state(self, session_id):
        return self._sessions.pop(session_id,None) is not None
    def _content(self, content):
        if not isinstance(content,dict) or not content: raise ValueError('content must be a nonempty object')
        return json.dumps(content,ensure_ascii=False,allow_nan=False)
    def create_memory(self, workspace_id, kind, content, source_ids, confirmed=False):
        self._workspace(workspace_id)
        if kind not in KINDS: raise ValueError('unsupported kind; drafts are session-only')
        if type(confirmed) is not bool: raise ValueError('confirmed must be bool')
        if not isinstance(source_ids,list) or any(not isinstance(s,str) or not s.strip() for s in source_ids):
            raise ValueError('source_ids must be a list of nonempty strings')
        if confirmed and not source_ids: raise ValueError('confirmation requires sources')
        encoded = self._content(content)
        mid, stamp = 'memory-'+str(uuid4()), now()
        with self.db:
            self.db.execute('INSERT INTO memories VALUES (?,?,?,?,?,?,?,?,?,NULL)',
                (mid,workspace_id,'long_term' if confirmed else 'long_session',kind,encoded,
                 json.dumps(list(dict.fromkeys(source_ids))),int(confirmed),stamp,stamp))
        return mid
    def _row(self, memory_id):
        nonempty(memory_id,'memory_id')
        sql='SELECT * FROM memories WHERE memory_id=? AND deleted_at IS NULL'
        args=[memory_id]
        if self.workspace_id is not None:
            sql+=' AND workspace_id=?'; args.append(self.workspace_id)
        return self.db.execute(sql,args).fetchone()
    @staticmethod
    def _decode(row):
        if row is None: return None
        result=dict(row)
        result['content']=json.loads(result.pop('content_json'))
        result['source_ids']=json.loads(result.pop('source_ids_json'))
        result['confirmed']=bool(result['confirmed'])
        return result
    def get_memory(self, memory_id):
        return self._decode(self._row(memory_id))
    def confirm_memory(self, memory_id):
        row=self._row(memory_id)
        if row is None: raise KeyError(memory_id)
        if not json.loads(row['source_ids_json']): raise ValueError('confirmation requires sources')
        with self.db:
            self.db.execute("UPDATE memories SET confirmed=1,scope='long_term',updated_at=? WHERE memory_id=?",(now(),memory_id))
        return self.get_memory(memory_id)
    def list_memories(self, workspace_id, scope=None):
        self._workspace(workspace_id)
        scope = scope or 'long_term'
        if scope not in {'long_term','long_session'}: raise ValueError('invalid scope')
        rows=self.db.execute('SELECT * FROM memories WHERE workspace_id=? AND scope=? AND deleted_at IS NULL ORDER BY created_at,memory_id',(workspace_id,scope))
        return [self._decode(r) for r in rows]
    def search_memories(self, workspace_id, query):
        self._workspace(workspace_id)
        nonempty(query,'query')
        # Literal Unicode substring search: %, _ and quotes have no SQL semantics.
        return [r for r in self.list_memories(workspace_id) if query.casefold() in json.dumps(r['content'],ensure_ascii=False).casefold()]
    def update_memory(self, memory_id, content):
        if self._row(memory_id) is None: raise KeyError(memory_id)
        encoded=self._content(content)
        # Editing revokes old confirmation; caller must explicitly confirm the new revision.
        with self.db:
            self.db.execute("UPDATE memories SET content_json=?,confirmed=0,scope='long_session',updated_at=? WHERE memory_id=?",(encoded,now(),memory_id))
        return self.get_memory(memory_id)
    def delete_memory(self, memory_id):
        if self._row(memory_id) is None: return False
        stamp=now()
        with self.db:
            self.db.execute('UPDATE memories SET deleted_at=?,updated_at=? WHERE memory_id=?',(stamp,stamp,memory_id))
        return True
    def clear_workspace_long_term_memory(self, workspace_id):
        self._workspace(workspace_id)
        stamp=now()
        with self.db:
            cursor=self.db.execute("UPDATE memories SET deleted_at=?,updated_at=? WHERE workspace_id=? AND scope='long_term' AND deleted_at IS NULL",(stamp,stamp,workspace_id))
        return cursor.rowcount
    def export_workspace_memory(self, workspace_id):
        return {'schema_version':'1.0','workspace_id':self._workspace(workspace_id),'memories':self.list_memories(workspace_id)}
    def add_workspace_record(self, workspace_id, kind, content):
        self._workspace(workspace_id)
        if kind not in WORKSPACE_KINDS: raise ValueError('invalid workspace record kind')
        encoded=self._content(content)
        rid='record-'+str(uuid4())
        with self.db:
            self.db.execute('INSERT INTO workspace_records VALUES (?,?,?,?,?)',(rid,workspace_id,kind,encoded,now()))
        return rid
    def list_workspace_records(self, workspace_id, kind=None):
        self._workspace(workspace_id)
        if kind is not None and kind not in WORKSPACE_KINDS: raise ValueError('invalid kind')
        rows=self.db.execute('SELECT * FROM workspace_records WHERE workspace_id=? ORDER BY created_at,record_id',(workspace_id,))
        return [{'record_id':r['record_id'],'workspace_id':r['workspace_id'],'kind':r['kind'],'content':json.loads(r['content_json']),'created_at':r['created_at']} for r in rows if kind is None or r['kind']==kind]
