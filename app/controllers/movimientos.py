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
            SELECT DISTINCT m.id_movimiento_producto, m.cantidad_producto, m.motivo, 
                m.fecha_movimiento, m.id_persona, m.id_producto,
                p.marca, cat.nombre_categoria, 
                per.nombre, per.apellido_paterno,
                prov.nombre_proveedor, prov.empresa
            FROM Movimiento_Producto m
            INNER JOIN Producto p ON m.id_producto = p.id_producto
            INNER JOIN Categoria_Producto cat ON p.id_categoria_producto = cat.id_categoria_producto
            LEFT JOIN Persona per ON m.id_persona = per.id_persona
            LEFT JOIN (
                SELECT id_producto, id_proveedor, 
                    ROW_NUMBER() OVER (PARTITION BY id_producto ORDER BY id_inventario DESC) as rn
                FROM Inventario
            ) inv ON p.id_producto = inv.id_producto AND inv.rn = 1
            LEFT JOIN Proveedor prov ON inv.id_proveedor = prov.id_proveedor
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
            # Obtener productos de recepciones con estado 'Recibido' - SIN agrupar por proveedor
            cursor.execute("""
                SELECT di.id_detalle_ingreso, p.id_producto, p.marca, cat.nombre_categoria,
                    ped.id_pedido, ped.id_proveedor, prov.nombre_proveedor, prov.empresa,
                    di.cantidad as cantidad_recibida,
                    ped.estado
                FROM Detalle_Ingreso di
                INNER JOIN Producto p ON di.id_producto = p.id_producto
                INNER JOIN Categoria_Producto cat ON p.id_categoria_producto = cat.id_categoria_producto
                INNER JOIN Pedido ped ON di.id_pedido = ped.id_pedido
                INNER JOIN Proveedor prov ON ped.id_proveedor = prov.id_proveedor
                WHERE ped.estado = 'Recibido'
                ORDER BY prov.nombre_proveedor, p.marca, di.id_detalle_ingreso
            """)
            productos_pendientes = cursor.fetchall()
            
            # Obtener almacenes disponibles
            cursor.execute("""
                SELECT a.id_almacen, a.nombre_almacen, a.ubicacion,
                    (a.capacidad - a.capacidad_ocupada) as disponible
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
        id_detalle_ingreso = request.form.get('id_detalle_ingreso')
        id_pedido = request.form.get('id_pedido')
        id_proveedor = request.form.get('id_proveedor')
        id_estante = request.form.get('id_estante')
        cantidad = request.form.get('cantidad')
        
        if not all([id_detalle_ingreso, id_pedido, id_proveedor, id_estante, cantidad]):
            flash('Todos los campos son obligatorios', 'warning')
            return redirect(url_for('movimientos.asignar'))
        
        cantidad = int(cantidad)
        
        # Obtener información del detalle de ingreso
        cursor.execute("""
            SELECT di.id_detalle_ingreso, di.id_producto, di.cantidad, ped.estado
            FROM Detalle_Ingreso di
            INNER JOIN Pedido ped ON di.id_pedido = ped.id_pedido
            WHERE di.id_detalle_ingreso = %s
        """, (id_detalle_ingreso,))
        detalle = cursor.fetchone()
        
        if not detalle or detalle['estado'] != 'Recibido':
            flash('El pedido no está en estado Recibido', 'warning')
            cursor.close()
            conn.close()
            return redirect(url_for('movimientos.asignar'))
        
        if cantidad > detalle['cantidad']:
            flash('La cantidad solicitada supera la cantidad recibida', 'warning')
            cursor.close()
            conn.close()
            return redirect(url_for('movimientos.asignar'))
        
        # Verificar capacidad del estante
        cursor.execute("SELECT capacidad, capacidad_ocupada FROM Estante WHERE id_estante = %s", (id_estante,))
        estante = cursor.fetchone()
        
        if estante['capacidad_ocupada'] + cantidad > estante['capacidad']:
            flash('El estante no tiene capacidad suficiente', 'warning')
            cursor.close()
            conn.close()
            return redirect(url_for('movimientos.asignar'))
        
        # Verificar si ya existe inventario para ese producto, estante y proveedor
        cursor.execute("""
            SELECT id_inventario, stock_producto 
            FROM Inventario 
            WHERE id_producto = %s AND id_estante = %s AND id_proveedor = %s
        """, (detalle['id_producto'], id_estante, id_proveedor))
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
                INSERT INTO Inventario (stock_producto, fecha_modificacion, id_estante, id_producto, id_proveedor, estado)
                VALUES (%s, %s, %s, %s, %s, 'Disponible')
            """, (cantidad, datetime.now().date(), id_estante, detalle['id_producto'], id_proveedor))
        
        # Actualizar capacidad ocupada del estante
        cursor.execute("""
            UPDATE Estante 
            SET capacidad_ocupada = capacidad_ocupada + %s
            WHERE id_estante = %s
        """, (cantidad, id_estante))
        
        # Actualizar capacidad ocupada del almacén
        cursor.execute("""
            UPDATE Almacen a
            INNER JOIN Estante e ON a.id_almacen = e.id_almacen
            SET a.capacidad_ocupada = a.capacidad_ocupada + %s
            WHERE e.id_estante = %s
        """, (cantidad, id_estante))
        
        # Registrar movimiento
        cursor.execute("""
            INSERT INTO Movimiento_Producto (cantidad_producto, motivo, fecha_movimiento, id_persona, id_producto)
            VALUES (%s, %s, %s, %s, %s)
        """, (cantidad, 'Ingreso Inicial', datetime.now().date(), session.get('user_id'), detalle['id_producto']))
        
        # Cambiar estado del pedido a 'Asignado'
        cursor.execute("""
            UPDATE Pedido
            SET estado = 'Asignado'
            WHERE id_pedido = %s
        """, (id_pedido,))
        
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
            # Obtener productos en inventario con información del proveedor
            cursor.execute("""
                SELECT inv.id_inventario, inv.stock_producto, inv.id_estante, inv.id_proveedor,
                    p.id_producto, p.marca, cat.nombre_categoria,
                    e.pasillo, a.nombre_almacen,
                    prov.nombre_proveedor, prov.empresa
                FROM Inventario inv
                INNER JOIN Producto p ON inv.id_producto = p.id_producto
                INNER JOIN Categoria_Producto cat ON p.id_categoria_producto = cat.id_categoria_producto
                INNER JOIN Estante e ON inv.id_estante = e.id_estante
                INNER JOIN Almacen a ON e.id_almacen = a.id_almacen
                LEFT JOIN Proveedor prov ON inv.id_proveedor = prov.id_proveedor
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
        
        # Actualizar capacidad almacén origen
        cursor.execute("""
            UPDATE Almacen a
            INNER JOIN Estante e ON a.id_almacen = e.id_almacen
            SET a.capacidad_ocupada = a.capacidad_ocupada - %s
            WHERE e.id_almacen = (SELECT id_almacen FROM Estante WHERE id_estante = %s)
        """, (cantidad, inv_origen['id_estante']))
        
        # Agregar stock en destino
        cursor.execute("""
            SELECT id_inventario, stock_producto 
            FROM Inventario 
            WHERE id_producto = %s AND id_estante = %s AND id_proveedor <=> %s
        """, (inv_origen['id_producto'], id_estante_destino, inv_origen['id_proveedor']))
        inv_destino = cursor.fetchone()
        
        if inv_destino:
            cursor.execute("""
                UPDATE Inventario 
                SET stock_producto = stock_producto + %s, fecha_modificacion = %s
                WHERE id_inventario = %s
            """, (cantidad, datetime.now().date(), inv_destino['id_inventario']))
        else:
            cursor.execute("""
                INSERT INTO Inventario (stock_producto, fecha_modificacion, id_estante, id_producto, id_proveedor, estado)
                VALUES (%s, %s, %s, %s, %s, 'Disponible')
            """, (cantidad, datetime.now().date(), id_estante_destino, inv_origen['id_producto'], inv_origen['id_proveedor']))
        
        # Actualizar capacidad estante destino
        cursor.execute("""
            UPDATE Estante 
            SET capacidad_ocupada = capacidad_ocupada + %s
            WHERE id_estante = %s
        """, (cantidad, id_estante_destino))
        
        # Actualizar capacidad almacén destino
        cursor.execute("""
            UPDATE Almacen a
            INNER JOIN Estante e ON a.id_almacen = e.id_almacen
            SET a.capacidad_ocupada = a.capacidad_ocupada + %s
            WHERE e.id_almacen = (SELECT id_almacen FROM Estante WHERE id_estante = %s)
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
                SELECT inv.*, p.marca, cat.nombre_categoria, 
                    e.pasillo, a.nombre_almacen,
                    prov.nombre_proveedor, prov.empresa
                FROM Inventario inv
                INNER JOIN Producto p ON inv.id_producto = p.id_producto
                INNER JOIN Categoria_Producto cat ON p.id_categoria_producto = cat.id_categoria_producto
                INNER JOIN Estante e ON inv.id_estante = e.id_estante
                INNER JOIN Almacen a ON e.id_almacen = a.id_almacen
                LEFT JOIN Proveedor prov ON inv.id_proveedor = prov.id_proveedor
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
            SELECT inv.*, e.capacidad_ocupada, e.capacidad, e.id_almacen
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
        
        # Actualizar capacidad del almacén
        cursor.execute("""
            UPDATE Almacen 
            SET capacidad_ocupada = capacidad_ocupada + %s
            WHERE id_almacen = %s
        """, (ajuste, inventario['id_almacen']))
        
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

@movimientos_bp.route('/proveedor-info/<int:id_producto>/<int:id_proveedor>', methods=['GET'])
def obtener_info_proveedor(id_producto, id_proveedor):
    """API para obtener información del proveedor de un producto"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT prov.nombre_proveedor, prov.empresa,
                COALESCE(SUM(di.cantidad), 0) as total_recibido,
                COALESCE(SUM(CASE WHEN ped.estado = 'Asignado' THEN di.cantidad ELSE 0 END), 0) as cantidad_asignada
            FROM Proveedor prov
            INNER JOIN Pedido ped ON prov.id_proveedor = ped.id_proveedor
            INNER JOIN Detalle_Ingreso di ON ped.id_pedido = di.id_pedido
            WHERE prov.id_proveedor = %s AND di.id_producto = %s AND ped.estado IN ('Recibido', 'Asignado')
            GROUP BY prov.id_proveedor
        """, (id_proveedor, id_producto))
        info = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if info:
            pendiente = info['total_recibido'] - info['cantidad_asignada']
            return {
                'success': True,
                'nombre': info['nombre_proveedor'],
                'empresa': info['empresa'],
                'pendiente': pendiente
            }
        return {'success': False}
    except Exception as e:
        return {'success': False, 'error': str(e)}