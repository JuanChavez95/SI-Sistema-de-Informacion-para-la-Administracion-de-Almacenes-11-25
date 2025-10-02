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
        nombre = request.form['nombre']
        apellido_paterno = request.form['apellido_paterno']
        apellido_materno = request.form.get('apellido_materno', '')
        ci = request.form['ci']
        email = request.form['email']
        password = request.form['password']
        fecha_nacimiento = request.form.get('fecha_nacimiento')
        
        # ✅ USAR CONEXIÓN DIRECTA
        conn = get_db_connection()
        if not conn:
            return render_template('auth/registro.html')
        
        cursor = conn.cursor(dictionary=True)
        
        try:
            # Validar que no exista el email o CI
            cursor.execute("SELECT * FROM Persona WHERE email = %s OR ci = %s", (email, ci))
            if cursor.fetchone():
                flash('El email o CI ya están registrados', 'danger')
                cursor.close()
                conn.close()
                return redirect(url_for('auth.registro'))
            
            # Hash de la contraseña
            hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            
            # Obtener próximo ID
            cursor.execute("SELECT COALESCE(MAX(id_persona), 0) as max_id FROM Persona")
            max_id = cursor.fetchone()['max_id']
            next_id = max_id + 1
            
            # Insertar persona
            cursor.execute("""
                INSERT INTO Persona (id_persona, nombre, apellido_paterno, apellido_materno, ci, email, contra, fecha_nacimiento)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (next_id, nombre, apellido_paterno, apellido_materno, ci, email, hashed.decode('utf-8'), fecha_nacimiento))
            
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
    
    return render_template('auth/registro.html')

@bp.route('/logout')
def logout():
    session.clear()
    flash('Has cerrado sesión', 'info')
    return redirect(url_for('auth.login'))