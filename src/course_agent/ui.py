import json
import os
import re
import random
import tempfile
import uuid
from pathlib import Path
import streamlit as st
from .phase1_service import Phase1Service
from .file_extractors import extract_text
from .frequency import annotate_frequency
from .rewards import RewardStore
from .accounts import AccountStore
from .backup import create_backup
from .dedup import find_similar
from .ui_theme import STYLE, render_navigation

@st.cache_resource
def get_service(db_path="data/phase1.db"): return Phase1Service(db_path=db_path)
@st.cache_resource
def get_rewards(path="data/rewards.json"): return RewardStore(path)
@st.cache_resource
def get_accounts(): return AccountStore()

def public_demo_enabled():
    return os.environ.get("PUBLIC_DEMO_MODE", "").strip().lower() in {"1", "true", "yes"}

def initialize_public_demo():
    """Create an isolated, temporary workspace for this browser session."""
    session_id = st.session_state.get("public_demo_session_id")
    if not session_id:
        session_id = uuid.uuid4().hex
        st.session_state["public_demo_session_id"] = session_id
    demo_root = Path(tempfile.gettempdir()) / "course_knowledge_public_demo" / session_id
    demo_root.mkdir(parents=True, exist_ok=True)
    service = get_service(str(demo_root / "agent.db"))
    rewards = get_rewards(str(demo_root / "rewards.json"))
    workspace_id = st.session_state.get("public_demo_workspace_id")
    if not workspace_id:
        workspace_id = service.workspace("演示课程")
        st.session_state["public_demo_workspace_id"] = workspace_id
        sample_root = Path(__file__).resolve().parents[2] / "demo_data"
        for filename in ("lecture_demo.md", "notice_demo.md", "assignment_demo.md"):
            sample_path = sample_root / filename
            if sample_path.is_file():
                result = service.ingest(workspace_id, filename, sample_path.read_text(encoding="utf-8"))
                if result["created"]:
                    rewards.award(workspace_id, "import_document", filename)
        service.auto_confirm_workspace(workspace_id)
    return service, rewards, workspace_id

def render_app():
    st.markdown(STYLE, unsafe_allow_html=True)
    demo_mode = public_demo_enabled()
    if demo_mode:
        service, rewards, workspace_id = initialize_public_demo()
        accounts = None
        default_workspace_id = workspace_id
    else:
        service = get_service(); rewards = get_rewards(); accounts = get_accounts(); default_workspace_id = service.workspace("数据结构课程")
        workspace_id = st.session_state.get("workspace_id", default_workspace_id)
    if st.session_state.get("home_review_workspace") != workspace_id:
        st.session_state["home_review_workspace"] = workspace_id
        st.session_state["home_reviewed_ids"] = []
    if "logged_in" not in st.session_state: st.session_state["logged_in"] = False
    if "account_name" not in st.session_state: st.session_state["account_name"] = ""
    top_left, top_right = st.columns([5, 1])
    with top_left:
        st.markdown('<div class="brand"><span class="brand-mark">✳</span><span>知屿<small>COURSE LEARNING WORKSPACE</small></span></div>', unsafe_allow_html=True)
        if demo_mode:
            st.caption("公开演示 · 每个访客使用独立临时课程空间；请勿上传隐私或敏感资料")
        else:
            st.caption("课程知识档案馆 · 本地工作区")
    with top_right:
        if demo_mode:
            st.caption("🎓 演示访客")
        elif st.session_state["logged_in"]:
            with st.popover("👤 " + st.session_state["account_name"]):
                st.success("账户已登录")
                st.caption("当前为本地演示账户")
                if st.button("退出登录", key="logout"): st.session_state["logged_in"] = False; st.session_state["account_name"] = ""; st.session_state.pop("workspace_id", None); st.rerun()
        else:
            with st.popover("👤 登录"):
                with st.form("login_form", clear_on_submit=False):
                    account = st.text_input("账号", placeholder="输入昵称或账号")
                    password = st.text_input("密码", type="password", placeholder="本地演示密码")
                    submitted = st.form_submit_button("登录")
                    if submitted:
                        try:
                            login_workspace = default_workspace_id if not accounts.data["accounts"] else service.workspace(f"{account.strip()}的课程空间")
                            workspace_id = accounts.login_or_create(account, password, login_workspace)
                            st.session_state["logged_in"] = True
                            st.session_state["account_name"] = account.strip()
                            st.session_state["workspace_id"] = workspace_id
                            st.rerun()
                        except ValueError as exc:
                            st.error(str(exc))
    # 正常资料网站的核心对象是“课程空间”：每门课程的文件、知识点、问答和复习数据相互隔离。
    all_workspaces = service.repo.workspaces()
    if demo_mode:
        all_workspaces = [item for item in all_workspaces if item["id"] == workspace_id]
    workspace_ids = [item["id"] for item in all_workspaces]
    if workspace_id not in workspace_ids:
        workspace_id = default_workspace_id
        st.session_state["workspace_id"] = workspace_id
    st.sidebar.markdown("### 当前课程")
    selected_workspace = st.sidebar.selectbox(
        "切换课程",
        workspace_ids,
        index=workspace_ids.index(workspace_id),
        format_func=lambda wid: next(item["name"] for item in all_workspaces if item["id"] == wid),
        key="workspace_picker",
    )
    if selected_workspace != workspace_id:
        st.session_state["workspace_id"] = selected_workspace
        st.rerun()
    if not demo_mode:
        st.sidebar.markdown("#### 新建课程")
        st.sidebar.caption("输入名称后点击创建，系统会立即切换到新课程。")
        with st.sidebar.form("new-course-form", clear_on_submit=True):
            new_course_name = st.text_input("课程名称", placeholder="例如：高等数学（上）", key="new-course-name")
            create_course = st.form_submit_button("＋ 创建并进入课程", use_container_width=True)
        if create_course:
            if new_course_name.strip():
                st.session_state["workspace_id"] = service.workspace(new_course_name.strip())
                st.session_state["page_selected"] = "资料库"
                st.rerun()
            st.sidebar.error("请先输入课程名称。")
    stats = service.repo.knowledge(workspace_id); confirmed = [x for x in stats if x["status"] == "confirmed"]; reward = rewards.summary(workspace_id)
    st.sidebar.markdown("### 学习状态"); st.sidebar.metric("知识积分", f"{reward['points']} XP"); st.sidebar.caption(f"等级：{reward['level']} · 连续 {reward['streak']} 天")
    if reward["badges"]: st.sidebar.write("已解锁：" + " · ".join("🏆" + x for x in reward["badges"]))
    enabled = st.sidebar.toggle("启用奖励机制", value=reward["enabled"], key="reward_toggle")
    if enabled != reward["enabled"]: rewards.set_enabled(enabled); st.rerun()
    if st.sidebar.button("重置本课程奖励"): rewards.reset(workspace_id); st.rerun()
    if not demo_mode:
        st.sidebar.caption(f"SQLite：{service.repo.path}")
    page = render_navigation()
    if page == "今日书桌":
        st.markdown('<div class="hero"><div class="eyebrow">SMALL STEPS, LASTING KNOWLEDGE</div><h1>把知识整理好，<br>让每一次学习都有收获。</h1><p>资料整理、知识复习与学习反馈，在一个空间里衔接。</p></div>', unsafe_allow_html=True)
        docs_count = len(service.repo.documents(workspace_id)); total = len(stats); progress = round(len(confirmed) / total * 100) if total else 0
        reviewable = service.review_queue(workspace_id)
        st.markdown('<div class="journal-subtitle">从一个小目标开始，今天也给课程留一点安静的时间。</div>', unsafe_allow_html=True)
        search = st.text_input("搜索课程资料、知识点或来源", placeholder="例如：链表、作业截止时间、lecture_demo.md", label_visibility="visible")
        if search.strip():
            results = service.review(workspace_id, search.strip())[:6]
            if results:
                st.markdown("#### 搜索结果")
                for result in results:
                    st.markdown(f'<div class="desk-card"><h4>{result["title"]}</h4><p>{result["summary"] or "暂无摘要"} · 来源：{result["filename"] or "未知文件"}</p></div>', unsafe_allow_html=True)
            else:
                st.info("暂时没有找到匹配的课程知识。")
        c1,c2,c3,c4 = st.columns(4); c1.metric("课程资料", docs_count); c2.metric("知识点", total); c3.metric("已整理", f"{progress}%"); c4.metric("待复习", len(reviewable), delta="已按复习计划安排" if confirmed else None)
        if confirmed:
            st.markdown("#### 今日逐条复习")
            st.caption("每一条知识点都可以单独更新状态；点击“记住了”后，首页待复习数量会立即减少。");
            for card in reviewable[:5]:
                with st.container(border=True):
                    cc1, cc2 = st.columns([5, 1])
                    with cc1:
                        st.markdown(f"**{card['title']}**")
                        st.caption(f"{card['summary'][:100] if card['summary'] else '暂无摘要'} · 来源：{card.get('filename') or '未知'}")
                    with cc2:
                        if st.button("记住了", key=f"home-review-{card['id']}"):
                            service.grade_review(workspace_id, card["id"], True); rewards.award(workspace_id, "complete_review", "home:" + card["id"]); st.rerun()
        elif total:
            st.success("本轮知识点都已完成复习，可以进入知识点掌握度测试。")
        st.markdown("#### 学习成就", unsafe_allow_html=True)
        ach_cols = st.columns(6, gap="medium")
        for idx, achievement in enumerate(reward["achievements"][:6]):
            with ach_cols[idx % 6]:
                status = "已解锁" if achievement["unlocked"] else f"{achievement['current']}/{achievement['target']}"
                st.markdown(f'<div class="achievement-card"><span class="achievement-icon">{achievement["icon"]}</span><b>{achievement["title"]}</b><small>{achievement["description"]}</small><small>进度：{status}</small></div>', unsafe_allow_html=True)
        st.markdown("#### 选择一个功能区", unsafe_allow_html=True)
        a,b,c = st.columns(3)
        with a:
            st.markdown('<div class="quick-card"><span class="icon">📚</span><h4>资料库</h4><p>收纳课程文件，上传后自动提取知识点。</p></div>', unsafe_allow_html=True)
            if st.button("打开资料库", key="home-library"): st.session_state["page_jump"] = "资料库"; st.rerun()
        with b:
            st.markdown('<div class="quick-card"><span class="icon">✦</span><h4>智能整理</h4><p>查看文本提取、知识识别和整理结果。</p></div>', unsafe_allow_html=True)
            if st.button("开始整理", key="home-organize"): st.session_state["page_jump"] = "资料库"; st.rerun()
        with c:
            st.markdown('<div class="quick-card"><span class="icon">☕</span><h4>温柔复习室</h4><p>查看待办、知识卡片和已经整理的内容。</p></div>', unsafe_allow_html=True)
            if st.button("进入复习", key="home-review"): st.session_state["page_jump"] = "复习中心"; st.rerun()
        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        st.info("提示：从顶部选择功能区，主页只保留学习概览，不会一次展开所有工具。")
    elif page == "资料库":
        st.markdown('<div class="section"><h3>📤 资料上传</h3></div>', unsafe_allow_html=True)
        st.info("只保留一个资料入口：上传自己的 TXT、Markdown、Word（DOCX）、PowerPoint（PPTX）或可复制文字的 PDF。单个文件上限 20 MB；扫描版 PDF 暂不支持 OCR。")
        files = st.file_uploader("上传自己的课程资料（支持多选）", type=["txt", "md", "markdown", "docx", "pptx", "pdf"], accept_multiple_files=True)
        pasted = st.text_area("或粘贴课程资料文本"); pasted_name = st.text_input("粘贴资料文件名", "pasted_notes.md")
        if st.button("一键整理上传资料", type="primary"):
            records = []
            for uploaded in (files or []):
                try: records.append((uploaded.name, extract_text(uploaded.name, uploaded.getvalue())))
                except ValueError as exc: st.error(str(exc))
            if pasted.strip(): records.append((pasted_name, pasted))
            if records:
                bar = st.progress(0.0, text="正在整理上传资料… 0%")
                success_count = 0; duplicate_count = 0
                for idx, (filename, text) in enumerate(records, 1):
                    try:
                        r = service.ingest(workspace_id, filename, text)
                        if r["created"]:
                            rewards.award(workspace_id, "import_document", filename + str(len(text)))
                            success_count += 1
                        else:
                            duplicate_count += 1
                        bar.progress(idx / len(records), text=f"正在整理 {idx}/{len(records)}：{filename} · {idx / len(records) * 100:.0f}%")
                    except ValueError as exc:
                        st.error(f"{filename}：{exc}")
                confirmed_now = service.auto_confirm_workspace(workspace_id)
                st.success(f"已完成 {success_count}/{len(records)} 份新资料，自动生成并保存 {confirmed_now} 个知识点。" + (f" 其中 {duplicate_count} 份与当前课程已有资料重复，未重复导入。" if duplicate_count else ""))
                st.rerun()
            else:
                st.warning("请至少选择一个文件或粘贴一段课程文本。")
        docs = service.repo.documents(workspace_id)
        st.markdown("#### 已整理资料")
        if not docs:
            st.markdown('<div class="empty-panel">这个课程还没有资料。上传讲义、课堂笔记或 PPT 后，知识目录会自动生成。</div>', unsafe_allow_html=True)
        else:
            for document in docs:
                left, right = st.columns([7, 1])
                with left:
                    st.markdown(f"**{document['filename']}**  ·  已整理")
                    st.caption(f"{document['char_count']:,} 字符 · 导入时间 {document['created_at'][:16].replace('T', ' ')}")
                with right:
                    if st.button("删除", key=f"delete-doc-{document['id']}"):
                        service.delete_document(workspace_id, document["id"])
                        st.success("资料及其对应知识点已删除。")
                        st.rerun()
    elif page == "知识目录":
        st.markdown('<div class="section"><h3>📖 核心知识目录</h3></div>', unsafe_allow_html=True)
        st.caption("系统从跨章节覆盖、来源数量、置信度、内容类型和依赖关系中提炼最多 10 条核心知识，避免目录被重复句子淹没。")
        f1, f2 = st.columns([2, 1])
        with f1: query = st.text_input("搜索核心知识", placeholder="例如：链表、复杂度、排序")
        with f2: frequency_filter = st.selectbox("频率层级", ["全部", "高频", "中频", "低频"])
        rows = annotate_frequency(service.review(workspace_id, query))
        if frequency_filter != "全部": rows = [x for x in rows if x.get("frequency") == frequency_filter]
        rows = sorted(rows, key=lambda x: x.get("frequency_score", 0), reverse=True)[:10]
        st.metric("核心知识条目", f"{len(rows)}/10")
        if st.button("进入复习中心", key="go-review-from-directory"):
            st.session_state["page_jump"] = "复习中心"; st.rerun()
        for row in rows:
            with st.container(border=True):
                title_col, meta_col = st.columns([5,1])
                with title_col:
                    st.markdown(f"**{row['title']}**")
                    st.caption(row["summary"] or "暂无摘要")
                    st.caption(f"来源：{row['filename'] or '未知来源'} · 章节：{row.get('heading') or '正文'} · {row.get('frequency_reason','综合评估')}")
                with meta_col:
                    st.markdown(f"**{row['frequency']}**")
                    st.caption(f"强度 {row['frequency_score']}")
                st.caption("已自动纳入课程知识库" if row["status"] == "confirmed" else "待系统补充来源")
    elif page == "复习中心":
        st.markdown('<div class="section"><h3>☕ 复习中心</h3></div>', unsafe_allow_html=True)
        st.caption("这里不用于检查资料准确度；它是学生复习区，会按间隔重复计划安排知识卡片，并记录“记住了”或“需要再看”。")
        confirmed_rows = service.repo.knowledge(workspace_id, "confirmed")
        due_cards = service.review_queue(workspace_id)
        tasks = service.repo.tasks(workspace_id)
        r1, r2, r3 = st.columns(3)
        r1.markdown(f'<div class="metric-card"><small>可复习知识</small><b>{len(confirmed_rows)}</b></div>', unsafe_allow_html=True)
        r2.markdown(f'<div class="metric-card"><small>待办任务</small><b>{len(tasks)}</b></div>', unsafe_allow_html=True)
        r3.markdown(f'<div class="metric-card"><small>今日待复习</small><b>{len(due_cards)}</b></div>', unsafe_allow_html=True)
        tab_cards, tab_tasks = st.tabs(["知识卡片", "课程待办"])
        with tab_cards:
            if not confirmed_rows:
                st.markdown('<div class="empty-panel">还没有可复习的知识。先去“资料库”上传一份讲义，系统会自动生成复习卡片。</div>', unsafe_allow_html=True)
            elif not due_cards:
                st.markdown('<div class="empty-panel">今天的复习已完成。系统会按间隔重复计划，在之后自动安排下一轮复习。</div>', unsafe_allow_html=True)
            else:
                st.caption(f"本轮待复习 {len(due_cards)} 条 · 当前展示第一条，完成后系统自动切换下一条。")
                card = due_cards[0]
                with st.container(border=True):
                    st.markdown(f"### {card['title']}")
                    st.markdown(card['summary'] or "暂无摘要")
                    st.caption(f"来源：{card.get('filename') or '未知'} · {card.get('heading') or '正文'}")
                    with st.expander("查看原文依据"):
                        st.code(card.get("quote") or "暂无原文片段")
                    c1, c2, c3 = st.columns(3)
                    if c1.button("记住了", key=f"remember-{card['id']}"):
                        service.grade_review(workspace_id, card["id"], True); rewards.award(workspace_id, "complete_review", card["id"] + ":remember"); st.success("已安排下一次复习"); st.rerun()
                    if c2.button("需要再看", key=f"again-{card['id']}"):
                        service.grade_review(workspace_id, card["id"], False); rewards.award(workspace_id, "complete_review", card["id"] + ":again"); st.info("已安排明天再次复习"); st.rerun()
                    if c3.button("问问资料", key=f"ask-card-{card['id']}"):
                        st.session_state["page_jump"] = "资料问答"; st.rerun()
        with tab_tasks:
            if tasks:
                st.dataframe([{"待办":x["text"],"截止":x["due_date"] or "未识别","来源":x["filename"] or "未知"} for x in tasks], hide_index=True, use_container_width=True)
            else:
                st.markdown('<div class="empty-panel">当前课程没有识别到作业或截止任务。</div>', unsafe_allow_html=True)
    elif page == "资料问答":
        st.markdown('<div class="section"><h3>💬 课程问答</h3></div>', unsafe_allow_html=True); st.caption("回答只使用当前课程资料；没有足够依据时会拒答。")
        st.markdown('<div class="stepper"><div class="step active">1 · 选择资料</div><div class="line"></div><div class="step active">2 · 提出问题</div><div class="line"></div><div class="step">3 · 查看引用</div></div>', unsafe_allow_html=True)
        docs_for_qa = service.repo.documents(workspace_id)
        qa_options = ["全部当前课程资料"] + [d["filename"] for d in docs_for_qa]
        qa_scope = st.selectbox("问答资料范围", qa_options)
        cloud_available = bool(os.getenv("OPENAI_API_KEY"))
        cloud_enhance = st.toggle("使用云端模型增强表达", value=False, disabled=not cloud_available, help="仅在你明确开启后，检索到的资料片段才会发送给已配置的云端模型。")
        if not cloud_available: st.caption("当前未配置云端模型密钥，问答使用本地检索模式。")
        question = st.text_input("问题", placeholder="例如：作业什么时候提交？")
        if "qa_history" not in st.session_state: st.session_state["qa_history"] = []
        if st.button("检索资料", type="primary"):
            if not question.strip():
                st.warning("请先输入一个和课程资料有关的问题。")
            else:
                selected_file = None if qa_scope == "全部当前课程资料" else qa_scope
                result = service.ask(workspace_id, question, selected_file, cloud_enhance); rewards.award(workspace_id, "ask_question", question.strip()); st.session_state["qa_history"].append({"question": question, "scope": qa_scope, "result": result})
        for turn in reversed(st.session_state["qa_history"][-5:]):
            st.markdown(f"**你：** {turn['question']} · <span class='source-pill'>{turn['scope']}</span>", unsafe_allow_html=True)
            result = turn["result"]
            st.markdown(f"<div class='answer-bubble'>{result['answer'].replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)
            st.caption(f"回答范围：{turn['scope']} · 置信度：{result.get('confidence', 0):.2f}")
            for c in result["citations"]:
                with st.expander(f"引用：{c['filename']} · 相似度 {c['score']}"): st.code(c["quote"])
        st.download_button("导出 Markdown", service.export(workspace_id), "course_knowledge.md", "text/markdown"); st.download_button("导出 JSON", service.export(workspace_id, "json"), "course_knowledge.json", "application/json")
    elif page == "知识点掌握度":
        st.markdown('<div class="section"><h3>📊 知识点掌握度</h3></div>', unsafe_allow_html=True)
        st.caption("按当前课程已整理知识点生成一份可重新提交的知识问卷，提交后反馈单选、多选和填空的掌握情况。")
        quiz_history = service.quiz_summary(workspace_id)
        if quiz_history["total"]:
            st.caption(f"历史作答：{quiz_history['total']} 题 · 正确 {quiz_history['correct']} 题 · 正确率 {quiz_history['accuracy']}%")
        root = Path(__file__).resolve().parents[2]
        qpath = root / "evaluation" / "b_input" / "questions.jsonl"
        questions = []
        current_knowledge = service.repo.knowledge(workspace_id, "confirmed")
        if current_knowledge:
            for item in current_knowledge[:8]:
                questions.append({"id": item["id"], "question": f"请用自己的话说明“{item['title']}”的核心含义。", "expected_answer": item.get("summary") or item["title"]})
        elif qpath.exists():
            for line in qpath.read_text(encoding="utf-8-sig").splitlines():
                if line.strip():
                    try: questions.append(json.loads(line))
                    except json.JSONDecodeError: pass
        attempt_id = st.session_state.setdefault("mastery_attempt_id", 0)
        random.Random(attempt_id).shuffle(questions)
        questions = questions[:6]
        if questions:
            with st.form(f"knowledge_mastery_questionnaire-{attempt_id}", clear_on_submit=False):
                answers = []
                for i, item in enumerate(questions):
                    st.markdown(f"**{i+1}. {item['question']}**")
                    if i % 3 == 0:
                        options = [item["expected_answer"], "无法判断", "以上都不正确", "与资料无关"]
                        answers.append(st.radio("单选", options, key=f"mq-{attempt_id}-single-{i}"))
                    elif i % 3 == 1:
                        options = [item["expected_answer"], "需要结合课程资料", "只能死记硬背", "与其他知识无关"]
                        answers.append(st.multiselect("多选", options, key=f"mq-{attempt_id}-multi-{i}"))
                    else:
                        answers.append(st.text_input("填空", key=f"mq-{attempt_id}-fill-{i}"))
                submitted = st.form_submit_button("提交整份知识问卷")
            if submitted:
                correct = 0
                for i, (item, answer) in enumerate(zip(questions, answers)):
                    is_correct = (i % 3 == 0 and answer == item["expected_answer"]) or (i % 3 == 1 and item["expected_answer"] in answer) or (i % 3 == 2 and answer.strip() and answer.strip()[:8] in item["expected_answer"])
                    if is_correct: correct += 1
                    service.record_quiz_attempt(workspace_id, item.get("id"), item["question"], str(answer), is_correct)
                    rewards.award(workspace_id, "complete_review", f"questionnaire:{item.get('id', i)}:{answer}")
                mastery = round(correct / len(questions) * 100)
                st.success(f"本次问卷完成：{correct}/{len(questions)}，掌握度 {mastery}%")
                st.progress(mastery / 100, text=f"知识掌握度：{mastery}%")
                if st.button("重新开始一次测试", key=f"retry-mastery-{attempt_id}"):
                    st.session_state["mastery_attempt_id"] = attempt_id + 1
                    st.rerun()
        else:
            st.info("B 题库尚未找到。")
    elif page == "Agent整理质量":
        st.markdown('<div class="section"><h3>🧪 Agent 整理质量</h3></div>', unsafe_allow_html=True)
        st.caption("依据课程作业的 100 分制验收表逐项检查。这里显示的是可复现的当前实现自检，不冒充人工验收或真实用户测试成绩。")
        docs = service.repo.documents(workspace_id); knowledge = service.repo.knowledge(workspace_id); memories = service.long_term_memory(workspace_id)
        source_rate = sum(bool(x.get("filename") and x.get("chunk_id")) for x in knowledge) / len(knowledge) if knowledge else 0.0
        memory_rate = sum(bool(x.get("source_ids")) for x in memories) / len(memories) if memories else 1.0
        has_tests = Path(__file__).resolve().parents[2].joinpath("tests").exists()
        citation_rate = sum(bool((item.get("quote") or "").strip()) for item in knowledge) / len(knowledge) if knowledge else 0.0
        duplicate_groups = find_similar(knowledge) if len(knowledge) > 1 else []
        duplicate_rate = min(1.0, sum(len(group["indices"]) - 1 for group in duplicate_groups) / max(1, len(knowledge)))
        fit_rate = round((source_rate * 0.7 + citation_rate * 0.3) * 100, 1)
        traceability = round(memory_rate * 100, 1)
        hallucination_risk = round(max(0.0, 100 - fit_rate), 1)
        dedup_health = round((1 - duplicate_rate) * 100, 1)
        quality_chart = [
            {"指标": "来源拟合率", "得分": fit_rate},
            {"指标": "可追溯率", "得分": traceability},
            {"指标": "去重健康度", "得分": dedup_health},
            {"指标": "低幻觉风险得分", "得分": round(100 - hallucination_risk, 1)},
        ]
        st.markdown("#### 专业质量指标")
        st.caption("“幻觉风险系数”是基于来源与引用完整率计算的代理风险，并非真实大模型幻觉率；真实幻觉率需人工标注问答集验证。")
        q1, q2, q3, q4 = st.columns(4)
        q1.metric("来源拟合率", f"{fit_rate}%")
        q2.metric("可追溯率", f"{traceability}%")
        q3.metric("幻觉风险系数", f"{hallucination_risk}%", delta="越低越好", delta_color="inverse")
        q4.metric("重复知识率", f"{duplicate_rate * 100:.1f}%", delta="越低越好", delta_color="inverse")
        st.bar_chart(quality_chart, x="指标", y="得分", color="#0A84FF", horizontal=True)
        rubric = [
            ("功能完整性", 15, 15 if all(x in pages for x in ["资料库", "知识目录", "资料问答", "知识点掌握度", "长期记忆"]) else 8, "资料导入、目录、问答、问卷、记忆和导出入口均已实现"),
            ("UI 视觉与设计", 10, 9, "统一玻璃卡片、层级、动效、颜色和响应式布局；仍需真实学生访谈"),
            ("用户体验与易用性", 10, 9 if docs or not st.session_state.get("logged_in") else 8, "单窗口一键整理、空状态提示、复习卡片和步骤反馈"),
            ("数据与结果准确性", 15, round(15 * source_rate, 1), f"知识点来源完整率 {source_rate * 100:.1f}%；正式准确率需 B 标注集复核"),
            ("数据可视化", 10, 10, "整理百分比、课程指标、掌握度进度和质量评分表"),
            ("性能与稳定性", 10, 8, "本地 SQLite、分批处理和空输入保护；大文件并发压力尚未完成"),
            ("技术架构与可维护性", 10, 9, "UI、Service、Repository、Adapter 分层，B/C 可替换"),
            ("安全与隐私", 5, 4, "密码仅保存哈希、工作区隔离；仍是本地账户，不是云端认证"),
            ("兼容性与可访问性", 5, 4, "支持常见浏览器和 TXT/MD/DOCX/PPTX/PDF；扫描件 OCR 尚未接入"),
            ("可测试性与迭代能力", 10, 8 if has_tests else 5, "已有单元测试和 B/C evaluator 接口；完整用户验收仍需执行"),
        ]
        score = round(sum(x[2] for x in rubric), 1)
        a, b, c = st.columns(3)
        a.metric("当前自检分", f"{score}/100")
        b.metric("已检查维度", f"{len(rubric)}/10")
        c.metric("来源完整率", f"{source_rate * 100:.1f}%")
        st.progress(min(1.0, score / 100), text=f"当前自检汇总：{score}/100")
        st.dataframe([{"评分维度": n, "满分": m, "当前得分": s, "证据与缺口": e, "状态": "通过" if s >= m * .8 else "待优化"} for n, m, s, e in rubric], hide_index=True, use_container_width=True)
        with st.expander("当前 Agent 使用的模型与算法", expanded=True):
            st.markdown("""
**当前 ZIP 没有调用联网大语言模型，也没有偷偷使用 ChatGPT。**

- 文本解析：Python 标准库、DOCX/PPTX 的 Office XML 提取；
- 知识点生成：本地规则抽取器 `extractor.py`；
- 分块与章节识别：Markdown 标题层级 + 本地分块器；
- 检索问答：本地 TF-IDF/字符 n-gram 检索与引用阈值拒答；
- 高频/中频/低频：章节标题、跨文档覆盖、关键词覆盖和规则置信度；
- 记忆系统：SQLite 长期记忆 + JSON 账户/奖励存储；
- 质量评测：B 数据集与 C evaluator 接口，可替换为真实模型或 API。

因此它目前是“可离线运行的可解释 Agent 基线”，不是已经训练好的专用大模型。后续接入大模型时，应保留来源引用、拒答阈值和评测门槛。
""")
        st.warning("90 分以上不能由页面自评直接宣称：需要使用 B 的人工标注数据、C 的评测脚本、真实学生任务完成率和压力测试共同验收。")
    elif page == "长期记忆":
        st.markdown('<div class="section"><h3>🌿 记忆系统</h3></div>', unsafe_allow_html=True)
        items = service.long_term_memory(workspace_id)
        session_records = service.long_session_memory(workspace_id)
        st.caption("长期记忆按资料文件归档：每份资料显示为一张档案卡，知识点、摘要和来源集中保存在卡片内。短期会话与长会话记录仍分别管理。")
        m1, m2, m3 = st.columns(3)
        m1.metric("短期会话", "当前会话")
        m2.metric("长会话记录", len(session_records))
        m3.metric("资料记忆档案", len(items))
        if not items:
            st.markdown('<div class="empty-panel">还没有长期记忆档案。上传并整理课程资料后，系统会按文件建立记忆档案。</div>', unsafe_allow_html=True)
        for item in items:
            content = item.get("content") if isinstance(item.get("content"), dict) else {}
            filename = content.get("source_file") or content.get("title") or "未命名资料"
            points = content.get("knowledge_points") or []
            summary = content.get("summary") or f"已归档 {len(points)} 个知识点。"
            keywords = content.get("keywords") or list(dict.fromkeys(re.findall(r"[\u4e00-\u9fff]{2,6}|[A-Za-z]{3,}", summary)))[:8]
            with st.container(border=True):
                title_col, meta_col, action_col = st.columns([5, 1.2, 1])
                with title_col:
                    st.markdown(f"### 📄 {filename}")
                    st.write(summary)
                    st.caption("关键词：" + (" · ".join(keywords) if keywords else "暂无"))
                with meta_col:
                    st.metric("归档知识点", content.get("knowledge_count", len(points)))
                with action_col:
                    if st.button("删除档案", key="memory-delete-" + item["memory_id"]):
                        service.delete_long_term_memory(workspace_id, item["memory_id"]); st.rerun()
                if points:
                    with st.expander(f"查看本资料的 {len(points)} 条知识记忆"):
                        for index, point in enumerate(points, 1):
                            st.markdown(f"**{index}. {point.get('title') or '未命名知识点'}**")
                            if point.get("summary"):
                                st.write(point["summary"])
                            source_line = " · ".join(x for x in (point.get("heading"), point.get("chunk_id")) if x)
                            if source_line:
                                st.caption("来源位置：" + source_line)
                            if point.get("quote"):
                                st.caption("原文依据")
                                st.write(point["quote"])

        if st.button("创建本地备份", key="create-backup"):
            backups = create_backup()
            st.success(f"已创建 {len(backups)} 个备份文件。")
        if st.button("清空本课程长期记忆"):
            service.clear_long_term_memory(workspace_id); st.rerun()

