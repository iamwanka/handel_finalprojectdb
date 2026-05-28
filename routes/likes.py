from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from services.db_service import ejecutar_funcion, toggle_guardado

likes_bp = Blueprint('likes', __name__)

@likes_bp.route('/toggle', methods=['POST'])
@login_required
def toggle_like():
    data = request.get_json()
    id_publicacion = data.get('id_publicacion')
    if not id_publicacion:
        return jsonify({'error': 'Falta id_publicacion'}), 400
    
    try:
        nuevo_estado = ejecutar_funcion('toggle_like', current_user.id, id_publicacion)
        # Obtener nuevo conteo de likes
        from services.db_service import get_db
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM likes WHERE id_publicacion = %s", (id_publicacion,))
            count = cur.fetchone()[0]
        return jsonify({
            'success': True,
            'liked': nuevo_estado,
            'count': count
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@likes_bp.route('/guardar/toggle', methods=['POST'])
@login_required
def toggle_guardar():
    data = request.get_json()
    id_publicacion = data.get('id_publicacion')
    if not id_publicacion:
        return jsonify({'error': 'Falta id_publicacion'}), 400
    
    try:
        nuevo_estado = toggle_guardado(current_user.id, id_publicacion)
        # Obtener nuevo conteo de guardados
        from services.db_service import get_db
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM guardado WHERE id_publicacion = %s", (id_publicacion,))
            count = cur.fetchone()[0]
        return jsonify({
            'success': True,
            'saved': nuevo_estado,
            'count': count
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@likes_bp.route('/rating/<int:id_publicacion>', methods=['GET'])
def get_post_rating(id_publicacion):
    """Obtiene el rating actualizado de un emprendedor basado en su publicación"""
    from services.db_service import get_db
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 
                vr.promedio_calificaciones,
                vr.total_resenas
            FROM publicacion p
            JOIN usuario u ON p.id_emprendedor = u.id_usuario
            LEFT JOIN vista_emprendedor_reputacion vr ON u.id_usuario = vr.id_usuario
            WHERE p.id_publicacion = %s
        """, (id_publicacion,))
        row = cur.fetchone()
        if row:
            return jsonify({
                'success': True,
                'promedio': float(row[0]) if row[0] else None,
                'total': row[1] or 0
            })
        return jsonify({'success': False, 'error': 'Publicación no encontrada'}), 404