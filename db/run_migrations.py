"""轻量级 migration 执行器。

读取 db/migrations/*.sql，按文件名顺序应用未执行的迁移。
版本号取文件名前 3 位数字（001, 002, ...）。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def get_conn():
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        dbname=os.environ["DB_NAME"],
    )


def applied_versions(conn) -> set[str]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
            "WHERE table_name = 'schema_migrations')"
        )
        if not cur.fetchone()[0]:
            return set()
        cur.execute("SELECT version FROM schema_migrations")
        return {row[0] for row in cur.fetchall()}


def run() -> int:
    conn = get_conn()
    try:
        applied = applied_versions(conn)
        sql_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
        if not sql_files:
            print("no migration files found")
            return 0

        pending = [
            f for f in sql_files
            if f.name.split("_", 1)[0] not in applied
        ]
        if not pending:
            print(f"all {len(sql_files)} migrations already applied ✓")
            return 0

        for sql_file in pending:
            version = sql_file.name.split("_", 1)[0]
            print(f"→ applying {sql_file.name} ...", end=" ", flush=True)
            sql = sql_file.read_text(encoding="utf-8")
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()
            print("ok")

        print(f"applied {len(pending)} migration(s)")
        return 0
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(run())
