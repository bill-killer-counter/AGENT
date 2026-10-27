import json
from datetime import date
from pathlib import Path

RULES = {"import_document": 10, "confirm_knowledge": 5, "complete_review": 8, "handle_task": 10, "ask_question": 2}
LEVELS = [(0, "资料新手"), (100, "知识整理员"), (300, "课程研究员"), (600, "知识架构师"), (1000, "学习系统设计师")]
BADGES = {
    "first_import": ("初次整理", "第一次把课程资料放进书桌", "📥"),
    "collector": ("资料收藏家", "整理 5 份课程资料", "🗂️"),
    "organizer": ("整理达人", "导入 10 份资料", "📚"),
    "knowledge_10": ("知识确认者", "确认 10 个知识点", "🌱"),
    "source_keeper": ("溯源守护者", "确认 20 个带来源知识点", "🔎"),
    "reviewer": ("温柔复习者", "完成 20 次复习动作", "☕"),
    "quiz_master": ("问卷完成者", "完成 5 份知识问卷", "📝"),
    "questioner": ("好奇提问者", "完成 10 次课程问答", "💬"),
    "explorer": ("课程探索者", "完成 25 次课程问答", "🧭"),
    "streak_3": ("三日相伴", "连续学习 3 天", "🔥"),
    "streak_7": ("一周同行", "连续学习 7 天", "🌈"),
}

class RewardStore:
    def __init__(self, path="data/rewards.json"):
        self.path = Path(path); self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {"enabled": True, "workspaces": {}}

    def _workspace(self, workspace_id):
        return self.data["workspaces"].setdefault(workspace_id, {"points": 0, "events": [], "confirmed": 0, "imports": 0, "reviews": 0, "questions": 0, "streak": 0, "last_activity": None})

    def _save(self): self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")

    def award(self, workspace_id, action, unique_key):
        if not self.data.get("enabled", True): return 0
        ws = self._workspace(workspace_id); event = f"{action}:{unique_key}"
        if event in ws["events"]: return 0
        ws["events"].append(event); ws["points"] += RULES.get(action, 0)
        if action == "confirm_knowledge": ws["confirmed"] += 1
        if action == "import_document": ws["imports"] += 1
        if action == "complete_review": ws["reviews"] += 1
        if action == "ask_question": ws["questions"] += 1
        today = date.today().isoformat()
        if ws.get("last_activity") != today:
            yesterday = date.fromisoformat(ws["last_activity"]) if ws.get("last_activity") else None
            ws["streak"] = ws.get("streak", 0) + 1 if yesterday and (date.today() - yesterday).days == 1 else 1
            ws["last_activity"] = today
        self._save(); return RULES.get(action, 0)

    def achievements(self, workspace_id):
        ws = self._workspace(workspace_id)
        values = {
            "first_import": (min(ws["imports"], 1), 1), "collector": (min(ws["imports"], 5), 5),
            "organizer": (min(ws["imports"], 10), 10), "knowledge_10": (min(ws["confirmed"], 10), 10),
            "source_keeper": (min(ws["confirmed"], 20), 20), "reviewer": (min(ws["reviews"], 20), 20),
            "quiz_master": (min(sum(e.startswith("questionnaire:") for e in ws["events"]), 5), 5),
            "questioner": (min(ws["questions"], 10), 10), "explorer": (min(ws["questions"], 25), 25),
            "streak_3": (min(ws.get("streak", 0), 3), 3), "streak_7": (min(ws.get("streak", 0), 7), 7),
        }
        return [{"id": k, "title": BADGES[k][0], "description": BADGES[k][1], "icon": BADGES[k][2], "current": c, "target": t, "unlocked": c >= t} for k, (c, t) in values.items()]

    def summary(self, workspace_id):
        ws = self._workspace(workspace_id); points = ws["points"]
        level = max((x for x in LEVELS if points >= x[0]), key=lambda x: x[0]); achievements = self.achievements(workspace_id)
        return {"points": points, "level": level[1], "next_level": next((x for x in LEVELS if x[0] > points), None), "badges": [a["title"] for a in achievements if a["unlocked"]], "achievements": achievements, "streak": ws.get("streak", 0), "enabled": self.data.get("enabled", True)}

    def set_enabled(self, enabled): self.data["enabled"] = bool(enabled); self._save()
    def reset(self, workspace_id): self.data["workspaces"].pop(workspace_id, None); self._save()

