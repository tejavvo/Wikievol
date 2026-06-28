#!/usr/bin/env python3
import argparse
import sqlite3
from pathlib import Path
from tabulate import tabulate

def list_tables(conn: sqlite3.Connection) -> list:
    """Get all table names."""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return [row[0] for row in cursor.fetchall()]

def get_table_data(conn: sqlite3.Connection, table_name: str, limit: int = None) -> tuple:
    """Fetch all data from a table. Returns (columns, rows)."""
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name}")
    
    columns = [description[0] for description in cursor.description]
    
    if limit:
        rows = cursor.fetchmany(limit)
    else:
        rows = cursor.fetchall()
    
    return columns, rows

def display_table(conn: sqlite3.Connection, table_name: str, limit: int = 10) -> None:
    """Display a single table."""
    try:
        columns, rows = get_table_data(conn, table_name, limit)
        
        if not rows:
            print(f"\n{table_name}: (empty)\n")
            return
        
        print(f"\n{'='*80}")
        print(f"Table: {table_name} ({len(rows)} rows shown)")
        print(f"{'='*80}")
        print(tabulate(rows, headers=columns, tablefmt="grid"))
        print()
    except Exception as e:
        print(f"Error displaying {table_name}: {e}")

def main() -> None:
    parser = argparse.ArgumentParser(description="Display SQLite database tables in the terminal.")
    parser.add_argument("--db", required=True, help="Path to SQLite database file")
    parser.add_argument("--table", help="Specific table to display (if not provided, shows all)")
    parser.add_argument("--limit", type=int, default=10, help="Max rows to display per table (default: 10)")
    args = parser.parse_args()

    db_path = Path(args.db)
    
    if not db_path.exists():
        raise SystemExit(f"Database file not found: {db_path}")

    conn = sqlite3.connect(str(db_path))
    try:
        tables = list_tables(conn)
        
        if not tables:
            print("No tables found in database.")
            return
        
        if args.table:
            if args.table in tables:
                display_table(conn, args.table, args.limit)
            else:
                print(f"Table '{args.table}' not found.")
                print(f"Available tables: {', '.join(tables)}")
        else:
            print(f"Found {len(tables)} tables: {', '.join(tables)}\n")
            for table_name in tables:
                display_table(conn, table_name, args.limit)
    finally:
        conn.close()

if __name__ == "__main__":
    main()