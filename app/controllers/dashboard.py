from flask import Blueprint, render_template, session, redirect, url_for
from app.utils.decorators import login_required
import mysql.connector
from app.config import Config
from datetime import datetime, timedelta

bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

def get_db_connection():
    """Obtener conexión a la base de datos"""
    return mysql.connector.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DB
    )

# Diccionario central que define todos los módulos disponibles en el sistema.
ALL_MODULES = {
    'Usuarios': {'nombre': 'Usuarios', 'descripcion': 'Gestión de empleados y clientes', 'url': 'usuarios.index', 'icono': '👥', 'color': 'morado'},
    'Empresas': {'nombre': 'Empresas', 'descripcion': 'Gestión de proveedores y clientes', 'url': 'empresas.index', 'icono': '🏢', 'color': 'negro'},
    'Almacenes': {'nombre': 'Almacenes', 'descripcion': 'Gestión de espacios y estantes', 'url': 'almacen.index', 'icono': '🏪', 'color': 'morado'},
    'Productos': {'nombre': 'Productos', 'descripcion': 'Catálogo de productos almacenados', 'url': 'productos.index', 'icono': '📦', 'color': 'negro'},
    'Inventario': {'nombre': 'Inventario', 'descripcion': 'Control de stock por ubicación', 'url': 'inventarios.index', 'icono': '📊', 'color': 'morado'},
    'Recepciones': {'nombre': 'Recepciones', 'descripcion': 'Entrada de mercancía (Pedidos Proveedor)', 'url': 'recepciones.index', 'icono': '📥', 'color': 'morado'},
    'Despachos': {'nombre': 'Despachos', 'descripcion': 'Salida a clientes finales (Pedidos Cliente)', 'url': 'despachos.index', 'icono': '📤', 'color': 'morado'},
    'Movimientos': {'nombre': 'Movimientos', 'descripcion': 'Traslados y ajustes de inventario', 'url': 'movimientos.index', 'icono': '🔄', 'color': 'morado'},
    'Reportes': {'nombre': 'Reportes', 'descripcion': 'Análisis, estadísticas e informes', 'url': 'reportes.index', 'icono': '📈', 'color': 'morado'},
    'Configuracion': {'nombre': 'Configuración', 'descripcion': 'Ajustes del sistema y permisos', 'url': 'configuracion.index', 'icono': '⚙️', 'color': 'negro'}
}

# Mapeo de roles a los módulos que deben ver y la plantilla a usar.
ROLE_DASHBOARDS = {
    'Administrador': {
        'modulos_keys': ['Usuarios', 'Empresas', 'Almacenes', 'Productos', 'Inventario', 'Recepciones', 'Despachos', 'Movimientos', 'Reportes', 'Configuracion'],
        'template': 'dashboard_administrador.html'
    },
    'Contador': {
        'modulos_keys': ['Reportes', 'Movimientos', 'Inventario', 'Despachos'],
        'template': 'dashboard_contador.html'
    },
    'Gerente': {
        'modulos_keys': ['Empresas', 'Almacenes', 'Productos', 'Inventario', 'Recepciones', 'Despachos', 'Movimientos', 'Reportes'],
        'template': 'dashboard_gerente.html'
    },
    'Auxiliar': {
        'modulos_keys': ['Recepciones', 'Despachos', 'Inventario', 'Movimientos'],
        'template': 'dashboard_auxiliar.html'
    },
    'Personal de Logistica': {
        'modulos_keys': ['Almacenes', 'Movimientos', 'Recepciones', 'Despachos'],
        'template': 'dashboard_personal_de_logistica.html'
    },
    'Cliente': {
        'modulos_keys': ['Productos', 'Despachos'],
        'template': 'dashboard_cliente.html'
    }
}

def get_dashboard_stats():
    """Obtiene las estadísticas principales del dashboard"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    stats = {}
    
    try:
        # 1. Productos Únicos
        cursor.execute("SELECT COUNT(DISTINCT id_producto) as total FROM Producto")
        stats['productos_unicos'] = cursor.fetchone()['total'] or 0
        
        # 2. Almacenes Activos
        cursor.execute("SELECT COUNT(*) as total FROM Almacen")
        stats['almacenes_activos'] = cursor.fetchone()['total'] or 0
        
        # 3. Recepciones Pendientes
        cursor.execute("SELECT COUNT(*) as total FROM Pedido WHERE estado = 'Pendiente'")
        stats['recepciones_pendientes'] = cursor.fetchone()['total'] or 0
        
        # 4. Clientes Registrados
        cursor.execute("SELECT COUNT(*) as total FROM Cliente")
        stats['clientes_registrados'] = cursor.fetchone()['total'] or 0
        
        # 5. Movimientos del Día
        cursor.execute("""
            SELECT COUNT(*) as total 
            FROM Movimiento_Producto 
            WHERE fecha_movimiento = CURDATE()
        """)
        stats['movimientos_hoy'] = cursor.fetchone()['total'] or 0
        
    except Exception as e:
        print(f"Error obteniendo estadísticas: {e}")
        stats = {
            'productos_unicos': 0,
            'almacenes_activos': 0,
            'recepciones_pendientes': 0,
            'clientes_registrados': 0,
            'movimientos_hoy': 0
        }
    finally:
        cursor.close()
        conn.close()
    
    return stats

def get_distribucion_almacenes():
    """Obtiene la distribución de productos por almacén"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT a.nombre_almacen, COALESCE(SUM(i.stock_producto), 0) as total_productos
            FROM Almacen a
            LEFT JOIN Estante e ON a.id_almacen = e.id_almacen
            LEFT JOIN Inventario i ON e.id_estante = i.id_estante
            GROUP BY a.id_almacen, a.nombre_almacen
            ORDER BY total_productos DESC
        """)
        resultados = cursor.fetchall()
        
        return {
            'labels': [r['nombre_almacen'] for r in resultados],
            'data': [int(r['total_productos'] or 0) for r in resultados]
        }
    except Exception as e:
        print(f"Error obteniendo distribución de almacenes: {e}")
        return {'labels': [], 'data': []}
    finally:
        cursor.close()
        conn.close()

def get_ocupacion_almacenes():
    """Obtiene la ocupación de cada almacén"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT 
                nombre_almacen,
                capacidad,
                capacidad_ocupada,
                ROUND((capacidad_ocupada/capacidad)*100, 2) as porcentaje_ocupacion
            FROM Almacen
            WHERE capacidad > 0
            ORDER BY porcentaje_ocupacion DESC
        """)
        resultados = cursor.fetchall()
        
        return {
            'labels': [r['nombre_almacen'] for r in resultados],
            'capacidad': [r['capacidad'] for r in resultados],
            'ocupada': [r['capacidad_ocupada'] for r in resultados],
            'porcentajes': [float(r['porcentaje_ocupacion'] or 0) for r in resultados]
        }
    except Exception as e:
        print(f"Error obteniendo ocupación de almacenes: {e}")
        return {'labels': [], 'capacidad': [], 'ocupada': [], 'porcentajes': []}
    finally:
        cursor.close()
        conn.close()

def get_recepciones_despachos():
    """Obtiene recepciones y despachos de los últimos 30 días"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Recepciones
        cursor.execute("""
            SELECT DATE(fecha_pedido) as fecha, COUNT(*) as cantidad
            FROM Pedido
            WHERE fecha_pedido >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            GROUP BY DATE(fecha_pedido)
            ORDER BY fecha
        """)
        recepciones = cursor.fetchall()
        
        # Despachos
        cursor.execute("""
            SELECT DATE(fecha_despacho) as fecha, COUNT(*) as cantidad
            FROM Pedido_Despacho
            WHERE fecha_despacho >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            AND fecha_despacho IS NOT NULL
            GROUP BY DATE(fecha_despacho)
            ORDER BY fecha
        """)
        despachos = cursor.fetchall()
        
        # Crear conjunto de fechas únicas
        fechas_set = set()
        for r in recepciones:
            if r['fecha']:
                fechas_set.add(r['fecha'])
        for d in despachos:
            if d['fecha']:
                fechas_set.add(d['fecha'])
        
        fechas = sorted(list(fechas_set))
        
        # Crear diccionarios para búsqueda rápida
        rec_dict = {r['fecha']: r['cantidad'] for r in recepciones if r['fecha']}
        desp_dict = {d['fecha']: d['cantidad'] for d in despachos if d['fecha']}
        
        return {
            'labels': [f.strftime('%d/%m') for f in fechas],
            'recepciones': [rec_dict.get(f, 0) for f in fechas],
            'despachos': [desp_dict.get(f, 0) for f in fechas]
        }
    except Exception as e:
        print(f"Error obteniendo recepciones y despachos: {e}")
        return {'labels': [], 'recepciones': [], 'despachos': []}
    finally:
        cursor.close()
        conn.close()

def get_productos_por_categoria():
    """Obtiene la cantidad de productos por categoría"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT cp.nombre_categoria, COUNT(p.id_producto) as cantidad
            FROM Categoria_Producto cp
            LEFT JOIN Producto p ON cp.id_categoria_producto = p.id_categoria_producto
            WHERE cp.estado = 'ACTIVA'
            GROUP BY cp.id_categoria_producto, cp.nombre_categoria
            HAVING cantidad > 0
            ORDER BY cantidad DESC
        """)
        resultados = cursor.fetchall()
        
        return {
            'labels': [r['nombre_categoria'] for r in resultados],
            'data': [r['cantidad'] for r in resultados]
        }
    except Exception as e:
        print(f"Error obteniendo productos por categoría: {e}")
        return {'labels': [], 'data': []}
    finally:
        cursor.close()
        conn.close()

def get_alertas():
    """Obtiene las alertas del sistema"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    alertas = []
    
    try:
        # Almacenes con capacidad > 90%
        cursor.execute("""
            SELECT nombre_almacen, 
                   ROUND((capacidad_ocupada/capacidad)*100, 2) as porcentaje
            FROM Almacen
            WHERE capacidad > 0 AND (capacidad_ocupada/capacidad)*100 > 90
            ORDER BY porcentaje DESC
        """)
        almacenes_criticos = cursor.fetchall()
        for a in almacenes_criticos:
            alertas.append({
                'tipo': 'warning',
                'icono': '⚠️',
                'mensaje': f"Almacén '{a['nombre_almacen']}' al {a['porcentaje']}% de capacidad"
            })
        
        # Productos con stock bajo (< 10 unidades)
        cursor.execute("""
            SELECT p.marca, SUM(i.stock_producto) as stock_total
            FROM Producto p
            JOIN Inventario i ON p.id_producto = i.id_producto
            GROUP BY p.id_producto, p.marca
            HAVING stock_total < 10 AND stock_total > 0
            ORDER BY stock_total
            LIMIT 5
        """)
        productos_bajo_stock = cursor.fetchall()
        for prod in productos_bajo_stock:
            alertas.append({
                'tipo': 'danger',
                'icono': '🔴',
                'mensaje': f"Stock bajo: {prod['marca']} ({prod['stock_total']} unidades)"
            })
        
        # Despachos con retraso
        cursor.execute("""
            SELECT numero_guia, DATEDIFF(CURDATE(), fecha_solicitud) as dias_retraso
            FROM Pedido_Despacho
            WHERE estado IN ('Pendiente', 'En Preparación')
            AND DATEDIFF(CURDATE(), fecha_solicitud) > 5
            ORDER BY dias_retraso DESC
            LIMIT 5
        """)
        despachos_retrasados = cursor.fetchall()
        for desp in despachos_retrasados:
            alertas.append({
                'tipo': 'danger',
                'icono': '⏰',
                'mensaje': f"Despacho {desp['numero_guia']} retrasado {desp['dias_retraso']} días"
            })
        
        # Pedidos pendientes por más de 7 días
        cursor.execute("""
            SELECT numero_documento, DATEDIFF(CURDATE(), fecha_pedido) as dias_pendiente
            FROM Pedido
            WHERE estado = 'Pendiente'
            AND DATEDIFF(CURDATE(), fecha_pedido) > 7
            ORDER BY dias_pendiente DESC
            LIMIT 5
        """)
        pedidos_pendientes = cursor.fetchall()
        for ped in pedidos_pendientes:
            alertas.append({
                'tipo': 'warning',
                'icono': '📋',
                'mensaje': f"Pedido #{ped['numero_documento']} pendiente {ped['dias_pendiente']} días"
            })
            
    except Exception as e:
        print(f"Error obteniendo alertas: {e}")
    finally:
        cursor.close()
        conn.close()
    
    return alertas

@bp.route('/')
@login_required
def index():
    user_role = session.get('user_role')
    
    # Validación de Rol
    if not user_role or user_role not in ROLE_DASHBOARDS:
        print(f"ERROR: Rol no reconocido: {user_role}. Redirigiendo a /login.")
        return redirect(url_for('auth.logout')) 

    dashboard_info = ROLE_DASHBOARDS[user_role]
    
    # Construcción de Módulos (Filtrado)
    modulos = []
    for key in dashboard_info['modulos_keys']:
        modulo = ALL_MODULES[key].copy()
        
        try:
            modulo['url_final'] = url_for(modulo['url'])
        except Exception:
            modulo['url_final'] = '#'
            
        modulos.append(modulo)
    
    # Obtener datos del dashboard
    stats = get_dashboard_stats()
    distribucion_almacenes = get_distribucion_almacenes()
    ocupacion_almacenes = get_ocupacion_almacenes()
    recepciones_despachos = get_recepciones_despachos()
    productos_categoria = get_productos_por_categoria()
    alertas = get_alertas()
    
    # Renderizar la plantilla específica para el rol
    return render_template(
        dashboard_info['template'], 
        modulos=modulos, 
        user_role=user_role,
        stats=stats,
        distribucion_almacenes=distribucion_almacenes,
        ocupacion_almacenes=ocupacion_almacenes,
        recepciones_despachos=recepciones_despachos,
        productos_categoria=productos_categoria,
        alertas=alertas
    )