"""
投资组合管理系统启动脚本
"""

import streamlit.web.cli as stcli
import sys
import os


def main():
    # 确保从项目根目录运行
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    # 设置Streamlit参数
    sys.argv = [
        "streamlit",
        "run",
        "ui/dashboard.py",
        "--server.port=8501",
        "--server.address=localhost",
        "--browser.gatherUsageStats=false",
    ]

    # 启动Streamlit
    sys.exit(stcli.main())


if __name__ == '__main__':
    main()
