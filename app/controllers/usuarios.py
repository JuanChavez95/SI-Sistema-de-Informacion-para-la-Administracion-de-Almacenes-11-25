from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from datetime import datetime
import mysql.connector
from werkzeug.security import generate_password_hash
from app.config import Config

usuarios_bp = Blueprint('usuarios', __name__, url_prefix='/usuarios')

def get_db_connection():
    return mysql.connector.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DB
    )

@usuarios_bp.route('/', methods=['GET'])
def index():
    """Listar todos los usuarios (empleados y clientes)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener empleados (personas con rol)
        cursor.execute("""
            SELECT p.*, GROUP_CONCAT(r.nombre_rol) as roles
            FROM Persona p
            LEFT JOIN Persona_Rol pr ON p.id_persona = pr.id_persona
            LEFT JOIN Rol r ON pr.id_rol = r.id_rol
            WHERE p.id_persona NOT IN (SELECT id_cliente FROM Cliente)
            GROUP BY p.id_persona
            ORDER BY p.id_persona DESC
        """)
        empleados = cursor.fetchall()
        
        # Obtener clientes
        cursor.execute("""
            SELECT p.*, c.tipo_cliente, c.categoria_cliente, c.empresa
            FROM Persona p
            INNER JOIN Cliente c ON p.id_persona = c.id_cliente
            ORDER BY p.id_persona DESC
        """)
        clientes = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('modulos/usuarios.html',
                            tab='lista',
                            empleados=empleados,
                            clientes=clientes)
    except Exception as e:
        flash(f'Error al cargar usuarios: {str(e)}', 'danger')
        return redirect(url_for('dashboard.index'))

@usuarios_bp.route('/crear', methods=['GET', 'POST'])
def crear():
    """Crear nuevo usuario"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        if request.method == 'GET':
            cursor.execute("SELECT * FROM Rol ORDER BY nombre_rol")
            roles = cursor.fetchall()
            cursor.close()
            conn.close()
            
            return render_template('modulos/usuarios.html', tab='crear', roles=roles)
        
        # POST
        tipo_usuario = request.form.get('tipo_usuario')
        nombre = request.form.get('nombre', '').strip()
        apellido_paterno = request.form.get('apellido_paterno', '').strip()
        apellido_materno = request.form.get('apellido_materno', '').strip()
        email = request.form.get('email', '').strip()
        ci = request.form.get('ci', '')
        fecha_nacimiento = request.form.get('fecha_nacimiento')
        contra = request.form.get('contra', '')
        
        if not all([nombre, apellido_paterno, email, ci, contra]):
            flash('Todos los campos obligatorios deben completarse', 'warning')
            return redirect(url_for('usuarios.crear'))
        
        # Verificar email único
        cursor.execute("SELECT id_persona FROM Persona WHERE email = %s", (email,))
        if cursor.fetchone():
            flash('El email ya está registrado', 'warning')
            cursor.close()
            conn.close()
            return redirect(url_for('usuarios.crear'))
        
        # Verificar CI único
        cursor.execute("SELECT id_persona FROM Persona WHERE ci = %s", (ci,))
        if cursor.fetchone():
            flash('El CI ya está registrado', 'warning')
            cursor.close()
            conn.close()
            return redirect(url_for('usuarios.crear'))
        
        # Crear persona
        query_persona = """
            INSERT INTO Persona (nombre, apellido_paterno, apellido_materno, email, ci, contra, fecha_nacimiento)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query_persona, (nombre, apellido_paterno, apellido_materno, email, int(ci), generate_password_hash(contra), fecha_nacimiento if fecha_nacimiento else None))
        conn.commit()
        
        id_persona = cursor.lastrowid
        
        if tipo_usuario == 'empleado':
            # Asignar rol
            id_rol = request.form.get('id_rol')
            if id_rol:
                cursor.execute("""
                    INSERT INTO Persona_Rol (id_rol, id_persona)
                    VALUES (%s, %s)
                """, (id_rol, id_persona))
                conn.commit()
        
        elif tipo_usuario == 'cliente':
            # Crear cliente
            tipo_cliente = request.form.get('tipo_cliente', 'Minorista')
            categoria_cliente = request.form.get('categoria_cliente', 'Básico')
            empresa = request.form.get('empresa', '').strip()
            limite_credito = request.form.get('limite_credito', 0)
            
            query_cliente = """
                INSERT INTO Cliente (id_cliente, fecha_ingreso, tipo_cliente, categoria_cliente, empresa, limite_credito)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query_cliente, (id_persona, datetime.now().date(), tipo_cliente, categoria_cliente, empresa, float(limite_credito) if limite_credito else 0))
            conn.commit()
        
        cursor.close()
        conn.close()
        
        flash(f'{tipo_usuario.capitalize()} creado exitosamente', 'success')
        return redirect(url_for('usuarios.index'))
    except Exception as e:
        flash(f'Error al crear usuario: {str(e)}', 'danger')
        return redirect(url_for('usuarios.crear'))

@usuarios_bp.route('/<int:id_persona>/editar', methods=['GET', 'POST'])
def editar(id_persona):
    """Editar usuario"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener persona
        cursor.execute("SELECT * FROM Persona WHERE id_persona = %s", (id_persona,))
        persona = cursor.fetchone()
        
        if not persona:
            flash('Usuario no encontrado', 'danger')
            cursor.close()
            conn.close()
            return redirect(url_for('usuarios.index'))
        
        # Determinar tipo de usuario
        cursor.execute("SELECT id_cliente FROM Cliente WHERE id_cliente = %s", (id_persona,))
        es_cliente = cursor.fetchone() is not None
        
        if request.method == 'GET':
            roles = []
            rol_actual = None
            
            if not es_cliente:
                cursor.execute("SELECT * FROM Rol ORDER BY nombre_rol")
                roles = cursor.fetchall()
                cursor.execute("SELECT id_rol FROM Persona_Rol WHERE id_persona = %s", (id_persona,))
                rol_result = cursor.fetchone()
                rol_actual = rol_result['id_rol'] if rol_result else None
            else:
                cursor.execute("SELECT * FROM Cliente WHERE id_cliente = %s", (id_persona,))
                cliente_data = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            return render_template('modulos/usuarios.html',
                                 tab='editar',
                                 persona=persona,
                                 es_cliente=es_cliente,
                                 cliente_data=cliente_data if es_cliente else None,
                                 roles=roles,
                                 rol_actual=rol_actual)
        
        # POST
        nombre = request.form.get('nombre', '').strip()
        apellido_paterno = request.form.get('apellido_paterno', '').strip()
        apellido_materno = request.form.get('apellido_materno', '').strip()
        email = request.form.get('email', '').strip()
        fecha_nacimiento = request.form.get('fecha_nacimiento')
        
        # Verificar email único (excluir el actual)
        cursor.execute("SELECT id_persona FROM Persona WHERE email = %s AND id_persona != %s", (email, id_persona))
        if cursor.fetchone():
            flash('El email ya está registrado', 'warning')
            cursor.close()
            conn.close()
            return redirect(url_for('usuarios.editar', id_persona=id_persona))
        
        query_update = """
            UPDATE Persona
            SET nombre = %s, apellido_paterno = %s, apellido_materno = %s, email = %s, fecha_nacimiento = %s
            WHERE id_persona = %s
        """
        cursor.execute(query_update, (nombre, apellido_paterno, apellido_materno, email, 
                                     fecha_nacimiento if fecha_nacimiento else None, id_persona))
        
        if not es_cliente:
            # Actualizar rol si es empleado
            id_rol = request.form.get('id_rol')
            cursor.execute("DELETE FROM Persona_Rol WHERE id_persona = %s", (id_persona,))
            if id_rol:
                cursor.execute("INSERT INTO Persona_Rol (id_rol, id_persona) VALUES (%s, %s)", (id_rol, id_persona))
        else:
            # Actualizar cliente
            tipo_cliente = request.form.get('tipo_cliente')
            categoria_cliente = request.form.get('categoria_cliente')
            empresa = request.form.get('empresa', '').strip()
            limite_credito = request.form.get('limite_credito', 0)
            
            cursor.execute("""
                UPDATE Cliente
                SET tipo_cliente = %s, categoria_cliente = %s, empresa = %s, limite_credito = %s
                WHERE id_cliente = %s
            """, (tipo_cliente, categoria_cliente, empresa, float(limite_credito) if limite_credito else 0, id_persona))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Usuario actualizado exitosamente', 'success')
        return redirect(url_for('usuarios.index'))
    except Exception as e:
        flash(f'Error al editar usuario: {str(e)}', 'danger')
        return redirect(url_for('usuarios.index'))

@usuarios_bp.route('/<int:id_persona>/eliminar', methods=['POST'])
def eliminar(id_persona):
    """Eliminar usuario"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # No permitir eliminar el usuario actual
        if id_persona == session.get('user_id'):
            flash('No puedes eliminar tu propia cuenta', 'warning')
            cursor.close()
            conn.close()
            return redirect(url_for('usuarios.index'))
        
        # Verificar si es cliente
        cursor.execute("SELECT id_cliente FROM Cliente WHERE id_cliente = %s", (id_persona,))
        if cursor.fetchone():
            cursor.execute("DELETE FROM Cliente WHERE id_cliente = %s", (id_persona,))
        
        # Eliminar roles
        cursor.execute("DELETE FROM Persona_Rol WHERE id_persona = %s", (id_persona,))
        
        # Eliminar persona
        cursor.execute("DELETE FROM Persona WHERE id_persona = %s", (id_persona,))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        flash('Usuario eliminado exitosamente', 'success')
        return redirect(url_for('usuarios.index'))
    except Exception as e:
        flash(f'Error al eliminar usuario: {str(e)}', 'danger')
        return redirect(url_for('usuarios.index'))