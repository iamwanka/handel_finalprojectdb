from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from services.db_service import (ejecutar_funcion_tabla, ejecutar_funcion, 
                                 obtener_productos_por_emprendedor,
                                 obtener_comentarios_por_publicacion,
                                 obtener_publicacion_por_id)
import re

content_bp = Blueprint('content', __name__)

@content_bp.route('/feed')
@login_required
def feed():
    pagina = request.args.get('pagina', 1, type=int)
    limite = 10
    try:
        posts = ejecutar_funcion_tabla('obtener_feed', current_user.id, pagina, limite)
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
    
    # Verificar si el usuario actual es dueño de la publicación (para posible edición)
    es_propietario = (current_user.id == publicacion['emprendedor_id'])
    
    return render_template('view_post.html', 
                          post=publicacion, 
                          comentarios=comentarios,
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
