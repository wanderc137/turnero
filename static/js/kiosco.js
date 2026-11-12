/**
 * kiosco.js - Logica para el kiosco del cliente.
 *
 * Maneja: seleccion de tramite, ingreso de RUT con validacion chilena,
 * solicitud de turno via API, y generacion de QR.
 */

(function () {
    'use strict';

    // --- Estado ---
    let tramiteSeleccionado = null;   // { id, codigo, nombre }
    let qrCodeInstance = null;
    let turnoActual = null;

    // --- Elementos DOM ---
    const $ = function (id) { return document.getElementById(id); };

    const paso1 = $('paso-1');
    const paso2 = $('paso-2');
    const paso3 = $('paso-3');
    const btnVolver = $('btn-volver-paso1');
    const btnSolicitar = $('btn-solicitar-turno');
    const btnNuevoTurno = $('btn-nuevo-turno');
    const rutInput = $('rut-input');
    const rutError = $('rut-error');
    const tramiteSeleccionadoNombre = $('tramite-seleccionado-nombre');
    const ticketCodigo = $('ticket-codigo');
    const ticketTramite = $('ticket-tramite');
    const qrcodeContainer = $('qrcode');

    // --- Datos de tramites (se cargan desde API) ---
    let TRAMITES = {};  // se llena con datos de /api/tramites
    const tramitesContainer = $('tramites-container');

    // --- Validacion de RUT Chileno ---
    function limpiarRUT(rut) {
        return rut.replace(/[^0-9kK]/g, '');
    }

    function formatearRUT(rut) {
        // Formato: XX.XXX.XXX-Y
        const limpio = limpiarRUT(rut);
        if (limpio.length <= 1) return limpio.toUpperCase();

        const numero = limpio.slice(0, -1);
        const dv = limpio.slice(-1).toUpperCase();

        // Agregar puntos
        let formateado = '';
        let count = 0;
        for (let i = numero.length - 1; i >= 0; i--) {
            if (count > 0 && count % 3 === 0) {
                formateado = '.' + formateado;
            }
            formateado = numero[i] + formateado;
            count++;
        }

        return formateado + '-' + dv;
    }

    function validarRUT(rut) {
        const limpio = limpiarRUT(rut);
        if (limpio.length < 2) return false;

        const numero = limpio.slice(0, -1);
        const dvIngresado = limpio.slice(-1).toUpperCase();

        if (!/^\d+$/.test(numero)) return false;
        if (numero.length < 1) return false;

        // Calcular digito verificador
        let suma = 0;
        let multiplicador = 2;

        for (let i = numero.length - 1; i >= 0; i--) {
            suma += parseInt(numero[i]) * multiplicador;
            multiplicador = multiplicador === 7 ? 2 : multiplicador + 1;
        }

        const resto = suma % 11;
        let dvCalculado = 11 - resto;
        if (dvCalculado === 11) dvCalculado = '0';
        else if (dvCalculado === 10) dvCalculado = 'K';
        else dvCalculado = dvCalculado.toString();

        return dvCalculado === dvIngresado;
    }

    // --- Navegacion entre pasos ---
    function mostrarPaso(numero) {
        paso1.classList.add('d-none');
        paso2.classList.add('d-none');
        paso3.classList.add('d-none');

        if (numero === 1) {
            paso1.classList.remove('d-none');
        } else if (numero === 2) {
            paso2.classList.remove('d-none');
        } else if (numero === 3) {
            paso3.classList.remove('d-none');
        }
    }

    // --- Cargar tramites desde API ---
    async function cargarTramites() {
        try {
            const resp = await fetch('/api/tramites');
            const data = await resp.json();

            if (!resp.ok) throw new Error(data.error || 'Error al cargar tramites');

            const tramites = data.tramites || [];
            // Construir indice TRAMITES { id: { codigo, nombre } }
            TRAMITES = {};
            tramitesContainer.innerHTML = '';

            tramites.forEach(function (t) {
                TRAMITES[t.id] = { codigo: t.codigo, nombre: t.nombre };

                const col = document.createElement('div');
                col.className = 'col-md-4';

                const card = document.createElement('div');
                card.className = 'card tramite-card';
                card.dataset.tramiteId = t.id;
                card.dataset.codigo = t.codigo;
                card.innerHTML =
                    '<div class="card-body text-center py-5">' +
                    '  <div class="tramite-icon">' + t.codigo + '</div>' +
                    '  <h4 class="card-title fw-bold mt-3">' + t.nombre + '</h4>' +
                    '  <p class="card-text text-muted">' + t.nombre + '</p>' +
                    '</div>';

                col.appendChild(card);
                tramitesContainer.appendChild(col);
            });

            // Vincular eventos a las nuevas tarjetas
            document.querySelectorAll('.tramite-card').forEach(function (card) {
                card.addEventListener('click', onTramiteCardClick);
            });
        } catch (err) {
            console.error('Error al cargar tramites:', err);
            usarTramitesFallback();
        }
    }

    function usarTramitesFallback() {
        // Fallback hardcodeado si la API falla
        const fallback = [
            { id: 1, codigo: 'A', nombre: 'Creditos' },
            { id: 2, codigo: 'B', nombre: 'Consultas Generales' },
            { id: 3, codigo: 'C', nombre: 'Retiro de Documentos' }
        ];
        TRAMITES = {};
        tramitesContainer.innerHTML = '';

        fallback.forEach(function (t) {
            TRAMITES[t.id] = { codigo: t.codigo, nombre: t.nombre };

            const col = document.createElement('div');
            col.className = 'col-md-4';

            const card = document.createElement('div');
            card.className = 'card tramite-card';
            card.dataset.tramiteId = t.id;
            card.dataset.codigo = t.codigo;
            card.innerHTML =
                '<div class="card-body text-center py-5">' +
                '  <div class="tramite-icon">' + t.codigo + '</div>' +
                '  <h4 class="card-title fw-bold mt-3">' + t.nombre + '</h4>' +
                '  <p class="card-text text-muted">' + t.nombre + '</p>' +
                '</div>';

            col.appendChild(card);
            tramitesContainer.appendChild(col);
        });

        document.querySelectorAll('.tramite-card').forEach(function (card) {
            card.addEventListener('click', onTramiteCardClick);
        });
    }

    function onTramiteCardClick() {
        const tramiteId = parseInt(this.dataset.tramiteId);
        const tramite = TRAMITES[tramiteId];

        if (!tramite) return;

        tramiteSeleccionado = {
            id: tramiteId,
            codigo: tramite.codigo,
            nombre: tramite.nombre
        };

        tramiteSeleccionadoNombre.textContent = tramite.nombre + ' (' + tramite.codigo + ')';

        // Highlight visual
        document.querySelectorAll('.tramite-card').forEach(function (c) { c.classList.remove('selected'); });
        this.classList.add('selected');

        // Limpiar RUT y errores
        rutInput.value = '';
        rutError.classList.add('d-none');
        rutError.textContent = '';

        mostrarPaso(2);
    }

    // --- Inicializar: cargar tramites al arrancar ---
    cargarTramites();

    // --- Volver a paso 1 ---
    btnVolver.addEventListener('click', function () {
        tramiteSeleccionado = null;
        document.querySelectorAll('.tramite-card').forEach(function (c) { c.classList.remove('selected'); });
        mostrarPaso(1);
    });

    // --- Formateo automatico de RUT ---
    rutInput.addEventListener('input', function () {
        const valor = this.value;
        if (valor.length > 0) {
            const formateado = formatearRUT(valor);
            if (formateado !== valor) {
                this.value = formateado;
            }
        }
        rutError.classList.add('d-none');
    });

    // --- Solicitar turno ---
    btnSolicitar.addEventListener('click', async function () {
        const rut = rutInput.value.trim();

        // Validar RUT
        if (!rut) {
            rutError.textContent = 'Ingrese un RUT valido';
            rutError.classList.remove('d-none');
            return;
        }

        if (!validarRUT(rut)) {
            rutError.textContent = 'RUT invalido. Verifique el formato y digito verificador.';
            rutError.classList.remove('d-none');
            return;
        }

        if (!tramiteSeleccionado) {
            alert('Seleccione un tramite primero');
            mostrarPaso(1);
            return;
        }

        btnSolicitar.disabled = true;
        btnSolicitar.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Solicitando...';

        try {
            const resp = await fetch('/api/turnos/solicitar', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
                body: JSON.stringify({
                    tipo_tramite_id: tramiteSeleccionado.id,
                    rut: limpiarRUT(rut)
                })
            });

            const data = await resp.json();

            if (!resp.ok) {
                throw new Error(data.error || 'Error al solicitar turno');
            }

            turnoActual = data.turno;

            // Mostrar paso 3
            ticketCodigo.textContent = turnoActual.codigo;
            ticketTramite.textContent = tramiteSeleccionado.nombre;

            // Generar QR
            generarQR(turnoActual.qr_token);

            mostrarPaso(3);
        } catch (err) {
            alert('Error: ' + err.message);
        }

        btnSolicitar.disabled = false;
        btnSolicitar.innerHTML = 'Solicitar Turno';
    });

    // --- Generar QR ---
    function generarQR(token) {
        // Limpiar QR anterior
        qrcodeContainer.innerHTML = '';

        try {
            qrCodeInstance = new QRCode(qrcodeContainer, {
                text: token,
                width: 200,
                height: 200,
                colorDark: '#1565C0',
                colorLight: '#FFFFFF',
                correctLevel: QRCode.CorrectLevel.H
            });
        } catch (err) {
            console.error('Error al generar QR:', err);
            qrcodeContainer.innerHTML = '<p class="text-muted">Error al generar QR</p>';
        }
    }

    // --- Nuevo turno ---
    btnNuevoTurno.addEventListener('click', function () {
        // Resetear todo
        tramiteSeleccionado = null;
        turnoActual = null;
        document.querySelectorAll('.tramite-card').forEach(function (c) { c.classList.remove('selected'); });
        rutInput.value = '';
        rutError.classList.add('d-none');
        qrcodeContainer.innerHTML = '';

        if (qrCodeInstance) {
            qrCodeInstance.clear();
            qrCodeInstance = null;
        }

        mostrarPaso(1);
    });

})();
