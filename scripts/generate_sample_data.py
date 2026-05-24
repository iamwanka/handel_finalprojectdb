#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para poblar la base de datos social_app_db con datos de prueba.
Requiere: psycopg2, faker, requests, beautifulsoup4
"""

import os
import sys
import random
import requests
from bs4 import BeautifulSoup
from faker import Faker
import psycopg2
from psycopg2 import sql
from datetime import datetime, timedelta

# ======================================================
# Configuración
# ======================================================

DB_NAME = "social_app_db"
DB_USER = "postgres"          # Cambia si usas otro usuario
DB_PASSWORD = "root" # ¡Cámbiala!
DB_HOST = "localhost"
DB_PORT = "5432"

# Cantidades
NUM_USERS = 150               # Usuarios totales (incluye emprendedores y solo compradores)
NUM_PRODUCTS = 200            # Productos
NUM_POSTS = 180               # Publicaciones (algunos usuarios publican varios)
MAX_COMMENTS_PER_POST = 15    # Comentarios por publicación (máximo)
MAX_RESPONSES_PER_COMMENT = 3 # Respuestas máximas a un comentario
MAX_LIKES_PER_USER = 50       # Likes que dará cada usuario (aprox)
MAX_SAVED_PER_USER = 30       # Guardados por usuario

# Proporción de usuarios que serán emprendedores (los que pueden publicar)
PROB_ENTREPRENEUR = 0.6

# URLs de videos de ejemplo (reales de YouTube, dominio público o de muestra)
VIDEO_URLS = [
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # ejemplo
    "https://www.youtube.com/watch?v=9bZkp7q19f0",
    "https://www.youtube.com/watch?v=3JZ_D3ELwOQ",
    "https://www.youtube.com/watch?v=5qap5aO4i9A",
    "https://www.youtube.com/watch?v=JGwWNGJdvx8",
    "https://www.youtube.com/watch?v=1vrEljMfXYo",
    "https://www.youtube.com/watch?v=K4DyBUG242c",
    "https://www.youtube.com/watch?v=fJ9rUzIMcZQ",
    "https://www.youtube.com/watch?v=YQHsXMglC9A",
    "https://www.youtube.com/watch?v=wZZ7oFKsKzY",
]

# URLs de imágenes de ejemplo (placeholder)
IMAGE_URLS = [
    "https://picsum.photos/id/1/200/300",
    "https://picsum.photos/id/10/200/300",
    "https://picsum.photos/id/100/200/300",
    "https://picsum.photos/id/101/200/300",
    "https://picsum.photos/id/104/200/300",
]

fake = Faker(['es_ES'])  # Datos en español

# ======================================================
# Conexión a la base de datos
# ======================================================

def get_db_connection():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

# ======================================================
# Funciones auxiliares
# ======================================================

def ejecutar_funcion(conn, funcion, *args):
    """Ejecuta una función de PostgreSQL y devuelve el resultado (primera columna de la primera fila)."""
    with conn.cursor() as cur:
        # Construir la llamada: SELECT funcion(param1, param2, ...)
        placeholders = ','.join(['%s'] * len(args))
        cur.execute(f"SELECT {funcion}({placeholders})", args)
        resultado = cur.fetchone()
        if resultado is None:
            return None
        return resultado[0]

def ejecutar_sql(conn, sql_str, params=None):
    with conn.cursor() as cur:
        cur.execute(sql_str, params)
        # No devuelve nada

def obtener_categorias(conn):
    """Devuelve lista de ids de categorías existentes."""
    with conn.cursor() as cur:
        cur.execute("SELECT id_categoria FROM categoria")
        return [row[0] for row in cur.fetchall()]

def obtener_ids_emprendedores(conn):
    """Devuelve lista de id_usuario de usuarios que tienen rol emprendedor."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT u.id_usuario FROM usuario u
            JOIN usuario_rol ur ON u.id_usuario = ur.id_usuario
            JOIN rol r ON ur.id_rol = r.id_rol
            WHERE r.nombre_rol = 'emprendedor'
        """)
        return [row[0] for row in cur.fetchall()]

def obtener_ids_usuarios(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT id_usuario FROM usuario")
        return [row[0] for row in cur.fetchall()]

def registrar_usuario(conn, nombre, email, password, hacer_emprendedor=False):
    """Registra un usuario usando la función registrar_usuario de la BD."""
    user_id = ejecutar_funcion(conn, "registrar_usuario", nombre, email, password)
    if hacer_emprendedor:
        # Agregar rol emprendedor al usuario recién creado
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO usuario_rol (id_usuario, id_rol)
                VALUES (%s, (SELECT id_rol FROM rol WHERE nombre_rol = 'emprendedor'))
            """, (user_id,))
    return user_id

def crear_producto(conn, nombre, descripcion, precio, id_emprendedor, id_categoria):
    """Inserta producto directamente (no usamos función, pero podemos usar INSERT)."""
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO producto (nombre, descripcion, precio, id_emprendedor, id_categoria)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id_producto
        """, (nombre, descripcion, precio, id_emprendedor, id_categoria))
        return cur.fetchone()[0]

def crear_publicacion(conn, titulo, descripcion, tipo_contenido, url_multimedia, id_emprendedor, productos_ids):
    """Llama a la función crear_publicacion de la BD."""
    # La función espera un array de enteros en PostgreSQL, lo pasamos como lista de Python
    return ejecutar_funcion(conn, "crear_publicacion", titulo, descripcion, tipo_contenido, url_multimedia, id_emprendedor, productos_ids)

def agregar_comentario(conn, texto, id_usuario, id_publicacion, id_padre=None):
    return ejecutar_funcion(conn, "agregar_comentario", texto, id_usuario, id_publicacion, id_padre)

def toggle_like(conn, id_usuario, id_publicacion):
    return ejecutar_funcion(conn, "toggle_like", id_usuario, id_publicacion)

def registrar_visualizacion(conn, id_usuario, id_publicacion, ip=None):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO visualizacion (id_usuario, id_publicacion, ip_origen)
            VALUES (%s, %s, %s)
        """, (id_usuario, id_publicacion, ip))
def registrar_evento_conversion(conn, tipo_evento, id_usuario, id_publicacion, id_producto):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO evento_conversion (tipo_evento, id_usuario, id_publicacion, id_producto)
            VALUES (%s, %s, %s, %s)
        """, (tipo_evento, id_usuario, id_publicacion, id_producto))

def registrar_guardado(conn, id_usuario, id_publicacion):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO guardado (id_usuario, id_publicacion)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
        """, (id_usuario, id_publicacion))

def registrar_transaccion(conn, id_comprador, id_producto, monto):
    # Usar el procedimiento almacenado
    with conn.cursor() as cur:
        cur.execute("CALL registrar_transaccion(%s, %s, %s)", (id_comprador, id_producto, monto))

def crear_resena(conn, calificacion, comentario, id_comprador, id_vendedor, id_producto):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO resena (calificacion, comentario, id_comprador, id_vendedor, id_producto)
            VALUES (%s, %s, %s, %s, %s)
        """, (calificacion, comentario, id_comprador, id_vendedor, id_producto))

# ======================================================
# Generación principal
# ======================================================

def main():
    conn = get_db_connection()
    # Autocommit para no tener que hacer commit manualmente después de cada operación
    conn.autocommit = True

    print("📌 Generando usuarios...")
    users = []  # lista de (id, email, es_emprendedor)
    for i in range(NUM_USERS):
        nombre = fake.name()
        email = fake.email()
        password = "123456"  # Contraseña fija para pruebas, luego puedes cambiarla
        es_emprendedor = random.random() < PROB_ENTREPRENEUR
        user_id = registrar_usuario(conn, nombre, email, password, hacer_emprendedor=es_emprendedor)
        users.append((user_id, email, es_emprendedor))
        if (i+1) % 20 == 0:
            print(f"   {i+1} usuarios creados...")
    print(f"✅ {len(users)} usuarios creados ({sum(1 for u in users if u[2])} emprendedores)")

    # Obtener IDs de emprendedores (pueden tener más de un rol)
    emprendedores_ids = [uid for uid, _, es in users if es]
    print(f"Emprendedores identificados: {len(emprendedores_ids)}")

    # Obtener categorías existentes
    categorias = obtener_categorias(conn)
    if not categorias:
        print("⚠️ No hay categorías en la BD. Debes insertarlas previamente (script lo hizo).")
        sys.exit(1)
    print(f"📌 Categorías disponibles: {len(categorias)}")

    # Generar productos
    print("📌 Generando productos...")
    productos = []  # lista de (id_producto, id_emprendedor)
    for i in range(NUM_PRODUCTS):
        nombre = fake.catch_phrase()
        descripcion = fake.paragraph(nb_sentences=3)
        precio = round(random.uniform(2000, 150000), 2)
        id_emprendedor = random.choice(emprendedores_ids) if emprendedores_ids else None
        id_categoria = random.choice(categorias)
        if id_emprendedor is None:
            continue
        pid = crear_producto(conn, nombre, descripcion, precio, id_emprendedor, id_categoria)
        productos.append((pid, id_emprendedor))
        # Añadir una o dos imágenes aleatorias al producto
        num_imgs = random.randint(1, 3)
        for _ in range(num_imgs):
            url_img = random.choice(IMAGE_URLS)
            with conn.cursor() as cur:
                cur.execute("INSERT INTO imagen_producto (url, id_producto) VALUES (%s, %s)", (url_img, pid))
        if (i+1) % 50 == 0:
            print(f"   {i+1} productos creados...")
    print(f"✅ {len(productos)} productos creados")

    # Crear publicaciones (solo emprendedores pueden publicar)
    print("📌 Generando publicaciones...")
    posts = []  # lista de id_publicacion
    # Organizar productos por emprendedor para asociarlos rápidamente
    productos_por_emprendedor = {}
    for pid, eid in productos:
        productos_por_emprendedor.setdefault(eid, []).append(pid)

    for i in range(NUM_POSTS):
        if not emprendedores_ids:
            break
        id_emprendedor = random.choice(emprendedores_ids)
        titulo = fake.sentence(nb_words=6)
        descripcion = fake.paragraph(nb_sentences=2)
        # Elegir tipo de contenido y URL correspondiente
        tipo = random.choices(['video', 'imagen', 'texto'], weights=[0.5, 0.3, 0.2])[0]
        if tipo == 'video':
            url = random.choice(VIDEO_URLS)
        elif tipo == 'imagen':
            url = random.choice(IMAGE_URLS)
        else:
            url = None
        # Seleccionar 1 a 3 productos del mismo emprendedor para asociar
        prods_disp = productos_por_emprendedor.get(id_emprendedor, [])
        if not prods_disp:
            # Si el emprendedor no tiene productos aún, omitimos publicación o creamos sin productos
            productos_ids = []
        else:
            num_prods = random.randint(1, min(3, len(prods_disp)))
            productos_ids = random.sample(prods_disp, num_prods)
        pid_post = crear_publicacion(conn, titulo, descripcion, tipo, url, id_emprendedor, productos_ids)
        posts.append(pid_post)
        if (i+1) % 30 == 0:
            print(f"   {i+1} publicaciones creadas...")
    print(f"✅ {len(posts)} publicaciones creadas")

    # Obtener todos los usuarios (incluidos compradores) para interacciones
    all_users = obtener_ids_usuarios(conn)
    print(f"📌 Usuarios disponibles para interacciones: {len(all_users)}")

    # Generar comentarios (anidados)
    print("📌 Generando comentarios...")
    comentarios_ids = []  # solo para referencia
    for post_id in posts:
        num_comments = random.randint(0, MAX_COMMENTS_PER_POST)
        for _ in range(num_comments):
            autor = random.choice(all_users)
            texto = fake.paragraph(nb_sentences=1)
            com_id = agregar_comentario(conn, texto, autor, post_id, None)
            comentarios_ids.append((com_id, post_id, autor))
            # Posibles respuestas a este comentario
            num_resp = random.randint(0, MAX_RESPONSES_PER_COMMENT)
            for __ in range(num_resp):
                autor_resp = random.choice(all_users)
                texto_resp = fake.sentence()
                agregar_comentario(conn, texto_resp, autor_resp, post_id, com_id)
    print(f"✅ Comentarios generados (incluidas respuestas)")

    # Likes
    print("📌 Generando likes...")
    # Para evitar que un usuario dé like muchas veces a la misma publicación, usamos un set
    liked_pairs = set()
    for user_id in all_users:
        num_likes = random.randint(0, MAX_LIKES_PER_USER)
        posts_copia = posts.copy()
        random.shuffle(posts_copia)
        for post_id in posts_copia[:num_likes]:
            if (user_id, post_id) not in liked_pairs:
                toggle_like(conn, user_id, post_id)
                liked_pairs.add((user_id, post_id))
    print(f"✅ Likes generados: {len(liked_pairs)}")

    # Guardados
    print("📌 Generando guardados...")
    saved_pairs = set()
    for user_id in all_users:
        num_saved = random.randint(0, MAX_SAVED_PER_USER)
        posts_copia = posts.copy()
        random.shuffle(posts_copia)
        for post_id in posts_copia[:num_saved]:
            if (user_id, post_id) not in saved_pairs:
                registrar_guardado(conn, user_id, post_id)
                saved_pairs.add((user_id, post_id))
    print(f"✅ Guardados generados: {len(saved_pairs)}")

    # Visualizaciones y eventos de conversión (algunas publicaciones tendrán muchos eventos)
    print("📌 Generando visualizaciones y eventos de conversión...")
    total_visualizaciones = 0
    total_conversiones = 0
    for post_id in posts:
        # Visualizaciones: entre 10 y 500 por publicación
        num_vis = random.randint(10, 500)
        for _ in range(num_vis):
            usuario_vis = random.choice(all_users) if random.random() < 0.8 else None  # 80% usuarios logueados
            registrar_visualizacion(conn, usuario_vis, post_id, fake.ipv4())
            total_visualizaciones += 1
        # Eventos de conversión: entre 0 y 30 por publicación
        num_conv = random.randint(0, 30)
        for _ in range(num_conv):
            usuario_conv = random.choice(all_users)
            tipo = random.choice(['clic_comprar', 'clic_contactar'])
            # Seleccionar un producto asociado a la publicación (si los hay)
            with conn.cursor() as cur:
                cur.execute("SELECT id_producto FROM publicacion_producto WHERE id_publicacion = %s LIMIT 1", (post_id,))
                prod_row = cur.fetchone()
                if prod_row:
                    prod_id = prod_row[0]
                else:
                    # Si no hay productos, elegimos uno aleatorio de cualquier emprendedor
                    prod_id = random.choice([p for p, _ in productos])
            registrar_evento_conversion(conn, tipo, usuario_conv, post_id, prod_id)
            total_conversiones += 1
    print(f"✅ Visualizaciones: {total_visualizaciones}, Eventos de conversión: {total_conversiones}")

    # Transacciones (compras) y reseñas
    print("📌 Generando transacciones y reseñas...")
    # Primero obtener usuarios compradores (todos, pues todos tienen rol comprador por defecto)
    compradores = all_users
    # Productos que aún no estén agotados (estado 'disponible')
    with conn.cursor() as cur:
        cur.execute("SELECT id_producto, id_emprendedor, precio FROM producto WHERE estado = 'disponible'")
        productos_disponibles = cur.fetchall()
    num_transacciones = min(len(productos_disponibles), 100)  # máximo 100 transacciones
    transacciones_creadas = 0
    for prod_id, vendedor_id, precio in productos_disponibles[:num_transacciones]:
        comprador = random.choice([c for c in compradores if c != vendedor_id])  # no auto-compra
        monto = precio
        try:
            registrar_transaccion(conn, comprador, prod_id, monto)
            transacciones_creadas += 1
            # Crear una reseña después de la transacción
            calificacion = random.randint(3, 5)  # generalmente positivas
            comentario_res = fake.sentence()
            crear_resena(conn, calificacion, comentario_res, comprador, vendedor_id, prod_id)
        except Exception as e:
            print(f"   Error en transacción: {e}")
    print(f"✅ Transacciones creadas: {transacciones_creadas}")

    # Refrescar la vista materializada (opcional)
    print("📌 Refrescando vista materializada de métricas...")
    with conn.cursor() as cur:
        cur.execute("REFRESH MATERIALIZED VIEW vista_materializada_metricas")
    print("✅ Vista materializada actualizada")

    print("\n🎉 POBLACIÓN COMPLETADA CON ÉXITO")
    print(f"Resumen: {len(users)} usuarios, {len(productos)} productos, {len(posts)} publicaciones, {total_visualizaciones} visualizaciones, {total_conversiones} eventos, {transacciones_creadas} transacciones.")
    conn.close()

if __name__ == "__main__":
    main()