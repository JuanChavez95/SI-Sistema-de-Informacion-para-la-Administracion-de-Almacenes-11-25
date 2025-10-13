from flask import Blueprint, render_template, session, redirect, url_for
from app.utils.decorators import login_required
from functools import wraps

bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')
bp = Blueprint('dashboard', __name__)

@bp.route('/dashboard')
@login_required
def index():
    modulos = [
        {
            'nombre': 'Usuarios',
            'icono': '👥',
            'descripcion': 'Gestión de usuarios y roles',
            'url': '#',
            'color': 'morado'
        },
        {
            'nombre': 'Productos',
            'icono': '📦',
            'descripcion': 'Catálogo de productos',
            'url': '#',
            'color': 'negro'
        },
        {
            'nombre': 'Inventario',
            'icono': '📊',
            'descripcion': 'Control de stock',
            'url': '#',
            'color': 'morado'
        },
        {
            'nombre': 'Almacenes',
            'descripcion': 'Gestión de almacenes y estantes',
            'url': url_for('almacen.index'),
            'icono': '🏪',
            'color': 'negro'
        },
        {
            'nombre': 'Pedidos',
            'icono': '🛒',
            'descripcion': 'Pedidos de clientes',
            'url': '#',
            'color': 'morado'
        },
        {
            'nombre': 'Proveedores',
            'icono': '🚚',
            'descripcion': 'Gestión de proveedores',
            'url': '#',
            'color': 'negro'
        },
        {
            'nombre': 'Reportes',
            'icono': '📈',
            'descripcion': 'Informes y estadísticas',
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