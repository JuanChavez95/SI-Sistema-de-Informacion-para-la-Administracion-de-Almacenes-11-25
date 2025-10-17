from flask import Blueprint, render_template, session, redirect, url_for
from app.utils.decorators import login_required

bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@bp.route('/')
@login_required
def index():
    # Modelo 3PL: Gestionas productos de empresas (Proveedores) 
    # y los entregas a consumidores finales (Clientes)
    modulos = [
        {
            'nombre': 'Usuarios',
            'descripcion': 'Empleados y clientes',
            'url': url_for('usuarios.index'),
            'icono': '👥',
            'color': 'morado'
        },
        {
            'nombre': 'Empresas',
            'icono': '🏢',
            'descripcion': 'Gestión de empresas',
            'url': url_for('empresas.index'),
            'color': 'negro'
        },
        {
            'nombre': 'Almacenes',
            'descripcion': 'Gestión de espacios y estantes',
            'url': url_for('almacen.index'),
            'icono': '🏪',
            'color': 'morado'
        },
        {
            'nombre': 'Productos',
            'icono': '📦',
            'descripcion': 'Catálogo de productos almacenados',
            'url': '#',
            'color': 'negro'
        },
        {
            'nombre': 'Inventario',
            'icono': '📊',
            'descripcion': 'Control de stock por estante',
            'url': '#',
            'color': 'morado'
        },
        {
            'nombre': 'Recepciones',
            'icono': '📥',
            'descripcion': 'Entrada de mercancía',
            'url': url_for('recepciones.index'),
            'color': 'morado'
        },
        {
            'nombre': 'Despachos',
            'icono': '📤',
            'descripcion': 'Salida a clientes finales',
            'url': '#',  # Tabla: Pedido_Cliente
            'color': 'morado'
        },
        {
            'nombre': 'Movimientos',
            'icono': '🔄',
            'descripcion': 'Traslados y ajustes',
            'url': url_for('movimientos.index'),
            'color': 'morado'
        },
        {
            'nombre': 'Reportes',
            'icono': '📈',
            'descripcion': 'Análisis y estadísticas',
            'url': '#',
            'color': 'morado'
        },
        {
            'nombre': 'Configuración',
            'icono': '⚙️',
            'descripcion': 'Ajustes del sistema',
            'url': '#',
            'color': 'negro'
        }
    ]
    
    return render_template('dashboard.html', modulos=modulos)