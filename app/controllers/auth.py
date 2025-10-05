from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import mysql.connector
import bcrypt
from app.config import Config

bp = Blueprint('auth', __name__)

# Configuración de BD (COPIADA DE TU CÓDIGO QUE SÍ FUNCIONA)

DB_CONFIG = {
    'host': Config.MYSQL_HOST,      # ← Viene del .env
    'user': Config.MYSQL_USER,      # ← Viene del .env
    'password': Config.MYSQL_PASSWORD,  # ← Viene del .env
    'database': Config.MYSQL_DB,    # ← Viene del .env
    'port': Config.MYSQL_PORT       # ← Viene del .env
}

def get_db_connection():
    """Crear conexión a la base de datos - MÉTODO CONFIABLE"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            return connection
    except Exception as e:
        print(f"❌ Error conectando a MySQL: {e}")
        flash('Error de conexión a la base de datos', 'danger')
        return None

@bp.route('/')
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        # ✅ USAR CONEXIÓN DIRECTA (COMO TU CÓDIGO QUE SÍ FUNCIONA)
        conn = get_db_connection()
        if not conn:
            return render_template('auth/login.html')
        
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT p.id_persona, p.nombre, p.apellido_paterno, p.contra, r.nombre_rol
                FROM Persona p
                LEFT JOIN Persona_Rol pr ON p.id_persona = pr.id_persona
                LEFT JOIN Rol r ON pr.id_rol = r.id_rol
                WHERE p.email = %s
            """, (email,))
            user = cursor.fetchone()
            
            if user and bcrypt.checkpw(password.encode('utf-8'), user['contra'].encode('utf-8')):
                session['user_id'] = user['id_persona']
                session['user_name'] = f"{user['nombre']} {user['apellido_paterno']}"
                session['user_role'] = user['nombre_rol'] if user['nombre_rol'] else 'Cliente'
                flash('Inicio de sesión exitoso', 'success')
                return redirect(url_for('dashboard.index'))
            else:
                flash('Credenciales incorrectas', 'danger')
        except Exception as e:
            flash('Error al verificar credenciales', 'danger')
            print(f"Error: {e}")
        finally:
            cursor.close()
            conn.close()
    
    return render_template('auth/login.html')

@bp.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        # Datos básicos de persona
        nombre = request.form['nombre']
        apellido_paterno = request.form['apellido_paterno']
        apellido_materno = request.form.get('apellido_materno', '')
        ci = request.form['ci']
        email = request.form['email']
        password = request.form['password']
        fecha_nacimiento = request.form.get('fecha_nacimiento')
        
        # Tipo de registro: empleado o cliente
        tipo_registro = request.form.get('tipo_registro')  # 'empleado' o 'cliente'
        
        # Validación de contraseña de administrador
        if tipo_registro == 'empleado':
            id_rol = request.form.get('id_rol')
            if id_rol == '1004':  # ID del rol Administrador
                password_admin = request.form.get('password_admin')
                if password_admin != 'JEFE123':
                    flash('Contraseña de administrador incorrecta', 'danger')
                    return redirect(url_for('auth.registro'))
        
        # Datos de cliente (si aplica)
        if tipo_registro == 'cliente':
            tipo_cliente = request.form.get('tipo_cliente')
            categoria_cliente = request.form.get('categoria_cliente')
            limite_credito = request.form.get('limite_credito', 0)
            empresa = request.form.get('empresa', '')
        
        conn = get_db_connection()
        if not conn:
            return render_template('auth/registro.html')
        
        cursor = conn.cursor(dictionary=True)
        
        try:
            # Validar email y CI únicos
            cursor.execute("SELECT * FROM Persona WHERE email = %s OR ci = %s", (email, ci))
            if cursor.fetchone():
                flash('El email o CI ya están registrados', 'danger')
                cursor.close()
                conn.close()
                return redirect(url_for('auth.registro'))
            
            # Hash de contraseña
            hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            
            # Insertar en Persona
            cursor.execute("""
                INSERT INTO Persona (nombre, apellido_paterno, apellido_materno, ci, email, contra, fecha_nacimiento)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (nombre, apellido_paterno, apellido_materno, ci, email, hashed.decode('utf-8'), fecha_nacimiento))
            
            id_persona = cursor.lastrowid
            
            if tipo_registro == 'empleado':
                # Asignar rol en Persona_Rol
                cursor.execute("""
                    INSERT INTO Persona_Rol (id_rol, id_persona)
                    VALUES (%s, %s)
                """, (id_rol, id_persona))
            
            elif tipo_registro == 'cliente':
                # Crear registro en Cliente
                cursor.execute("""
                    INSERT INTO Cliente (id_cliente, fecha_ingreso, tipo_cliente, categoria_cliente, limite_credito, empresa)
                    VALUES (%s, CURDATE(), %s, %s, %s, %s)
                """, (id_persona, tipo_cliente, categoria_cliente, limite_credito, empresa))
            
            conn.commit()
            flash('Registro exitoso. Ya puedes iniciar sesión', 'success')
            
        except Exception as e:
            conn.rollback()
            flash('Error en el registro: ' + str(e), 'danger')
            print(f"Error registro: {e}")
        finally:
            cursor.close()
            conn.close()
        
        return redirect(url_for('auth.login'))
    
    # GET: Obtener roles para el formulario
    conn = get_db_connection()
    roles = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id_rol, nombre_rol FROM Rol")
        roles = cursor.fetchall()
        cursor.close()
        conn.close()
    
    return render_template('auth/registro.html', roles=roles)

@bp.route('/logout')
def logout():
    session.clear()
    flash('Has cerrado sesión', 'info')
    return redirect(url_for('auth.login'))