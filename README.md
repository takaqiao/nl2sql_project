# NL2SQL: 基于大模型与 MCP 服务的自然语言数据库查询系统

本项目是一个基于大语言模型（通义千问）和 Model Context Protocol (MCP) 的自然语言数据库查询系统。用户可以通过命令行(CLI)或图形界面(GUI)输入自然语言问题，系统会将其转换为 SQL 查询，执行后返回结果。

## 项目特点

- **双模交互**: 同时支持 **Streamlit GUI** 和 **Rich CLI** 两种查询方式。
- **模块化设计**: 前后端分离，核心逻辑、Web 服务和 UI 界面完全解耦。
- **异步后端**: 基于 `aiohttp` 和 `aiomysql` 构建高性能 MCP 服务器。
- **增强功能**: 实现查询日志、结果分页、动态 Schema 查询等高级功能。
- **安全保障**: 内置多层安全机制，包括只读查询过滤、敏感字段拦截和基础 SQL 注入防御。
- **Prompt 优化**: 采用 Few-shot 学习和效率指令，提升生成 SQL 的准确性和性能。
- **现代化包管理**: 使用 `uv` 进行项目环境和依赖管理。

## 项目结构

```
nl2sql_project/
├── .env                  # 存储环境变量 (数据库凭证, LLM API密钥)
├── pyproject.toml        # uv 配置文件
├── README.md             # 本文档
├── college.sql           # 数据库定义与数据文件
|
├── core/                 # 核心业务逻辑模块
│   ├── llm_handler.py    # 与Qwen LLM交互的逻辑
│   ├── security.py       # SQL验证与安全检查逻辑
│   └── orchestrator.py   # 业务流程编排器
|
├── mcp_server/           # MCP服务器模块
│   └── server.py         # MCP服务器核心逻辑、API端点定义
|
├── streamlit_app/        # Streamlit前端应用模块
│   └── app.py            # Streamlit界面代码
|
└── cli.py                # 命令行界面(CLI)实现
```

## 环境设置与运行

本项目推荐使用 `uv` 作为包管理器，它能极大地提升环境创建和依赖安装的速度。

### 1. 安装 uv

如果您尚未安装 `uv`，请根据您的操作系统执行相应命令：

```bash
# macOS / Linux
curl -LsSf [https://astral.sh/uv/install.sh](https://astral.sh/uv/install.sh) | sh

# Windows
powershell -c "irm [https://astral.sh/uv/install.ps1](https://astral.sh/uv/install.ps1) | iex"
```

### 2. 创建虚拟环境并安装依赖

在项目根目录 (`nl2sql_project/`) 下运行以下命令，`uv` 会自动创建 `.venv` 虚拟环境并安装 `pyproject.toml` 中定义的所有依赖。

```bash
uv sync
```

### 3. 配置环境变量

复制 `.env.example` 文件为 `.env`，并填入你的配置信息。

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```ini
# .env
DB_HOST="localhost"
DB_PORT=3306
DB_USER="your_db_user"      # <-- 替换为你的数据库用户名
DB_PASSWORD="your_db_password" # <-- 替换为你的数据库密码
DB_NAME="college"

# 确保你的环境中有名为 DASHSCOPE_API_KEY 的环境变量
# 在此文件中设置也可，但更推荐设置为系统环境变量
DASHSCOPE_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxx"
```

### 4. 准备数据库

确保你的 MySQL/MariaDB 服务正在运行。然后创建数据库并导入数据。

```bash
# 使用你的数据库用户登录
mysql -u your_db_user -p

# 在 mysql shell 中执行
CREATE DATABASE IF NOT EXISTS college;
exit;

# 导入数据
mysql -u your_db_user -p college < college.sql
```

### 5. 启动服务

你需要 **两个独立的终端** 来分别运行后端和前端。

**终端 1: 激活环境并启动 MCP 后端服务器**

```bash
# 激活虚拟环境
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# 启动服务器
python -m mcp_server.server
```

成功启动后，你会看到服务器在 `http://0.0.0.0:8080` 运行的日志。

---

**终端 2: 运行 GUI 或 CLI**

**选项 A: 启动 Streamlit GUI 界面**

```bash
# 激活虚拟环境
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# 运行 Streamlit 应用
streamlit run streamlit_app/app.py
```

浏览器将自动打开 `http://localhost:8501`。

**选项 B: 运行 CLI 交互界面**

```bash
# 激活虚拟环境
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# 运行 CLI 应用
python cli.py
```

你可以在终端中直接输入自然语言问题进行查询。

## 功能演示

### GUI 界面

- **实时查询**: 在文本框中输入问题，立即获得生成的 SQL 和数据表。
- **分页加载**: 当结果集过大时，会出现 "加载下一页" 按钮。
- **Schema 展示**: 侧边栏实时展示数据库表结构。

### CLI 界面

- **交互式输入**: 支持在终端循环提问。
- **优雅输出**: 使用 `rich` 库美化 SQL 和表格的输出。
- **分页支持**: 当结果有多页时，可输入 `next` 来获取下一页数据。
- **退出**: 输入 `exit` 退出程序。
