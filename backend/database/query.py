import re

from sqlalchemy import text

from core.clients import get_database_engine


FORBIDDEN_SQL = re.compile(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|COPY|CALL|DO|MERGE|VACUUM|ANALYZE|COMMENT|SET|RESET)\b", re.IGNORECASE)


def clean_sql(sql: str) -> str:
    sql = sql.strip()
    if sql.startswith("```"):
        lines = sql.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        sql = "\n".join(lines).strip()
    if sql.lower().startswith("sql\n"):
        sql = sql[4:].strip()
    return sql[:-1].strip() if sql.endswith(";") else sql


def validate_select_sql(sql: str) -> str:
    sql = clean_sql(sql)
    if not re.match(r"^SELECT\b", sql, re.IGNORECASE):
        raise ValueError("Only SELECT queries are allowed")
    if ";" in sql:
        raise ValueError("Multiple SQL statements are not allowed")
    if FORBIDDEN_SQL.search(sql):
        raise ValueError("Unsafe SQL statement rejected")
    return sql


def execute_select(sql: str) -> list[dict]:
    sql = validate_select_sql(sql)
    with get_database_engine().connect() as connection:
        result = connection.execute(text(sql))
        return [dict(row._mapping) for row in result]
