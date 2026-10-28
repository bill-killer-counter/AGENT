"""Minimal green workspace theme and native, keyboard-accessible navigation."""
import streamlit as st

NAVIGATION = [
    ("今日书桌", "学习概览", "space_dashboard", "查看资料、整理进度与今日复习"),
    ("资料库", "资料上传", "upload_file", "上传课件并一键整理"),
    ("知识目录", "知识目录", "account_tree", "查看重点知识与来源"),
    ("复习中心", "复习中心", "style", "使用知识卡片安排复习"),
    ("资料问答", "资料问答", "forum", "围绕课程资料提问"),
    ("知识点掌握度", "掌握度测试", "quiz", "完成问卷并查看反馈"),
    ("Agent整理质量", "可靠度分析", "analytics", "查看整理质量与证据"),
    ("长期记忆", "长期记忆", "inventory_2", "按来源文件管理知识档案"),
]

STYLE = """<style>
:root{--ink:#173f36;--muted:#6d8279;--green:#28644f;--line:#e0e7e0;--surface:#f5f6f1}
[data-testid="stAppViewContainer"]{background:var(--surface);color:var(--ink)}
[data-testid="stHeader"]{background:transparent}
.block-container{max-width:1480px;padding:2rem 2.5rem 4rem}
h1,h2,h3,h4{color:var(--ink);letter-spacing:-.025em;font-family:Arial,'Microsoft YaHei',sans-serif!important}
.brand{display:flex;align-items:center;gap:12px;font-weight:750;font-size:1.6rem;color:var(--ink);line-height:1.3}
.brand-mark{background:#173f36;color:#e6eee1;border-radius:13px;padding:8px 13px;font-size:1.5rem}
.brand small{display:block;font-size:.68rem;letter-spacing:.15em;color:var(--muted);font-weight:500;margin-top:4px}
.st-key-top_navigation{background:#fff;border:1px solid var(--line);border-radius:18px;padding:12px 14px;margin:6px 0 22px;box-shadow:0 4px 18px #173f3605}
.st-key-top_navigation [data-testid="stHorizontalBlock"]{gap:8px}
.st-key-top_navigation button{min-height:76px!important;flex-direction:column!important;gap:7px!important;padding:10px 3px!important;border-radius:12px!important;font-size:.82rem!important;white-space:nowrap;box-shadow:none!important}
.st-key-top_navigation button [data-testid="stIconMaterial"]{font-size:24px!important}
.st-key-top_navigation button>div{width:100%}
.st-key-top_navigation button>div>span{display:flex!important;flex-direction:column!important;align-items:center;justify-content:center;gap:7px;width:100%}
.st-key-top_navigation [data-testid="stMarkdownContainer"]{overflow:visible!important;white-space:normal!important}
.st-key-top_navigation button[kind="secondary"]{border:1px solid transparent!important;background:#fff!important;color:#60796c!important}
.st-key-top_navigation button[kind="secondary"]:hover{background:#edf3e9!important;border-color:#d9e5d4!important;color:#173f36!important;transform:translateY(-2px)}
.st-key-top_navigation button[kind="primary"]{background:#173f36!important;border:1px solid #173f36!important;color:#fff!important;box-shadow:0 4px 10px #173f3620!important}
button:focus-visible{outline:3px solid #96b694!important;outline-offset:3px}
.hero{background:#e0ebd9;border:1px solid #dbe7d4;border-radius:22px;padding:2.4rem 2.8rem;margin-bottom:1.4rem}
.hero .eyebrow{color:#688372;font-size:.75rem;letter-spacing:.12em;margin-bottom:20px}
.hero h1{font-size:2.35rem;line-height:1.35;font-weight:750;margin:0 0 16px;max-width:700px}
.hero p{font-size:1rem;color:#527563;margin:0;line-height:1.8}
.section{border-left:3px solid #789675;padding-left:14px;margin:10px 0 22px}
.section h3{font-size:1.5rem;font-weight:650}
.stButton>button,.stDownloadButton>button{background:#edf2e9;color:#24503f;border:1px solid #dfe8db;border-radius:11px;min-height:44px;padding:10px 16px;transition:background .18s,transform .18s,box-shadow .18s}
.stButton>button:hover,.stDownloadButton>button:hover{background:#e0eadb;color:#173f36;border-color:#a6bda5;transform:translateY(-1px)}
.stButton>button[kind="primary"],.stFormSubmitButton>button[kind="primary"]{background:#28644f;color:white;border-color:#28644f}
[data-testid="stMetric"]{background:white;border:1px solid var(--line);border-radius:17px;padding:20px 22px;min-height:146px}
[data-testid="stMetricLabel"]{color:#809488;font-size:.85rem}
[data-testid="stMetricValue"]{color:#173f36;font-size:2.1rem;font-weight:550}
.desk-card,.quick-card,.achievement-card,.metric-card{background:#fff;border:1px solid var(--line);border-radius:16px;padding:22px;box-shadow:none;height:100%;transition:transform .18s,border-color .18s}
.desk-card h4,.quick-card h4{font-size:1rem;margin:12px 0 7px;color:#173f36}
.desk-card p,.quick-card p{font-size:.87rem;color:#6d8279;line-height:1.7;margin:0}
.quick-card{min-height:162px}.quick-card:hover{border-color:#a3b69b;transform:translateY(-2px)}
.quick-card .icon{font-size:1.7rem}.journal-subtitle{color:#6d8279;font-size:.95rem;margin:0 0 16px}
.achievement-card{min-height:165px;padding:20px 16px}.achievement-icon{font-size:1.5rem;display:block;margin-bottom:13px}
.achievement-card b{display:block;color:#27513e;font-size:.9rem}.achievement-card small{display:block;color:#819184;font-size:.76rem;margin-top:9px;line-height:1.6}
.stTextInput input,.stTextArea textarea{background:white;color:#173f36;border-radius:10px}
[data-testid="stForm"],[data-testid="stExpander"]{background:white;border:1px solid var(--line);border-radius:15px}
[data-testid="stSidebar"]{background:#edf1e8;border-right:1px solid var(--line)}
[data-testid="stSidebar"] [data-testid="stMetric"]{padding:12px;min-height:90px}
.answer-bubble{padding:22px;border-radius:16px;background:#e9f1e5;border:1px solid #d5e3ce;color:#244b3e;line-height:1.9}
.empty-panel{padding:36px;border:1px dashed #cbd9c5;border-radius:16px;text-align:center;color:#6d8279;background:#fafbf8}
.stepper{display:flex;gap:10px;align-items:center;margin:16px 0 24px}.stepper .step{flex:1;background:#ebeee8;color:#7b8a7e;padding:14px;border-radius:10px;text-align:center;font-size:.85rem}.stepper .step.active{background:#dfead8;color:#28513f;font-weight:600}.stepper .line{height:1px;background:#ccd7c7;flex:.12}
.stTabs [data-baseweb="tab-list"]{gap:12px;border-bottom:1px solid var(--line)}.stTabs [aria-selected="true"]{color:#28644f}
@media(max-width:1100px){.st-key-top_navigation [data-testid="stHorizontalBlock"]{flex-wrap:wrap!important}.st-key-top_navigation [data-testid="stColumn"]{min-width:21%!important;flex:1 1 21%!important}.block-container{padding:1.2rem}}
@media(max-width:600px){.hero{padding:25px 22px}.hero h1{font-size:1.7rem}.st-key-top_navigation{padding:8px}.st-key-top_navigation button{font-size:.75rem!important;min-height:68px!important}[data-testid="stMetric"]{min-height:115px;padding:16px}}
@media(prefers-reduced-motion:reduce){*,*:before,*:after{transition:none!important;animation:none!important}}
</style>"""

def select_page(page):
    st.session_state["page_selected"] = page

def render_navigation():
    if "page_jump" in st.session_state:
        select_page(st.session_state.pop("page_jump"))
    valid = {item[0] for item in NAVIGATION}
    page = st.session_state.get("page_selected", "今日书桌")
    if page not in valid:
        page = "知识点掌握度" if page == "我的掌握度" else "今日书桌"
        select_page(page)
    with st.container(key="top_navigation"):
        columns = st.columns(len(NAVIGATION), gap="small")
        for column, (target, label, icon, help_text) in zip(columns, NAVIGATION):
            column.button(label, icon=f":material/{icon}:", help=help_text,
                          type="primary" if page == target else "secondary",
                          use_container_width=True, key=f"nav_{target}",
                          on_click=select_page, args=(target,))
    return page
