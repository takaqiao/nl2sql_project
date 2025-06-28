# core/llm_handler.py
import os
import logging
from dashscope import Generation

# 确保 API Key 已加载
QWEN_API_KEY = os.getenv("DASHSCOPE_API_KEY")
if not QWEN_API_KEY:
    raise ValueError("错误：环境变量 DASHSCOPE_API_KEY 未设置。")

def build_prompt(user_question: str, schema_string: str) -> str:
    """
    构建一个包含指令、Schema 和示例的复杂 Prompt。
    """
    return f"""
### 任务
你是一个专业的数据库专家，擅长将自然语言问题转换为 MySQL 查询语句。
请根据下面提供的数据库表结构和用户问题，生成一个准确、高效的 MySQL 查询。

### 数据库表结构 (CREATE TABLE statements):
{schema_string}

### 指示
1.  只生成 `SELECT` 类型的 SQL 查询。
2.  确保 SQL 语法正确无误，并且符合 MySQL 规范。
3.  不要在 SQL 中使用任何可能修改数据库的操作（如 UPDATE, DELETE）。
4.  如果问题无法根据提供的表结构回答，请返回 "Error: Cannot answer the question with the given schema."

### 示例 (Few-shot examples):
# Question: List the names of all courses ordered by their titles and credits.
SELECT title, credits FROM course ORDER BY title, credits;

# Question: What are the titles of courses without prerequisites?
SELECT T.title FROM course AS T LEFT JOIN prereq AS P ON T.course_id = P.course_id WHERE P.prereq_id IS NULL;

# Question: What are the names of students who have more than one advisor?
SELECT name FROM student WHERE ID IN (SELECT s_ID FROM advisor GROUP BY s_ID HAVING count(*) > 1);

### 用户问题
{user_question}

### 生成的 SQL 查询:
"""

async def get_sql_from_llm(user_question: str, db_schema: dict) -> str:
    """使用通义千问将自然语言转换为 SQL"""
    schema_string = "\n\n".join(db_schema.values())
    prompt = build_prompt(user_question, schema_string)

    try:
        response = Generation.call(
            model="qwen-turbo", # 或 qwen-plus
            prompt=prompt,
            api_key=QWEN_API_KEY,
            result_format='text'
        )
        if response.status_code == 200:
            generated_sql = response.output.text.strip()
            # 清理模型可能返回的 markdown 代码块
            if generated_sql.startswith("```sql"):
                generated_sql = generated_sql[6:].strip()
            if generated_sql.endswith("```"):
                generated_sql = generated_sql[:-3].strip()
            return generated_sql
        else:
            logging.error(f"通义千问 API 调用失败: {response.message}")
            return f"Error: LLM API call failed with message: {response.message}"
            
    except Exception as e:
        logging.error(f"调用 LLM 时发生异常: {e}")
        return f"Error: An exception occurred during the LLM call."