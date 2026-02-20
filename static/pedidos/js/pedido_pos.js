document.addEventListener("DOMContentLoaded", function () {
    const modal = document.getElementById('modalItem');
    const resumen = document.getElementById('resumenPedido');
    const totalPedido = document.getElementById('totalPedido');
    const form = document.getElementById('pedidoForm');

    let pedidoItems = [];

    // Inicializar si hay pedido cargado (edición)
    if (window.PEDIDO_INICIAL && Array.isArray(window.PEDIDO_INICIAL)) {
        pedidoItems = window.PEDIDO_INICIAL.map(item => ({
            ...item,
            id: parseInt(item.id, 10),   // 👈 forzar id a número
            precio: item.tipo === "entrada" ? 0 : parseFloat(item.precio) || 0,
            cantidad: parseInt(item.cantidad) || 0
        }));
        renderResumen();
        injectHiddenInputs();
    }

    // Mostrar modal
    modal.addEventListener('show.bs.modal', function (event) {
        const btn = event.relatedTarget;
        if (!btn) return;

        const tipo = btn.dataset.tipo;
        const id = parseInt(btn.dataset.id, 10); // 👈 número
        const nombre = btn.dataset.nombre;
        const precio = parseFloat(btn.dataset.precio) || 0;

        document.getElementById('modalItemId').value = id;
        document.getElementById('modalItemTipo').value = tipo;
        document.getElementById('modalItemNombre').textContent = nombre;
        document.getElementById('modalItemCantidad').value = 1;
        document.getElementById('modalItemObs').value = '';

        const precioFinal = tipo === 'entrada' ? 0 : precio;
        document.getElementById('modalItemPrecio').textContent = precioFinal.toFixed(2);
    });

    // Agregar ítem desde modal
    function agregarItem(cerrarModal = true) {
        const id = parseInt(document.getElementById('modalItemId').value, 10); // 👈 número
        const tipo = document.getElementById('modalItemTipo').value;
        const nombre = document.getElementById('modalItemNombre').textContent;
        const cantidad = parseInt(document.getElementById('modalItemCantidad').value) || 0;
        if (cantidad <= 0) return;
        const obs = document.getElementById('modalItemObs').value;
        const precio = (tipo === 'entrada') ? 0 : parseFloat(document.getElementById('modalItemPrecio').textContent) || 0;

        let existente = pedidoItems.find(i => i.id === id && i.tipo === tipo); // 👈 comparación segura
        if (existente) {
            existente.cantidad += cantidad;
            if (obs.trim()) {
                existente.obs = obs; // solo sobreescribir si escriben algo
            }
        } else {
            pedidoItems.push({ id, tipo, nombre, precio, cantidad, obs });
        }

        renderResumen();
        injectHiddenInputs();
        if (cerrarModal) bootstrap.Modal.getInstance(modal).hide();
    }

    // Renderizar resumen lateral
    function renderResumen() {
        if (!pedidoItems.length) {
            resumen.innerHTML = '<p class="text-muted">No hay ítems aún.</p>';
            totalPedido.textContent = 'Total: S/ 0.00';
            return;
        }

        let html = '<ul class="list-group">';
        let total = 0;

        pedidoItems.forEach((item, idx) => {
            const subtotal = item.precio * item.cantidad;
            total += subtotal;

            html += `
                <li class="list-group-item d-flex justify-content-between align-items-center">
                    <div>
                        <strong>${item.nombre}</strong><br>
                        <input type="number" min="1" value="${item.cantidad}"
                               class="form-control form-control-sm d-inline-block w-auto me-2"
                               onchange="actualizarCantidad(${idx}, this.value)">
                        ${item.obs ? `<br><small class="text-muted">${item.obs}</small>` : ""}
                        <button type="button" class="btn btn-sm btn-outline-secondary mt-1"
                                onclick="editarObs(${idx})">
                            <i class="fas fa-edit"></i> Obs
                        </button>
                    </div>
                    <div class="text-end">
                        <span class="fw-bold">
                            ${item.tipo === "entrada" ? "S/ 0.00" : "S/ " + subtotal.toFixed(2)}
                        </span>
                        <button type="button" class="btn btn-sm btn-danger ms-2" onclick="eliminarItem(${idx})">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </li>
            `;
        });

        html += '</ul>';
        resumen.innerHTML = html;
        totalPedido.textContent = 'Total: S/ ' + total.toFixed(2);
    }

    // Inyectar inputs ocultos al form
    function injectHiddenInputs() {
        [...form.querySelectorAll('input[type=hidden]')].forEach(el => {
            if (!['csrfmiddlewaretoken', 'mesa'].includes(el.name)) el.remove();
        });

        pedidoItems.forEach(item => {
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = (item.tipo === "producto" ? "producto_" : "plato_") + item.id;
            input.value = item.cantidad;
            form.appendChild(input);

            const obsInput = document.createElement('input');
            obsInput.type = 'hidden';
            obsInput.name = 'observaciones_' + item.id;
            obsInput.value = item.obs;
            form.appendChild(obsInput);
        });
    }

    // Funciones globales para edición inline
    window.eliminarItem = function (index) {
        pedidoItems.splice(index, 1);
        renderResumen();
        injectHiddenInputs();
    };

    window.actualizarCantidad = function (index, nuevaCantidad) {
        nuevaCantidad = parseInt(nuevaCantidad);
        if (nuevaCantidad > 0) {
            pedidoItems[index].cantidad = nuevaCantidad;
            renderResumen();
            injectHiddenInputs();
        }
    };

    window.editarObs = function (index) {
        const nuevaObs = prompt("Observaciones:", pedidoItems[index].obs || "");
        if (nuevaObs !== null) {
            pedidoItems[index].obs = nuevaObs;
            renderResumen();
            injectHiddenInputs();
        }
    };

    // Botones modal
    document.getElementById('modalItemAdd').addEventListener('click', () => agregarItem(true));
    document.getElementById('modalAddContinuar').addEventListener('click', () => agregarItem(false));
    document.getElementById('btnMas').addEventListener('click', () => {
        let input = document.getElementById('modalItemCantidad');
        input.value = parseInt(input.value) + 1;
    });
    document.getElementById('btnMenos').addEventListener('click', () => {
        let input = document.getElementById('modalItemCantidad');
        if (parseInt(input.value) > 1) input.value = parseInt(input.value) - 1;
    });

    // Búsqueda
    document.getElementById('busqueda').addEventListener('input', function () {
        const term = this.value.toLowerCase();
        document.querySelectorAll('.item-buscable').forEach(el => {
            el.style.display = el.innerText.toLowerCase().includes(term) ? '' : 'none';
        });
    });

    // Debug en submit
    form.addEventListener('submit', function () {
        injectHiddenInputs();
        const fd = new FormData(form);
        console.log('FormData →', Array.from(fd.entries()));
    });

    // Toggle Menús y Entradas
    const toggleBtn = document.getElementById("toggle-menu-entradas");
    if (!toggleBtn) return;

    const entradas = document.querySelectorAll(".plato-seccion.entrada");
    const menus = document.querySelectorAll(".plato-seccion.menu");

    const preferencia = localStorage.getItem("mostrarMenusEntradas");
    const defaultVisible = "{{ turno_tarde|yesno:'false,true' }}";
    let visible = (preferencia !== null) ? (preferencia === "true") : (defaultVisible === "true");

    function actualizarVista() {
        [...entradas, ...menus].forEach(sec => {
            sec.style.display = visible ? "block" : "none";
        });
        toggleBtn.innerHTML = visible
            ? '<i class="fas fa-eye-slash"></i> Ocultar Menús y Entradas'
            : '<i class="fas fa-eye"></i> Mostrar Menús y Entradas';
    }

    actualizarVista();

    toggleBtn.addEventListener("click", () => {
        visible = !visible;
        localStorage.setItem("mostrarMenusEntradas", visible);
        actualizarVista();
    });
});