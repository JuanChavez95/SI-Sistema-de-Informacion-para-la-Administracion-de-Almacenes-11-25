// Auto-cerrar mensajes flash después de 5 segundos
document.addEventListener('DOMContentLoaded', function() {
    const flashMessages = document.querySelectorAll('.flash');
    
    flashMessages.forEach(function(flash) {
        setTimeout(function() {
            flash.style.animation = 'slideOut 0.3s ease';
            setTimeout(function() {
                if (flash.parentElement) {
                    flash.remove();
                }
            }, 300);
        }, 5000);
    });

    // Cerrar mensajes flash al hacer click en la X
    flashMessages.forEach(function(flash) {
        const closeBtn = flash.querySelector('button');
        if (closeBtn) {
            closeBtn.addEventListener('click', function() {
                flash.style.animation = 'slideOut 0.3s ease';
                setTimeout(function() {
                    if (flash.parentElement) {
                        flash.remove();
                    }
                }, 300);
            });
        }
    });
});

// Validación de formularios
function validateForm(form) {
    const inputs = form.querySelectorAll('input[required]');
    let isValid = true;

    inputs.forEach(function(input) {
        if (!input.value.trim()) {
            input.style.borderColor = '#ef4444';
            isValid = false;
        } else {
            input.style.borderColor = '#e5e7eb';
        }
    });

    return isValid;
}

// Validación de email
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

// Validación de contraseña (mínimo 6 caracteres)
function isValidPassword(password) {
    return password.length >= 6;
}

// Efectos de hover para tarjetas
document.addEventListener('DOMContentLoaded', function() {
    const cards = document.querySelectorAll('.modulo-card, .stat-card');
    
    cards.forEach(function(card) {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });
});

// Toggle sidebar en móviles
function toggleSidebar() {
    const sidebar = document.querySelector('.sidebar');
    const mainContent = document.querySelector('.main-content');
    
    if (sidebar && mainContent) {
        sidebar.classList.toggle('active');
        
        if (window.innerWidth <= 768) {
            if (sidebar.classList.contains('active')) {
                mainContent.style.marginLeft = '280px';
            } else {
                mainContent.style.marginLeft = '0';
            }
        }
    }
}

// Cerrar sidebar al hacer click fuera de él (en móviles)
document.addEventListener('click', function(event) {
    const sidebar = document.querySelector('.sidebar');
    const mainContent = document.querySelector('.main-content');
    
    if (window.innerWidth <= 768 && sidebar && mainContent) {
        if (!sidebar.contains(event.target) && !event.target.closest('.menu-toggle')) {
            sidebar.classList.remove('active');
            mainContent.style.marginLeft = '0';
        }
    }
});

// Manejo de formulario de login
const loginForm = document.querySelector('.auth-form');
if (loginForm && window.location.pathname.includes('login')) {
    loginForm.addEventListener('submit', function(e) {
        const email = document.getElementById('email');
        const password = document.getElementById('password');
        
        if (email && !isValidEmail(email.value)) {
            e.preventDefault();
            email.style.borderColor = '#ef4444';
            showError('Por favor ingresa un email válido');
            return;
        }
        
        if (password && !isValidPassword(password.value)) {
            e.preventDefault();
            password.style.borderColor = '#ef4444';
            showError('La contraseña debe tener al menos 6 caracteres');
            return;
        }
        
        // Mostrar loading
        const submitBtn = this.querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.innerHTML = 'Ingresando...';
            submitBtn.disabled = true;
        }
    });
}

// Manejo de formulario de registro
const registroForm = document.querySelector('.auth-form');
if (registroForm && window.location.pathname.includes('registro')) {
    registroForm.addEventListener('submit', function(e) {
        const password = document.getElementById('password');
        const ci = document.getElementById('ci');
        
        if (password && !isValidPassword(password.value)) {
            e.preventDefault();
            password.style.borderColor = '#ef4444';
            showError('La contraseña debe tener al menos 6 caracteres');
            return;
        }
        
        if (ci && ci.value.length < 6) {
            e.preventDefault();
            ci.style.borderColor = '#ef4444';
            showError('El CI debe tener al menos 6 dígitos');
            return;
        }
        
        // Mostrar loading
        const submitBtn = this.querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.innerHTML = 'Registrando...';
            submitBtn.disabled = true;
        }
    });
}

// Función para mostrar errores temporales
function showError(message) {
    // Crear elemento de error
    const errorDiv = document.createElement('div');
    errorDiv.className = 'flash flash-danger';
    errorDiv.innerHTML = `
        ${message}
        <button onclick="this.parentElement.remove()">&times;</button>
    `;
    
    // Agregar al contenedor de flashes
    const flashContainer = document.querySelector('.flash-container');
    if (flashContainer) {
        flashContainer.appendChild(errorDiv);
    } else {
        // Crear contenedor si no existe
        const newFlashContainer = document.createElement('div');
        newFlashContainer.className = 'flash-container';
        newFlashContainer.appendChild(errorDiv);
        document.body.appendChild(newFlashContainer);
    }
    
    // Auto-remover después de 5 segundos
    setTimeout(() => {
        if (errorDiv.parentElement) {
            errorDiv.remove();
        }
    }, 5000);
}

// Animación de carga para botones
function setLoading(button, isLoading) {
    if (isLoading) {
        button.innerHTML = '<div class="loading-spinner"></div> Procesando...';
        button.disabled = true;
    } else {
        button.innerHTML = button.getAttribute('data-original-text') || 'Enviar';
        button.disabled = false;
    }
}

// Efectos de focus para inputs
document.addEventListener('DOMContentLoaded', function() {
    const inputs = document.querySelectorAll('input, select, textarea');
    
    inputs.forEach(function(input) {
        // Guardar texto original de los botones
        if (input.type === 'submit' || input.tagName === 'BUTTON') {
            input.setAttribute('data-original-text', input.innerHTML);
        }
        
        input.addEventListener('focus', function() {
            this.parentElement.classList.add('focused');
        });
        
        input.addEventListener('blur', function() {
            this.parentElement.classList.remove('focused');
        });
    });
});

// Detectar si es móvil
function isMobile() {
    return window.innerWidth <= 768;
}

// Ajustar layout en resize
window.addEventListener('resize', function() {
    const sidebar = document.querySelector('.sidebar');
    const mainContent = document.querySelector('.main-content');
    
    if (window.innerWidth > 768 && sidebar && mainContent) {
        sidebar.classList.remove('active');
        mainContent.style.marginLeft = '280px';
    } else if (window.innerWidth <= 768 && sidebar && mainContent) {
        if (!sidebar.classList.contains('active')) {
            mainContent.style.marginLeft = '0';
        }
    }
});

// Inicializar cuando carga la página
document.addEventListener('DOMContentLoaded', function() {
    console.log('Sistema de Almacenes - JS cargado correctamente');
    
    // Aplicar estilos iniciales según el tamaño de pantalla
    if (isMobile()) {
        const mainContent = document.querySelector('.main-content');
        if (mainContent) {
            mainContent.style.marginLeft = '0';
        }
    }
});

// CSS para el spinner de loading (se inyecta dinámicamente)
const loadingStyles = `
@keyframes slideOut {
    from {
        transform: translateX(0);
        opacity: 1;
    }
    to {
        transform: translateX(100%);
        opacity: 0;
    }
}

.loading-spinner {
    display: inline-block;
    width: 16px;
    height: 16px;
    border: 2px solid #ffffff;
    border-radius: 50%;
    border-top-color: transparent;
    animation: spin 1s ease-in-out infinite;
    margin-right: 8px;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}

.form-group.focused label {
    color: #7c3aed;
}

.form-group.focused .form-control {
    border-color: #7c3aed;
    box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.1);
}

@media (max-width: 768px) {
    .menu-toggle {
        display: block;
        position: fixed;
        top: 15px;
        left: 15px;
        z-index: 1000;
        background: #7c3aed;
        color: white;
        border: none;
        border-radius: 5px;
        padding: 10px;
        cursor: pointer;
    }
}
`;

// Inyectar los estilos
const styleSheet = document.createElement('style');
styleSheet.textContent = loadingStyles;
document.head.appendChild(styleSheet);