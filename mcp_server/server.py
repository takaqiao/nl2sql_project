# mcp_server/server.py
import os
import json
import logging
from logging.handlers import RotatingFileHandler

import aiomysql
import aiohttp_cors
from aiohttp import web
from dotenv import load_dotenv

# 在所有其他导入之前加载环境变量
load_dotenv()

from core import orchestrator

# --- 日志配置 ---
log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_file_path = os.path.join(log_dir, 'app.log')

# 创建一个 rotating file handler
# 每个日志文件最大 5MB, 最多保留 5 个备份
file_handler = RotatingFileHandler(log_file_path, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# 配置根 logger
logging.basicConfig(level=logging.INFO, handlers=[
    logging.StreamHandler(),  # 同时输出到控制台
    file_handler              # 和文件
])


# --- 全局状态 ---
db_pool = None

# --- MCP 工具处理模块 ---
async def handle_query(request):
    """处理 /query 工具的请求"""
    try:
        data = await request.json()
        question = data.get("prompt")
        page_size = int(data.get("page_size", 10))
        offset = int(data.get("offset", 0))

        if not question:
            return web.json_response({"error": "Prompt 'question' is required."}, status=400)

        result = await orchestrator.process_natural_language_query(
            request.app['db_pool'], question, page_size, offset
        )
        
        status_code = 400 if "error" in result else 200
        return web.json_response(result, status=status_code)

    except json.JSONDecodeError:
        return web.json_response({"error": "Invalid JSON format."}, status=400)
    except Exception as e:
        logging.error(f"处理 /query 时发生未知错误: {e}", exc_info=True)
        return web.json_response({"error": "An internal server error occurred."}, status=500)

async def handle_schema(request):
    """处理 /schema 工具的请求"""
    try:
        table_name = request.query.get("table_name")
        schema = await orchestrator.get_db_schema(request.app['db_pool'], table_name)
        if table_name and not schema:
            return web.json_response({"error": f"Table '{table_name}' not found."}, status=404)
        return web.json_response(schema)
    except Exception as e:
        logging.error(f"处理 /schema 时发生错误: {e}", exc_info=True)
        return web.json_response({"error": "An internal server error occurred."}, status=500)

async def handle_logs(request):
    """处理 /logs 工具的请求"""
    return web.json_response({"logs": orchestrator.query_logs})


# --- 服务器主程序 ---
async def init_db_pool(app):
    """初始化数据库连接池并存储在 app 对象中"""
    logging.info("正在初始化数据库连接池...")
    try:
        app['db_pool'] = await aiomysql.create_pool(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT")),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            db=os.getenv("DB_NAME"),
            autocommit=True
        )
        logging.info("数据库连接池初始化成功。")
    except Exception as e:
        logging.error(f"数据库连接失败: {e}")
        raise

async def cleanup_db_pool(app):
    """关闭数据库连接池"""
    logging.info("正在关闭数据库连接池...")
    app['db_pool'].close()
    await app['db_pool'].wait_closed()
    logging.info("数据库连接池已关闭。")

def main():
    app = web.Application()
    
    # 注册启动和清理事件
    app.on_startup.append(init_db_pool)
    app.on_cleanup.append(cleanup_db_pool)
    
    # 配置 CORS
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        )
    })
    
    # 注册路由并应用 CORS
    cors.add(app.router.add_post('/query', handle_query))
    cors.add(app.router.add_get('/schema', handle_schema))
    cors.add(app.router.add_get('/logs', handle_logs))

    port = int(os.getenv("PORT", 8080))
    logging.info(f"MCP 服务器将在 http://0.0.0.0:{port} 启动")
    web.run_app(app, host='0.0.0.0', port=port)

if __name__ == "__main__":
    main()