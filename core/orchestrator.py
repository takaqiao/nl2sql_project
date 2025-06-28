# core/orchestrator.py
import logging
import aiomysql
from datetime import datetime

from . import llm_handler
from . import security

# 在内存中存储日志
# 注意：在生产环境中，日志应写入文件或日志系统
query_logs = []

async def get_db_schema(pool, table_name=None):
    """从数据库获取表结构 (CREATE TABLE 语句)"""
    schema = {}
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SHOW TABLES")
            tables = await cursor.fetchall()
            table_list = [table[0] for table in tables]

            if table_name:
                if table_name in table_list:
                    await cursor.execute(f"SHOW CREATE TABLE `{table_name}`")
                    result = await cursor.fetchone()
                    if result:
                      schema[table_name] = result[1]
                # 如果找不到表，返回空 dict
            else:
                for t in table_list:
                    await cursor.execute(f"SHOW CREATE TABLE `{t}`")
                    result = await cursor.fetchone()
                    if result:
                      schema[t] = result[1]
    return schema

async def execute_query_in_db(pool, sql, page_size=10, offset=0):
    """在数据库中执行最终的 SQL"""
    paginated_sql = f"{sql.strip(';')} LIMIT {page_size} OFFSET {offset}"
    
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute(paginated_sql)
            results = await cursor.fetchall()
            
            has_more = len(results) == page_size
            next_offset = offset + page_size if has_more else None
            
            return {"data": results, "next_offset": next_offset}

async def process_natural_language_query(pool, question, page_size=10, offset=0):
    """
    处理自然语言查询的完整流程编排。
    """
    # 1. 获取数据库 Schema
    db_schema = await get_db_schema(pool)
    if not db_schema:
        return {"error": "Failed to retrieve database schema."}

    # 2. 调用 LLM 生成 SQL
    generated_sql = await llm_handler.get_sql_from_llm(question, db_schema)
    if generated_sql.lower().startswith("error:"):
        return {"error": generated_sql}
    logging.info(f"LLM 生成的 SQL: {generated_sql}")
    
    # 3. 运行所有安全校验
    is_safe, error_message = security.run_all_security_checks(question, generated_sql)
    if not is_safe:
        return {"error": error_message, "generated_sql": generated_sql}

    # 4. 执行查询
    try:
        result = await execute_query_in_db(pool, generated_sql, page_size, offset)
        
        # 5. 记录成功的查询
        log_entry = {
            "question": question,
            "sql": generated_sql,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "success"
        }
        query_logs.append(log_entry)
        
        return {
            "generated_sql": generated_sql,
            **result
        }
    except Exception as e:
        logging.error(f"数据库执行 SQL 时出错: {e}")
        log_entry = {
            "question": question,
            "sql": generated_sql,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "error",
            "error_message": str(e)
        }
        query_logs.append(log_entry)
        return {"error": f"Database execution error: {e}", "generated_sql": generated_sql}