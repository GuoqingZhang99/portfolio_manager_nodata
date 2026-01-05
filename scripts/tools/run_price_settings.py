"""
价格设置快速启动脚本

直接运行此文件打开价格设置页面：
streamlit run run_price_settings.py
"""

import streamlit as st
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

from config import DATABASE_PATH
from core.database import Database
from core.calculator import PortfolioCalculator
from ui.pages import price_settings

# 页面配置
st.set_page_config(
    page_title="价格数据源设置",
    page_icon="💰",
    layout="wide"
)

# 初始化组件
@st.cache_resource
def init_components():
    db = Database(DATABASE_PATH)
    calc = PortfolioCalculator(db)
    return {
        'db': db,
        'calc': calc
    }

components = init_components()

# 渲染页面
price_settings.render(components)

# 提示信息
st.sidebar.markdown("---")
st.sidebar.info("""
### 💡 使用提示

**手动输入价格**：
1. 切换到"手动输入价格"标签
2. 为每只股票输入当前价格
3. 点击"保存所有价格"

**配置 API**：
1. 切换到"API 数据源"标签
2. 选择 Alpha Vantage 或 Finnhub
3. 注册并获取免费 API Key
4. 输入 API Key 并测试

**测试数据源**：
1. 切换到"测试数据源"标签
2. 点击相应按钮测试
3. 查看结果

---

设置完成后，返回主应用即可看到价格显示。
""")
