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

def ejecutar_funcion_tabla(funcion_name, *args):
    """Ejecuta una función que retorna TABLE y devuelve lista de diccionarios."""
    conn = get_db()
    with conn.cursor() as cur:
        placeholders = ','.join(['%s'] * len(args))
        cur.execute(f"SELECT * FROM {funcion_name}({placeholders})", args)
        columnas = [desc[0] for desc in cur.description]
        resultados = []
        for row in cur.fetchall():
            resultados.append(dict(zip(columnas, row)))
        return resultados

def obtener_productos_por_emprendedor(id_emprendedor):
    """Devuelve lista de productos de un emprendedor."""
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id_producto, nombre, precio 
            FROM producto 
            WHERE id_emprendedor = %s AND estado = 'disponible'
            ORDER BY nombre
        """, (id_emprendedor,))
        return [{'id': row[0], 'nombre': row[1], 'precio': float(row[2])} for row in cur.fetchall()]

def obtener_comentarios_por_publicacion(id_publicacion):
    """Devuelve todos los comentarios de una publicación, ordenados jerárquicamente."""
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 
                c.id_comentario,
                c.texto,
                c.fecha,
                u.nombre as autor,
                u.id_usuario as autor_id,
                c.id_comentario_padre
            FROM comentario c
            JOIN usuario u ON c.id_usuario = u.id_usuario
            WHERE c.id_publicacion = %s
            ORDER BY c.fecha ASC
        """, (id_publicacion,))
        comentarios_raw = cur.fetchall()
    
    # Construir estructura anidada (diccionario con hijos)
    comentarios_dict = {}
    for row in comentarios_raw:
        comentarios_dict[row[0]] = {
            'id': row[0],
            'texto': row[1],
            'fecha': row[2],
            'autor': row[3],
            'autor_id': row[4],
            'padre_id': row[5],
            'respuestas': []
        }
    
    # Construir árbol
    comentarios_raiz = []
    for com in comentarios_dict.values():
        if com['padre_id'] is None:
            comentarios_raiz.append(com)
        else:
            padre = comentarios_dict.get(com['padre_id'])
            if padre:
                padre['respuestas'].append(com)
    return comentarios_raiz

def obtener_publicacion_por_id(id_publicacion):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 
                p.id_publicacion,
                p.titulo,
                p.descripcion,
                p.tipo_contenido,
                p.url_multimedia,
                p.fecha_publicacion,
                u.nombre as nombre_emprendedor,
                u.id_usuario as emprendedor_id
            FROM publicacion p
            JOIN usuario u ON p.id_emprendedor = u.id_usuario
            WHERE p.id_publicacion = %s AND p.activo = TRUE
        """, (id_publicacion,))
        row = cur.fetchone()
        if not row:
            return None
        return {
            'id': row[0],
            'titulo': row[1],
            'descripcion': row[2],
            'tipo_contenido': row[3],
            'url_multimedia': row[4],
            'fecha_publicacion': row[5],
            'nombre_emprendedor': row[6],
            'emprendedor_id': row[7]
        }