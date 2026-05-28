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
    """Devuelve lista de productos de un emprendedor, incluyendo la primera imagen."""
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 
                p.id_producto, 
                p.nombre, 
                p.precio,
                (SELECT url FROM imagen_producto WHERE id_producto = p.id_producto LIMIT 1) as imagen
            FROM producto p
            WHERE p.id_emprendedor = %s AND p.estado = 'disponible'
            ORDER BY p.nombre
        """, (id_emprendedor,))
        return [{'id': row[0], 'nombre': row[1], 'precio': float(row[2]), 'imagen': row[3]} for row in cur.fetchall()]

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

def obtener_publicacion_por_id(id_publicacion, id_usuario=None):
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
                u.id_usuario as emprendedor_id,
                vr.promedio_calificaciones,
                vr.total_resenas,
                COUNT(DISTINCT l.id_usuario) as num_likes,
                COUNT(DISTINCT g.id_usuario) as num_guardados,
                COUNT(DISTINCT c.id_comentario) as num_comentarios
            FROM publicacion p
            JOIN usuario u ON p.id_emprendedor = u.id_usuario
            LEFT JOIN vista_emprendedor_reputacion vr ON u.id_usuario = vr.id_usuario
            LEFT JOIN likes l ON p.id_publicacion = l.id_publicacion
            LEFT JOIN guardado g ON p.id_publicacion = g.id_publicacion
            LEFT JOIN comentario c ON p.id_publicacion = c.id_publicacion
            WHERE p.id_publicacion = %s AND p.activo = TRUE
            GROUP BY p.id_publicacion, u.nombre, u.id_usuario, vr.promedio_calificaciones, vr.total_resenas
        """, (id_publicacion,))
        row = cur.fetchone()
        if not row:
            return None
        
        # Verificar si el usuario actual le dio like o guardó
        me_gusta = False
        me_guardado = False
        if id_usuario:
            with conn.cursor() as cur2:
                cur2.execute("SELECT 1 FROM likes WHERE id_usuario = %s AND id_publicacion = %s", 
                           (id_usuario, id_publicacion))
                me_gusta = cur2.fetchone() is not None
                
                cur2.execute("SELECT 1 FROM guardado WHERE id_usuario = %s AND id_publicacion = %s", 
                           (id_usuario, id_publicacion))
                me_guardado = cur2.fetchone() is not None
        
        return {
            'id': row[0],
            'id_publicacion': row[0],
            'titulo': row[1],
            'descripcion': row[2],
            'tipo_contenido': row[3],
            'url_multimedia': row[4],
            'fecha_publicacion': row[5],
            'nombre_emprendedor': row[6],
            'emprendedor_id': row[7],
            'promedio_calificacion': float(row[8]) if row[8] else None,
            'total_resenas': row[9] or 0,
            'num_likes': row[10],
            'num_guardados': row[11],
            'num_comentarios': row[12],
            'me_gusta': me_gusta,
            'me_guardado': me_guardado
        }

def obtener_recomendaciones(id_usuario, limite=10):
    """Llama a la función recomendar_publicaciones y devuelve lista de diccionarios."""
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM recomendar_publicaciones(%s, %s)", (id_usuario, limite))
        columnas = [desc[0] for desc in cur.description]
        resultados = [dict(zip(columnas, row)) for row in cur.fetchall()]
        return resultados
    
def obtener_reporte_emprendedores(limite=10):
    """Llama a la función reporte_emprendedores_top y devuelve lista de diccionarios."""
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM reporte_emprendedores_top(%s)", (limite,))
        columnas = [desc[0] for desc in cur.description]
        resultados = [dict(zip(columnas, row)) for row in cur.fetchall()]
        return resultados

def toggle_guardado(id_usuario, id_publicacion):
    """Llama a la función toggle_guardado y devuelve el nuevo estado (True=guardado, False=no guardado)."""
    return ejecutar_funcion('toggle_guardado', id_usuario, id_publicacion)

def obtener_guardados(id_usuario, pagina=1, limite=10):
    """Devuelve publicaciones guardadas por el usuario (paginated)."""
    conn = get_db()
    offset = (pagina - 1) * limite
    with conn.cursor() as cur:
        cur.execute("""
            SELECT p.id_publicacion, p.titulo, p.tipo_contenido, p.url_multimedia,
                   p.fecha_publicacion, u.nombre as emprendedor,
                   (SELECT COUNT(*) FROM likes l WHERE l.id_publicacion = p.id_publicacion) as num_likes,
                   (SELECT COUNT(*) FROM comentario c WHERE c.id_publicacion = p.id_publicacion) as num_comentarios
            FROM guardado g
            JOIN publicacion p ON g.id_publicacion = p.id_publicacion
            JOIN usuario u ON p.id_emprendedor = u.id_usuario
            WHERE g.id_usuario = %s AND p.activo = TRUE
            ORDER BY g.fecha DESC
            LIMIT %s OFFSET %s
        """, (id_usuario, limite, offset))
        columnas = [desc[0] for desc in cur.description]
        posts = [dict(zip(columnas, row)) for row in cur.fetchall()]
        return posts
    
def obtener_perfil_usuario(id_usuario):
    """Devuelve información básica del usuario y su calificación promedio como vendedor."""
    conn = get_db()
    with conn.cursor() as cur:
        # Datos básicos
        cur.execute("SELECT id_usuario, nombre, email, fecha_registro, telefono, verificado FROM usuario WHERE id_usuario = %s", (id_usuario,))
        user_row = cur.fetchone()
        if not user_row:
            return None
        user = {
            'id': user_row[0],
            'nombre': user_row[1],
            'email': user_row[2],
            'fecha_registro': user_row[3],
            'telefono': user_row[4],
            'verificado': user_row[5]
        }
        # Calificación promedio como vendedor (desde reseñas)
        cur.execute("SELECT AVG(calificacion) FROM resena WHERE id_vendedor = %s", (id_usuario,))
        avg = cur.fetchone()[0]
        user['calificacion_promedio'] = round(avg, 1) if avg else None
        # Número de reseñas
        cur.execute("SELECT COUNT(*) FROM resena WHERE id_vendedor = %s", (id_usuario,))
        user['total_resenas'] = cur.fetchone()[0]
        return user

def obtener_publicaciones_por_usuario(id_usuario, pagina=1, limite=10):
    """Devuelve publicaciones de un usuario (para mostrar en su perfil)."""
    conn = get_db()
    offset = (pagina - 1) * limite
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id_publicacion, titulo, tipo_contenido, url_multimedia, fecha_publicacion,
                   (SELECT COUNT(*) FROM likes WHERE id_publicacion = p.id_publicacion) as num_likes,
                   (SELECT COUNT(*) FROM comentario WHERE id_publicacion = p.id_publicacion) as num_comentarios
            FROM publicacion p
            WHERE id_emprendedor = %s AND activo = TRUE
            ORDER BY fecha_publicacion DESC
            LIMIT %s OFFSET %s
        """, (id_usuario, limite, offset))
        columnas = [desc[0] for desc in cur.description]
        posts = [dict(zip(columnas, row)) for row in cur.fetchall()]
        return posts
    
def obtener_metricas_emprendedor(id_emprendedor):
    """Devuelve métricas agregadas de las publicaciones y productos de un emprendedor."""
    conn = get_db()
    with conn.cursor() as cur:
        # Métricas generales
        cur.execute("""
            SELECT 
                COUNT(DISTINCT p.id_publicacion) as total_posts,
                COUNT(DISTINCT l.id_usuario) as total_likes,
                COUNT(DISTINCT c.id_comentario) as total_comentarios,
                SUM(CASE WHEN ev.tipo_evento = 'clic_comprar' THEN 1 ELSE 0 END) as total_conversiones,
                SUM(v.total_vis) as total_visualizaciones
            FROM usuario u
            LEFT JOIN publicacion p ON u.id_usuario = p.id_emprendedor AND p.activo = TRUE
            LEFT JOIN likes l ON p.id_publicacion = l.id_publicacion
            LEFT JOIN comentario c ON p.id_publicacion = c.id_publicacion
            LEFT JOIN evento_conversion ev ON p.id_publicacion = ev.id_publicacion
            LEFT JOIN (SELECT id_publicacion, COUNT(*) as total_vis FROM visualizacion GROUP BY id_publicacion) v ON p.id_publicacion = v.id_publicacion
            WHERE u.id_usuario = %s
        """, (id_emprendedor,))
        row = cur.fetchone()
        metrics = {
            'total_posts': row[0] or 0,
            'total_likes': row[1] or 0,
            'total_comentarios': row[2] or 0,
            'total_conversiones': row[3] or 0,
            'total_visualizaciones': row[4] or 0
        }
        if metrics['total_visualizaciones']:
            metrics['tasa_conversion'] = round(metrics['total_conversiones'] / metrics['total_visualizaciones'], 4)
        else:
            metrics['tasa_conversion'] = 0.0
        
        # Top 3 productos más vistos (asociados a sus publicaciones)
        cur.execute("""
            SELECT pr.nombre, COUNT(*) as total
            FROM producto pr
            JOIN publicacion_producto pp ON pr.id_producto = pp.id_producto
            JOIN publicacion p ON pp.id_publicacion = p.id_publicacion
            JOIN visualizacion v ON p.id_publicacion = v.id_publicacion
            WHERE p.id_emprendedor = %s
            GROUP BY pr.id_producto, pr.nombre
            ORDER BY total DESC
            LIMIT 3
        """, (id_emprendedor,))
        metrics['top_productos'] = [{'nombre': row[0], 'vistas': row[1]} for row in cur.fetchall()]
        
        # Rendimiento por publicación (últimas 5)
        cur.execute("""
            SELECT p.id_publicacion, p.titulo,
                   (SELECT COUNT(*) FROM likes WHERE id_publicacion = p.id_publicacion) as likes,
                   (SELECT COUNT(*) FROM comentario WHERE id_publicacion = p.id_publicacion) as comentarios,
                   (SELECT COUNT(*) FROM visualizacion WHERE id_publicacion = p.id_publicacion) as visualizaciones,
                   (SELECT COUNT(*) FROM evento_conversion WHERE id_publicacion = p.id_publicacion AND tipo_evento = 'clic_comprar') as conversiones
            FROM publicacion p
            WHERE p.id_emprendedor = %s AND p.activo = TRUE
            ORDER BY p.fecha_publicacion DESC
            LIMIT 5
        """, (id_emprendedor,))
        cols = ['id', 'titulo', 'likes', 'comentarios', 'visualizaciones', 'conversiones']
        metrics['ultimas_publicaciones'] = [dict(zip(cols, row)) for row in cur.fetchall()]
        
        return metrics

def obtener_resenas_recibidas(id_vendedor, limite=10):
    """Devuelve las reseñas que ha recibido un vendedor (emprendedor)."""
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT r.calificacion, r.comentario, r.fecha, 
                   u.nombre as comprador_nombre, pr.nombre as producto_nombre
            FROM resena r
            JOIN usuario u ON r.id_comprador = u.id_usuario
            JOIN producto pr ON r.id_producto = pr.id_producto
            WHERE r.id_vendedor = %s
            ORDER BY r.fecha DESC
            LIMIT %s
        """, (id_vendedor, limite))
        return [{'calificacion': row[0], 'comentario': row[1], 'fecha': row[2],
                 'comprador': row[3], 'producto': row[4]} for row in cur.fetchall()]