from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, id_usuario, nombre, email, roles):
        self.id = str(id_usuario)
        self.nombre = nombre
        self.email = email
        self.roles = roles  # lista de strings

    @staticmethod
    def get(user_id):
        # Esta función se usará para recargar el usuario desde la sesión
        from services.db_service import ejecutar_sql
        row = ejecutar_sql("SELECT id_usuario, nombre, email FROM usuario WHERE id_usuario = %s", (user_id,), fetch_one=True)
        if row:
            # Obtener roles
            roles = ejecutar_sql("""
                SELECT r.nombre_rol FROM usuario_rol ur
                JOIN rol r ON ur.id_rol = r.id_rol
                WHERE ur.id_usuario = %s
            """, (user_id,), fetch_all=True)
            roles_list = [r[0] for r in roles] if roles else []
            return User(row[0], row[1], row[2], roles_list)
        return None