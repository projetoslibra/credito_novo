# db.py
import os
from dotenv import load_dotenv
import psycopg
from psycopg.rows import dict_row

# 🔹 Caminho absoluto para o .env
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".env"))
print(f"Carregando .env de: {env_path}")

# 🔹 Força o carregamento das variáveis
load_dotenv(dotenv_path=env_path, override=True)

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "sslmode": os.getenv("DB_SSLMODE", "require"),
}

print("DB_CONFIG (teste):", DB_CONFIG)

DDL = """
CREATE TABLE IF NOT EXISTS financefly_clients (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    item_id TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
"""

def get_conn():
    return psycopg.connect(**DB_CONFIG)

def init_db():
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(DDL)
        conn.commit()

def save_client(name, email, item_id):
    sql = """
    INSERT INTO financefly_clients (name, email, item_id)
    VALUES (%s, %s, %s)
    ON CONFLICT (item_id) DO NOTHING
    RETURNING id;
    """
    with get_conn() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, (name, email, item_id))
        row = cur.fetchone()
        conn.commit()
        return row["id"] if row else None
