import hashlib,json,os,sqlite3,uuid
from pathlib import Path
from datetime import datetime,timezone,timedelta
from contextlib import contextmanager
def now():return datetime.now(timezone.utc).isoformat()
def db_path():return Path(os.environ.get("AGENT_DB_PATH","data/agent.db"))
class Repository:
 def __init__(self,path=None):self.path=Path(path) if path else db_path();self.path.parent.mkdir(parents=True,exist_ok=True);self.init()
 @contextmanager
 def conn(self):
  c=sqlite3.connect(self.path);c.row_factory=sqlite3.Row;c.execute("PRAGMA foreign_keys=ON")
  try:yield c;c.commit()
  finally:c.close()
 def init(self):
  with self.conn() as c:c.executescript("""
  CREATE TABLE IF NOT EXISTS workspaces(id TEXT PRIMARY KEY,name TEXT NOT NULL,created_at TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,filename TEXT NOT NULL,sha256 TEXT NOT NULL,content TEXT NOT NULL,char_count INTEGER NOT NULL,created_at TEXT NOT NULL,UNIQUE(workspace_id,sha256));
  CREATE TABLE IF NOT EXISTS chunks(id TEXT PRIMARY KEY,document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,ordinal INTEGER NOT NULL,text TEXT NOT NULL,heading TEXT,start_offset INTEGER,end_offset INTEGER);
  CREATE TABLE IF NOT EXISTS knowledge_items(id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,title TEXT NOT NULL,summary TEXT NOT NULL,keywords_json TEXT NOT NULL,status TEXT NOT NULL,extraction_method TEXT NOT NULL,confidence REAL NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS knowledge_sources(knowledge_id TEXT NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE,chunk_id TEXT NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,quote TEXT NOT NULL,relation TEXT NOT NULL,PRIMARY KEY(knowledge_id,chunk_id));
  CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,text TEXT NOT NULL,due_date TEXT,status TEXT NOT NULL,source_chunk_id TEXT REFERENCES chunks(id) ON DELETE SET NULL);
  CREATE TABLE IF NOT EXISTS memory_entries(id TEXT PRIMARY KEY,workspace_id TEXT REFERENCES workspaces(id) ON DELETE CASCADE,scope TEXT NOT NULL,session_id TEXT,kind TEXT NOT NULL,content_json TEXT NOT NULL,source_ids_json TEXT NOT NULL,confirmed INTEGER NOT NULL,expires_at TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS feedback_events(id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,target_id TEXT NOT NULL,action TEXT NOT NULL,before_json TEXT,after_json TEXT,created_at TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS review_cards(knowledge_id TEXT PRIMARY KEY REFERENCES knowledge_items(id) ON DELETE CASCADE,workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,due_at TEXT NOT NULL,interval_days INTEGER NOT NULL DEFAULT 0,repetitions INTEGER NOT NULL DEFAULT 0,last_result TEXT,updated_at TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS quiz_attempts(id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,knowledge_id TEXT,question TEXT NOT NULL,answer TEXT NOT NULL,is_correct INTEGER NOT NULL,created_at TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS audit_events(id TEXT PRIMARY KEY,workspace_id TEXT,event_type TEXT NOT NULL,detail_json TEXT NOT NULL,created_at TEXT NOT NULL);
  CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(document_id);CREATE INDEX IF NOT EXISTS idx_knowledge_ws ON knowledge_items(workspace_id,status);CREATE INDEX IF NOT EXISTS idx_memory_ws ON memory_entries(workspace_id,scope);
  CREATE INDEX IF NOT EXISTS idx_review_due ON review_cards(workspace_id,due_at);CREATE INDEX IF NOT EXISTS idx_quiz_ws ON quiz_attempts(workspace_id,created_at);
  """)
 def create_workspace(self,name):
  wid=str(uuid.uuid4())
  with self.conn() as c:c.execute("INSERT INTO workspaces VALUES(?,?,?)",(wid,name.strip() or "未命名课程",now()))
  return wid
 def workspaces(self):
  with self.conn() as c:return [dict(r) for r in c.execute("SELECT * FROM workspaces ORDER BY created_at DESC")]
 def add_document(self,wid,filename,text,chunks,candidates,tasks):
  sha=hashlib.sha256(text.encode()).hexdigest();did=str(uuid.uuid4())
  with self.conn() as c:
   row=c.execute("SELECT id FROM documents WHERE workspace_id=? AND sha256=?",(wid,sha)).fetchone()
   if row:return row["id"],False
   c.execute("INSERT INTO documents VALUES(?,?,?,?,?,?,?)",(did,wid,filename,sha,text,len(text),now()))
   for x in chunks:c.execute("INSERT INTO chunks VALUES(?,?,?,?,?,?,?)",(x.id,did,x.ordinal,x.text,x.heading,x.start_offset,x.end_offset))
   for x in candidates:
    c.execute("INSERT INTO knowledge_items VALUES(?,?,?,?,?,?,?,?,?,?)",(x.id,wid,x.title,x.summary,json.dumps(x.keywords,ensure_ascii=False),"candidate",x.extraction_method,x.confidence,now(),now()))
    for cid in x.source_chunk_ids:
     q=next((z.text for z in chunks if z.id==cid),"")[:300];c.execute("INSERT INTO knowledge_sources VALUES(?,?,?,?)",(x.id,cid,q,"primary"))
   for t in tasks:c.execute("INSERT INTO tasks VALUES(?,?,?,?,?,?)",(t["id"],wid,t["text"],t.get("due_date"),"open",t["source_chunk_id"]))
  return did,True
 def knowledge(self,wid,status=None):
  q="SELECT k.*,d.id document_id,d.filename,c.id chunk_id,c.heading,s.quote FROM knowledge_items k LEFT JOIN knowledge_sources s ON s.knowledge_id=k.id LEFT JOIN chunks c ON c.id=s.chunk_id LEFT JOIN documents d ON d.id=c.document_id WHERE k.workspace_id=?";args=[wid]
  if status:q+=" AND k.status=?";args.append(status)
  with self.conn() as c:return [dict(r) for r in c.execute(q+" ORDER BY k.created_at DESC",args)]
 def confirm_knowledge(self,kid,title,summary):
  with self.conn() as c:
   r=c.execute("SELECT workspace_id FROM knowledge_items WHERE id=?",(kid,)).fetchone()
   if not r:return False
   c.execute("UPDATE knowledge_items SET title=?,summary=?,status='confirmed',updated_at=? WHERE id=?",(title,summary,now(),kid))
   c.execute("INSERT OR IGNORE INTO review_cards VALUES(?,?,?,?,?,?,?)",(kid,r["workspace_id"],now(),0,0,None,now()))
   return True
 def chunks(self,wid):
  with self.conn() as c:return [dict(r) for r in c.execute("SELECT c.*,d.workspace_id,d.filename FROM chunks c JOIN documents d ON d.id=c.document_id WHERE d.workspace_id=?",(wid,))]
 def documents(self,wid):
  with self.conn() as c:return [dict(r) for r in c.execute("SELECT id,filename,char_count,created_at FROM documents WHERE workspace_id=? ORDER BY created_at DESC",(wid,))]
 def delete_document(self,wid,did):
  """删除一个课程文件及其孤立知识点、待办和长期记忆引用。"""
  with self.conn() as c:
   row=c.execute("SELECT id FROM documents WHERE id=? AND workspace_id=?",(did,wid)).fetchone()
   if not row:return False
   knowledge_ids={r[0] for r in c.execute("SELECT DISTINCT s.knowledge_id FROM knowledge_sources s JOIN chunks ch ON ch.id=s.chunk_id WHERE ch.document_id=?",(did,))}
   c.execute("DELETE FROM tasks WHERE workspace_id=? AND source_chunk_id IN (SELECT id FROM chunks WHERE document_id=?)",(wid,did))
   c.execute("DELETE FROM documents WHERE id=?",(did,))
   c.execute("DELETE FROM knowledge_items WHERE workspace_id=? AND id NOT IN (SELECT DISTINCT knowledge_id FROM knowledge_sources)",(wid,))
   for memory in c.execute("SELECT id,content_json,source_ids_json FROM memory_entries WHERE workspace_id=? AND scope='long_term'",(wid,)).fetchall():
    try:
     content=json.loads(memory["content_json"]); sources=json.loads(memory["source_ids_json"])
    except (TypeError,json.JSONDecodeError):
     content={}; sources=[]
    if content.get("document_id")==did or content.get("knowledge_id") in knowledge_ids or any(source in knowledge_ids or source==did for source in sources):
     c.execute("DELETE FROM memory_entries WHERE id=?",(memory["id"],))
   return True
 def tasks(self,wid):
  with self.conn() as c:return [dict(r) for r in c.execute("SELECT t.*,d.filename FROM tasks t LEFT JOIN chunks c ON c.id=t.source_chunk_id LEFT JOIN documents d ON d.id=c.document_id WHERE t.workspace_id=?",(wid,))]
 def memory(self,wid,scope=None):
  q="SELECT * FROM memory_entries WHERE workspace_id=?";a=[wid]
  if scope:q+=" AND scope=?";a.append(scope)
  with self.conn() as c:return [dict(r) for r in c.execute(q+" ORDER BY created_at DESC",a)]
 def clear_long_term(self,wid):
  with self.conn() as c:c.execute("DELETE FROM memory_entries WHERE workspace_id=? AND scope='long_term'",(wid,))
 def delete_memory(self,memory_id):
  with self.conn() as c:
   cur=c.execute("DELETE FROM memory_entries WHERE id=? AND scope='long_term'",(memory_id,))
   return cur.rowcount == 1
 def delete_workspace(self,wid):
  with self.conn() as c:c.execute("DELETE FROM workspaces WHERE id=?",(wid,))
 def log_feedback(self,wid,target,action,before=None,after=None):
  with self.conn() as c:c.execute("INSERT INTO feedback_events VALUES(?,?,?,?,?,?,?)",(str(uuid.uuid4()),wid,target,action,json.dumps(before,ensure_ascii=False),json.dumps(after,ensure_ascii=False),now()))
 def review_queue(self,wid,limit=20):
  with self.conn() as c:
   c.execute("INSERT OR IGNORE INTO review_cards(knowledge_id,workspace_id,due_at,interval_days,repetitions,last_result,updated_at) SELECT id,workspace_id,?,0,0,NULL,? FROM knowledge_items WHERE workspace_id=? AND status='confirmed'",(now(),now(),wid))
   return [dict(r) for r in c.execute("SELECT k.*,d.filename,rc.due_at,rc.interval_days,rc.repetitions,rc.last_result FROM review_cards rc JOIN knowledge_items k ON k.id=rc.knowledge_id LEFT JOIN knowledge_sources s ON s.knowledge_id=k.id LEFT JOIN chunks c ON c.id=s.chunk_id LEFT JOIN documents d ON d.id=c.document_id WHERE rc.workspace_id=? AND rc.due_at<=? ORDER BY rc.due_at ASC LIMIT ?",(wid,now(),limit))]
 def grade_review(self,wid,kid,remembered):
  with self.conn() as c:
   row=c.execute("SELECT repetitions,interval_days FROM review_cards WHERE workspace_id=? AND knowledge_id=?",(wid,kid)).fetchone()
   if not row:return False
   reps=int(row["repetitions"]); old=max(1,int(row["interval_days"]))
   if remembered:
    reps+=1; interval=1 if reps==1 else 3 if reps==2 else min(90,round(old*2.2)); result="remembered"
   else: reps=0; interval=1; result="again"
   due=(datetime.now(timezone.utc)+timedelta(days=interval)).isoformat()
   c.execute("UPDATE review_cards SET due_at=?,interval_days=?,repetitions=?,last_result=?,updated_at=? WHERE knowledge_id=?",(due,interval,reps,result,now(),kid))
   return True
 def record_quiz_attempt(self,wid,kid,question,answer,is_correct):
  with self.conn() as c:c.execute("INSERT INTO quiz_attempts VALUES(?,?,?,?,?,?,?)",(str(uuid.uuid4()),wid,kid,question,answer,int(bool(is_correct)),now()))
 def quiz_summary(self,wid):
  with self.conn() as c:
   r=c.execute("SELECT COUNT(*) total,COALESCE(SUM(is_correct),0) correct FROM quiz_attempts WHERE workspace_id=?",(wid,)).fetchone()
   return {"total":r["total"],"correct":r["correct"],"accuracy":round(r["correct"]/r["total"]*100,1) if r["total"] else None}
 def audit(self,wid,event_type,detail):
  with self.conn() as c:c.execute("INSERT INTO audit_events VALUES(?,?,?,?,?)",(str(uuid.uuid4()),wid,event_type,json.dumps(detail,ensure_ascii=False),now()))

