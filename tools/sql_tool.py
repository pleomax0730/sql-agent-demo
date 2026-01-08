import sqlite3
import os
import traceback
from typing import Any
from langchain_core.tools import tool
from langchain.tools.tool_node import ToolRuntime
from db.schema import get_database_schema

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "inventory.db")


def _get_conn():
    return sqlite3.connect(DB_PATH)


def _print_runtime_info(runtime: ToolRuntime, tool_name: str):
    """
    打印開發者要求的調試資訊。
    """
    # 從 runtime 獲取 config
    config = runtime.config

    # 獲取 Thread ID (在 configurable 中)
    thread_id = config.get("configurable", {}).get("thread_id", "N/A")

    # 獲取 Run ID (優先從頂層拿，備案從 metadata 拿)
    run_id = config.get("run_id") or config.get("metadata", {}).get("run_id", "N/A")

    # 獲取 User ID (由 auth.py 提供)
    user_info = config.get("configurable", {}).get("langgraph_auth_user", {})
    user_id = user_info.get("identity", "unknown")

    print("-" * 50)
    print(f"🔧 [Tool: {tool_name}] 執行資訊：")
    print(f"🆔 Thread ID: {thread_id}")
    print(f"🔥 Run ID:    {run_id}")
    print(f"👤 User ID:   {user_id}")
    print("-" * 50)


def execute_sqlite_query(raw_sql: str) -> dict[str, Any]:
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        cursor.execute(raw_sql)

        if cursor.description:
            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
            conn.close()
            results = []
            for row in rows:
                results.append(dict(zip(columns, row)))
            return {"success": True, "data": results, "row_count": len(rows)}
        else:
            conn.commit()
            rows_affected = cursor.rowcount
            conn.close()
            return {
                "success": True,
                "message": f"查詢執行成功。影響行數: {rows_affected}",
            }
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def list_tables(runtime: ToolRuntime) -> list[dict[str, Any]]:
    """
    列出資料庫中所有可用資料表的詳細結構。
    """
    _print_runtime_info(runtime, "list_tables")
    try:
        schema = get_database_schema()
        return schema.get("tables", [])
    except Exception as e:
        traceback.print_exc()
        return [{"error": str(e)}]


@tool
def query_data(raw_sql: str, runtime: ToolRuntime) -> Any:
    """
    執行 SQL 查詢並獲取結果數據。

    Args:
        raw_sql: 要執行的完整 SQL 查詢語句。
    """
    _print_runtime_info(runtime, "query_data")
    try:
        result = execute_sqlite_query(raw_sql)

        if not result.get("success"):
            return {"error": result.get("error")}

        if "message" in result:
            return {"status": "success", "info": result["message"]}

        return result.get("data", [])

    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}
