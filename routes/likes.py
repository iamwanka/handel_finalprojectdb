from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from services.db_service import ejecutar_funcion

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