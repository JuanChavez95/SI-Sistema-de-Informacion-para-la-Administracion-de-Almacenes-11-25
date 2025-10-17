from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from datetime import datetime
import mysql.connector
from app.config import Config

almacen_bp = Blueprint('almacen', __name__, url_prefix='/almacenes')

def get_db_connection():
    """Obtener conexión a la base de datos"""
    return mysql.connector.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DB
    )

def actualizar_capacidad_estante(cursor, id_estante):
    """Actualizar capacidad_ocupada de un estante basado en su inventario"""
    query = """
        UPDATE Estante 
        SET capacidad_ocupada = (
            SELECT COALESCE(SUM(i.stock_producto), 0)
            FROM Inventario i
            WHERE i.id_estante = %s
        )
        WHERE id_estante = %s
    """
    cursor.execute(query, (id_estante, id_estante))

def actualizar_capacidad_almacen(cursor, id_almacen):
    """Actualizar capacidad_ocupada de un almacén basado en sus estantes"""
    query = """
        UPDATE Almacen 
        SET capacidad_ocupada = (
            SELECT COALESCE(SUM(e.capacidad_ocupada), 0)
            FROM Estante e
            WHERE e.id_almacen = %s
        )
        WHERE id_almacen = %s
    """
    cursor.execute(query, (id_almacen, id_almacen))

def actualizar_todas_capacidades_almacen(cursor, id_almacen):
    """Actualizar todas las capacidades en cascada: Inventario → Estante → Almacén"""
    # Paso 1: Actualizar capacidad de todos los estantes del almacén
    cursor.execute("SELECT id_estante FROM Estante WHERE id_almacen = %s", (id_almacen,))
    estantes = cursor.fetchall()
    
    for estante in estantes:
        # Acceder al diccionario correctamente
        id_estante = estante['id_estante'] if isinstance(estante, dict) else estante[0]
        actualizar_capacidad_estante(cursor, id_estante)
    
    # Paso 2: Actualizar capacidad del almacén
    actualizar_capacidad_almacen(cursor, id_almacen)

@almacen_bp.route('/', methods=['GET'])
def index():
    """Listar todos los almacenes"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Actualizar capacidades de todos los almacenes
        cursor.execute("SELECT id_almacen FROM Almacen")
        almacenes_ids = cursor.fetchall()
        
        for alm in almacenes_ids:
            actualizar_todas_capacidades_almacen(cursor, alm['id_almacen'])
        
        conn.commit()
        
        # Obtener almacenes con información del responsable
        query = """
            SELECT a.*, p.nombre, p.apellido_paterno 
            FROM Almacen a 
            LEFT JOIN Persona p ON a.id_persona = p.id_persona 
            ORDER BY a.id_almacen DESC
        """
        cursor.execute(query)
        almacenes = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('modulos/almacen.html', almacenes=almacenes, tab='lista')
    except Exception as e:
        flash(f'Error al cargar almacenes: {str(e)}', 'danger')
        return redirect(url_for('dashboard.index'))

@almacen_bp.route('/crear', methods=['GET', 'POST'])
def crear():
    """Crear nuevo almacén"""
    if request.method == 'GET':
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id_persona, nombre, apellido_paterno FROM Persona LIMIT 50")
            personas = cursor.fetchall()
            cursor.close()
            conn.close()
            
            return render_template('modulos/almacen.html', tab='crear', personas=personas)
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('almacen.index'))
    
    # POST - Guardar nuevo almacén
    try:
        nombre = request.form.get('nombre_almacen', '').strip()
        capacidad = request.form.get('capacidad', 0)
        ubicacion = request.form.get('ubicacion', '').strip()
        id_persona = request.form.get('id_persona', None)
        
        if not nombre or not capacidad:
            flash('El nombre y capacidad son requeridos', 'warning')
            return redirect(url_for('almacen.crear'))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
            INSERT INTO Almacen (nombre_almacen, capacidad, ubicacion, id_persona)
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(query, (nombre, capacidad, ubicacion, id_persona if id_persona else None))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        flash('Almacén creado exitosamente', 'success')
        return redirect(url_for('almacen.index'))
    except Exception as e:
        flash(f'Error al crear almacén: {str(e)}', 'danger')
        return redirect(url_for('almacen.crear'))

@almacen_bp.route('/<int:id_almacen>', methods=['GET'])
def ver_detalle(id_almacen):
    """Ver detalles del almacén y sus estantes"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Actualizar capacidades antes de mostrar
        actualizar_todas_capacidades_almacen(cursor, id_almacen)
        conn.commit()
        
        # Obtener almacén
        cursor.execute("""
            SELECT a.*, p.nombre, p.apellido_paterno 
            FROM Almacen a 
            LEFT JOIN Persona p ON a.id_persona = p.id_persona 
            WHERE a.id_almacen = %s
        """, (id_almacen,))
        almacen = cursor.fetchone()
        
        if not almacen:
            flash('Almacén no encontrado', 'danger')
            cursor.close()
            conn.close()
            return redirect(url_for('almacen.index'))
        
        # Obtener estantes del almacén
        cursor.execute("""
            SELECT * FROM Estante 
            WHERE id_almacen = %s 
            ORDER BY pasillo ASC
        """, (id_almacen,))
        estantes = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('modulos/almacen.html', tab='detalle', almacen=almacen, estantes=estantes)
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('almacen.index'))

@almacen_bp.route('/<int:id_almacen>/editar', methods=['GET', 'POST'])
def editar(id_almacen):
    """Editar almacén existente"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        if request.method == 'GET':
            # Actualizar capacidades antes de mostrar
            actualizar_todas_capacidades_almacen(cursor, id_almacen)
            conn.commit()
            
            cursor.execute("""
                SELECT a.*, p.nombre, p.apellido_paterno 
                FROM Almacen a 
                LEFT JOIN Persona p ON a.id_persona = p.id_persona 
                WHERE a.id_almacen = %s
            """, (id_almacen,))
            almacen = cursor.fetchone()
            
            cursor.execute("SELECT id_persona, nombre, apellido_paterno FROM Persona LIMIT 50")
            personas = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            if not almacen:
                flash('Almacén no encontrado', 'danger')
                return redirect(url_for('almacen.index'))
            
            return render_template('modulos/almacen.html', tab='editar', almacen=almacen, personas=personas)
        
        # POST - Actualizar
        nombre = request.form.get('nombre_almacen', '').strip()
        capacidad = request.form.get('capacidad', 0)
        ubicacion = request.form.get('ubicacion', '').strip()
        id_persona = request.form.get('id_persona', None)
        
        if not nombre or not capacidad:
            flash('El nombre y capacidad son requeridos', 'warning')
            cursor.close()
            conn.close()
            return redirect(url_for('almacen.editar', id_almacen=id_almacen))
        
        query = """
            UPDATE Almacen 
            SET nombre_almacen = %s, capacidad = %s, ubicacion = %s, id_persona = %s
            WHERE id_almacen = %s
        """
        cursor.execute(query, (nombre, capacidad, ubicacion, id_persona if id_persona else None, id_almacen))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        flash('Almacén actualizado exitosamente', 'success')
        return redirect(url_for('almacen.ver_detalle', id_almacen=id_almacen))
    except Exception as e:
        flash(f'Error al editar almacén: {str(e)}', 'danger')
        return redirect(url_for('almacen.index'))

@almacen_bp.route('/<int:id_almacen>/eliminar', methods=['POST'])
def eliminar(id_almacen):
    """Eliminar almacén"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar si tiene estantes
        cursor.execute("SELECT COUNT(*) as count FROM Estante WHERE id_almacen = %s", (id_almacen,))
        result = cursor.fetchone()
        
        if result[0] > 0:
            flash('No se puede eliminar un almacén que tiene estantes asignados', 'warning')
            cursor.close()
            conn.close()
            return redirect(url_for('almacen.ver_detalle', id_almacen=id_almacen))
        
        cursor.execute("DELETE FROM Almacen WHERE id_almacen = %s", (id_almacen,))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        flash('Almacén eliminado exitosamente', 'success')
        return redirect(url_for('almacen.index'))
    except Exception as e:
        flash(f'Error al eliminar almacén: {str(e)}', 'danger')
        return redirect(url_for('almacen.index'))

# ============== ESTANTES ==============

@almacen_bp.route('/<int:id_almacen>/estantes/crear', methods=['GET', 'POST'])
def crear_estante(id_almacen):
    """Crear nuevo estante en un almacén"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Verificar que el almacén existe
        cursor.execute("SELECT * FROM Almacen WHERE id_almacen = %s", (id_almacen,))
        almacen = cursor.fetchone()
        
        if not almacen:
            flash('Almacén no encontrado', 'danger')
            cursor.close()
            conn.close()
            return redirect(url_for('almacen.index'))
        
        if request.method == 'GET':
            cursor.close()
            conn.close()
            return render_template('modulos/almacen.html', tab='crear_estante', almacen=almacen)
        
        # POST - Guardar estante
        pasillo = request.form.get('pasillo', '').strip()
        capacidad = request.form.get('capacidad', 0)
        estado = request.form.get('estado', 'Disponible')
        
        if not pasillo or not capacidad:
            flash('El pasillo y capacidad son requeridos', 'warning')
            cursor.close()
            conn.close()
            return redirect(url_for('almacen.crear_estante', id_almacen=id_almacen))
        
        query = """
            INSERT INTO Estante (pasillo, capacidad, estado, id_almacen)
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(query, (pasillo, capacidad, estado, id_almacen))
        conn.commit()
        
        # Actualizar capacidad del almacén después de crear el estante
        actualizar_capacidad_almacen(cursor, id_almacen)
        conn.commit()
        
        cursor.close()
        conn.close()
        
        flash('Estante creado exitosamente', 'success')
        return redirect(url_for('almacen.ver_detalle', id_almacen=id_almacen))
    except Exception as e:
        flash(f'Error al crear estante: {str(e)}', 'danger')
        return redirect(url_for('almacen.ver_detalle', id_almacen=id_almacen))

@almacen_bp.route('/estante/<int:id_estante>/editar', methods=['GET', 'POST'])
def editar_estante(id_estante):
    """Editar estante"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM Estante WHERE id_estante = %s", (id_estante,))
        estante = cursor.fetchone()
        
        if not estante:
            flash('Estante no encontrado', 'danger')
            cursor.close()
            conn.close()
            return redirect(url_for('almacen.index'))
        
        if request.method == 'GET':
            # Actualizar capacidad antes de mostrar
            actualizar_capacidad_estante(cursor, id_estante)
            conn.commit()
            
            # Recargar el estante con datos actualizados
            cursor.execute("SELECT * FROM Estante WHERE id_estante = %s", (id_estante,))
            estante = cursor.fetchone()
            
            cursor.close()
            conn.close()
            return render_template('modulos/almacen.html', tab='editar_estante', estante=estante)
        
        # POST - Actualizar
        pasillo = request.form.get('pasillo', '').strip()
        capacidad = request.form.get('capacidad', 0)
        estado = request.form.get('estado', 'Disponible')
        
        if not pasillo or not capacidad:
            flash('El pasillo y capacidad son requeridos', 'warning')
            cursor.close()
            conn.close()
            return redirect(url_for('almacen.editar_estante', id_estante=id_estante))
        
        query = """
            UPDATE Estante 
            SET pasillo = %s, capacidad = %s, estado = %s
            WHERE id_estante = %s
        """
        cursor.execute(query, (pasillo, capacidad, estado, id_estante))
        conn.commit()
        
        # Actualizar capacidad del almacén
        actualizar_capacidad_almacen(cursor, estante['id_almacen'])
        conn.commit()
        
        cursor.close()
        conn.close()
        
        flash('Estante actualizado exitosamente', 'success')
        return redirect(url_for('almacen.ver_detalle', id_almacen=estante['id_almacen']))
    except Exception as e:
        flash(f'Error al editar estante: {str(e)}', 'danger')
        return redirect(url_for('almacen.index'))

@almacen_bp.route('/estante/<int:id_estante>/eliminar', methods=['POST'])
def eliminar_estante(id_estante):
    """Eliminar estante"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT id_almacen FROM Estante WHERE id_estante = %s", (id_estante,))
        estante = cursor.fetchone()
        
        if not estante:
            flash('Estante no encontrado', 'danger')
            cursor.close()
            conn.close()
            return redirect(url_for('almacen.index'))
        
        # Verificar si tiene inventario
        cursor.execute("SELECT COUNT(*) as count FROM Inventario WHERE id_estante = %s", (id_estante,))
        result = cursor.fetchone()
        
        if result['count'] > 0:
            flash('No se puede eliminar un estante que contiene productos', 'warning')
            cursor.close()
            conn.close()
            return redirect(url_for('almacen.ver_detalle', id_almacen=estante['id_almacen']))
        
        id_almacen = estante['id_almacen']
        
        cursor.execute("DELETE FROM Estante WHERE id_estante = %s", (id_estante,))
        conn.commit()
        
        # Actualizar capacidad del almacén después de eliminar
        actualizar_capacidad_almacen(cursor, id_almacen)
        conn.commit()
        
        cursor.close()
        conn.close()
        
        flash('Estante eliminado exitosamente', 'success')
        return redirect(url_for('almacen.ver_detalle', id_almacen=id_almacen))
    except Exception as e:
        flash(f'Error al eliminar estante: {str(e)}', 'danger')
        return redirect(url_for('almacen.index'))