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

@admin_bp.route('/auditoria')
@login_required
@admin_required
def ver_auditoria():
    # Obtener filtros de la URL
    tabla = request.args.get('tabla', '')
    accion = request.args.get('accion', '')
    
    conn = get_db()
    with conn.cursor() as cur:
        query = "SELECT id_log, tabla_afectada, accion, id_registro, usuario_bd, fecha, datos_viejos, datos_nuevos FROM auditoria_log WHERE 1=1"
        params = []
        if tabla:
            query += " AND tabla_afectada = %s"
            params.append(tabla)
        if accion:
            query += " AND accion = %s"
            params.append(accion)
        query += " ORDER BY fecha DESC LIMIT 200"
        cur.execute(query, params)
        rows = cur.fetchall()
        columnas = [desc[0] for desc in cur.description]
    
    # Obtener lista de tablas y acciones para los filtros
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT tabla_afectada FROM auditoria_log ORDER BY tabla_afectada")
        tablas = [row[0] for row in cur.fetchall()]
        cur.execute("SELECT DISTINCT accion FROM auditoria_log ORDER BY accion")
        acciones = [row[0] for row in cur.fetchall()]
    
    return render_template('admin/auditoria.html', 
                         rows=rows, 
                         columnas=columnas, 
                         tablas=tablas, 
                         acciones=acciones,
                         filtro_tabla=tabla,
                         filtro_accion=accion)

@admin_bp.route('/reporte-emprendedores')
@login_required
@admin_required
def reporte_emprendedores():
    try:
        from services.db_service import obtener_reporte_emprendedores
        reporte = obtener_reporte_emprendedores(20)
    except Exception as e:
        flash(f'Error al generar reporte: {e}', 'danger')
        reporte = []
    return render_template('admin/reporte_emprendedores.html', reporte=reporte)