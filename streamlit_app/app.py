# streamlit_app/app.py
import streamlit as st
import requests
import pandas as pd
import json

# --- 配置 ---
MCP_SERVER_URL = "http://localhost:8080" # MCP 服务器地址

# --- Streamlit 页面配置 ---
st.set_page_config(page_title="自然语言数据库查询系统", layout="wide")
st.title("自然语言数据库查询系统 🤖️")
st.caption("基于大语言模型与 MCP 服务的数据库查询")

# --- 会话状态管理 ---
if 'query_history' not in st.session_state:
    st.session_state.query_history = []
if 'current_result' not in st.session_state:
    st.session_state.current_result = None
if 'current_sql' not in st.session_state:
    st.session_state.current_sql = ""
if 'error_message' not in st.session_state:
    st.session_state.error_message = ""

# --- API 调用函数 ---
def query_mcp_server(prompt, page_size=10, offset=0):
    """向 MCP 服务器发送查询请求"""
    try:
        response = requests.post(
            f"{MCP_SERVER_URL}/query",
            json={"prompt": prompt, "page_size": page_size, "offset": offset},
            timeout=60  # 60秒超时
        )
        response.raise_for_status() # 如果是 4xx 或 5xx 错误，会抛出异常
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"无法连接到 MCP 服务器: {e}"}

# --- UI 界面 ---
col1, col2 = st.columns([2, 1])

with col1:
    with st.form("query_form"):
        natural_language_query = st.text_area(
            "请输入你的问题 (自然语言):",
            "计算机科学系 (Comp. Sci.) 有哪些课程？",
            height=100
        )
        submitted = st.form_submit_button("🚀 执行查询")

    if submitted:
        if not natural_language_query.strip():
            st.error("问题不能为空！")
        else:
            with st.spinner("正在思考并查询数据库..."):
                result = query_mcp_server(natural_language_query)
                st.session_state.current_result = result
                
                if "error" in result:
                    st.session_state.error_message = result.get("error")
                    st.session_state.current_sql = result.get("generated_sql", "")
                else:
                    st.session_state.error_message = ""
                    st.session_state.current_sql = result.get("generated_sql", "")
                
                # 记录历史
                st.session_state.query_history.insert(0, {
                    "question": natural_language_query,
                    "result": result
                })


# --- 结果展示 ---
st.markdown("---")
st.subheader("查询结果")

if st.session_state.error_message:
    st.error(f"发生错误: {st.session_state.error_message}")

if st.session_state.current_sql:
    st.code(st.session_state.current_sql, language="sql")

if st.session_state.current_result and "data" in st.session_state.current_result:
    data = st.session_state.current_result["data"]
    if data:
        df = pd.DataFrame(data)
        st.dataframe(df)
        st.success(f"查询成功，返回 {len(data)} 条记录。")
    else:
        st.info("查询成功，但没有返回任何数据。")

# --- 侧边栏 ---
with st.sidebar:
    st.header("功能区")
    st.info(f"MCP 服务器地址: `{MCP_SERVER_URL}`")
    
    st.subheader("测试用例")
    test_cases = [
        "List the names of all courses ordered by their titles and credits.",
        "What is the title, credit value, and department name for courses with more than one prerequisite?",
        "What are the names of students who have more than one advisor?",
        "What are the titles of courses without prerequisites?",
        "查询所有预算超过85000美元的系的名称和预算"
    ]
    selected_test_case = st.selectbox("选择一个测试问题", options=test_cases)
    if st.button("使用此测试用例填充"):
        st.session_state.test_query = selected_test_case # 触发主程序重新运行
        st.rerun() # 重新运行整个脚本

# 如果测试用例被触发，更新主输入框
if 'test_query' in st.session_state:
    st.text_area("请输入你的问题 (自然语言):", value=st.session_state.test_query, key="main_input_area_rerun")
    del st.session_state.test_query

with col2:
    st.subheader("Schema (表结构)")
    with st.spinner("正在加载 Schema..."):
        try:
            schema_res = requests.get(f"{MCP_SERVER_URL}/schema", timeout=10)
            if schema_res.status_code == 200:
                st.json(schema_res.json(), expanded=False)
            else:
                st.error("加载 Schema 失败。请确保 MCP 服务器正在运行。")
        except requests.exceptions.RequestException:
            st.error("无法连接到 MCP 服务器。")

    st.subheader("查询历史")
    if not st.session_state.query_history:
        st.text("暂无历史记录")
    else:
        for i, item in enumerate(st.session_state.query_history):
            with st.expander(f"#{i+1}: {item['question'][:50]}..."):
                st.json(item['result'])