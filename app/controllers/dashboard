from flask import Blueprint, render_template, session, redirect, url_for
from app.utils.decorators import login_required # Se mantiene la ruta original del decorador

bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

# Diccionario central que define todos los módulos disponibles en el sistema.
# Las claves del diccionario corresponden a nombres de rutas de ejemplo (e.g., 'usuarios.index').
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
# IMPORTANTE: Las claves aquí deben coincidir exactamente con los nombres de rol almacenados en la sesión.
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
        # 'Despachos' se usa aquí para el seguimiento de 'Pedidos_Cliente'
        'modulos_keys': ['Productos', 'Despachos'],
        'template': 'dashboard_cliente.html'
    }
}

@bp.route('/')
@login_required
def index():
    user_role = session.get('user_role')
    
    # 1. Validación de Rol
    if not user_role or user_role not in ROLE_DASHBOARDS:
        # Fallback de seguridad si el rol no existe o no está definido
        print(f"ERROR: Rol no reconocido: {user_role}. Redirigiendo a /login.")
        return redirect(url_for('auth.logout')) 

    dashboard_info = ROLE_DASHBOARDS[user_role]
    
    # 2. Construcción de Módulos (Filtrado)
    modulos = []
    for key in dashboard_info['modulos_keys']:
        modulo = ALL_MODULES[key]
        
        # Generar la URL real usando url_for() o usar '#' como fallback
        try:
            modulo['url_final'] = url_for(modulo['url'])
        except Exception:
            # En caso de que la ruta de Flask no esté definida aún
            modulo['url_final'] = '#'
            
        modulos.append(modulo)
            
    # 3. Renderizar la plantilla específica para el rol
    return render_template(dashboard_info['template'], modulos=modulos, user_role=user_role)