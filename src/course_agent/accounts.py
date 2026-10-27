import hashlib
import json
import os
from pathlib import Path

class AccountStore:
    def __init__(self, path="data/accounts.json"):
        self.path = Path(path); self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {"accounts": {}}
    def _save(self): self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
    def _hash(self, password, salt=None):
        salt = salt or os.urandom(16).hex()
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 200_000).hex()
        return f"pbkdf2_sha256${salt}${digest}"
    def _verify(self, password, stored):
        if stored.startswith("pbkdf2_sha256$"):
            _, salt, expected = stored.split("$", 2)
            return self._hash(password, salt).split("$", 2)[2] == expected
        # 兼容早期本地演示账户；登录成功后立即升级散列格式。
        return hashlib.sha256(password.encode("utf-8")).hexdigest() == stored
    def login_or_create(self, username, password, default_workspace_id):
        username = username.strip()
        if not username or not password.strip(): raise ValueError("账号和密码不能为空")
        accounts = self.data["accounts"]
        if username in accounts:
            if not self._verify(password, accounts[username]["password_hash"]): raise ValueError("密码不正确")
            if not accounts[username]["password_hash"].startswith("pbkdf2_sha256$"):
                accounts[username]["password_hash"] = self._hash(password); self._save()
        else:
            accounts[username] = {"password_hash": self._hash(password), "workspace_id": default_workspace_id}
            self._save()
        return accounts[username]["workspace_id"]
    def workspace_id(self, username):
        item = self.data["accounts"].get(username)
        return item.get("workspace_id") if item else None
