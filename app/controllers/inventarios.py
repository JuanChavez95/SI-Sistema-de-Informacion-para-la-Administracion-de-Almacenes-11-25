from flask import Blueprint, render_template, request, flash, redirect, url_for
import mysql.connector
from app.config import Config

inventarios_bp = Blueprint('inventarios', __name__, url_prefix='/inventarios')

def get_db_connection():
    return mysql.connector.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DB
    )

@inventarios_bp.route('/', methods=['GET'])
def index():
    """Visualizar inventario completo con filtros"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener filtros
        filtro_almacen = request.args.get('almacen', '')
        filtro_categoria = request.args.get('categoria', '')
        filtro_busqueda = request.args.get('busqueda', '')
        
        # Query base
        query = """
            SELECT inv.id_inventario, inv.stock_producto, inv.fecha_modificacion,
                p.id_producto, p.marca, p.costo_inicial,
                cat.nombre_categoria,
                e.id_estante, e.pasillo, e.capacidad as capacidad_estante,
                a.id_almacen, a.nombre_almacen, a.ubicacion
            FROM Inventario inv
            INNER JOIN Producto p ON inv.id_producto = p.id_producto
            INNER JOIN Categoria_Producto cat ON p.id_categoria_producto = cat.id_categoria_producto
            INNER JOIN Estante e ON inv.id_estante = e.id_estante
            INNER JOIN Almacen a ON e.id_almacen = a.id_almacen
            WHERE 1=1
        """
        params = []
        
        # Aplicar filtros
        if filtro_almacen:
            query += " AND a.id_almacen = %s"
            params.append(int(filtro_almacen))
        
        if filtro_categoria:
            query += " AND cat.id_categoria_producto = %s"
            params.append(int(filtro_categoria))
        
        if filtro_busqueda:
            query += " AND p.marca LIKE %s"
            params.append(f'%{filtro_busqueda}%')
        
        query += " ORDER BY a.nombre_almacen, e.pasillo, p.marca"
        
        cursor.execute(query, params)
        inventario = cursor.fetchall()
        
        # Obtener datos para filtros
        cursor.execute("SELECT * FROM Almacen ORDER BY nombre_almacen")
        almacenes = cursor.fetchall()
        
        cursor.execute("SELECT * FROM Categoria_Producto WHERE estado = 'ACTIVA' ORDER BY nombre_categoria")
        categorias = cursor.fetchall()
        
        # Calcular estadísticas
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT inv.id_producto) as total_productos,
                SUM(inv.stock_producto) as total_unidades,
                COUNT(DISTINCT a.id_almacen) as total_almacenes
            FROM Inventario inv
            INNER JOIN Estante e ON inv.id_estante = e.id_estante
            INNER JOIN Almacen a ON e.id_almacen = a.id_almacen
        """)
        estadisticas = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return render_template('modulos/inventarios.html',
                            inventario=inventario,
                            almacenes=almacenes,
                            categorias=categorias,
                            estadisticas=estadisticas,
                            filtro_almacen=filtro_almacen,
                            filtro_categoria=filtro_categoria,
                            filtro_busqueda=filtro_busqueda)
    except Exception as e:
        flash(f'Error al cargar inventario: {str(e)}', 'danger')
        return redirect(url_for('dashboard.index'))

@inventarios_bp.route('/producto/<int:id_producto>', methods=['GET'])
def detalle_producto(id_producto):
    """Ver detalle de ubicaciones de un producto"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener información del producto
        cursor.execute("""
            SELECT p.*, cat.nombre_categoria, cat.descripcion
            FROM Producto p
            INNER JOIN Categoria_Producto cat ON p.id_categoria_producto = cat.id_categoria_producto
            WHERE p.id_producto = %s
        """, (id_producto,))
        producto = cursor.fetchone()
        
        if not producto:
            flash('Producto no encontrado', 'danger')
            cursor.close()
            conn.close()
            return redirect(url_for('inventarios.index'))
        
        # Obtener todas las ubicaciones del producto
        cursor.execute("""
            SELECT inv.stock_producto, inv.fecha_modificacion,
                e.pasillo, e.capacidad as capacidad_estante,
                a.nombre_almacen, a.ubicacion
            FROM Inventario inv
            INNER JOIN Estante e ON inv.id_estante = e.id_estante
            INNER JOIN Almacen a ON e.id_almacen = a.id_almacen
            WHERE inv.id_producto = %s
            ORDER BY a.nombre_almacen, e.pasillo
        """, (id_producto,))
        ubicaciones = cursor.fetchall()
        
        # Total de stock del producto
        cursor.execute("""
            SELECT SUM(stock_producto) as stock_total
            FROM Inventario
            WHERE id_producto = %s
        """, (id_producto,))
        stock_info = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return render_template('modulos/inventarios.html',
                            tab='detalle',
                            producto=producto,
                            ubicaciones=ubicaciones,
                            stock_total=stock_info['stock_total'] or 0)
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('inventarios.index'))

@inventarios_bp.route('/almacen/<int:id_almacen>', methods=['GET'])
def por_almacen(id_almacen):
    """Ver inventario de un almacén específico"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener info del almacén
        cursor.execute("SELECT * FROM Almacen WHERE id_almacen = %s", (id_almacen,))
        almacen = cursor.fetchone()
        
        if not almacen:
            flash('Almacén no encontrado', 'danger')
            cursor.close()
            conn.close()
            return redirect(url_for('inventarios.index'))
        
        # Obtener inventario del almacén
        cursor.execute("""
            SELECT inv.stock_producto, p.marca, cat.nombre_categoria, e.pasillo
            FROM Inventario inv
            INNER JOIN Producto p ON inv.id_producto = p.id_producto
            INNER JOIN Categoria_Producto cat ON p.id_categoria_producto = cat.id_categoria_producto
            INNER JOIN Estante e ON inv.id_estante = e.id_estante
            WHERE e.id_almacen = %s
            ORDER BY e.pasillo, p.marca
        """, (id_almacen,))
        productos = cursor.fetchall()
        
        # Estadísticas del almacén
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT inv.id_producto) as total_productos,
                SUM(inv.stock_producto) as total_unidades,
                a.capacidad, a.capacidad_ocupada
            FROM Almacen a
            LEFT JOIN Estante e ON a.id_almacen = e.id_almacen
            LEFT JOIN Inventario inv ON e.id_estante = inv.id_estante
            WHERE a.id_almacen = %s
            GROUP BY a.id_almacen
        """, (id_almacen,))
        stats = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return render_template('modulos/inventarios.html',
                            tab='almacen',
                            almacen=almacen,
                            productos=productos,
                            stats=stats)
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('inventarios.index'))