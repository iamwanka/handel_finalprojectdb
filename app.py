from flask import Flask, render_template, session, redirect, url_for
from config import Config
from services.db_service import init_db_pool, close_db
from flask_login import LoginManager, current_user
import os

app = Flask(__name__)
app.config.from_object(Config)

# Inicializar pool de conexiones
init_db_pool(app)
app.teardown_appcontext(close_db)

# Login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

# Cargar usuario desde la sesión
@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.get(user_id)

# Para usar en plantillas
@app.context_processor
def inject_user():
    return dict(current_user=current_user)

# Registrar blueprints (los definiremos después)
from routes.auth import auth_bp
from routes.content import content_bp
# from routes.admin import admin_bp
# from routes.comments import comments_bp
# from routes.likes import likes_bp

app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(content_bp)
# app.register_blueprint(admin_bp, url_prefix='/admin')
# app.register_blueprint(comments_bp, url_prefix='/comments')
# app.register_blueprint(likes_bp, url_prefix='/likes')

@app.route('/')
def index():
    # return "Bienvenido a la aplicación de red social. Por favor, <a href='/auth/login'>inicia sesión</a> para ver el feed."
    # return redirect(url_for('content.feed'))
    return redirect(url_for('auth.login'))

if __name__ == '__main__':
    app.run(debug=True)