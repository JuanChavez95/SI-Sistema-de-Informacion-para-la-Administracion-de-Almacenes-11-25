from flask import Blueprint, render_template, request, flash, redirect, url_for
from datetime import datetime
import mysql.connector
from app.config import Config

empresas_bp = Blueprint('empresas', __name__, url_prefix='/empresas')

def get_db_connection():
    return mysql.connector.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DB
    )

@empresas_bp.route('/', methods=['GET'])
def index():
    """Listar todas las empresas"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM Proveedor ORDER BY id_proveedor DESC")
        empresas = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('modulos/empresas.html',
                            tab='lista',
                            empresas=empresas)
    except Exception as e:
        flash(f'Error al cargar empresas: {str(e)}', 'danger')
        return redirect(url_for('dashboard.index'))

@empresas_bp.route('/crear', methods=['GET', 'POST'])
def crear():
    """Crear nueva empresa"""
    if request.method == 'GET':
        return render_template('modulos/empresas.html', tab='crear')
    
    try:
        nit = request.form.get('nit', '').strip()
        nombre = request.form.get('nombre_proveedor', '').strip()
        empresa = request.form.get('empresa', '').strip()
        telefono = request.form.get('telefono', '').strip()
        direccion = request.form.get('direccion', '').strip()
        
        if not all([nit, nombre]):
            flash('NIT y nombre son obligatorios', 'warning')
            return redirect(url_for('empresas.crear'))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar NIT único
        cursor.execute("SELECT id_proveedor FROM Proveedor WHERE nit = %s", (int(nit),))
        if cursor.fetchone():
            flash('El NIT ya está registrado', 'warning')
            cursor.close()
            conn.close()
            return redirect(url_for('empresas.crear'))
        
        query = """
            INSERT INTO Proveedor (nit, nombre_proveedor, empresa, telefono, direccion)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query, (int(nit), nombre, empresa, int(telefono) if telefono else None, direccion))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        flash('Empresa creada exitosamente', 'success')
        return redirect(url_for('empresas.index'))
    except Exception as e:
        flash(f'Error al crear empresa: {str(e)}', 'danger')
        return redirect(url_for('empresas.crear'))

@empresas_bp.route('/<int:id_proveedor>', methods=['GET'])
def ver_detalle(id_proveedor):
    """Ver detalles y historial de pedidos de la empresa"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener empresa
        cursor.execute("SELECT * FROM Proveedor WHERE id_proveedor = %s", (id_proveedor,))
        empresa = cursor.fetchone()
        
        if not empresa:
            flash('Empresa no encontrada', 'danger')
            cursor.close()
            conn.close()
            return redirect(url_for('empresas.index'))
        
        # Obtener historial de pedidos con resumen
        cursor.execute("""
            SELECT 
                p.id_pedido,
                p.numero_documento,
                p.fecha_pedido,
                p.fecha_entrega,
                p.precio_total,
                p.estado,
                COUNT(di.id_detalle_ingreso) as total_productos,
                SUM(di.cantidad) as cantidad_total
            FROM Pedido p
            LEFT JOIN Detalle_Ingreso di ON p.id_pedido = di.id_pedido
            WHERE p.id_proveedor = %s
            GROUP BY p.id_pedido
            ORDER BY p.fecha_pedido DESC
        """, (id_proveedor,))
        pedidos = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('modulos/empresas.html',
                            tab='detalle',
                            empresa=empresa,
                            pedidos=pedidos)
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('empresas.index'))

@empresas_bp.route('/<int:id_proveedor>/editar', methods=['GET', 'POST'])
def editar(id_proveedor):
    """Editar empresa"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        if request.method == 'GET':
            cursor.execute("SELECT * FROM Proveedor WHERE id_proveedor = %s", (id_proveedor,))
            empresa = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            if not empresa:
                flash('Empresa no encontrada', 'danger')
                return redirect(url_for('empresas.index'))
            
            return render_template('modulos/empresas.html',
                                tab='editar',
                                empresa=empresa)
        
        # POST
        nombre = request.form.get('nombre_proveedor', '').strip()
        empresa_name = request.form.get('empresa', '').strip()
        telefono = request.form.get('telefono', '').strip()
        direccion = request.form.get('direccion', '').strip()
        
        if not nombre:
            flash('El nombre es obligatorio', 'warning')
            cursor.close()
            conn.close()
            return redirect(url_for('empresas.editar', id_proveedor=id_proveedor))
        
        query = """
            UPDATE Proveedor
            SET nombre_proveedor = %s, empresa = %s, telefono = %s, direccion = %s
            WHERE id_proveedor = %s
        """
        cursor.execute(query, (nombre, empresa_name, int(telefono) if telefono else None, 
                            direccion, id_proveedor))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        flash('Empresa actualizada exitosamente', 'success')
        return redirect(url_for('empresas.ver_detalle', id_proveedor=id_proveedor))
    except Exception as e:
        flash(f'Error al editar empresa: {str(e)}', 'danger')
        return redirect(url_for('empresas.index'))

@empresas_bp.route('/<int:id_proveedor>/eliminar', methods=['POST'])
def eliminar(id_proveedor):
    """Eliminar empresa"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar si tiene pedidos
        cursor.execute("SELECT COUNT(*) as count FROM Pedido WHERE id_proveedor = %s", (id_proveedor,))
        result = cursor.fetchone()
        
        if result[0] > 0:
            flash('No se puede eliminar una empresa con pedidos registrados', 'warning')
            cursor.close()
            conn.close()
            return redirect(url_for('empresas.ver_detalle', id_proveedor=id_proveedor))
        
        cursor.execute("DELETE FROM Proveedor WHERE id_proveedor = %s", (id_proveedor,))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        flash('Empresa eliminada exitosamente', 'success')
        return redirect(url_for('empresas.index'))
    except Exception as e:
        flash(f'Error al eliminar empresa: {str(e)}', 'danger')
        return redirect(url_for('empresas.index'))

@empresas_bp.route('/buscar', methods=['GET'])
def buscar():
    """Buscar empresas"""
    try:
        query = request.args.get('q', '').strip()
        
        if not query:
            return redirect(url_for('empresas.index'))
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT * FROM Proveedor 
            WHERE nombre_proveedor LIKE %s 
            OR empresa LIKE %s 
            OR nit LIKE %s
            ORDER BY id_proveedor DESC
        """, (f'%{query}%', f'%{query}%', f'%{query}%'))
        empresas = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('modulos/empresas.html',
                            tab='lista',
                            empresas=empresas,
                            query=query)
    except Exception as e:
        flash(f'Error en la búsqueda: {str(e)}', 'danger')
        return redirect(url_for('empresas.index'))