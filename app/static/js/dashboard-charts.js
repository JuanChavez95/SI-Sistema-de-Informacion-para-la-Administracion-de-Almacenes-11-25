// dashboard-charts.js - Gráficos del Dashboard

document.addEventListener('DOMContentLoaded', function() {
    // Obtener datos del script JSON
    const dataScript = document.getElementById('dashboard-data');
    if (!dataScript) {
        console.error('No se encontraron datos del dashboard');
        return;
    }
    
    let dashboardData;
    try {
        dashboardData = JSON.parse(dataScript.textContent);
    } catch (e) {
        console.error('Error al parsear datos:', e);
        return;
    }
    
    // Configuración de colores
    const colors = {
        morado: '#7c3aed',
        moradoLight: 'rgba(124, 58, 237, 0.2)',
        negro: '#1a1a1a',
        negroLight: 'rgba(26, 26, 26, 0.2)',
        verde: '#10b981',
        rojo: '#ef4444',
        naranja: '#f59e0b',
        azul: '#3b82f6'
    };
    
    // 1. Gráfico de Recepciones vs Despachos
    const ctxRecepciones = document.getElementById('chartRecepcionesDespachos');
    if (ctxRecepciones && dashboardData.recepcionesDespachos) {
        new Chart(ctxRecepciones, {
            type: 'line',
            data: {
                labels: dashboardData.recepcionesDespachos.labels,
                datasets: [
                    {
                        label: 'Recepciones',
                        data: dashboardData.recepcionesDespachos.recepciones,
                        borderColor: colors.morado,
                        backgroundColor: colors.moradoLight,
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: 'Despachos',
                        data: dashboardData.recepcionesDespachos.despachos,
                        borderColor: colors.negro,
                        backgroundColor: colors.negroLight,
                        tension: 0.4,
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                aspectRatio: 2.5,
                plugins: {
                    legend: {
                        position: 'top'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                }
            }
        });
    }
    
    // 2. Gráfico de Distribución por Almacén
    const ctxDistribucion = document.getElementById('chartDistribucionAlmacenes');
    if (ctxDistribucion && dashboardData.distribucionAlmacenes) {
        new Chart(ctxDistribucion, {
            type: 'bar',
            data: {
                labels: dashboardData.distribucionAlmacenes.labels,
                datasets: [{
                    label: 'Cantidad de Productos',
                    data: dashboardData.distribucionAlmacenes.data,
                    backgroundColor: colors.morado
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                aspectRatio: 1.5,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }
    
    // 3. Gráfico de Ocupación de Almacenes
    const ctxOcupacion = document.getElementById('chartOcupacionAlmacenes');
    if (ctxOcupacion && dashboardData.ocupacionAlmacenes) {
        new Chart(ctxOcupacion, {
            type: 'bar',
            data: {
                labels: dashboardData.ocupacionAlmacenes.labels,
                datasets: [
                    {
                        label: 'Capacidad Total',
                        data: dashboardData.ocupacionAlmacenes.capacidad,
                        backgroundColor: colors.negroLight,
                        borderColor: colors.negro,
                        borderWidth: 1
                    },
                    {
                        label: 'Capacidad Ocupada',
                        data: dashboardData.ocupacionAlmacenes.ocupada,
                        backgroundColor: colors.morado
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                aspectRatio: 1.5,
                plugins: {
                    legend: {
                        position: 'top'
                    },
                    tooltip: {
                        callbacks: {
                            afterLabel: function(context) {
                                const index = context.dataIndex;
                                const porcentajes = dashboardData.ocupacionAlmacenes.porcentajes;
                                if (porcentajes && porcentajes[index]) {
                                    return 'Ocupación: ' + porcentajes[index].toFixed(2) + '%';
                                }
                                return '';
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }
    
    // 4. Gráfico de Productos por Categoría
    const ctxCategoria = document.getElementById('chartProductosCategoria');
    if (ctxCategoria && dashboardData.productosCategoria) {
        const categoriasData = dashboardData.productosCategoria.data;
        const coloresArray = [colors.morado, colors.negro, colors.verde, colors.rojo, colors.naranja, colors.azul];
        const backgroundColors = categoriasData.map(function(valor, index) {
            return coloresArray[index % coloresArray.length];
        });
        
        new Chart(ctxCategoria, {
            type: 'doughnut',
            data: {
                labels: dashboardData.productosCategoria.labels,
                datasets: [{
                    label: 'Cantidad',
                    data: categoriasData,
                    backgroundColor: backgroundColors,
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                aspectRatio: 2.5,
                plugins: {
                    legend: {
                        position: 'right'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.parsed || 0;
                                const total = context.dataset.data.reduce(function(a, b) {
                                    return a + b;
                                }, 0);
                                const percentage = ((value / total) * 100).toFixed(1);
                                return label + ': ' + value + ' (' + percentage + '%)';
                            }
                        }
                    }
                }
            }
        });
    }
    
    console.log('Dashboard charts cargados correctamente');
});