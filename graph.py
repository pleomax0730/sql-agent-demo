"""
LangGraph Graph Definition for the SQL Agent

This module exposes the agent as a LangGraph-compatible graph
that can be served via `langgraph dev` command.
"""

import os
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver

from db.schema import get_database_schema, format_schema_for_prompt
from tools.sql_tool import execute_sql

# SQLite 檔案路徑 (用於持久化對話記錄)
CHECKPOINT_DB_PATH = os.path.join(os.path.dirname(__file__), "chat_history.db")


def build_system_prompt() -> str:
    """
    Build the system prompt with dynamically injected database schema.
    """
    schema = get_database_schema()
    formatted_schema = format_schema_for_prompt(schema)

    return f"""你是一個專業的 SQL 助手，專門幫助用戶查詢和操作資料庫。你可以使用 execute_sql 工具來執行 SQL 查詢。

## 📋 可用的資料庫結構

{formatted_schema}

## 🎯 你的職責

1. **理解用戶需求**: 仔細分析用戶的問題，確定需要查詢哪些資料表
2. **生成正確的 SQL**: 根據上述結構生成正確的 SQL 語句
3. **執行查詢**: 使用 execute_sql 工具執行查詢
4. **解釋結果**: 用清晰的繁體中文解釋查詢結果

## ⚠️ 注意事項

- 使用正確的資料表和欄位名稱
- 注意資料類型的匹配
- 對於複雜查詢，使用適當的 JOIN
- 執行 INSERT/UPDATE/DELETE 前要確認用戶意圖

請用繁體中文回答，並在執行查詢後解釋結果。
"""


# 初始化 SQLite Checkpointer (持久化對話記錄)
checkpointer = SqliteSaver.from_conn_string(CHECKPOINT_DB_PATH)


def create_sql_agent():
    """
    Create and return the SQL agent graph.

    This function is called by the LangGraph server to instantiate the agent.
    """
    llm = ChatOpenAI(
        base_url="http://localhost:8080/v1",
        api_key="EMPTY",
        model="qwen",
    )

    graph = create_agent(
        model=llm,
        tools=[execute_sql],
        system_prompt=build_system_prompt(),
        checkpointer=checkpointer,  # 使用 SQLite 持久化
    )

    return graph


# Export the graph for langgraph dev
graph = create_sql_agent()
