import sys
from pathlib import Path

# 让直接双击启动、Streamlit 启动和 PowerShell 启动都能找到 src/course_agent。
PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import streamlit as st
from course_agent.ui import render_app

def main():
    st.set_page_config(page_title="课程知识整理 Agent", page_icon="📚", layout="wide")
    render_app()

if __name__ == "__main__":
    main()
