from flask import Blueprint, render_template, request, flash, redirect, url_for, session, jsonify
from datetime import datetime
import mysql.connector
from app.config import Config

despachos_bp = Blueprint('despachos', __name__, url_prefix='/despachos')

def get_db_connection():
    return mysql.connector.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DB
    )

@despachos_bp.route('/')
def index():
    """1. Listar todos los despachos"""
    try:
        user_role = session.get('user_role')
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT pd.*, prov.nombre_proveedor, prov.empresa,
                per.nombre, per.apellido_paterno,
                COUNT(dd.id_detalle_despacho) as total_items,
                SUM(dd.cantidad_solicitada) as total_solicitado,
                SUM(dd.cantidad_despachada) as total_despachado
            FROM Pedido_Despacho pd
            INNER JOIN Proveedor prov ON pd.id_proveedor = prov.id_proveedor
            INNER JOIN Persona per ON pd.id_persona = per.id_persona
            LEFT JOIN Detalle_Despacho dd ON pd.id_pedido_despacho = dd.id_pedido_despacho
            GROUP BY pd.id_pedido_despacho
            ORDER BY pd.fecha_solicitud DESC
        """)
        despachos = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if user_role == 'Auxiliar' or user_role == "Cliente":
            return render_template('auxiliar/despachos_auxiliar.html', despachos=despachos, tab='lista')
        
        return render_template('modulos/despachos.html', despachos=despachos, tab='lista')
    except Exception as e:
        flash(f'Error al cargar despachos: {str(e)}', 'danger')
        return redirect(url_for('dashboard.index'))

@despachos_bp.route('/crear', methods=['GET', 'POST'])
def crear():
    """2. Crear nuevo despacho"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        if request.method == 'GET':
            # Obtener proveedores que tienen productos en inventario
            cursor.execute("""
                SELECT DISTINCT prov.id_proveedor, prov.nombre_proveedor, prov.empresa, prov.nit
                FROM Proveedor prov
                INNER JOIN Inventario inv ON prov.id_proveedor = inv.id_proveedor
                WHERE inv.stock_producto > 0
                ORDER BY prov.nombre_proveedor
            """)
            proveedores = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return render_template('modulos/despachos.html', proveedores=proveedores, tab='crear')
        
        # POST - Crear despacho
        id_proveedor = request.form.get('id_proveedor')
        observaciones = request.form.get('observaciones', '')
        productos = request.form.getlist('productos[]')
        cantidades = request.form.getlist('cantidades[]')
        inventarios = request.form.getlist('inventarios[]')
        
        if not id_proveedor or not productos:
            flash('Debe seleccionar un proveedor y al menos un producto', 'warning')
            return redirect(url_for('despachos.crear'))
        
        # Generar número de guía
        cursor.execute("SELECT COUNT(*) as total FROM Pedido_Despacho")
        total = cursor.fetchone()['total']
        numero_guia = f"GS-{datetime.now().strftime('%Y%m%d')}-{total + 1:04d}"
        
        # Insertar pedido de despacho
        cursor.execute("""
            INSERT INTO Pedido_Despacho (numero_guia, fecha_solicitud, observaciones, id_proveedor, id_persona)
            VALUES (%s, %s, %s, %s, %s)
        """, (numero_guia, datetime.now().date(), observaciones, id_proveedor, session.get('user_id')))
        
        id_pedido_despacho = cursor.lastrowid
        
        # Insertar detalles
        for i in range(len(productos)):
            if productos[i] and cantidades[i]:
                cursor.execute("""
                    INSERT INTO Detalle_Despacho (id_pedido_despacho, id_producto, id_inventario, cantidad_solicitada)
                    VALUES (%s, %s, %s, %s)
                """, (id_pedido_despacho, productos[i], inventarios[i] if inventarios[i] else None, cantidades[i]))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash(f'Despacho {numero_guia} creado exitosamente', 'success')
        return redirect(url_for('despachos.detalle', id=id_pedido_despacho))
    except Exception as e:
        flash(f'Error al crear despacho: {str(e)}', 'danger')
        return redirect(url_for('despachos.crear'))

@despachos_bp.route('/<int:id>/detalle')
def detalle(id):
    """3. Ver detalle del despacho"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener pedido de despacho
        cursor.execute("""
            SELECT pd.*, prov.nombre_proveedor, prov.empresa, prov.telefono, prov.direccion,
                per.nombre, per.apellido_paterno, per.email
            FROM Pedido_Despacho pd
            INNER JOIN Proveedor prov ON pd.id_proveedor = prov.id_proveedor
            INNER JOIN Persona per ON pd.id_persona = per.id_persona
            WHERE pd.id_pedido_despacho = %s
        """, (id,))
        despacho = cursor.fetchone()
        
        if not despacho:
            flash('Despacho no encontrado', 'warning')
            return redirect(url_for('despachos.index'))
        
        # Obtener detalles
        cursor.execute("""
            SELECT dd.*, p.marca, cat.nombre_categoria,
                inv.stock_producto, e.pasillo, a.nombre_almacen
            FROM Detalle_Despacho dd
            INNER JOIN Producto p ON dd.id_producto = p.id_producto
            INNER JOIN Categoria_Producto cat ON p.id_categoria_producto = cat.id_categoria_producto
            LEFT JOIN Inventario inv ON dd.id_inventario = inv.id_inventario
            LEFT JOIN Estante e ON inv.id_estante = e.id_estante
            LEFT JOIN Almacen a ON e.id_almacen = a.id_almacen
            WHERE dd.id_pedido_despacho = %s
        """, (id,))
        detalles = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('modulos/despachos.html', despacho=despacho, detalles=detalles, tab='detalle')
    except Exception as e:
        flash(f'Error al cargar detalle: {str(e)}', 'danger')
        return redirect(url_for('despachos.index'))

@despachos_bp.route('/<int:id>/picking')
def picking(id):
    """4. Vista de preparación/picking"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT pd.*, prov.nombre_proveedor, prov.empresa
            FROM Pedido_Despacho pd
            INNER JOIN Proveedor prov ON pd.id_proveedor = prov.id_proveedor
            WHERE pd.id_pedido_despacho = %s
        """, (id,))
        despacho = cursor.fetchone()
        
        cursor.execute("""
            SELECT dd.*, p.marca, cat.nombre_categoria,
                inv.stock_producto, e.pasillo, a.nombre_almacen, a.id_almacen, e.id_estante
            FROM Detalle_Despacho dd
            INNER JOIN Producto p ON dd.id_producto = p.id_producto
            INNER JOIN Categoria_Producto cat ON p.id_categoria_producto = cat.id_categoria_producto
            LEFT JOIN Inventario inv ON dd.id_inventario = inv.id_inventario
            LEFT JOIN Estante e ON inv.id_estante = e.id_estante
            LEFT JOIN Almacen a ON e.id_almacen = a.id_almacen
            WHERE dd.id_pedido_despacho = %s
            ORDER BY a.nombre_almacen, e.pasillo
        """, (id,))
        detalles = cursor.fetchall()
        
        # Actualizar estado a "En Preparación"
        if despacho['estado'] == 'Pendiente':
            cursor.execute("""
                UPDATE Pedido_Despacho SET estado = 'En Preparación' WHERE id_pedido_despacho = %s
            """, (id,))
            conn.commit()
            despacho['estado'] = 'En Preparación'
        
        cursor.close()
        conn.close()
        
        return render_template('modulos/despachos.html', despacho=despacho, detalles=detalles, tab='picking')
    except Exception as e:
        flash(f'Error al cargar picking: {str(e)}', 'danger')
        return redirect(url_for('despachos.index'))

@despachos_bp.route('/<int:id>/confirmar', methods=['POST'])
def confirmar(id):
    """5. Confirmar despacho y actualizar inventario"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cantidades_despachadas = request.form.getlist('cantidades_despachadas[]')
        ids_detalle = request.form.getlist('ids_detalle[]')
        
        # Obtener despacho
        cursor.execute("SELECT * FROM Pedido_Despacho WHERE id_pedido_despacho = %s", (id,))
        despacho = cursor.fetchone()
        
        if despacho['estado'] == 'Despachado':
            flash('Este despacho ya fue confirmado', 'warning')
            return redirect(url_for('despachos.detalle', id=id))
        
        # Procesar cada detalle
        for i in range(len(ids_detalle)):
            id_detalle = ids_detalle[i]
            cantidad_despachada = int(cantidades_despachadas[i])
            
            # Obtener detalle
            cursor.execute("""
                SELECT dd.*, inv.stock_producto, inv.id_estante, e.id_almacen
                FROM Detalle_Despacho dd
                LEFT JOIN Inventario inv ON dd.id_inventario = inv.id_inventario
                LEFT JOIN Estante e ON inv.id_estante = e.id_estante
                WHERE dd.id_detalle_despacho = %s
            """, (id_detalle,))
            detalle = cursor.fetchone()
            
            if cantidad_despachada > 0:
                # Actualizar cantidad despachada
                cursor.execute("""
                    UPDATE Detalle_Despacho SET cantidad_despachada = %s WHERE id_detalle_despacho = %s
                """, (cantidad_despachada, id_detalle))
                
                # Reducir inventario
                nuevo_stock = detalle['stock_producto'] - cantidad_despachada
                if nuevo_stock <= 0:
                    cursor.execute("DELETE FROM Inventario WHERE id_inventario = %s", (detalle['id_inventario'],))
                else:
                    cursor.execute("""
                        UPDATE Inventario SET stock_producto = %s, fecha_modificacion = %s 
                        WHERE id_inventario = %s
                    """, (nuevo_stock, datetime.now().date(), detalle['id_inventario']))
                
                # Reducir capacidad ocupada del estante
                cursor.execute("""
                    UPDATE Estante SET capacidad_ocupada = capacidad_ocupada - %s WHERE id_estante = %s
                """, (cantidad_despachada, detalle['id_estante']))
                
                # Reducir capacidad ocupada del almacén
                cursor.execute("""
                    UPDATE Almacen SET capacidad_ocupada = capacidad_ocupada - %s WHERE id_almacen = %s
                """, (cantidad_despachada, detalle['id_almacen']))
                
                # Registrar movimiento de salida
                cursor.execute("""
                    INSERT INTO Movimiento_Producto (cantidad_producto, motivo, fecha_movimiento, id_persona, id_producto)
                    VALUES (%s, %s, %s, %s, %s)
                """, (cantidad_despachada, f'Despacho {despacho["numero_guia"]}', datetime.now().date(), 
                      session.get('user_id'), detalle['id_producto']))
        
        # Actualizar estado del pedido
        cursor.execute("""
            UPDATE Pedido_Despacho SET estado = 'Despachado', fecha_despacho = %s WHERE id_pedido_despacho = %s
        """, (datetime.now().date(), id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Despacho confirmado exitosamente', 'success')
        return redirect(url_for('despachos.detalle', id=id))
    except Exception as e:
        flash(f'Error al confirmar despacho: {str(e)}', 'danger')
        return redirect(url_for('despachos.picking', id=id))

@despachos_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
def editar(id):
    """6. Editar despacho (solo si está pendiente)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        if request.method == 'GET':
            cursor.execute("""
                SELECT pd.*, prov.nombre_proveedor
                FROM Pedido_Despacho pd
                INNER JOIN Proveedor prov ON pd.id_proveedor = prov.id_proveedor
                WHERE pd.id_pedido_despacho = %s
            """, (id,))
            despacho = cursor.fetchone()
            
            if despacho['estado'] != 'Pendiente':
                flash('Solo se pueden editar despachos pendientes', 'warning')
                return redirect(url_for('despachos.detalle', id=id))
            
            cursor.execute("""
                SELECT dd.*, p.marca, cat.nombre_categoria
                FROM Detalle_Despacho dd
                INNER JOIN Producto p ON dd.id_producto = p.id_producto
                INNER JOIN Categoria_Producto cat ON p.id_categoria_producto = cat.id_categoria_producto
                WHERE dd.id_pedido_despacho = %s
            """, (id,))
            detalles = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return render_template('modulos/despachos.html', despacho=despacho, detalles=detalles, tab='editar')
        
        # POST - Actualizar
        observaciones = request.form.get('observaciones', '')
        
        cursor.execute("""
            UPDATE Pedido_Despacho SET observaciones = %s WHERE id_pedido_despacho = %s
        """, (observaciones, id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Despacho actualizado exitosamente', 'success')
        return redirect(url_for('despachos.detalle', id=id))
    except Exception as e:
        flash(f'Error al editar despacho: {str(e)}', 'danger')
        return redirect(url_for('despachos.detalle', id=id))

@despachos_bp.route('/<int:id>/cancelar', methods=['POST'])
def cancelar(id):
    """7. Cancelar despacho"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT estado FROM Pedido_Despacho WHERE id_pedido_despacho = %s", (id,))
        despacho = cursor.fetchone()
        
        if despacho['estado'] == 'Despachado':
            flash('No se puede cancelar un despacho ya despachado', 'warning')
            return redirect(url_for('despachos.detalle', id=id))
        
        cursor.execute("""
            UPDATE Pedido_Despacho SET estado = 'Cancelado' WHERE id_pedido_despacho = %s
        """, (id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Despacho cancelado exitosamente', 'success')
        return redirect(url_for('despachos.index'))
    except Exception as e:
        flash(f'Error al cancelar despacho: {str(e)}', 'danger')
        return redirect(url_for('despachos.detalle', id=id))

@despachos_bp.route('/empresa/<int:id>')
def historial_empresa(id):
    """8. Historial de despachos por empresa"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM Proveedor WHERE id_proveedor = %s", (id,))
        proveedor = cursor.fetchone()
        
        cursor.execute("""
            SELECT pd.*, 
                COUNT(dd.id_detalle_despacho) as total_items,
                SUM(dd.cantidad_despachada) as total_despachado
            FROM Pedido_Despacho pd
            LEFT JOIN Detalle_Despacho dd ON pd.id_pedido_despacho = dd.id_pedido_despacho
            WHERE pd.id_proveedor = %s
            GROUP BY pd.id_pedido_despacho
            ORDER BY pd.fecha_solicitud DESC
        """, (id,))
        despachos = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('modulos/despachos.html', proveedor=proveedor, despachos=despachos, tab='historial')
    except Exception as e:
        flash(f'Error al cargar historial: {str(e)}', 'danger')
        return redirect(url_for('despachos.index'))

@despachos_bp.route('/productos/<int:id_proveedor>')
def productos_empresa(id_proveedor):
    """9. API: Obtener productos disponibles de una empresa - CON DEBUG"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # DEBUG: Verificar si el proveedor existe
        cursor.execute("SELECT * FROM Proveedor WHERE id_proveedor = %s", (id_proveedor,))
        proveedor = cursor.fetchone()
        print(f"[DEBUG] Proveedor encontrado: {proveedor}")
        
        # DEBUG: Ver cuántos productos tiene este proveedor en inventario
        cursor.execute("""
            SELECT COUNT(*) as total 
            FROM Inventario 
            WHERE id_proveedor = %s AND stock_producto > 0
        """, (id_proveedor,))
        total_inv = cursor.fetchone()
        print(f"[DEBUG] Total en inventario con stock > 0: {total_inv}")
        
        # CONSULTA PRINCIPAL
        cursor.execute("""
            SELECT 
                prov.id_proveedor,
                prov.nombre_proveedor,
                prov.empresa,
                a.nombre_almacen,
                e.pasillo,
                p.marca,
                cat.nombre_categoria,
                inv.stock_producto,
                inv.id_inventario,
                inv.fecha_modificacion,
                p.id_producto
            FROM Inventario inv
            INNER JOIN Proveedor prov ON inv.id_proveedor = prov.id_proveedor
            INNER JOIN Producto p ON inv.id_producto = p.id_producto
            INNER JOIN Categoria_Producto cat ON p.id_categoria_producto = cat.id_categoria_producto
            INNER JOIN Estante e ON inv.id_estante = e.id_estante
            INNER JOIN Almacen a ON e.id_almacen = a.id_almacen
            WHERE inv.id_proveedor = %s 
              AND inv.stock_producto > 0
            ORDER BY a.nombre_almacen, e.pasillo, p.marca
        """, (id_proveedor,))
        productos = cursor.fetchall()
        
        print(f"[DEBUG] Productos encontrados: {len(productos)}")
        print(f"[DEBUG] Datos: {productos}")
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True, 
            'productos': productos,
            'debug': {
                'id_proveedor': id_proveedor,
                'total_productos': len(productos),
                'proveedor': proveedor
            }
        })
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})