from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required
from utils.decorators import admin_required
from services.db_service import get_db

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    # Obtener conteos para el dashboard
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM usuario")
        total_usuarios = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM publicacion")
        total_publicaciones = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM producto")
        total_productos = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM comentario")
        total_comentarios = cur.fetchone()[0]
    return render_template('admin/dashboard.html',
                         total_usuarios=total_usuarios,
                         total_publicaciones=total_publicaciones,
                         total_productos=total_productos,
                         total_comentarios=total_comentarios)

@admin_bp.route('/tabla/<string:tabla>')
@login_required
@admin_required
def ver_tabla(tabla):
    tablas_permitidas = ['usuario', 'publicacion', 'producto', 'comentario']
    if tabla not in tablas_permitidas:
        flash('Tabla no permitida', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    conn = get_db()
    with conn.cursor() as cur:
        # Obtener todas las filas
        cur.execute(f"SELECT * FROM {tabla} ORDER BY 1 DESC LIMIT 100")
        rows = cur.fetchall()
        # Obtener nombres de columnas
        columnas = [desc[0] for desc in cur.description]
    return render_template('admin/table_view.html', tabla=tabla, columnas=columnas, rows=rows)

@admin_bp.route('/eliminar/<string:tabla>/<int:id>')
@login_required
@admin_required
def eliminar_registro(tabla, id):
    tablas_permitidas = {
        'usuario': 'id_usuario',
        'publicacion': 'id_publicacion',
        'producto': 'id_producto',
        'comentario': 'id_comentario'
    }
    if tabla not in tablas_permitidas:
        flash('Tabla no permitida', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    pk_column = tablas_permitidas[tabla]
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(f"DELETE FROM {tabla} WHERE {pk_column} = %s", (id,))
        conn.commit()
    flash(f'Registro eliminado de {tabla}', 'success')
    return redirect(url_for('admin.ver_tabla', tabla=tabla))