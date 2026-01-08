from typing import Any
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "inventory.db")


def get_database_schema() -> dict[str, Any]:
    """
    Retrieves the actual schema from the SQLite database.
    """
    if not os.path.exists(DB_PATH):
        return {"database_name": "inventory_db", "tables": [], "relationships": []}

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]

    schema_tables = []
    for table_name in tables:
        # Get column info
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns_info = cursor.fetchall()

        columns = []
        for col in columns_info:
            columns.append(
                {
                    "name": col[1],
                    "type": col[2],
                    "primary_key": bool(col[5]),
                    "nullable": not bool(col[3]),
                    "description": "",  # SQLite doesn't store descriptions easily
                }
            )

        schema_tables.append(
            {
                "name": table_name,
                "description": f"Table: {table_name}",
                "columns": columns,
            }
        )

    conn.close()

    # Relationships are hardcoded for now as SQLite doesn't always have them enforced/visible via simple introspection
    return {
        "database_name": "laptop_inventory_db",
        "tables": schema_tables,
        "relationships": [
            {
                "from": "laptop_components.laptop_id",
                "to": "laptops.id",
                "type": "many-to-one",
            },
            {
                "from": "laptop_components.component_id",
                "to": "components.id",
                "type": "many-to-one",
            },
        ],
    }


def format_schema_for_prompt(schema: dict[str, Any]) -> str:
    """
    Format the database schema into a readable string for the system prompt.
    """
    lines = [f"📊 Database: {schema['database_name']}", "=" * 60, ""]

    for table in schema["tables"]:
        lines.append(f"📋 Table: {table['name']}")
        lines.append(f"   Columns:")

        for col in table["columns"]:
            constraints = []
            if col.get("primary_key"):
                constraints.append("PK")
            if col.get("nullable") is False:
                constraints.append("NOT NULL")

            constraint_str = f" [{', '.join(constraints)}]" if constraints else ""
            lines.append(f"      - {col['name']}: {col['type']}{constraint_str}")

        lines.append("")

    lines.append("🔗 Relationships:")
    for rel in schema["relationships"]:
        lines.append(f"   - {rel['from']} → {rel['to']} ({rel['type']})")

    return "\n".join(lines)


# For backward compatibility if build_system_prompt was moved elsewhere
def build_system_prompt() -> str:
    schema = get_database_schema()
    formatted_schema = format_schema_for_prompt(schema)
    return f"Database Schema:\n\n{formatted_schema}"
