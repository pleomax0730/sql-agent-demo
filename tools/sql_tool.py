import sqlite3
import os
from typing import Any
from langchain_core.tools import tool

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "inventory.db")


def execute_sqlite_query(raw_sql: str) -> dict[str, Any]:
    """
    Executes a real SQL query against the SQLite database.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(raw_sql)

        # Check if it's a SELECT query
        if cursor.description:
            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
            conn.close()
            return {
                "success": True,
                "columns": columns,
                "rows": [list(row) for row in rows],
                "row_count": len(rows),
                "execution_time_ms": 0,  # Not measured
            }
        else:
            conn.commit()
            rows_affected = cursor.rowcount
            conn.close()
            return {
                "success": True,
                "message": f"Query executed successfully. Rows affected: {rows_affected}",
                "rows_affected": rows_affected,
                "execution_time_ms": 0,
            }

    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def execute_sql(raw_sql: str) -> str:
    """
    Execute a raw SQL query against the laptop inventory database.

    The database contains the following tables:
    - laptops: id, brand, model_name, serial_number, manufacture_date
    - components: id, name, type, manufacturer, specs
    - laptop_components: laptop_id, component_id, installation_date

    Args:
        raw_sql: The complete SQL query to execute. Must be valid SQLite syntax.
    """
    try:
        result = execute_sqlite_query(raw_sql)

        if not result.get("success"):
            return f"❌ Query failed: {result.get('error', 'Unknown error')}"

        output_lines = ["✅ Query executed successfully!", ""]

        if "message" in result:
            output_lines.append(f"📝 {result['message']}")

        elif "columns" in result and "rows" in result:
            columns = result["columns"]
            rows = result["rows"]

            output_lines.append(
                f"📊 Results ({result.get('row_count', len(rows))} rows):"
            )
            output_lines.append("")

            if not rows:
                output_lines.append("(No rows returned)")
            else:
                col_widths = [len(str(col)) for col in columns]
                for row in rows:
                    for i, cell in enumerate(row):
                        col_widths[i] = max(col_widths[i], len(str(cell)))

                header = " | ".join(
                    str(col).ljust(col_widths[i]) for i, col in enumerate(columns)
                )
                separator = "-+-".join("-" * w for w in col_widths)

                output_lines.append(header)
                output_lines.append(separator)

                for row in rows:
                    row_str = " | ".join(
                        str(cell).ljust(col_widths[i]) for i, cell in enumerate(row)
                    )
                    output_lines.append(row_str)

        return "\n".join(output_lines)

    except Exception as e:
        return f"❌ Error executing query: {str(e)}"
