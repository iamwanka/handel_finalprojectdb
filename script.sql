-- ======================================================
-- SCRIPT DE CREACIÓN DE LA BASE DE DATOS SOCIAL APP
-- PostgreSQL 14+ 
-- ======================================================

-- 1. Creación de la base de datos (opcional, comenta si ya existe)
-- CREATE DATABASE social_app_db
--     WITH OWNER = postgres
--     ENCODING = 'UTF8'
--     CONNECTION LIMIT = -1;

-- Conectarse a la base de datos (si se ejecuta por separado)
-- \c social_app_db;

-- ======================================================
-- 2. Extensiones necesarias
-- ======================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- Para hash de contraseñas (crypt)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp"; -- Opcional, por si necesitamos UUIDs

-- ======================================================
-- 3. Tipos ENUM (para columnas con valores fijos)
-- ======================================================

CREATE TYPE rol_enum AS ENUM ('emprendedor', 'comprador', 'admin');
CREATE TYPE estado_producto_enum AS ENUM ('disponible', 'agotado');
CREATE TYPE tipo_contenido_enum AS ENUM ('video', 'imagen', 'texto');
CREATE TYPE tipo_evento_enum AS ENUM ('clic_comprar', 'clic_contactar');
CREATE TYPE estado_transaccion_enum AS ENUM ('completada', 'pendiente', 'cancelada');

-- ======================================================
-- 4. Tablas principales
-- ======================================================

-- Tabla Usuario
CREATE TABLE usuario (
    id_usuario SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    contraseña_hash VARCHAR(255) NOT NULL,
    fecha_registro TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    telefono VARCHAR(20),
    verificado BOOLEAN DEFAULT FALSE
);

-- Tabla Rol (catálogo de roles, aunque usamos ENUM, dejamos tabla por si se expande)
CREATE TABLE rol (
    id_rol SERIAL PRIMARY KEY,
    nombre_rol rol_enum NOT NULL UNIQUE
);

-- Insertar roles básicos
INSERT INTO rol (nombre_rol) VALUES ('emprendedor'), ('comprador'), ('admin')
ON CONFLICT (nombre_rol) DO NOTHING;

-- Tabla usuario_rol (relación N:M)
CREATE TABLE usuario_rol (
    id_usuario INTEGER NOT NULL REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    id_rol INTEGER NOT NULL REFERENCES rol(id_rol) ON DELETE CASCADE,
    fecha_asignacion TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_usuario, id_rol)
);

-- Tabla Categoria (jerárquica)
CREATE TABLE categoria (
    id_categoria SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL,
    id_categoria_padre INTEGER REFERENCES categoria(id_categoria) ON DELETE SET NULL
);

-- Tabla Producto
CREATE TABLE producto (
    id_producto SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    precio DECIMAL(10,2) NOT NULL CHECK (precio > 0),
    estado estado_producto_enum DEFAULT 'disponible',
    id_emprendedor INTEGER NOT NULL REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    id_categoria INTEGER NOT NULL REFERENCES categoria(id_categoria),
    fecha_creacion TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Tabla ImagenProducto
CREATE TABLE imagen_producto (
    id_imagen SERIAL PRIMARY KEY,
    url VARCHAR(255) NOT NULL,
    id_producto INTEGER NOT NULL REFERENCES producto(id_producto) ON DELETE CASCADE
);

-- Tabla Publicacion
CREATE TABLE publicacion (
    id_publicacion SERIAL PRIMARY KEY,
    titulo VARCHAR(100) NOT NULL,
    descripcion TEXT,
    tipo_contenido tipo_contenido_enum NOT NULL,
    url_multimedia VARCHAR(255),
    fecha_publicacion TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    id_emprendedor INTEGER NOT NULL REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    activo BOOLEAN DEFAULT TRUE
);

-- Tabla Publicacion_Producto (relación N:M)
CREATE TABLE publicacion_producto (
    id_publicacion INTEGER NOT NULL REFERENCES publicacion(id_publicacion) ON DELETE CASCADE,
    id_producto INTEGER NOT NULL REFERENCES producto(id_producto) ON DELETE CASCADE,
    PRIMARY KEY (id_publicacion, id_producto)
);

-- Tabla Like
CREATE TABLE likes (   -- 'like' es palabra reservada, usamos 'likes'
    id_usuario INTEGER NOT NULL REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    id_publicacion INTEGER NOT NULL REFERENCES publicacion(id_publicacion) ON DELETE CASCADE,
    fecha TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_usuario, id_publicacion)
);

-- Tabla Comentario (con auto-relación para respuestas anidadas)
CREATE TABLE comentario (
    id_comentario SERIAL PRIMARY KEY,
    texto TEXT NOT NULL,
    fecha TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    id_usuario INTEGER NOT NULL REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    id_publicacion INTEGER NOT NULL REFERENCES publicacion(id_publicacion) ON DELETE CASCADE,
    id_comentario_padre INTEGER REFERENCES comentario(id_comentario) ON DELETE CASCADE
);

-- Tabla Guardado
CREATE TABLE guardado (
    id_usuario INTEGER NOT NULL REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    id_publicacion INTEGER NOT NULL REFERENCES publicacion(id_publicacion) ON DELETE CASCADE,
    fecha TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_usuario, id_publicacion)
);

-- Tabla Visualizacion (para métricas)
CREATE TABLE visualizacion (
    id_visualizacion SERIAL PRIMARY KEY,
    id_usuario INTEGER NULL REFERENCES usuario(id_usuario) ON DELETE SET NULL, -- anónimo permitido
    id_publicacion INTEGER NOT NULL REFERENCES publicacion(id_publicacion) ON DELETE CASCADE,
    fecha TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ip_origen VARCHAR(45)   -- soporte IPv4/IPv6
);

-- Tabla EventoConversion
CREATE TABLE evento_conversion (
    id_evento SERIAL PRIMARY KEY,
    tipo_evento tipo_evento_enum NOT NULL,
    fecha TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    id_usuario INTEGER NOT NULL REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    id_publicacion INTEGER NOT NULL REFERENCES publicacion(id_publicacion) ON DELETE CASCADE,
    id_producto INTEGER NOT NULL REFERENCES producto(id_producto) ON DELETE CASCADE
);

-- Tabla Transaccion
CREATE TABLE transaccion (
    id_transaccion SERIAL PRIMARY KEY,
    fecha TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    monto DECIMAL(10,2) NOT NULL CHECK (monto > 0),
    estado estado_transaccion_enum DEFAULT 'pendiente',
    id_comprador INTEGER NOT NULL REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    id_producto INTEGER NOT NULL REFERENCES producto(id_producto) ON DELETE CASCADE
);

-- Tabla Reseña
CREATE TABLE reseña (
    id_reseña SERIAL PRIMARY KEY,
    calificacion INTEGER NOT NULL CHECK (calificacion BETWEEN 1 AND 5),
    comentario TEXT,
    respuesta_emprendedor TEXT,
    fecha TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    id_comprador INTEGER NOT NULL REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    id_vendedor INTEGER NOT NULL REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    id_producto INTEGER NOT NULL REFERENCES producto(id_producto) ON DELETE CASCADE
);

-- Tabla Auditoria (para triggers)
CREATE TABLE auditoria_log (
    id_log SERIAL PRIMARY KEY,
    tabla_afectada VARCHAR(50),
    accion VARCHAR(10),
    id_registro INTEGER,
    usuario_bd VARCHAR(50) DEFAULT CURRENT_USER,
    fecha TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    datos_viejos JSONB,
    datos_nuevos JSONB
);

-- ======================================================
-- 5. Índices para mejorar rendimiento
-- ======================================================

CREATE INDEX idx_usuario_email ON usuario(email);
CREATE INDEX idx_publicacion_fecha ON publicacion(fecha_publicacion DESC);
CREATE INDEX idx_publicacion_emprendedor ON publicacion(id_emprendedor);
CREATE INDEX idx_producto_categoria ON producto(id_categoria);
CREATE INDEX idx_producto_emprendedor ON producto(id_emprendedor);
CREATE INDEX idx_comentario_publicacion ON comentario(id_publicacion);
CREATE INDEX idx_likes_publicacion ON likes(id_publicacion);
CREATE INDEX idx_guardado_publicacion ON guardado(id_publicacion);
CREATE INDEX idx_visualizacion_publicacion ON visualizacion(id_publicacion);
CREATE INDEX idx_evento_publicacion ON evento_conversion(id_publicacion);
CREATE INDEX idx_transaccion_comprador ON transaccion(id_comprador);
CREATE INDEX idx_reseña_vendedor ON reseña(id_vendedor);

-- Índice de búsqueda de texto completo para publicaciones (opcional, avanzado)
-- CREATE INDEX idx_publicacion_busqueda ON publicacion USING GIN (to_tsvector('spanish', titulo || ' ' || COALESCE(descripcion, '')));

-- ======================================================
-- 6. Secuencias (ejemplo de una secuencia manual para visualizacion)
-- ======================================================
-- Aunque id_visualizacion es SERIAL, creamos una secuencia explícita para demostración
CREATE SEQUENCE seq_visualizacion START 1000;

-- ======================================================
-- 7. FUNCIONES Y PROCEDIMIENTOS ALMACENADOS
-- ======================================================

-- 7.1 Función para registrar usuario (con hash de contraseña)
CREATE OR REPLACE FUNCTION registrar_usuario(
    p_nombre VARCHAR,
    p_email VARCHAR,
    p_password TEXT
)
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_id_usuario INTEGER;
    v_id_rol_comprador INTEGER;
BEGIN
    -- Validar que email no exista
    IF EXISTS (SELECT 1 FROM usuario WHERE email = p_email) THEN
        RAISE EXCEPTION 'El correo electrónico ya está registrado';
    END IF;
    
    -- Obtener ID del rol 'comprador'
    SELECT id_rol INTO v_id_rol_comprador FROM rol WHERE nombre_rol = 'comprador';
    
    -- Insertar usuario con contraseña hasheada (bcrypt)
    INSERT INTO usuario (nombre, email, contraseña_hash)
    VALUES (p_nombre, p_email, crypt(p_password, gen_salt('bf')))
    RETURNING id_usuario INTO v_id_usuario;
    
    -- Asignar rol 'comprador' por defecto
    INSERT INTO usuario_rol (id_usuario, id_rol) VALUES (v_id_usuario, v_id_rol_comprador);
    
    RETURN v_id_usuario;
END;
$$;

-- 7.2 Función para autenticar usuario
CREATE OR REPLACE FUNCTION autenticar_usuario(
    p_email VARCHAR,
    p_password TEXT
)
RETURNS TABLE(
    id_usuario INTEGER,
    nombre VARCHAR,
    email VARCHAR,
    roles TEXT[]
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT u.id_usuario, u.nombre, u.email,
           ARRAY_AGG(r.nombre_rol::TEXT) AS roles
    FROM usuario u
    JOIN usuario_rol ur ON u.id_usuario = ur.id_usuario
    JOIN rol r ON ur.id_rol = r.id_rol
    WHERE u.email = p_email
      AND u.contraseña_hash = crypt(p_password, u.contraseña_hash)
    GROUP BY u.id_usuario, u.nombre, u.email;
END;
$$;

-- 7.3 Función para crear publicación (con asociación a productos mediante array)
CREATE OR REPLACE FUNCTION crear_publicacion(
    p_titulo VARCHAR,
    p_descripcion TEXT,
    p_tipo_contenido tipo_contenido_enum,
    p_url_multimedia VARCHAR,
    p_id_emprendedor INTEGER,
    p_productos_ids INTEGER[]   -- array de id_producto
)
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_id_publicacion INTEGER;
    v_producto_id INTEGER;
BEGIN
    -- Validar que el usuario sea emprendedor (tiene el rol)
    IF NOT EXISTS (
        SELECT 1 FROM usuario_rol ur
        JOIN rol r ON ur.id_rol = r.id_rol
        WHERE ur.id_usuario = p_id_emprendedor AND r.nombre_rol = 'emprendedor'
    ) THEN
        RAISE EXCEPTION 'El usuario no tiene rol de emprendedor';
    END IF;
    
    -- Insertar publicación
    INSERT INTO publicacion (titulo, descripcion, tipo_contenido, url_multimedia, id_emprendedor)
    VALUES (p_titulo, p_descripcion, p_tipo_contenido, p_url_multimedia, p_id_emprendedor)
    RETURNING id_publicacion INTO v_id_publicacion;
    
    -- Asociar productos (si el array no está vacío)
    IF array_length(p_productos_ids, 1) > 0 THEN
        FOREACH v_producto_id IN ARRAY p_productos_ids
        LOOP
            INSERT INTO publicacion_producto (id_publicacion, id_producto)
            VALUES (v_id_publicacion, v_producto_id);
        END LOOP;
    END IF;
    
    RETURN v_id_publicacion;
END;
$$;

-- 7.4 Función para obtener el feed (paginado, con indicador de like del usuario actual)
CREATE OR REPLACE FUNCTION obtener_feed(
    p_id_usuario INTEGER,
    p_pagina INTEGER DEFAULT 1,
    p_limite INTEGER DEFAULT 10
)
RETURNS TABLE(
    id_publicacion INTEGER,
    titulo VARCHAR,
    tipo_contenido tipo_contenido_enum,
    url_multimedia VARCHAR,
    fecha_publicacion TIMESTAMPTZ,
    nombre_emprendedor VARCHAR,
    num_likes BIGINT,
    num_comentarios BIGINT,
    me_gusta BOOLEAN
)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_offset INTEGER;
BEGIN
    v_offset := (p_pagina - 1) * p_limite;
    
    RETURN QUERY
    SELECT 
        p.id_publicacion,
        p.titulo,
        p.tipo_contenido,
        p.url_multimedia,
        p.fecha_publicacion,
        u.nombre AS nombre_emprendedor,
        (SELECT COUNT(*) FROM likes l WHERE l.id_publicacion = p.id_publicacion) AS num_likes,
        (SELECT COUNT(*) FROM comentario c WHERE c.id_publicacion = p.id_publicacion) AS num_comentarios,
        EXISTS (SELECT 1 FROM likes l WHERE l.id_publicacion = p.id_publicacion AND l.id_usuario = p_id_usuario) AS me_gusta
    FROM publicacion p
    JOIN usuario u ON p.id_emprendedor = u.id_usuario
    WHERE p.activo = TRUE
    ORDER BY p.fecha_publicacion DESC
    LIMIT p_limite OFFSET v_offset;
END;
$$;

-- 7.5 Función para agregar comentario (con posibilidad de respuesta)
CREATE OR REPLACE FUNCTION agregar_comentario(
    p_texto TEXT,
    p_id_usuario INTEGER,
    p_id_publicacion INTEGER,
    p_id_comentario_padre INTEGER DEFAULT NULL
)
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_id_comentario INTEGER;
BEGIN
    -- Validar que la publicación exista
    IF NOT EXISTS (SELECT 1 FROM publicacion WHERE id_publicacion = p_id_publicacion AND activo = TRUE) THEN
        RAISE EXCEPTION 'La publicación no existe o está inactiva';
    END IF;
    
    -- Si se especifica padre, validar que exista
    IF p_id_comentario_padre IS NOT NULL AND NOT EXISTS (SELECT 1 FROM comentario WHERE id_comentario = p_id_comentario_padre) THEN
        RAISE EXCEPTION 'El comentario padre no existe';
    END IF;
    
    INSERT INTO comentario (texto, id_usuario, id_publicacion, id_comentario_padre)
    VALUES (p_texto, p_id_usuario, p_id_publicacion, p_id_comentario_padre)
    RETURNING id_comentario INTO v_id_comentario;
    
    RETURN v_id_comentario;
END;
$$;

-- 7.6 Función para toggle like (si existe lo elimina, si no lo inserta)
CREATE OR REPLACE FUNCTION toggle_like(
    p_id_usuario INTEGER,
    p_id_publicacion INTEGER
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_existe BOOLEAN;
BEGIN
    SELECT EXISTS (SELECT 1 FROM likes WHERE id_usuario = p_id_usuario AND id_publicacion = p_id_publicacion) INTO v_existe;
    
    IF v_existe THEN
        DELETE FROM likes WHERE id_usuario = p_id_usuario AND id_publicacion = p_id_publicacion;
        RETURN FALSE;  -- Indica que se quitó el like
    ELSE
        INSERT INTO likes (id_usuario, id_publicacion) VALUES (p_id_usuario, p_id_publicacion);
        RETURN TRUE;   -- Indica que se agregó el like
    END IF;
END;
$$;

-- 7.7 Función de búsqueda de publicaciones (por título o descripción)
CREATE OR REPLACE FUNCTION buscar_publicaciones(
    p_texto_busqueda TEXT,
    p_pagina INTEGER DEFAULT 1,
    p_limite INTEGER DEFAULT 10
)
RETURNS TABLE(
    id_publicacion INTEGER,
    titulo VARCHAR,
    descripcion TEXT,
    fecha_publicacion TIMESTAMPTZ,
    nombre_emprendedor VARCHAR
)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_offset INTEGER;
BEGIN
    v_offset := (p_pagina - 1) * p_limite;
    
    RETURN QUERY
    SELECT 
        p.id_publicacion,
        p.titulo,
        p.descripcion,
        p.fecha_publicacion,
        u.nombre
    FROM publicacion p
    JOIN usuario u ON p.id_emprendedor = u.id_usuario
    WHERE p.activo = TRUE
      AND (p.titulo ILIKE '%' || p_texto_busqueda || '%' OR p.descripcion ILIKE '%' || p_texto_busqueda || '%')
    ORDER BY p.fecha_publicacion DESC
    LIMIT p_limite OFFSET v_offset;
END;
$$;

-- 7.8 Función para calcular la tasa de conversión de una publicación (clics compra / visualizaciones)
CREATE OR REPLACE FUNCTION calcular_tasa_conversion(
    p_id_publicacion INTEGER
)
RETURNS DECIMAL(5,4)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_visualizaciones BIGINT;
    v_clics_comprar BIGINT;
    v_tasa DECIMAL(5,4);
BEGIN
    SELECT COUNT(*) INTO v_visualizaciones FROM visualizacion WHERE id_publicacion = p_id_publicacion;
    SELECT COUNT(*) INTO v_clics_comprar FROM evento_conversion WHERE id_publicacion = p_id_publicacion AND tipo_evento = 'clic_comprar';
    
    IF v_visualizaciones = 0 THEN
        RETURN 0.0;
    END IF;
    
    v_tasa := v_clics_comprar::DECIMAL / v_visualizaciones::DECIMAL;
    RETURN ROUND(v_tasa, 4);
END;
$$;

-- 7.9 Procedimiento almacenado para registrar una transacción y actualizar estado del producto
CREATE OR REPLACE PROCEDURE registrar_transaccion(
    p_id_comprador INTEGER,
    p_id_producto INTEGER,
    p_monto DECIMAL
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_id_transaccion INTEGER;
    v_estado_producto estado_producto_enum;
BEGIN
    -- Validar que el producto exista y esté disponible
    SELECT estado INTO v_estado_producto FROM producto WHERE id_producto = p_id_producto;
    IF v_estado_producto = 'agotado' THEN
        RAISE EXCEPTION 'El producto ya está agotado';
    END IF;
    
    -- Insertar transacción
    INSERT INTO transaccion (id_comprador, id_producto, monto, estado)
    VALUES (p_id_comprador, p_id_producto, p_monto, 'completada')
    RETURNING id_transaccion INTO v_id_transaccion;
    
    -- Marcar producto como agotado (para este ejercicio asumimos que una compra agota el stock)
    UPDATE producto SET estado = 'agotado' WHERE id_producto = p_id_producto;
    
    -- (Opcional) Registrar evento de conversión de tipo 'clic_comprar' ya se habría registrado antes
    -- Aquí podríamos también actualizar el contador de ventas del emprendedor, etc.
    
    RAISE NOTICE 'Transacción % registrada exitosamente', v_id_transaccion;
END;
$$;

-- ======================================================
-- 8. TRIGGERS Y AUDITORÍA
-- ======================================================

-- 8.1 Función de auditoría genérica
CREATE OR REPLACE FUNCTION auditoria_trigger()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_datos_viejos JSONB = NULL;
    v_datos_nuevos JSONB = NULL;
BEGIN
    IF TG_OP = 'DELETE' THEN
        v_datos_viejos = row_to_json(OLD);
    ELSIF TG_OP = 'UPDATE' THEN
        v_datos_viejos = row_to_json(OLD);
        v_datos_nuevos = row_to_json(NEW);
    ELSIF TG_OP = 'INSERT' THEN
        v_datos_nuevos = row_to_json(NEW);
    END IF;
    
    INSERT INTO auditoria_log (tabla_afectada, accion, id_registro, datos_viejos, datos_nuevos)
    VALUES (TG_TABLE_NAME, TG_OP, COALESCE(OLD.id_publicacion, NEW.id_publicacion, OLD.id_producto, NEW.id_producto), v_datos_viejos, v_datos_nuevos);
    
    RETURN NULL;
END;
$$;

-- 8.2 Aplicar trigger de auditoría a tablas relevantes
CREATE TRIGGER auditoria_publicacion
    AFTER INSERT OR UPDATE OR DELETE ON publicacion
    FOR EACH ROW EXECUTE FUNCTION auditoria_trigger();

CREATE TRIGGER auditoria_producto
    AFTER INSERT OR UPDATE OR DELETE ON producto
    FOR EACH ROW EXECUTE FUNCTION auditoria_trigger();

CREATE TRIGGER auditoria_transaccion
    AFTER INSERT OR UPDATE OR DELETE ON transaccion
    FOR EACH ROW EXECUTE FUNCTION auditoria_trigger();

-- 8.3 Trigger para actualizar estado del producto después de una transacción (aunque ya lo hace el procedimiento, lo dejamos como seguridad)
CREATE OR REPLACE FUNCTION actualizar_estado_producto()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.estado = 'completada' THEN
        UPDATE producto SET estado = 'agotado' WHERE id_producto = NEW.id_producto;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trigger_actualizar_estado
    AFTER INSERT ON transaccion
    FOR EACH ROW
    EXECUTE FUNCTION actualizar_estado_producto();

-- ======================================================
-- 9. VISTAS (simples y materializadas)
-- ======================================================

-- 9.1 Vista de publicaciones populares (con más de 10 likes o 5 comentarios)
CREATE VIEW vista_publicaciones_populares AS
SELECT 
    p.id_publicacion,
    p.titulo,
    COUNT(DISTINCT l.id_usuario) AS total_likes,
    COUNT(DISTINCT c.id_comentario) AS total_comentarios,
    (COUNT(DISTINCT l.id_usuario) + COUNT(DISTINCT c.id_comentario)) AS popularidad
FROM publicacion p
LEFT JOIN likes l ON p.id_publicacion = l.id_publicacion
LEFT JOIN comentario c ON p.id_publicacion = c.id_publicacion
WHERE p.activo = TRUE
GROUP BY p.id_publicacion
HAVING COUNT(DISTINCT l.id_usuario) > 10 OR COUNT(DISTINCT c.id_comentario) > 5;

-- 9.2 Vista de reputación del emprendedor (promedio de calificaciones)
CREATE VIEW vista_emprendedor_reputacion AS
SELECT 
    u.id_usuario,
    u.nombre,
    COALESCE(AVG(r.calificacion), 0) AS promedio_calificaciones,
    COUNT(r.id_reseña) AS total_reseñas
FROM usuario u
LEFT JOIN reseña r ON u.id_usuario = r.id_vendedor
GROUP BY u.id_usuario, u.nombre;

-- 9.3 Vista materializada de métricas (se refrescará periódicamente)
CREATE MATERIALIZED VIEW vista_materializada_metricas AS
SELECT 
    p.id_publicacion,
    (SELECT COUNT(*) FROM likes l WHERE l.id_publicacion = p.id_publicacion) AS num_likes,
    (SELECT COUNT(*) FROM comentario c WHERE c.id_publicacion = p.id_publicacion) AS num_comentarios,
    (SELECT COUNT(*) FROM guardado g WHERE g.id_publicacion = p.id_publicacion) AS num_guardados,
    (SELECT COUNT(*) FROM visualizacion v WHERE v.id_publicacion = p.id_publicacion) AS num_visualizaciones,
    (SELECT COUNT(*) FROM evento_conversion e WHERE e.id_publicacion = p.id_publicacion AND e.tipo_evento = 'clic_comprar') AS num_conversiones,
    calcular_tasa_conversion(p.id_publicacion) AS tasa_conversion
FROM publicacion p;

-- Crear índice único para refresco concurrente
CREATE UNIQUE INDEX idx_vista_materializada ON vista_materializada_metricas (id_publicacion);

-- ======================================================
-- 10. ROLES Y PERMISOS (opcional, para demostración)
-- ======================================================
-- NOTA: Esto se debe ejecutar con un usuario superusuario (postgres)
-- Se crean roles a nivel de base de datos y se asignan permisos específicos.
-- La aplicación usará un rol intermedio 'app_user' con permisos limitados.

/*
-- Crear roles (si no existen)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_emprendedor') THEN
        CREATE ROLE app_emprendedor NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_comprador') THEN
        CREATE ROLE app_comprador NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_admin') THEN
        CREATE ROLE app_admin NOLOGIN;
    END IF;
END$$;

-- Asignar permisos
-- Emprendedor: puede insertar y modificar sus propias publicaciones y productos
GRANT SELECT, INSERT, UPDATE ON publicacion, producto, imagen_producto TO app_emprendedor;
GRANT SELECT ON usuario, categoria, comentario TO app_emprendedor;

-- Comprador: puede ver todo, comentar, dar like, guardar
GRANT SELECT ON publicacion, producto, usuario, categoria TO app_comprador;
GRANT INSERT ON comentario, likes, guardado, visualizacion TO app_comprador;

-- Admin: todos los permisos
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO app_admin;

-- Crear usuario para la aplicación (con contraseña)
-- CREATE USER app_user WITH PASSWORD 'secure_password';
-- GRANT app_comprador TO app_user;
-- (dependiendo del rol del usuario logueado, se cambiaría el rol en la conexión)
*/

-- ======================================================
-- 11. DATOS INICIALES DE CATEGORÍAS (opcional)
-- ======================================================
INSERT INTO categoria (nombre, id_categoria_padre) VALUES
    ('Alimentos', NULL),
    ('Comidas preparadas', 1),
    ('Postres', 2),
    ('Tecnología', NULL),
    ('Servicios profesionales', NULL),
    ('Manualidades', NULL),
    ('Belleza y cuidado personal', NULL)
ON CONFLICT DO NOTHING;

-- ======================================================
-- FIN DEL SCRIPT
-- ======================================================