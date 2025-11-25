# app/controllers/reportes.py
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, send_file
from app.utils.decorators import login_required
from app.config import Config
import mysql.connector
import pandas as pd
import io
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages
import base64
from datetime import datetime

# Blueprint
reportes_bp = Blueprint('reportes', __name__, url_prefix='/reportes')

def get_db_connection():
    return mysql.connector.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DB
    )

# === CONTROL DE ACCESO ===
def tiene_acceso_reportes():
    rol = session.get('user_role')
    return rol in ['Administrador', 'Contador', 'Gerente']

# === RUTA PRINCIPAL ===
@reportes_bp.route('/', methods=['GET'])
@login_required
def index():
    if not tiene_acceso_reportes():
        flash('No tienes permisos para acceder a reportes.', 'danger')
        return redirect(url_for('dashboard.index'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id_proveedor, nombre_proveedor FROM Proveedor ORDER BY nombre_proveedor")
        proveedores = cursor.fetchall()

        cursor.execute("SELECT id_categoria_producto, nombre_categoria FROM Categoria_Producto WHERE estado = 'ACTIVA'")
        categorias = cursor.fetchall()

        cursor.execute("SELECT id_almacen, nombre_almacen FROM Almacen ORDER BY nombre_almacen")
        almacenes = cursor.fetchall()

        cursor.execute("""
            SELECT p.id_persona, CONCAT(p.nombre, ' ', p.apellido_paterno) AS nombre_completo
            FROM Persona p
            JOIN Persona_Rol pr ON p.id_persona = pr.id_persona
            JOIN Rol r ON pr.id_rol = r.id_rol
            WHERE r.nombre_rol IN ('Administrador', 'Gerente', 'Auxiliar', 'Personal de Logistica')
            ORDER BY nombre_completo
        """)
        responsables = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template('modulos/reportes.html',
                               proveedores=proveedores,
                               categorias=categorias,
                               almacenes=almacenes,
                               responsables=responsables)

    except Exception as e:
        flash(f'Error al cargar reportes: {str(e)}', 'danger')
        return redirect(url_for('dashboard.index'))

# === GENERAR REPORTE ===
@reportes_bp.route('/generar', methods=['POST'])
@login_required
def generar():
    if not tiene_acceso_reportes():
        return {'error': 'Acceso denegado'}, 403

    data = request.get_json()
    tipo = data.get('tipo_reporte')
    fi = data.get('fecha_inicio')
    ff = data.get('fecha_fin')
    prov = data.get('proveedor_id')
    cat = data.get('categoria_id')
    alm = data.get('almacen_id')
    est = data.get('estado_despacho')
    resp = data.get('responsable_id')
    grafico = data.get('grafico_tipo', 'barras')

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Aquí se llama correctamente con todos los parámetros
        query, columns, params = construir_query_segura(tipo, fi, ff, prov, cat, alm, est, resp)

        cursor.execute(query, params)
        results = cursor.fetchall()
        cursor.close()
        conn.close()

        df = pd.DataFrame(results) if results else pd.DataFrame(columns=columns)
        chart_url = generar_grafico(df, tipo, grafico) if not df.empty else None

        return {
            'data': df.to_dict(orient='records'),
            'columns': columns,
            'chart_url': chart_url
        }

    except Exception as e:
        return {'error': str(e)}, 500

# === EXPORTAR EXCEL ===
@reportes_bp.route('/exportar/excel', methods=['POST'])
@login_required
def exportar_excel():
    if not tiene_acceso_reportes():
        return {'error': 'Acceso denegado'}, 403

    data = request.get_json()
    df = pd.DataFrame(data['data'])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Reporte')
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name=f"reporte_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

# === EXPORTAR PDF ===
@reportes_bp.route('/exportar/pdf', methods=['POST'])
@login_required
def exportar_pdf():
    if not tiene_acceso_reportes():
        return {'error': 'Acceso denegado'}, 403

    data = request.get_json()
    df = pd.DataFrame(data['data'])
    chart_b64 = data.get('chart_url', '').split(',')[1] if data.get('chart_url') else None

    output = io.BytesIO()
    with PdfPages(output) as pdf:
        fig, ax = plt.subplots(figsize=(11, 6))
        ax.axis('off')
        table = ax.table(cellText=df.values, colLabels=df.columns, loc='center', cellLoc='center')
        table.auto_set_font_size(False)
        table.set_fontsize(8)
        table.scale(1.2, 1.5)
        plt.title(f"Reporte - {datetime.now().strftime('%d/%m/%Y %H:%M')}", fontsize=16, pad=20)
        pdf.savefig(fig, bbox_inches='tight')
        plt.close()

        if chart_b64:
            chart_img = base64.b64decode(chart_b64)
            fig2, ax2 = plt.subplots()
            ax2.imshow(plt.imread(io.BytesIO(chart_img)))
            ax2.axis('off')
            pdf.savefig(fig2, bbox_inches='tight')
            plt.close(fig2)

    output.seek(0)
    return send_file(
        output,
        as_attachment=True,
        download_name=f"reporte_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
        mimetype='application/pdf'
    )

# === CONSTRUIR QUERY SEGURA ===
def construir_query_segura(tipo, fi, ff, prov, cat, alm, est, resp):
    condiciones = []
    params = []

    if fi and ff:
        if tipo == 'ingreso':
            condiciones.append("ped.fecha_pedido BETWEEN %s AND %s")
            params.extend([fi, ff])
        elif tipo == 'inventario':
            condiciones.append("inv.fecha_modificacion BETWEEN %s AND %s")
            params.extend([fi, ff])
        elif tipo == 'despacho':
            condiciones.append("pd.fecha_solicitud BETWEEN %s AND %s")
            params.extend([fi, ff])

    if prov and prov != '':
        if tipo in ['ingreso', 'despacho']:
            condiciones.append("prov.id_proveedor = %s")
            params.append(prov)
        elif tipo == 'inventario':
            condiciones.append("inv.id_proveedor = %s")
            params.append(prov)

    if cat and cat != '':
        condiciones.append("p.id_categoria_producto = %s")
        params.append(cat)

    if alm and alm != '':
        condiciones.append("a.id_almacen = %s")
        params.append(alm)

    if est and est != '' and tipo == 'despacho':
        condiciones.append("pd.estado = %s")
        params.append(est)

    if resp and resp != '':
        if tipo == 'ingreso':
            condiciones.append("ped.id_persona = %s")
            params.append(resp)
        elif tipo == 'despacho':
            condiciones.append("pd.id_persona = %s")
            params.append(resp)

    where_clause = " AND ".join(condiciones) if condiciones else "1=1"

    queries = {
        'ingreso': (
            f"""
            SELECT 
                ped.id_pedido AS 'ID',
                prov.nombre_proveedor AS 'Proveedor',
                p.marca AS 'Producto',
                di.cantidad AS 'Cant.',
                di.precio_unitario AS 'Precio',
                ped.fecha_pedido AS 'Fecha'
            FROM Pedido ped
            JOIN Detalle_Ingreso di ON ped.id_pedido = di.id_pedido
            JOIN Producto p ON di.id_producto = p.id_producto
            JOIN Proveedor prov ON ped.id_proveedor = prov.id_proveedor
            WHERE {where_clause}
            """,
            ['ID', 'Proveedor', 'Producto', 'Cant.', 'Precio', 'Fecha']
        ),
        'inventario': (
            f"""
            SELECT 
                inv.id_inventario AS 'ID',
                p.marca AS 'Producto',
                cat.nombre_categoria AS 'Categoría',
                inv.stock_producto AS 'Stock',
                a.nombre_almacen AS 'Almacén'
            FROM Inventario inv
            JOIN Producto p ON inv.id_producto = p.id_producto
            JOIN Categoria_Producto cat ON p.id_categoria_producto = cat.id_categoria_producto
            JOIN Estante e ON inv.id_estante = e.id_estante
            JOIN Almacen a ON e.id_almacen = a.id_almacen
            WHERE {where_clause}
            """,
            ['ID', 'Producto', 'Categoría', 'Stock', 'Almacén']
        ),
        'despacho': (
            f"""
            SELECT 
                pd.id_pedido_despacho AS 'ID',
                pd.numero_guia AS 'Guía',
                CONCAT(per.nombre, ' ', per.apellido_patern) AS 'Responsable',
                p.marca AS 'Producto',
                dd.cantidad_solicitada AS 'Cant.',
                pd.estado AS 'Estado'
            FROM Pedido_Despacho pd
            JOIN Detalle_Despacho dd ON pd.id_pedido_despacho = dd.id_pedido_despacho
            JOIN Producto p ON dd.id_producto = p.id_producto
            JOIN Persona per ON pd.id_persona = per.id_persona
            WHERE {where_clause}
            """,
            ['ID', 'Guía', 'Responsable', 'Producto', 'Cant.', 'Estado']
        )
    }

    query, columns = queries.get(tipo, ("SELECT 1", []))
    return query, columns, params

# === GENERAR GRÁFICO ===
def generar_grafico(df, tipo, estilo):
    plt.figure(figsize=(8, 5))
    sns.set_style("whitegrid")

    if tipo == 'ingreso':
        grupo = df.groupby('Proveedor')['Cant.'].sum()
    elif tipo == 'inventario':
        grupo = df.groupby('Almacén')['Stock'].sum()
    elif tipo == 'despacho':
        grupo = df.groupby('Estado')['Cant.'].sum()
    else:
        plt.close()
        return None

    if estilo == 'torta':
        plt.pie(grupo, labels=grupo.index, autopct='%1.1f%%', startangle=90)
    else:
        grupo.plot(kind='bar', color='skyblue')
        plt.ylabel('Cantidad')
        plt.xticks(rotation=45)

    plt.tight_layout()
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    img = buffer.getvalue()
    buffer.close()
    plt.close()
    return 'data:image/png;base64,' + base64.b64encode(img).decode()