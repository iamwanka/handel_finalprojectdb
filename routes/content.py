from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from services.db_service import (ejecutar_funcion_tabla, ejecutar_funcion, 
                                 obtener_productos_por_emprendedor,
                                 obtener_comentarios_por_publicacion,
                                 obtener_publicacion_por_id, obtener_recomendaciones)
import re

content_bp = Blueprint('content', __name__)

@content_bp.route('/feed')
@login_required
def feed():
    pagina = request.args.get('pagina', 1, type=int)
    limite = 10
    try:
        posts = ejecutar_funcion_tabla('obtener_feed', current_user.id, pagina, limite)
        # Para cada post, obtener productos asociados (primeros 2 para no saturar)
        from services.db_service import get_db
        conn = get_db()
        for post in posts:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT pr.id_producto, pr.nombre, pr.precio,
                           (SELECT url FROM imagen_producto WHERE id_producto = pr.id_producto LIMIT 1) as imagen
                    FROM publicacion_producto pp
                    JOIN producto pr ON pp.id_producto = pr.id_producto
                    WHERE pp.id_publicacion = %s
                    LIMIT 2
                """, (post['id_publicacion'],))
                productos = []
                for row in cur.fetchall():
                    productos.append({
                        'id': row[0],
                        'nombre': row[1],
                        'precio': float(row[2]),
                        'imagen': row[3]
                    })
                post['productos'] = productos
    except Exception as e:
        current_app.logger.error(f"Error al obtener feed: {e}")
        posts = []
    return render_template('feed.html', posts=posts, pagina=pagina)

@content_bp.route('/post/<int:id>', methods=['GET', 'POST'])
@login_required
def view_post(id):
    publicacion = obtener_publicacion_por_id(id)
    if not publicacion:
        flash('Publicación no encontrada', 'danger')
        return redirect(url_for('content.feed'))
    
    # Procesar nuevo comentario (principal o respuesta)
    if request.method == 'POST':
        texto = request.form.get('texto', '').strip()
        comentario_padre = request.form.get('padre_id')
        if comentario_padre and comentario_padre.strip():
            padre_id = int(comentario_padre)
        else:
            padre_id = None
        
        if not texto:
            flash('El comentario no puede estar vacío', 'warning')
        else:
            try:
                nuevo_id = ejecutar_funcion('agregar_comentario', texto, current_user.id, id, padre_id)
                flash('Comentario agregado', 'success')
            except Exception as e:
                flash(f'Error al agregar comentario: {str(e)}', 'danger')
        return redirect(url_for('content.view_post', id=id))
    
    # Obtener comentarios anidados
    comentarios = obtener_comentarios_por_publicacion(id)
    
    # Obtener productos del emprendedor
    try:
        productos = obtener_productos_por_emprendedor(publicacion['emprendedor_id'])
    except Exception as e:
        current_app.logger.error(f"Error al obtener productos: {e}")
        productos = []
    
    # Verificar si el usuario actual es dueño de la publicación (para posible edición)
    es_propietario = (current_user.id == publicacion['emprendedor_id'])
    
    return render_template('view_post.html', 
                          post=publicacion, 
                          comentarios=comentarios,
                          productos=productos,
                          es_propietario=es_propietario)


@content_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_post():
    # Solo emprendedores pueden crear publicaciones
    if 'emprendedor' not in current_user.roles:
        flash('Solo usuarios emprendedores pueden crear publicaciones.', 'warning')
        return redirect(url_for('content.feed'))
    
    productos = obtener_productos_por_emprendedor(current_user.id)
    
    if request.method == 'POST':
        titulo = request.form.get('titulo', '').strip()
        descripcion = request.form.get('descripcion', '').strip()
        tipo_contenido = request.form.get('tipo_contenido')
        url_multimedia = request.form.get('url_multimedia', '').strip()
        productos_ids = request.form.getlist('productos_ids')  # lista de strings
        
        # Validaciones básicas
        if not titulo:
            flash('El título es obligatorio.', 'danger')
            return render_template('create_post.html', productos=productos)
        
        if tipo_contenido not in ['video', 'imagen', 'texto']:
            flash('Tipo de contenido inválido.', 'danger')
            return render_template('create_post.html', productos=productos)
        
        # Para video, convertir URL de youtube a embed si es necesario
        if tipo_contenido == 'video' and url_multimedia:
            # Si es URL de youtube normal (watch?v=), convertir a embed
            if 'youtube.com/watch?v=' in url_multimedia:
                video_id = url_multimedia.split('v=')[1].split('&')[0]
                url_multimedia = f'https://www.youtube.com/embed/{video_id}'
            elif 'youtu.be/' in url_multimedia:
                video_id = url_multimedia.split('/')[-1]
                url_multimedia = f'https://www.youtube.com/embed/{video_id}'
        
        # Convertir productos_ids a lista de enteros (eliminar vacíos)
        productos_ids_int = [int(pid) for pid in productos_ids if pid]
        
        try:
            # Llamar a la función crear_publicacion de la BD
            new_post_id = ejecutar_funcion(
                'crear_publicacion',
                titulo,
                descripcion,
                tipo_contenido,
                url_multimedia if url_multimedia else None,
                current_user.id,
                productos_ids_int
            )
            flash('Publicación creada exitosamente.', 'success')
            return redirect(url_for('content.view_post', id=new_post_id))
        except Exception as e:
            flash(f'Error al crear publicación: {str(e)}', 'danger')
            current_app.logger.error(f"Error crear publicación: {e}")
    
    return render_template('create_post.html', productos=productos)

@content_bp.route('/search')
@login_required
def search():
    query = request.args.get('q', '').strip()
    pagina = request.args.get('pagina', 1, type=int)
    limite = 10
    
    if not query:
        flash('Ingresa un término de búsqueda', 'warning')
        return redirect(url_for('content.feed'))
    
    try:
        from services.db_service import ejecutar_funcion_tabla
        resultados = ejecutar_funcion_tabla('buscar_publicaciones', query, pagina, limite)
    except Exception as e:
        current_app.logger.error(f"Error en búsqueda: {e}")
        resultados = []
    
    return render_template('search_results.html', query=query, results=resultados, pagina=pagina)

@content_bp.route('/recommendations')
@login_required
def recommendations():
    try:
        recomendaciones = obtener_recomendaciones(current_user.id, 10)
    except Exception as e:
        current_app.logger.error(f"Error en recomendaciones: {e}")
        recomendaciones = []
    return render_template('recommendations.html', recomendaciones=recomendaciones)

@content_bp.route('/saved')
@login_required
def saved_posts():
    pagina = request.args.get('pagina', 1, type=int)
    limite = 10
    try:
        from services.db_service import obtener_guardados
        posts = obtener_guardados(current_user.id, pagina, limite)
    except Exception as e:
        current_app.logger.error(f"Error al obtener guardados: {e}")
        posts = []
    return render_template('saved_posts.html', posts=posts, pagina=pagina)

@content_bp.route('/finalizar-compra', methods=['POST'])
@login_required
def finalizar_compra():
    id_producto = request.form.get('id_producto', type=int)
    monto = request.form.get('monto', type=float)
    
    if not id_producto or not monto:
        flash('Datos de compra incompletos', 'danger')
        return redirect(url_for('content.feed'))
    
    try:
        from services.db_service import get_db
        conn = get_db()
        with conn.cursor() as cur:
            # Registrar la transacción usando el procedimiento almacenado
            cur.execute("CALL registrar_transaccion(%s, %s, %s)", (current_user.id, id_producto, monto))
            conn.commit()
        
        flash('Compra realizada con éxito', 'success')
        # Redirigir a la página de reseña para ese producto
        return redirect(url_for('content.resenar_producto', id_producto=id_producto))
    except Exception as e:
        flash(f'Error al procesar compra: {str(e)}', 'danger')
        return redirect(url_for('content.feed'))

@content_bp.route('/resenar/<int:id_producto>', methods=['GET', 'POST'])
@login_required
def resenar_producto(id_producto):
    # Obtener información del producto y del vendedor
    from services.db_service import get_db
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT p.nombre, p.id_emprendedor, u.nombre as vendedor
            FROM producto p
            JOIN usuario u ON p.id_emprendedor = u.id_usuario
            WHERE p.id_producto = %s
        """, (id_producto,))
        producto = cur.fetchone()
        if not producto:
            flash('Producto no encontrado', 'danger')
            return redirect(url_for('content.feed'))
        nombre_producto, id_vendedor, nombre_vendedor = producto
    
    if request.method == 'POST':
        calificacion = request.form.get('calificacion', type=int)
        comentario = request.form.get('comentario', '').strip()
        
        if not calificacion or calificacion < 1 or calificacion > 5:
            flash('Calificación inválida (1-5)', 'danger')
            return render_template('resenar.html', nombre_producto=nombre_producto, vendedor=nombre_vendedor)
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO resena (calificacion, comentario, id_comprador, id_vendedor, id_producto)
                    VALUES (%s, %s, %s, %s, %s)
                """, (calificacion, comentario, current_user.id, id_vendedor, id_producto))
                conn.commit()
            flash('Gracias por tu reseña', 'success')
            return redirect(url_for('content.purchases'))
        except Exception as e:
            flash(f'Error al guardar reseña: {str(e)}', 'danger')
    
    return render_template('resenar.html', nombre_producto=nombre_producto, vendedor=nombre_vendedor)

@content_bp.route('/purchases')
@login_required
def purchases():
    from services.db_service import get_db
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT t.id_transaccion, t.fecha, t.monto, t.estado,
                   p.nombre as producto_nombre, u.nombre as vendedor_nombre,
                   r.calificacion, r.comentario
            FROM transaccion t
            JOIN producto p ON t.id_producto = p.id_producto
            JOIN usuario u ON p.id_emprendedor = u.id_usuario
            LEFT JOIN resena r ON r.id_producto = p.id_producto AND r.id_comprador = t.id_comprador
            WHERE t.id_comprador = %s
            ORDER BY t.fecha DESC
        """, (current_user.id,))
        rows = cur.fetchall()
        purchases = []
        for row in rows:
            purchases.append({
                'id': row[0],
                'fecha': row[1],
                'monto': float(row[2]),
                'estado': row[3],
                'producto': row[4],
                'vendedor': row[5],
                'calificacion': row[6],
                'comentario': row[7]
            })
    return render_template('purchases.html', purchases=purchases)

@content_bp.route('/perfil/<int:id>')
@login_required
def perfil(id):
    from services.db_service import obtener_perfil_usuario, obtener_publicaciones_por_usuario
    user = obtener_perfil_usuario(id)
    if not user:
        flash('Usuario no encontrado', 'danger')
        return redirect(url_for('content.feed'))
    
    pagina = request.args.get('pagina', 1, type=int)
    posts = obtener_publicaciones_por_usuario(id, pagina)
    
    es_propio = (current_user.id == id)
    return render_template('perfil.html', user=user, posts=posts, pagina=pagina, es_propio=es_propio)

@content_bp.route('/editar-perfil', methods=['GET', 'POST'])
@login_required
def editar_perfil():
    from services.db_service import get_db
    conn = get_db()
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        telefono = request.form.get('telefono', '').strip()
        if not nombre:
            flash('El nombre es obligatorio', 'danger')
        else:
            with conn.cursor() as cur:
                cur.execute("UPDATE usuario SET nombre = %s, telefono = %s WHERE id_usuario = %s", (nombre, telefono, current_user.id))
                conn.commit()
            flash('Perfil actualizado', 'success')
            return redirect(url_for('content.perfil', id=current_user.id))
    # GET: mostrar datos actuales
    with conn.cursor() as cur:
        cur.execute("SELECT nombre, telefono FROM usuario WHERE id_usuario = %s", (current_user.id,))
        row = cur.fetchone()
        nombre = row[0]
        telefono = row[1] if row[1] else ''
    return render_template('editar_perfil.html', nombre=nombre, telefono=telefono)

@content_bp.route('/my-stats')
@login_required
def my_stats():
    if 'emprendedor' not in current_user.roles:
        flash('Esta página es solo para emprendedores', 'warning')
        return redirect(url_for('content.feed'))
    from services.db_service import obtener_metricas_emprendedor
    metrics = obtener_metricas_emprendedor(current_user.id)
    return render_template('my_stats.html', metrics=metrics)

@content_bp.route('/productos/crear', methods=['GET', 'POST'])
@login_required
def crear_producto():
    if 'emprendedor' not in current_user.roles:
        flash('Solo emprendedores pueden crear productos', 'warning')
        return redirect(url_for('content.feed'))
    
    from services.db_service import get_db
    conn = get_db()
    # Obtener categorías
    with conn.cursor() as cur:
        cur.execute("SELECT id_categoria, nombre FROM categoria ORDER BY nombre")
        categorias = cur.fetchall()
    
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        descripcion = request.form.get('descripcion', '').strip()
        precio = request.form.get('precio', type=float)
        id_categoria = request.form.get('id_categoria', type=int)
        imagen_url = request.form.get('imagen_url', '').strip()
        
        if not nombre or not precio or not id_categoria:
            flash('Nombre, precio y categoría son obligatorios', 'danger')
        else:
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO producto (nombre, descripcion, precio, id_emprendedor, id_categoria)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING id_producto
                    """, (nombre, descripcion, precio, current_user.id, id_categoria))
                    new_id = cur.fetchone()[0]
                    if imagen_url:
                        cur.execute("INSERT INTO imagen_producto (url, id_producto) VALUES (%s, %s)", (imagen_url, new_id))
                    conn.commit()
                flash('Producto creado exitosamente', 'success')
                return redirect(url_for('content.mis_productos'))
            except Exception as e:
                flash(f'Error al crear producto: {str(e)}', 'danger')
    
    return render_template('crear_producto.html', categorias=categorias)

@content_bp.route('/mis-productos')
@login_required
def mis_productos():
    if 'emprendedor' not in current_user.roles:
        flash('Esta página es solo para emprendedores', 'warning')
        return redirect(url_for('content.feed'))
    from services.db_service import obtener_productos_por_emprendedor
    productos = obtener_productos_por_emprendedor(current_user.id)
    return render_template('mis_productos.html', productos=productos)