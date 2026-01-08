import sqlite3
import pandas as pd
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "inventory.db")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def init_db():
    print(f"Initializing database at {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)

    # Load CSVs
    csv_files = {
        "laptops": "laptops.csv",
        "components": "components.csv",
        "laptop_components": "laptop_components.csv",
    }

    for table_name, csv_file in csv_files.items():
        csv_path = os.path.join(DATA_DIR, csv_file)
        if os.path.exists(csv_path):
            print(f"Loading {csv_file} into table '{table_name}'...")
            df = pd.read_csv(csv_path)
            df.to_sql(table_name, conn, if_exists="replace", index=False)
        else:
            print(f"Warning: {csv_path} not found.")

    conn.close()
    print("Database initialization complete.")


if __name__ == "__main__":
    init_db()
