# core/security.py
import re
import sqlparse
import logging
from sqlparse.sql import Identifier

# 安全配置
FORBIDDEN_FIELDS = {'password', 'salary', 'ssn', 'credentials'}
# 简易 SQL 注入模式
SQLI_PATTERNS = re.compile(r"(\s*(--|#))|(\s*(union|select|insert|update|delete|drop|alter)\s+)", re.IGNORECASE)

def is_potential_sqli(text: str) -> bool:
    """对用户原始输入进行简单的 SQL 注入模式检查"""
    if SQLI_PATTERNS.search(text):
        logging.warning(f"检测到潜在的 SQL 注入攻击: {text}")
        return True
    return False

def is_readonly_query(sql: str) -> bool:
    """使用 sqlparse 检查是否为只读查询"""
    parsed = sqlparse.parse(sql)
    for statement in parsed:
        if statement.get_type() != 'SELECT':
            logging.warning(f"非只读查询被拒绝: {sql}")
            return False
    return True

def _find_identifiers(tokens):
    """一个递归生成器，用于从 token 列表中深度查找所有 Identifier 对象。"""
    for token in tokens:
        # 如果 token 本身就是一个 Identifier 对象，就产生它
        if isinstance(token, Identifier):
            yield token
        # 如果 token 是一个包含子 token 的列表 (并且它不是一个 Identifier)
        # 那么就递归地进入这个列表进行查找
        elif token.is_group:
            yield from _find_identifiers(token.tokens)

def contains_forbidden_fields(sql: str) -> bool:
    """
    检查 SQL 是否查询了被禁止的敏感字段 (基于官方文档的正确实现)。
    """
    try:
        parsed = sqlparse.parse(sql)[0]
        for identifier in _find_identifiers(parsed.tokens):
            # .get_real_name() 是获取标识符真实名称的推荐方法
            real_name = identifier.get_real_name()
            if real_name and real_name.lower() in FORBIDDEN_FIELDS:
                logging.warning(f"查询包含敏感字段被拒绝: {real_name}")
                return True
        return False
    except IndexError:
        # 处理空的或无效的 SQL 字符串
        return False
def run_all_security_checks(natural_question: str, generated_sql: str) -> (bool, str):
    """
    运行所有安全检查。
    返回一个元组 (is_safe, error_message)。
    """
    if is_potential_sqli(natural_question):
        return False, "Invalid input detected. Potential SQL injection attempt."
    
    if not is_readonly_query(generated_sql):
        return False, "Security check failed: Only SELECT queries are allowed."

    if contains_forbidden_fields(generated_sql):
        return False, "Security check failed: Query attempts to access forbidden fields."
        
    return True, ""