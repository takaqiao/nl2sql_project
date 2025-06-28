# core/security.py
import re
import sqlparse
import logging

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

def contains_forbidden_fields(sql: str) -> bool:
    """检查 SQL 是否查询了被禁止的敏感字段"""
    parsed = sqlparse.parse(sql)
    if not parsed:
        return False
    
    tokens = parsed[0].flatten()
    for token in tokens:
        if token.ttype is sqlparse.tokens.Name or token.ttype is sqlparse.tokens.Identifier:
            if token.value.lower().strip('`"') in FORBIDDEN_FIELDS:
                logging.warning(f"查询包含敏感字段被拒绝: {token.value}")
                return True
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