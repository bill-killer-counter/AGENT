import argparse,json
from pathlib import Path
from .repository import Repository
from .service import CourseAgent
def main():
 p=argparse.ArgumentParser();p.add_argument("--dataset",required=True);p.add_argument("--db",default=None);a=p.parse_args();repo=Repository(a.db);agent=CourseAgent(repo);rows=[json.loads(x) for x in Path(a.dataset).read_text(encoding="utf-8").splitlines() if x.strip()];scored=[]
 for r in rows:
  ws=next((w for w in repo.workspaces() if w["name"]==r["workspace"]),None)
  result=agent.ask(ws["id"],r["question"]) if ws else {"citations":[],"abstained":True}
  expected=set(r.get("expected_chunk_ids",[]));actual={c["chunk_id"] for c in result["citations"]};scored.append({"id":r["id"],"expected":sorted(expected),"actual":sorted(actual),"abstained":result["abstained"],"hit":bool(expected&actual) if expected else None})
 report={"dataset":a.dataset,"n":len(rows),"results":scored,"note":"小样本脚本输出检索命中明细；空标签占位数据不构成性能结果。"};print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
