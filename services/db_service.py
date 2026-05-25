import psycopg2
from psycopg2 import pool
from flask import current_app, g

# Pool de conexiones (simple)
connection_pool = None

def init_db_pool(app):
    global connection_pool
    connection_pool = psycopg2.pool.SimpleConnectionPool(
        1, 10,
        dbname=app.config['DB_NAME'],
        user=app.config['DB_USER'],
        password=app.config['DB_PASSWORD'],
        host=app.config['DB_HOST'],
        port=app.config['DB_PORT']
    )

def get_db():
    """Obtiene una conexión del pool para la solicitud actual."""
    if 'db' not in g:
        g.db = connection_pool.getconn()
    return g.db

def close_db(e=None):
    """Devuelve la conexión al pool al final de la solicitud."""
    db = g.pop('db', None)
    if db is not None:
        connection_pool.putconn(db)

def ejecutar_funcion(funcion_name, *args):
    """Ejecuta una función de PostgreSQL y devuelve el resultado (primera columna)."""
    conn = get_db()
    with conn.cursor() as cur:
        placeholders = ','.join(['%s'] * len(args))
        cur.execute(f"SELECT {funcion_name}({placeholders})", args)
        resultado = cur.fetchone()
        conn.commit()  # Commit después de ejecutar la función
        return resultado[0] if resultado else None

def ejecutar_sql(sql, params=None, fetch_one=False, fetch_all=False):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(sql, params)
        if fetch_one:
            return cur.fetchone()
        if fetch_all:
            return cur.fetchall()
        conn.commit()