import os
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, send_file, current_app
from app.utils.decorators import login_required
from app.config import Config
import mysql.connector
import pandas as pd
import io
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.backends.backend_pdf import PdfPages
import seaborn as sns
import base64
from datetime import datetime
import matplotlib
matplotlib.use('Agg')  # Elimina el warning del hilo GUI

# Blueprint
reportes_bp = Blueprint('reportes', __name__, url_prefix='/reportes')

def get_db_connection():
    """Establece y devuelve la conexión a la base de datos MySQL."""
    return mysql.connector.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DB
    )

# === CONTROL DE ACCESO ===
def tiene_acceso_reportes():
    """Controla el acceso basado en el rol de usuario."""
    rol = session.get('user_role')
    return rol in ['Administrador', 'Contador', 'Gerente']

# === RUTA PRINCIPAL (index) ===
@reportes_bp.route('/', methods=['GET'])
@login_required
def index():
    """Carga los filtros necesarios (Proveedores, Categorías, Almacenes, Responsables) para la interfaz de reportes."""
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

# === GENERAR REPORTE (generar) ===
@reportes_bp.route('/generar', methods=['POST'])
@login_required
def generar():
    """Recibe parámetros, ejecuta consulta segura y devuelve datos + gráfico en JSON."""
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

# === EXPORTAR EXCEL (DISEÑO CORPORATIVO FORNO) ===
@reportes_bp.route('/exportar/excel', methods=['POST'])
@login_required
def exportar_excel():
    """Exporta datos filtrados a Excel con diseño corporativo FORNO."""
    if not tiene_acceso_reportes():
        return {'error': 'Acceso denegado'}, 403

    data = request.get_json()
    df = pd.DataFrame(data['data'])
    
    # Datos del usuario y fecha
    usuario_nombre = session.get('nombre_completo', 'Usuario del Sistema')
    # Formato de fecha simplificado: DD/MM/AAAA
    fecha_impresion = datetime.now().strftime('%d/%m/%Y') 

    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        sheet_name = 'Reporte Forno'
        # Empezamos en la fila 10 para dejar espacio al encabezado corporativo
        start_row = 10 
        df.to_excel(writer, index=False, sheet_name=sheet_name, startrow=start_row)
        
        workbook = writer.book
        worksheet = writer.sheets[sheet_name]
        
        # --- 1. CONFIGURACIÓN DE PÁGINA ---
        worksheet.set_portrait() # Vertical
        worksheet.set_paper(9)   # A4
        worksheet.set_margins(left=0.7, right=0.7, top=0.75, bottom=0.75)
        worksheet.fit_to_pages(1, 0) # Ajustar ancho a 1 página
        
        # Calcular la última columna del reporte para centrar
        last_col = len(df.columns) - 1 if not df.empty else 5
        merge_range = f'A1:{chr(ord("A") + last_col)}1'

        # --- 2. ESTILOS CORPORATIVOS ---
        # Título Principal CENTRADO (Gris oscuro profesional)
        fmt_titulo_main = workbook.add_format({
            'bold': True, 'font_size': 14, 'font_name': 'Calibri',
            'align': 'center', 'valign': 'vcenter', 'color': '#333333'
        })
        # Datos Empresa (Subtítulos, Gris Suave)
        fmt_empresa = workbook.add_format({
            'font_size': 10, 'font_name': 'Calibri', 'align': 'center', 'color': '#555555'
        })
        # Datos Generación (Derecha, Cursiva)
        fmt_meta_info = workbook.add_format({
            'font_size': 9, 'font_name': 'Calibri', 'align': 'right', 'color': '#777777', 'italic': True
        })
        # Encabezados de Tabla (Gris Oscuro + Texto Blanco)
        fmt_header_table = workbook.add_format({
            'bold': True, 'text_wrap': True, 'valign': 'top', 
            'fg_color': '#404040', 'font_color': '#FFFFFF', # Gris oscuro corporativo
            'border': 1, 'border_color': '#000000', 
            'font_name': 'Calibri', 'align': 'center'
        })

        # --- 3. ENCABEZADO DEL REPORTE (CENTRADO) ---
        
        # Fila 1: Título Principal (Merge y Centrado)
        worksheet.merge_range(merge_range, "GRUPO FORNO – Almacenamientos", fmt_titulo_main)
        
        # Filas 2-5: Datos de Contacto (Merge y Centrado)
        worksheet.merge_range(f'A2:{chr(ord("A") + last_col)}2', "📍 Dirección: Av Chacaltaya Nº 789 – Zona Achachicala", fmt_empresa)
        worksheet.merge_range(f'A3:{chr(ord("A") + last_col)}3', "📱 Celular: 76216960", fmt_empresa)
        worksheet.merge_range(f'A4:{chr(ord("A") + last_col)}4', "💬 WhatsApp: +591 76216960", fmt_empresa)
        worksheet.merge_range(f'A5:{chr(ord("A") + last_col)}5', "🌐 Sitio web: https://grupoforno.com/", fmt_empresa)

        # Lado Derecho: Logo e Info de Usuario
        
        # CAMBIO: Usamos el nombre de archivo con guion 'logo-forno.png'
        try:
            logo_path = os.path.join(current_app.root_path, 'static', 'img', 'logo-forno.png')
            if os.path.exists(logo_path):
                # Insertamos imagen flotante en la celda de la derecha
                worksheet.insert_image(0, last_col, logo_path, {'x_scale': 0.7, 'y_scale': 0.7, 'x_offset': -5, 'y_offset': 5})
        except Exception:
            pass # Si falla, simplemente no pone el logo

        # Texto "Generado por" (Fila 6, Alineado a la derecha)
        info_texto = f"Generado por: {usuario_nombre} | Fecha: {fecha_impresion}"
        worksheet.merge_range(6, last_col - 3, 6, last_col, info_texto, fmt_meta_info)

        # Título del Reporte (Centrado antes de la tabla)
        tipo_reporte = request.json.get('tipo_reporte', 'General').upper()
        fmt_report_title = workbook.add_format({'bold': True, 'align': 'center', 'font_size': 12, 'bottom': 2, 'bottom_color': '#999999'})
        worksheet.merge_range(start_row - 2, 0, start_row - 2, last_col, f"REPORTE DE {tipo_reporte}", fmt_report_title)

        # --- 4. FORMATO DE TABLA ---
        # Configuración de estilo de cuerpo (se aplica con el autoajuste de columnas)
        fmt_body = workbook.add_format({
            'border': 1, 'border_color': '#E0E0E0', 'font_name': 'Calibri',
            'font_size': 10, 'align': 'left'
        })

        # Reescribir encabezados con formato
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(start_row, col_num, value, fmt_header_table)

        # Autoajuste de columnas y aplicación de formato de cuerpo
        for i, col in enumerate(df.columns):
            # Calcular ancho basado en contenido y encabezado
            max_len = max(
                df[col].astype(str).map(len).max() if not df[col].empty else 0,
                len(str(col))
            ) + 2
            # Limitamos a un ancho razonable
            worksheet.set_column(i, i, min(max_len, 45), fmt_body)
            # Aplicar formato de filas alternas (Zebra Striping)
            for row_num, _ in enumerate(df.index):
                row_excel = row_num + start_row + 1
                if (row_excel % 2) != 0:
                    alt_fmt = workbook.add_format({'bg_color': '#F3F3F3', 'border': 1, 'border_color': '#E0E0E0', 'font_name': 'Calibri', 'font_size': 10, 'align': 'left'})
                    worksheet.write(row_excel, i, df.iloc[row_num][col], alt_fmt)


    output.seek(0)
    filename = f"Reporte_Forno_{datetime.now().strftime('%Y%m%d')}.xlsx"
    return send_file(output, as_attachment=True, download_name=filename, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# === EXPORTAR PDF (DISEÑO CORPORATIVO FORNO) ===
@reportes_bp.route('/exportar/pdf', methods=['POST'])
@login_required
def exportar_pdf():
    """Exporta datos y gráfico a PDF con diseño corporativo FORNO."""
    if not tiene_acceso_reportes():
        return {'error': 'Acceso denegado'}, 403

    data = request.get_json()
    df = pd.DataFrame(data['data'])
    chart_b64 = data.get('chart_url', '').split(',')[1] if data.get('chart_url') else None
    
    # Metadatos para el reporte
    tipo_reporte = data.get('tipo_reporte', 'GENERAL').upper()
    usuario_nombre = session.get('nombre_completo', 'Usuario del Sistema')
    # Formato de fecha simplificado
    fecha_impresion = datetime.now().strftime('%d/%m/%Y') 

    output = io.BytesIO()
    
    # Configuración de fuentes y estilo
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Calibri', 'Arial', 'DejaVu Sans']
    plt.rcParams['axes.edgecolor'] = '#999999'

    with PdfPages(output) as pdf:
        # A4 Vertical
        fig = plt.figure(figsize=(8.27, 11.69))
        
        # --- 1. ENCABEZADO (Header) - CENTRADO ---
        header_y = 0.95
        line_height = 0.015
        
        # Título Principal (Centrado y más grande)
        fig.text(0.5, header_y, "GRUPO FORNO – Almacenamientos", fontsize=16, weight='bold', color='#333333', ha='center')
        
        # Datos de Contacto (Centrados)
        fig.text(0.5, header_y - line_height*2, " Dirección: Av Chacaltaya Nº 789 – Zona Achachicala", fontsize=9, color='#555555', ha='center')
        fig.text(0.5, header_y - line_height*3.5, " Celular/WhatsApp: +591 76216960", fontsize=9, color='#555555', ha='center')
        fig.text(0.5, header_y - line_height*5, " Sitio web: https://grupoforno.com/", fontsize=9, color='#555555', ha='center')

        # Lado Derecho: Logo
        # CAMBIO: Usamos el nombre de archivo con guion 'logo-forno.png'
        try:
            logo_path = os.path.join(current_app.root_path, 'static', 'img', 'logo-forno.png')
            if os.path.exists(logo_path):
                logo_img = plt.imread(logo_path)
                # Ejes para el logo (x, y, ancho, alto) en coordenadas de la figura (0 a 1)
                newax = fig.add_axes([0.75, header_y - line_height*4, 0.15, 0.08], anchor='NE', zorder=1)
                newax.imshow(logo_img)
                newax.axis('off')
        except Exception:
            pass # Si falla carga de imagen, no detener flujo

        # Info Usuario (Alineado a la derecha, debajo del logo)
        fig.text(0.9, header_y - line_height*7, f"Generado por: {usuario_nombre}", fontsize=8, ha='right', color='#777777', style='italic')
        fig.text(0.9, header_y - line_height*8.5, f"Fecha: {fecha_impresion}", fontsize=8, ha='right', color='#777777', style='italic')

        # Línea divisoria del header (Gris claro)
        linea = plt.Line2D([0.1, 0.9], [header_y - line_height*10, header_y - line_height*10], transform=fig.transFigure, color='#CCCCCC', linewidth=1.5)
        fig.add_artist(linea)

        # --- 2. TÍTULO DEL REPORTE ---
        fig.text(0.5, 0.82, f"REPORTE DE {tipo_reporte}", fontsize=14, weight='bold', ha='center', color='black')
        # Subtítulo (opcional, si hubiera fechas filtro)
        if data.get('fecha_inicio') and data.get('fecha_fin'):
            periodo = f"Periodo: {data.get('fecha_inicio')} al {data.get('fecha_fin')}"
            fig.text(0.5, 0.80, periodo, fontsize=10, ha='center', color='#555555')

        # --- 3. TABLA DE DATOS Y GRÁFICO (Optimización de espacio) ---
        # Usamos GridSpec para distribuir el espacio de manera más eficiente
        # Top ajustado debajo del título
        gs = gridspec.GridSpec(2, 1, height_ratios=[2, 1.8], top=0.77, bottom=0.1, left=0.05, right=0.95, hspace=0.3)
        
        ax_table = fig.add_subplot(gs[0])
        ax_table.axis('off')
        
        df_display = df.head(40) # Aumentamos el límite de filas para aprovechar el espacio

        if not df_display.empty:
            table = ax_table.table(
                cellText=df_display.values,
                colLabels=df_display.columns,
                loc='center',
                cellLoc='center'
            )
            
            table.auto_set_font_size(False)
            table.set_fontsize(7) # Fuente más pequeña para más datos
            table.scale(1, 1.1)

            # Estilo con líneas suaves y encabezado oscuro
            for (row, col), cell in table.get_celld().items():
                cell.set_linewidth(0.2)
                cell.set_edgecolor('#B0B0B0') # Borde gris suave
                if row == 0:
                    cell.set_text_props(weight='bold', color='white')
                    cell.set_facecolor('#404040') # Cabecera Gris Oscuro
                else:
                    cell.set_text_props(color='black')
                    # Filas alternas (Zebra striping suave)
                    if row % 2 == 0:
                        cell.set_facecolor('#F8F8F8')
                    else:
                        cell.set_facecolor('white')
        else:
            ax_table.text(0.5, 0.5, "No hay datos para mostrar con los filtros seleccionados.", 
                         ha='center', va='center', fontsize=10, style='italic', color='#777777')

        # --- 4. GRÁFICO ---
        if chart_b64:
            ax_chart = fig.add_subplot(gs[1])
            ax_chart.axis('off')
            
            chart_img = base64.b64decode(chart_b64)
            image = plt.imread(io.BytesIO(chart_img))
            
            ax_chart.imshow(image)
            ax_chart.set_title("Representación Gráfica de Datos", fontsize=10, pad=5, color='#333333', weight='bold')

        # --- 5. PIE DE PÁGINA (DISCLAIMER) ---
        footer_text = (
            "Este documento debe ser utilizado de manera responsable. Grupo FORNO se exime de responsabilidad por cualquier uso indebido.\n"
            "Verifique la fecha de generación para asegurar la vigencia de los datos."
        )
        fig.text(0.5, 0.03, footer_text, ha='center', fontsize=7, color='#666666', style='italic')
        
        pdf.savefig(fig)
        plt.close()

    output.seek(0)
    filename = f"Reporte_Forno_{datetime.now().strftime('%Y%m%d')}.pdf"
    return send_file(output, as_attachment=True, download_name=filename, mimetype='application/pdf')

# === CONSTRUIR QUERY SEGURA (construir_query_segura) ===
def construir_query_segura(tipo, fi, ff, prov, cat, alm, est, resp):
    """Crea consultas SQL dinámicas con parámetros seguros."""
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
                CONCAT(per.nombre, ' ', per.apellido_paterno) AS 'Responsable',
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

# === GENERAR GRÁFICO (generar_grafico) ===
def generar_grafico(df, tipo, estilo):
    """Genera gráficos de barras o torta y los codifica en Base64."""
    plt.figure(figsize=(8, 5))
    # Estilo minimalista y profesional
    sns.set_style("white")
    sns.set_context("talk", font_scale=0.8)

    if tipo == 'ingreso':
        grupo = df.groupby('Proveedor')['Cant.'].sum()
        xlabel = 'Proveedor'
    elif tipo == 'inventario':
        grupo = df.groupby('Almacén')['Stock'].sum()
        xlabel = 'Almacén'
    elif tipo == 'despacho':
        grupo = df.groupby('Estado')['Cant.'].sum()
        xlabel = 'Estado'
    else:
        plt.close()
        return None

    # Colores en escala de grises
    grey_palette = sns.color_palette("Greys_r", n_colors=len(grupo))

    if estilo == 'torta':
        # Gráfico de torta en tonos grises
        plt.pie(grupo, labels=grupo.index, autopct='%1.1f%%', startangle=90, colors=grey_palette)
        plt.title(f'Distribución por {xlabel}', fontsize=12, weight='bold', color='#333333', pad=20)
    else:
        # Gráfico de barras en gris sólido profesional
        ax = grupo.plot(kind='bar', color='#666666', width=0.6)
        plt.title(f'Suma de Cantidades por {xlabel}', fontsize=12, weight='bold', color='#333333', pad=20)
        plt.ylabel('Cantidad')
        plt.xlabel(xlabel)
        plt.xticks(rotation=45, ha='right')
        # Quitar bordes innecesarios
        sns.despine()
        plt.grid(axis='y', linestyle='--', alpha=0.5)

    plt.tight_layout()
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=150) # Mayor DPI para mejor calidad
    buffer.seek(0)
    img = buffer.getvalue()
    buffer.close()
    plt.close()
    
    return 'data:image/png;base64,' + base64.b64encode(img).decode()