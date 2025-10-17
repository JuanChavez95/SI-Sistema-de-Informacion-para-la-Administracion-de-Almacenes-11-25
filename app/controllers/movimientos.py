from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from datetime import datetime
import mysql.connector
from app.config import Config

movimientos_bp = Blueprint('movimientos', __name__, url_prefix='/movimientos')

def get_db_connection():
    return mysql.connector.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DB
    )

@movimientos_bp.route('/', methods=['GET'])
def index():
    """Listar todos los movimientos"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT m.*, p.marca, cat.nombre_categoria, per.nombre, per.apellido_paterno
            FROM Movimiento_Producto m
            INNER JOIN Producto p ON m.id_producto = p.id_producto
            INNER JOIN Categoria_Producto cat ON p.id_categoria_producto = cat.id_categoria_producto
            LEFT JOIN Persona per ON m.id_persona = per.id_persona
            ORDER BY m.fecha_movimiento DESC, m.id_movimiento_producto DESC
        """)
        movimientos = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('modulos/movimientos.html',
                            tab='lista',
                            movimientos=movimientos)
    except Exception as e:
        flash(f'Error al cargar movimientos: {str(e)}', 'danger')
        return redirect(url_for('dashboard.index'))

@movimientos_bp.route('/asignar', methods=['GET', 'POST'])
def asignar():
    """Asignar producto de recepción a estante (Ingreso Inicial)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        if request.method == 'GET':
            # Obtener productos de recepciones que aún no están en inventario
            cursor.execute("""
                SELECT DISTINCT p.id_producto, p.marca, cat.nombre_categoria,
                    SUM(di.cantidad) as cantidad_recibida,
                    COALESCE(SUM(inv.stock_producto), 0) as cantidad_inventario,
                    (SUM(di.cantidad) - COALESCE(SUM(inv.stock_producto), 0)) as pendiente_asignar
                FROM Detalle_Ingreso di
                INNER JOIN Producto p ON di.id_producto = p.id_producto
                INNER JOIN Categoria_Producto cat ON p.id_categoria_producto = cat.id_categoria_producto
                LEFT JOIN Inventario inv ON p.id_producto = inv.id_producto
                GROUP BY p.id_producto
                HAVING pendiente_asignar > 0
            """)
            productos_pendientes = cursor.fetchall()
            
            # Obtener almacenes y estantes disponibles
            cursor.execute("""
                SELECT a.id_almacen, a.nombre_almacen, a.ubicacion
                FROM Almacen a
                ORDER BY a.nombre_almacen
            """)
            almacenes = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return render_template('modulos/movimientos.html',
                                tab='asignar',
                                productos=productos_pendientes,
                                almacenes=almacenes)
        
        # POST - Asignar producto
        id_producto = request.form.get('id_producto')
        id_estante = request.form.get('id_estante')
        cantidad = request.form.get('cantidad')
        
        if not all([id_producto, id_estante, cantidad]):
            flash('Todos los campos son obligatorios', 'warning')
            return redirect(url_for('movimientos.asignar'))
        
        cantidad = int(cantidad)
        
        # Verificar capacidad del estante
        cursor.execute("SELECT capacidad, capacidad_ocupada FROM Estante WHERE id_estante = %s", (id_estante,))
        estante = cursor.fetchone()
        
        if estante['capacidad_ocupada'] + cantidad > estante['capacidad']:
            flash('El estante no tiene capacidad suficiente', 'warning')
            cursor.close()
            conn.close()
            return redirect(url_for('movimientos.asignar'))
        
        # Verificar si ya existe inventario en ese estante para ese producto
        cursor.execute("""
            SELECT id_inventario, stock_producto 
            FROM Inventario 
            WHERE id_producto = %s AND id_estante = %s
        """, (id_producto, id_estante))
        inventario_existe = cursor.fetchone()
        
        if inventario_existe:
            # Actualizar inventario existente
            nuevo_stock = inventario_existe['stock_producto'] + cantidad
            cursor.execute("""
                UPDATE Inventario 
                SET stock_producto = %s, fecha_modificacion = %s
                WHERE id_inventario = %s
            """, (nuevo_stock, datetime.now().date(), inventario_existe['id_inventario']))
        else:
            # Crear nuevo registro de inventario
            cursor.execute("""
                INSERT INTO Inventario (stock_producto, fecha_modificacion, id_estante, id_producto)
                VALUES (%s, %s, %s, %s)
            """, (cantidad, datetime.now().date(), id_estante, id_producto))
        
        # Actualizar capacidad ocupada del estante
        cursor.execute("""
            UPDATE Estante 
            SET capacidad_ocupada = capacidad_ocupada + %s
            WHERE id_estante = %s
        """, (cantidad, id_estante))
        
        # Registrar movimiento
        cursor.execute("""
            INSERT INTO Movimiento_Producto (cantidad_producto, motivo, fecha_movimiento, id_persona, id_producto)
            VALUES (%s, %s, %s, %s, %s)
        """, (cantidad, 'Ingreso Inicial', datetime.now().date(), session.get('user_id'), id_producto))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Producto asignado exitosamente al inventario', 'success')
        return redirect(url_for('movimientos.asignar'))
    except Exception as e:
        flash(f'Error al asignar producto: {str(e)}', 'danger')
        return redirect(url_for('movimientos.asignar'))

@movimientos_bp.route('/trasladar', methods=['GET', 'POST'])
def trasladar():
    """Mover producto entre estantes"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        if request.method == 'GET':
            # Obtener productos en inventario
            cursor.execute("""
                SELECT inv.id_inventario, inv.stock_producto, inv.id_estante,
                    p.id_producto, p.marca, cat.nombre_categoria,
                    e.pasillo, a.nombre_almacen
                FROM Inventario inv
                INNER JOIN Producto p ON inv.id_producto = p.id_producto
                INNER JOIN Categoria_Producto cat ON p.id_categoria_producto = cat.id_categoria_producto
                INNER JOIN Estante e ON inv.id_estante = e.id_estante
                INNER JOIN Almacen a ON e.id_almacen = a.id_almacen
                WHERE inv.stock_producto > 0
                ORDER BY a.nombre_almacen, e.pasillo
            """)
            inventarios = cursor.fetchall()
            
            # Obtener almacenes
            cursor.execute("SELECT * FROM Almacen ORDER BY nombre_almacen")
            almacenes = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return render_template('modulos/movimientos.html',
                                tab='trasladar',
                                inventarios=inventarios,
                                almacenes=almacenes)
        
        # POST - Trasladar
        id_inventario = request.form.get('id_inventario')
        id_estante_destino = request.form.get('id_estante_destino')
        cantidad = request.form.get('cantidad')
        
        if not all([id_inventario, id_estante_destino, cantidad]):
            flash('Todos los campos son obligatorios', 'warning')
            return redirect(url_for('movimientos.trasladar'))
        
        cantidad = int(cantidad)
        
        # Obtener información del inventario origen
        cursor.execute("""
            SELECT inv.*, e.capacidad_ocupada as estante_ocupado_origen
            FROM Inventario inv
            INNER JOIN Estante e ON inv.id_estante = e.id_estante
            WHERE inv.id_inventario = %s
        """, (id_inventario,))
        inv_origen = cursor.fetchone()
        
        if cantidad > inv_origen['stock_producto']:
            flash('Cantidad mayor al stock disponible', 'warning')
            cursor.close()
            conn.close()
            return redirect(url_for('movimientos.trasladar'))
        
        # Verificar capacidad del estante destino
        cursor.execute("SELECT capacidad, capacidad_ocupada FROM Estante WHERE id_estante = %s", (id_estante_destino,))
        estante_destino = cursor.fetchone()
        
        if estante_destino['capacidad_ocupada'] + cantidad > estante_destino['capacidad']:
            flash('El estante destino no tiene capacidad suficiente', 'warning')
            cursor.close()
            conn.close()
            return redirect(url_for('movimientos.trasladar'))
        
        # Reducir stock en origen
        nuevo_stock_origen = inv_origen['stock_producto'] - cantidad
        if nuevo_stock_origen == 0:
            cursor.execute("DELETE FROM Inventario WHERE id_inventario = %s", (id_inventario,))
        else:
            cursor.execute("""
                UPDATE Inventario 
                SET stock_producto = %s, fecha_modificacion = %s
                WHERE id_inventario = %s
            """, (nuevo_stock_origen, datetime.now().date(), id_inventario))
        
        # Actualizar capacidad estante origen
        cursor.execute("""
            UPDATE Estante 
            SET capacidad_ocupada = capacidad_ocupada - %s
            WHERE id_estante = %s
        """, (cantidad, inv_origen['id_estante']))
        
        # Agregar stock en destino
        cursor.execute("""
            SELECT id_inventario, stock_producto 
            FROM Inventario 
            WHERE id_producto = %s AND id_estante = %s
        """, (inv_origen['id_producto'], id_estante_destino))
        inv_destino = cursor.fetchone()
        
        if inv_destino:
            cursor.execute("""
                UPDATE Inventario 
                SET stock_producto = stock_producto + %s, fecha_modificacion = %s
                WHERE id_inventario = %s
            """, (cantidad, datetime.now().date(), inv_destino['id_inventario']))
        else:
            cursor.execute("""
                INSERT INTO Inventario (stock_producto, fecha_modificacion, id_estante, id_producto)
                VALUES (%s, %s, %s, %s)
            """, (cantidad, datetime.now().date(), id_estante_destino, inv_origen['id_producto']))
        
        # Actualizar capacidad estante destino
        cursor.execute("""
            UPDATE Estante 
            SET capacidad_ocupada = capacidad_ocupada + %s
            WHERE id_estante = %s
        """, (cantidad, id_estante_destino))
        
        # Registrar movimiento
        cursor.execute("""
            INSERT INTO Movimiento_Producto (cantidad_producto, motivo, fecha_movimiento, id_persona, id_producto)
            VALUES (%s, %s, %s, %s, %s)
        """, (cantidad, 'Traslado', datetime.now().date(), session.get('user_id'), inv_origen['id_producto']))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Traslado realizado exitosamente', 'success')
        return redirect(url_for('movimientos.trasladar'))
    except Exception as e:
        flash(f'Error al trasladar: {str(e)}', 'danger')
        return redirect(url_for('movimientos.trasladar'))

@movimientos_bp.route('/ajustar', methods=['GET', 'POST'])
def ajustar():
    """Ajustar stock (correcciones, mermas)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        if request.method == 'GET':
            cursor.execute("""
                SELECT inv.*, p.marca, cat.nombre_categoria, e.pasillo, a.nombre_almacen
                FROM Inventario inv
                INNER JOIN Producto p ON inv.id_producto = p.id_producto
                INNER JOIN Categoria_Producto cat ON p.id_categoria_producto = cat.id_categoria_producto
                INNER JOIN Estante e ON inv.id_estante = e.id_estante
                INNER JOIN Almacen a ON e.id_almacen = a.id_almacen
                ORDER BY a.nombre_almacen, e.pasillo
            """)
            inventarios = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return render_template('modulos/movimientos.html',
                                tab='ajustar',
                                inventarios=inventarios)
        
        # POST - Ajustar
        id_inventario = request.form.get('id_inventario')
        ajuste = request.form.get('ajuste')
        motivo = request.form.get('motivo', 'Ajuste')
        
        if not all([id_inventario, ajuste]):
            flash('Todos los campos son obligatorios', 'warning')
            return redirect(url_for('movimientos.ajustar'))
        
        ajuste = int(ajuste)
        
        # Obtener inventario actual
        cursor.execute("""
            SELECT inv.*, e.capacidad_ocupada, e.capacidad
            FROM Inventario inv
            INNER JOIN Estante e ON inv.id_estante = e.id_estante
            WHERE inv.id_inventario = %s
        """, (id_inventario,))
        inventario = cursor.fetchone()
        
        nuevo_stock = inventario['stock_producto'] + ajuste
        
        if nuevo_stock < 0:
            flash('El stock no puede ser negativo', 'warning')
            cursor.close()
            conn.close()
            return redirect(url_for('movimientos.ajustar'))
        
        # Actualizar inventario
        if nuevo_stock == 0:
            cursor.execute("DELETE FROM Inventario WHERE id_inventario = %s", (id_inventario,))
        else:
            cursor.execute("""
                UPDATE Inventario 
                SET stock_producto = %s, fecha_modificacion = %s
                WHERE id_inventario = %s
            """, (nuevo_stock, datetime.now().date(), id_inventario))
        
        # Actualizar capacidad del estante
        cursor.execute("""
            UPDATE Estante 
            SET capacidad_ocupada = capacidad_ocupada + %s
            WHERE id_estante = %s
        """, (ajuste, inventario['id_estante']))
        
        # Registrar movimiento
        cursor.execute("""
            INSERT INTO Movimiento_Producto (cantidad_producto, motivo, fecha_movimiento, id_persona, id_producto)
            VALUES (%s, %s, %s, %s, %s)
        """, (abs(ajuste), motivo, datetime.now().date(), session.get('user_id'), inventario['id_producto']))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Ajuste de stock realizado exitosamente', 'success')
        return redirect(url_for('movimientos.ajustar'))
    except Exception as e:
        flash(f'Error al ajustar stock: {str(e)}', 'danger')
        return redirect(url_for('movimientos.ajustar'))

@movimientos_bp.route('/estantes/<int:id_almacen>', methods=['GET'])
def obtener_estantes(id_almacen):
    """API para obtener estantes de un almacén"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT id_estante, pasillo, capacidad, capacidad_ocupada,
                (capacidad - capacidad_ocupada) as disponible
            FROM Estante
            WHERE id_almacen = %s AND estado != 'Inutilizable'
            ORDER BY pasillo
        """, (id_almacen,))
        estantes = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # Generar HTML options
        html = '<option value="">-- Seleccionar Estante --</option>'
        for estante in estantes:
            html += f'<option value="{estante["id_estante"]}">{estante["pasillo"]} (Disponible: {estante["disponible"]})</option>'
        
        return html
    except Exception as e:
        return f'<option value="">Error al cargar estantes</option>'