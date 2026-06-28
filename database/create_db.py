import sqlite3

DB_NAME = "wikievolution.db"
SCHEMA_FILE = "schema.sql"

conn = sqlite3.connect(DB_NAME)

with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
    conn.executescript(f.read())

conn.commit()
conn.close()

print(f"Database '{DB_NAME}' created successfully!")