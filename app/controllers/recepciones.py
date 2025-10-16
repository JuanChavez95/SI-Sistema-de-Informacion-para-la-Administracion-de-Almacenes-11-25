from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from datetime import datetime
import mysql.connector
from app.config import Config

recepciones_bp = Blueprint('recepciones', __name__, url_prefix='/recepciones')

def get_db_connection():
    return mysql.connector.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DB
    )

@recepciones_bp.route('/', methods=['GET'])
def index():
    """Listar todas las recepciones"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT p.*, pr.nombre_proveedor, pr.empresa,
                COUNT(di.id_detalle_ingreso) as total_productos,
                SUM(di.cantidad) as cantidad_total
            FROM Pedido p
            INNER JOIN Proveedor pr ON p.id_proveedor = pr.id_proveedor
            LEFT JOIN Detalle_Ingreso di ON p.id_pedido = di.id_pedido
            GROUP BY p.id_pedido
            ORDER BY p.fecha_pedido DESC
        """)
        recepciones = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('modulos/recepciones.html',
                            tab='lista',
                            recepciones=recepciones)
    except Exception as e:
        flash(f'Error al cargar recepciones: {str(e)}', 'danger')
        return redirect(url_for('dashboard.index'))

@recepciones_bp.route('/crear', methods=['GET', 'POST'])
def crear():
    """Crear nueva recepción"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        if request.method == 'GET':
            cursor.execute("SELECT * FROM Proveedor ORDER BY nombre_proveedor")
            empresas = cursor.fetchall()
            
            cursor.execute("""
                SELECT p.*, c.nombre_categoria 
                FROM Producto p
                INNER JOIN Categoria_Producto c ON p.id_categoria_producto = c.id_categoria_producto
                ORDER BY p.id_producto DESC
            """)
            productos = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return render_template('modulos/recepciones.html',
                                tab='crear',
                                empresas=empresas,
                                productos=productos)
        
        # POST - Crear recepción
        id_proveedor = request.form.get('id_proveedor')
        numero_documento = request.form.get('numero_documento', '').strip()
        fecha_pedido = request.form.get('fecha_pedido')
        fecha_entrega = request.form.get('fecha_entrega')
        estado = request.form.get('estado', 'Pendiente')
        
        # Obtener productos del formulario
        productos_ids = request.form.getlist('producto_id[]')
        cantidades = request.form.getlist('cantidad[]')
        precios = request.form.getlist('precio_unitario[]')
        
        if not id_proveedor or not fecha_pedido:
            flash('Empresa y fecha de pedido son obligatorios', 'warning')
            cursor.close()
            conn.close()
            return redirect(url_for('recepciones.crear'))
        
        if not productos_ids or len(productos_ids) == 0:
            flash('Debe agregar al menos un producto', 'warning')
            cursor.close()
            conn.close()
            return redirect(url_for('recepciones.crear'))
        
        # Calcular precio total
        precio_total = sum(float(precios[i]) * int(cantidades[i]) for i in range(len(productos_ids)))
        
        # Crear pedido
        query_pedido = """
            INSERT INTO Pedido (numero_documento, precio_total, fecha_pedido, fecha_entrega, estado, id_proveedor)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query_pedido, (
            int(numero_documento) if numero_documento else None,
            precio_total,
            fecha_pedido,
            fecha_entrega if fecha_entrega else None,
            estado,
            int(id_proveedor)
        ))
        conn.commit()
        
        id_pedido = cursor.lastrowid
        
        # Insertar detalles de ingreso
        for i in range(len(productos_ids)):
            cursor.execute("""
                INSERT INTO Detalle_Ingreso (precio_unitario, cantidad, id_producto, id_pedido)
                VALUES (%s, %s, %s, %s)
            """, (float(precios[i]), int(cantidades[i]), int(productos_ids[i]), id_pedido))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Recepción creada exitosamente', 'success')
        return redirect(url_for('recepciones.ver_detalle', id_pedido=id_pedido))
    except Exception as e:
        flash(f'Error al crear recepción: {str(e)}', 'danger')
        return redirect(url_for('recepciones.crear'))

@recepciones_bp.route('/<int:id_pedido>', methods=['GET'])
def ver_detalle(id_pedido):
    """Ver detalle de recepción"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener pedido
        cursor.execute("""
            SELECT p.*, pr.nombre_proveedor, pr.empresa, pr.nit
            FROM Pedido p
            INNER JOIN Proveedor pr ON p.id_proveedor = pr.id_proveedor
            WHERE p.id_pedido = %s
        """, (id_pedido,))
        pedido = cursor.fetchone()
        
        if not pedido:
            flash('Recepción no encontrada', 'danger')
            cursor.close()
            conn.close()
            return redirect(url_for('recepciones.index'))
        
        # Obtener detalles
        cursor.execute("""
            SELECT di.*, prod.marca, cat.nombre_categoria
            FROM Detalle_Ingreso di
            INNER JOIN Producto prod ON di.id_producto = prod.id_producto
            INNER JOIN Categoria_Producto cat ON prod.id_categoria_producto = cat.id_categoria_producto
            WHERE di.id_pedido = %s
        """, (id_pedido,))
        detalles = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('modulos/recepciones.html',
                            tab='detalle',
                            pedido=pedido,
                            detalles=detalles)
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('recepciones.index'))

@recepciones_bp.route('/<int:id_pedido>/editar', methods=['GET', 'POST'])
def editar(id_pedido):
    """Editar recepción"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        if request.method == 'GET':
            cursor.execute("SELECT * FROM Pedido WHERE id_pedido = %s", (id_pedido,))
            pedido = cursor.fetchone()
            
            if not pedido:
                flash('Recepción no encontrada', 'danger')
                cursor.close()
                conn.close()
                return redirect(url_for('recepciones.index'))
            
            cursor.close()
            conn.close()
            
            return render_template('modulos/recepciones.html',
                                tab='editar',
                                pedido=pedido)
        
        # POST - Actualizar
        numero_documento = request.form.get('numero_documento', '').strip()
        fecha_pedido = request.form.get('fecha_pedido')
        fecha_entrega = request.form.get('fecha_entrega')
        estado = request.form.get('estado')
        
        query = """
            UPDATE Pedido
            SET numero_documento = %s, fecha_pedido = %s, fecha_entrega = %s, estado = %s
            WHERE id_pedido = %s
        """
        cursor.execute(query, (
            int(numero_documento) if numero_documento else None,
            fecha_pedido,
            fecha_entrega if fecha_entrega else None,
            estado,
            id_pedido
        ))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        flash('Recepción actualizada exitosamente', 'success')
        return redirect(url_for('recepciones.ver_detalle', id_pedido=id_pedido))
    except Exception as e:
        flash(f'Error al editar recepción: {str(e)}', 'danger')
        return redirect(url_for('recepciones.index'))

@recepciones_bp.route('/<int:id_pedido>/eliminar', methods=['POST'])
def eliminar(id_pedido):
    """Eliminar recepción"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Eliminar detalles primero
        cursor.execute("DELETE FROM Detalle_Ingreso WHERE id_pedido = %s", (id_pedido,))
        
        # Eliminar pedido
        cursor.execute("DELETE FROM Pedido WHERE id_pedido = %s", (id_pedido,))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        flash('Recepción eliminada exitosamente', 'success')
        return redirect(url_for('recepciones.index'))
    except Exception as e:
        flash(f'Error al eliminar recepción: {str(e)}', 'danger')
        return redirect(url_for('recepciones.index'))

# ===== GESTIÓN DE PRODUCTOS =====

@recepciones_bp.route('/productos', methods=['GET'])
def listar_productos():
    """Listar productos disponibles"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT p.*, c.nombre_categoria
            FROM Producto p
            INNER JOIN Categoria_Producto c ON p.id_categoria_producto = c.id_categoria_producto
            ORDER BY p.id_producto DESC
        """)
        productos = cursor.fetchall()
        
        cursor.execute("SELECT * FROM Categoria_Producto WHERE estado = 'ACTIVA' ORDER BY nombre_categoria")
        categorias = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('modulos/recepciones.html',
                            tab='productos',
                            productos=productos,
                            categorias=categorias)
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('recepciones.index'))

@recepciones_bp.route('/productos/crear', methods=['POST'])
def crear_producto():
    """Crear nuevo producto"""
    try:
        marca = request.form.get('marca', '').strip()
        fecha_fabricacion = request.form.get('fecha_fabricacion')
        costo_inicial = request.form.get('costo_inicial', 0)
        id_categoria = request.form.get('id_categoria_producto')
        
        if not marca or not id_categoria:
            flash('Marca y categoría son obligatorios', 'warning')
            return redirect(url_for('recepciones.listar_productos'))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO Producto (marca, fecha_fabricacion, costo_inicial, id_categoria_producto)
            VALUES (%s, %s, %s, %s)
        """, (marca, fecha_fabricacion if fecha_fabricacion else None, 
            float(costo_inicial) if costo_inicial else 0, int(id_categoria)))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        flash('Producto creado exitosamente', 'success')
        return redirect(url_for('recepciones.listar_productos'))
    except Exception as e:
        flash(f'Error al crear producto: {str(e)}', 'danger')
        return redirect(url_for('recepciones.listar_productos'))