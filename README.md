# 课程知识整理 Agent · 公网演示版

本项目使用 Streamlit 运行课程资料整理演示。公开演示入口为 `demo_app.py`；每位访客使用独立的临时课程空间，自动载入三份示例资料。请勿上传隐私或敏感文件，数据可能在会话结束或服务重启后丢失。

本版采用规则抽取和本地检索，默认没有启用联网大语言模型；整理质量页是自动自检，不能视为人工评测或真实幻觉率。详见 DEPLOYMENT.md。

本地启动：`python -m pip install -r requirements.txt`，随后运行 `python -m streamlit run demo_app.py`。
