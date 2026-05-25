from flask import Blueprint, render_template, request, redirect, url_for, flash
from services.db_service import ejecutar_funcion, get_db
from models import User
from flask_login import login_user, logout_user, login_required

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        
        if not nombre or not email or not password:
            flash('Por favor completa todos los campos.', 'danger')
            return render_template('register.html')
        
        try:
            user_id = ejecutar_funcion('registrar_usuario', nombre, email, password)
            if user_id:
                flash('Registro exitoso. Ahora puedes iniciar sesión.', 'success')
                return redirect(url_for('auth.login'))
            else:
                flash('Error al registrar: No se pudo crear el usuario.', 'danger')
        except Exception as e:
            flash(f'Error al registrar: {str(e)}', 'danger')
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        
        if not email or not password:
            flash('Por favor completa todos los campos.', 'danger')
            return render_template('login.html')
        
        try:
            # Llamar a la función autenticar_usuario
            conn = get_db()
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM autenticar_usuario(%s, %s)", (email, password))
                row = cur.fetchone()
            
            if row:
                # row: (id_usuario, nombre, email, roles_array)
                user = User(row[0], row[1], row[2], row[3] if row[3] else [])
                login_user(user)
                flash(f'Bienvenido, {user.nombre}', 'success')
                next_page = request.args.get('next')
                return redirect(next_page or url_for('content.feed'))
            else:
                flash('Correo o contraseña incorrectos', 'danger')
        except Exception as e:
            flash(f'Error al iniciar sesión: {str(e)}', 'danger')
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada', 'info')
    return redirect(url_for('auth.login'))