# 📦 Sistema de Administración de Almacenes

![GitHub repo size](https://img.shields.io/github/repo-size/JuanChavez95/SI-Sistema-de-Informacion-para-la-Administracion-de-Almacenes-11-25)
![GitHub contributors](https://img.shields.io/github/contributors/JuanChavez95/SI-Sistema-de-Informacion-para-la-Administracion-de-Almacenes-11-25)
![GitHub stars](https://img.shields.io/github/stars/JuanChavez95/SI-Sistema-de-Informacion-para-la-Administracion-de-Almacenes-11-25?style=social)
![GitHub forks](https://img.shields.io/github/forks/JuanChavez95/SI-Sistema-de-Informacion-para-la-Administracion-de-Almacenes-11-25?style=social)

## 📋 Descripción

El presente sistema tiene como objetivo desarrollar una solución de administración integral para **automatizar y optimizar** los procesos de gestión de inventario, recepción, almacenamiento y distribución espacial. Con la finalidad de mejorar la eficiencia operativa y la gestión de costos en entornos de almacén.

## 👥 Equipo de Desarrollo

- **Kevin Jheferson Jiménez Quisbert**
- **Juan Carlos Chávez Machaca**
- **Fernando Castro Vargas**
- **Willka Daniel Conde Ventura**
- **Erick Iván Luna Tarqui**
- **Juan Antonio Ramos Rojas**

---

## 📊 Análisis de Requerimientos

En esta sección se definen los aspectos fundamentales para la toma de requerimientos en torno a las necesidades del cliente y las funciones necesarias para desarrollar un sistema **funcional, eficiente y escalable**.

### 📋 Contenido del Análisis:
- ✅ **Requerimientos Funcionales**
- ⚙️ **Requerimientos No Funcionales**  
- 💰 **Análisis de Costos**

📄 **Documentación Completa**: [`docs/AnálisisRequerimientos.pdf`](./docs/AnálisisRequerimientos.pdf)

---

## 🗓️ Planificación

El proyecto sigue un **enfoque incremental por fases**, donde cada fase representa un nivel de madurez del sistema, implementando la metodología ágil **SCRUM** para garantizar entregas continuas y adaptabilidad.

### 🔗 Recursos de Planificación:

| Recurso | Enlace |
|---------|--------|
| 📋 **Tablero Trello** | [Ver Proyecto](https://trello.com/invite/b/68bf7bb6936eb730fbc6cbbb/ATTI1d1829d8ff29254a68330b9a32e827e2335571D5/sistema-de-informacion-para-la-administracion-de-almacenes) |
| 📄 **Documento de Planificación** | [`docs/Planificacion.pdf`](./docs/Planificacion.pdf) |
| 🏗️ **Organigrama del Proyecto** | [`diagrams/Organigrama.jpg`](./diagrams/Organigrama.jpg) |

---

## 🎨 Modelado del Sistema

Para esta versión del sistema, se presenta el modelado completo mediante diagramas de clases y relacional, proporcionando una visión integral de la arquitectura del sistema de administración de almacenes.

### 📐 Diagrama de Clases

El flujo operativo del sistema abarca desde la **gestión de productos y categorías**, pasando por el **control de inventario** con la clase `ESTANTE`, hasta el **procesamiento completo de pedidos**. 

Los `PEDIDOS` generan `DETALLE_PEDIDO` que especifican productos individuales, mientras que el `INVENTARIO` rastrea las cantidades disponibles y sus movimientos. El sistema también incluye gestión de proveedores y un módulo de ingresos para registrar la recepción de mercancías, creando un **ecosistema completo** para el manejo de operaciones comerciales y logísticas.

🔗 **Ver Diagrama**: [`diagrams/DiagramaClases.png`](./diagrams/DiagramaClases.png)

### 🗄️ Diagrama Relacional  

Este diagrama relacional muestra la **implementación física de la base de datos** del sistema de gestión de inventario, donde las entidades conceptuales del diagrama de clases se han transformado en tablas con sus respectivas **claves primarias y foráneas**.

🔗 **Ver Diagrama**: [`diagrams/DiagramaRelacional.png`](./diagrams/DiagramaRelacional.png)

---

## 🚀 Tecnologías Utilizadas

```bash
# Agregar las tecnologías que utilizarán
- Frontend: HTML5 y CSS
- Backend: Python
- Base de Datos: MySQL
- Metodología: SCRUM
```

## 📁 Estructura del Proyecto

```
Sistema-Administracion-Almacenes/
├── 📄 README.md
├── 📁 Docs/
│   ├── AnalisisRequerimientos.pdf
│   └── Planificacion.pdf
├── 📁 diagrams/
│   ├── DiagramaClases.png
│   ├── DiagramaRelacional.png
│   └── Organigrama.jpg
├── 📁 src/
│   └── [Código fuente]
└── 📁 database/
    └── [Scripts de base de datos]
```

## 🤝 Contribución

Las contribuciones son bienvenidas. Para contribuir:

1. 🍴 Fork el proyecto
2. 🔄 Crea tu rama de feature (`git checkout -b feature/AmazingFeature`)
3. 💫 Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. 📤 Push a la rama (`git push origin feature/AmazingFeature`)
5. 🔃 Abre un Pull Request

## 📞 Contacto

Para más información sobre el proyecto, contacta a cualquier miembro del equipo de desarrollo Los Error 505.

---
