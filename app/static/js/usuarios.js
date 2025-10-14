// ============ MÓDULO DE USUARIOS ============

// Cargar roles al abrir página
document.addEventListener('DOMContentLoaded', function() {
    cargarRoles();
});

// Cambiar tabs
function cambiarTab(tab) {
    var tabButtons = document.querySelectorAll('.tab-btn');
    var tabContents = document.querySelectorAll('.tab-content');
    
    tabButtons.forEach(function(btn) {
        btn.classList.remove('active');
    });
    
    tabContents.forEach(function(content) {
        content.classList.remove('active');
    });
    
    event.target.classList.add('active');
    document.getElementById('tab-' + tab).classList.add('active');
}

// Abrir modal empleado
function abrirModalEmpleado() {
    document.getElementById('tituloModalEmpleado').textContent = 'Nuevo Empleado';
    document.getElementById('formEmpleado').reset();
    document.getElementById('formEmpleado').action = '/usuarios/crear-empleado';
    
    var checkboxes = document.querySelectorAll('#rolesCheckbox input');
    checkboxes.forEach(function(cb) {
        cb.checked = false;
    });
    
    // Mostrar campo contraseña
    var passwordField = document.querySelector('#formEmpleado input[name="password"]');
    if (passwordField && passwordField.parentElement) {
        passwordField.parentElement.style.display = 'flex';
        passwordField.setAttribute('required', 'required');
    }
    
    // Habilitar CI
    var ciField = document.querySelector('#formEmpleado input[name="ci"]');
    if (ciField) {
        ciField.disabled = false;
    }
    
    document.getElementById('modalEmpleado').classList.add('active');
}

// Abrir modal cliente
function abrirModalCliente() {
    document.getElementById('tituloModalCliente').textContent = 'Nuevo Cliente';
    document.getElementById('formCliente').reset();
    document.getElementById('formCliente').action = '/usuarios/crear-cliente';
    
    // Mostrar campo contraseña
    var passwordField = document.querySelector('#formCliente input[name="password"]');
    if (passwordField && passwordField.parentElement) {
        passwordField.parentElement.style.display = 'flex';
        passwordField.setAttribute('required', 'required');
    }
    
    // Habilitar CI
    var ciField = document.querySelector('#formCliente input[name="ci"]');
    if (ciField) {
        ciField.disabled = false;
    }
    
    document.getElementById('modalCliente').classList.add('active');
}

// Cerrar modal
function cerrarModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

// Cerrar modal al hacer click fuera
window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.classList.remove('active');
    }
}

// Cargar roles disponibles
function cargarRoles() {
    fetch('/usuarios/api/roles')
        .then(function(response) {
            return response.json();
        })
        .then(function(roles) {
            var container = document.getElementById('rolesCheckbox');
            container.innerHTML = '';
            
            roles.forEach(function(rol) {
                var div = document.createElement('div');
                div.className = 'checkbox-item';
                div.innerHTML = '<input type="checkbox" name="roles[]" value="' + rol.id_rol + '" id="rol_' + rol.id_rol + '">' +
                                '<label for="rol_' + rol.id_rol + '">' + rol.nombre_rol + '</label>';
                container.appendChild(div);
            });
        })
        .catch(function(error) {
            console.error('Error al cargar roles:', error);
        });
}

// Editar empleado
function editarEmpleado(id) {
    fetch('/usuarios/api/usuario/' + id)
        .then(function(response) {
            return response.json();
        })
        .then(function(usuario) {
            document.getElementById('tituloModalEmpleado').textContent = 'Editar Empleado';
            document.getElementById('formEmpleado').action = '/usuarios/editar-empleado/' + id;
            
            // Llenar formulario
            document.querySelector('#formEmpleado input[name="nombre"]').value = usuario.nombre;
            document.querySelector('#formEmpleado input[name="apellido_paterno"]').value = usuario.apellido_paterno;
            document.querySelector('#formEmpleado input[name="apellido_materno"]').value = usuario.apellido_materno || '';
            document.querySelector('#formEmpleado input[name="ci"]').value = usuario.ci;
            document.querySelector('#formEmpleado input[name="ci"]').disabled = true;
            document.querySelector('#formEmpleado input[name="email"]').value = usuario.email;
            document.querySelector('#formEmpleado input[name="fecha_nacimiento"]').value = usuario.fecha_nacimiento || '';
            
            // Ocultar campo contraseña en edición
            var passwordField = document.querySelector('#formEmpleado input[name="password"]');
            if (passwordField && passwordField.parentElement) {
                passwordField.parentElement.style.display = 'none';
                passwordField.removeAttribute('required');
            }
            
            // Marcar roles
            var checkboxes = document.querySelectorAll('#rolesCheckbox input');
            checkboxes.forEach(function(cb) {
                // Asumo que usuario.roles es un array de IDs de roles o un string que puedes verificar
                // Nota: Tu código original tenía un error lógico aquí. Lo estoy corrigiendo a una verificación más simple.
                // Idealmente, tu API debería devolver una lista de IDs para comparar con parseInt(cb.value)
                cb.checked = usuario.roles_string && usuario.roles_string.includes(cb.name); 
            });
            
            document.getElementById('modalEmpleado').classList.add('active');
        })
        .catch(function(error) {
            console.error('Error al cargar empleado:', error);
            alert('Error al cargar los datos del empleado');
        });
}

// Editar cliente
function editarCliente(id) {
    fetch('/usuarios/api/usuario/' + id)
        .then(function(response) {
            return response.json();
        })
        .then(function(usuario) {
            document.getElementById('tituloModalCliente').textContent = 'Editar Cliente';
            document.getElementById('formCliente').action = '/usuarios/editar-cliente/' + id;
            
            // Llenar formulario
            document.querySelector('#formCliente input[name="nombre"]').value = usuario.nombre;
            document.querySelector('#formCliente input[name="apellido_paterno"]').value = usuario.apellido_paterno;
            document.querySelector('#formCliente input[name="apellido_materno"]').value = usuario.apellido_materno || '';
            document.querySelector('#formCliente input[name="ci"]').value = usuario.ci;
            document.querySelector('#formCliente input[name="ci"]').disabled = true;
            document.querySelector('#formCliente input[name="email"]').value = usuario.email;
            document.querySelector('#formCliente input[name="fecha_nacimiento"]').value = usuario.fecha_nacimiento || '';
            document.querySelector('#formCliente select[name="tipo_cliente"]').value = usuario.tipo_cliente;
            document.querySelector('#formCliente select[name="categoria_cliente"]').value = usuario.categoria_cliente;
            document.querySelector('#formCliente input[name="empresa"]').value = usuario.empresa || '';
            document.querySelector('#formCliente input[name="limite_credito"]').value = usuario.limite_credito || 0;
            document.querySelector('#formCliente textarea[name="observaciones"]').value = usuario.observaciones || '';
            
            // Ocultar campo contraseña en edición
            var passwordField = document.querySelector('#formCliente input[name="password"]');
            if (passwordField && passwordField.parentElement) {
                passwordField.parentElement.style.display = 'none';
                passwordField.removeAttribute('required');
            }
            
            document.getElementById('modalCliente').classList.add('active');
        })
        .catch(function(error) {
            console.error('Error al cargar cliente:', error);
            alert('Error al cargar los datos del cliente');
        });
}
// NOTA: Se eliminó la función "confirmarEliminar" de aquí.