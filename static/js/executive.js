/**
 * executive.js - Logica para la consola del ejecutivo.
 *
 * Gestiona: llamado de turnos, escaneo QR, atencion en curso,
 * finalizacion de atencion, y visualizacion de la cola de espera.
 */

(function () {
    'use strict';

    // --- Estado ---
    let html5QrCode = null;
    let scanning = false;
    let timerInterval = null;
    let startTime = null;

    // --- Elementos DOM ---
    const $ = function (id) { return document.getElementById(id); };

    const sinTurnoView = $('sin-turno-view');
    const llamadoView = $('llamado-view');
    const atencionView = $('atencion-view');
    const btnLlamar = $('btn-llamar-siguiente');
    const btnFinalizar = $('btn-finalizar');
    const btnLogout = $('btn-logout');
    const btnScanQR = $('btn-scan-qr');
    const btnStopScan = $('btn-stop-scan');
    const ticketLlamado = $('ticket-llamado');
    const infoLlamado = $('info-llamado');
    const ticketActual = $('ticket-actual');
    const tramiteActual = $('tramite-actual');
    const rutActual = $('rut-actual');
    const tiempoAtencion = $('tiempo-atencion');
    const tipoAtencion = $('tipo-atencion');
    const comentariosAtencion = $('comentarios-atencion');
    const qrReader = $('qr-reader');
    const qrResults = $('qr-reader-results');
    const qrResultDisplay = $('qr-result-display');
    const qrResultText = $('qr-result-text');
    const colaContent = $('cola-content');
    const totalCola = $('total-cola');

    // --- Utilidad Fetch API ---
    async function apiFetch(url, options) {
        const resp = await fetch(url, {
            headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
            ...options
        });
        const data = await resp.json();
        if (!resp.ok) {
            throw new Error(data.error || 'Error en la solicitud');
        }
        return data;
    }

    // --- Cambiar vistas ---
    function mostrarVista(vista) {
        sinTurnoView.classList.add('d-none');
        llamadoView.classList.add('d-none');
        atencionView.classList.add('d-none');

        if (vista === 'sin-turno') {
            sinTurnoView.classList.remove('d-none');
        } else if (vista === 'llamado') {
            llamadoView.classList.remove('d-none');
        } else if (vista === 'atencion') {
            atencionView.classList.remove('d-none');
        }
    }

    // --- Timer de atencion ---
    function iniciarTimer() {
        startTime = Date.now();
        if (timerInterval) clearInterval(timerInterval);
        timerInterval = setInterval(function () {
            if (!startTime) return;
            const elapsed = Math.floor((Date.now() - startTime) / 1000);
            const mins = String(Math.floor(elapsed / 60)).padStart(2, '0');
            const secs = String(elapsed % 60).padStart(2, '0');
            tiempoAtencion.textContent = mins + ':' + secs;
        }, 1000);
    }

    function detenerTimer() {
        if (timerInterval) {
            clearInterval(timerInterval);
            timerInterval = null;
        }
        startTime = null;
        tiempoAtencion.textContent = '00:00';
    }

    // --- Cargar estado inicial ---
    async function loadEstado() {
        try {
            const data = await apiFetch('/api/ejecutivo/estado');
            const turno = data.turno_activo;

            if (!turno) {
                mostrarVista('sin-turno');
                detenerTimer();
            } else if (turno.estado === 'llamado') {
                mostrarVista('llamado');
                ticketLlamado.textContent = turno.codigo;
                infoLlamado.textContent = 'Tramite: ' + (turno.tipo_tramite || '---') +
                                          ' | RUT: ' + (turno.rut_cliente || '---');
                detenerTimer();
            } else if (turno.estado === 'en_atencion') {
                mostrarVista('atencion');
                ticketActual.textContent = turno.codigo;
                tramiteActual.textContent = turno.tipo_tramite || '---';
                rutActual.textContent = turno.rut_cliente || '---';
                if (turno.fecha_inicio_atencion) {
                    const inicio = new Date(turno.fecha_inicio_atencion);
                    startTime = inicio.getTime();
                    iniciarTimer();
                }
            }

            // Cargar cola
            await loadCola();
        } catch (err) {
            console.error('Error al cargar estado:', err);
        }
    }

    // --- Cargar cola de espera ---
    async function loadCola() {
        try {
            const data = await apiFetch('/api/ejecutivo/cola');
            const cola = data.cola || [];
            let total = 0;
            let html = '';

            cola.forEach(function (grupo) {
                total += grupo.total || 0;
                if (grupo.total === 0) return;

                html += `
                    <div class="mb-3">
                        <h6 class="fw-bold text-primary mb-2">
                            ${grupo.tipo_tramite} (${grupo.codigo})
                            <span class="badge bg-secondary float-end">${grupo.total}</span>
                        </h6>
                        <div class="d-flex flex-wrap gap-2">
                `;

                (grupo.turnos || []).forEach(function (t) {
                    html += `<span class="badge bg-light text-dark border px-3 py-2 fs-6">${t.codigo}</span>`;
                });

                html += `</div></div>`;
            });

            if (total === 0) {
                html = '<div class="text-center text-muted py-3">No hay turnos en espera</div>';
            }

            colaContent.innerHTML = html;
            totalCola.textContent = total;
        } catch (err) {
            console.error('Error al cargar cola:', err);
        }
    }

    // --- Llamar siguiente turno ---
    btnLlamar.addEventListener('click', async function () {
        btnLlamar.disabled = true;
        btnLlamar.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Llamando...';

        try {
            const data = await apiFetch('/api/ejecutivo/siguiente');

            if (!data.turno) {
                alert(data.mensaje || 'No hay turnos en espera');
                btnLlamar.disabled = false;
                btnLlamar.innerHTML = 'Llamar Siguiente Turno';
                return;
            }

            // Mostrar vista de llamado
            mostrarVista('llamado');
            ticketLlamado.textContent = data.turno.codigo;
            infoLlamado.textContent = 'Tramite: ' + (data.turno.tipo_tramite || '---') +
                                      ' | RUT: ' + (data.turno.rut_cliente || '---');
            detenerTimer();
            await loadCola();
        } catch (err) {
            alert('Error: ' + err.message);
        }

        btnLlamar.disabled = false;
        btnLlamar.innerHTML = 'Llamar Siguiente Turno';
    });

    // --- Finalizar atencion ---
    btnFinalizar.addEventListener('click', async function () {
        const tipo = tipoAtencion.value;
        const comentarios = comentariosAtencion.value;

        if (!tipo) {
            alert('Seleccione un tipo de atencion');
            return;
        }

        btnFinalizar.disabled = true;
        btnFinalizar.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Finalizando...';

        try {
            const data = await apiFetch('/api/ejecutivo/finalizar-atencion', {
                method: 'POST',
                body: JSON.stringify({
                    tipo_atencion: tipo,
                    comentarios: comentarios
                })
            });

            // Reset formulario
            tipoAtencion.value = '';
            comentariosAtencion.value = '';
            detenerTimer();
            await loadEstado();
        } catch (err) {
            alert('Error: ' + err.message);
        }

        btnFinalizar.disabled = false;
        btnFinalizar.innerHTML = 'Finalizar Atencion';
    });

    // --- Logout ---
    btnLogout.addEventListener('click', async function () {
        try {
            await apiFetch('/api/auth/logout', { method: 'POST' });
            window.location.reload();
        } catch (err) {
            console.error('Error al cerrar sesion:', err);
            window.location.reload();
        }
    });

    // --- Escaner QR ---
    btnScanQR.addEventListener('click', function () {
        if (scanning) return;

        if (!html5QrCode) {
            html5QrCode = new Html5Qrcode('qr-reader');
        }

        const config = {
            fps: 10,
            qrbox: { width: 250, height: 250 }
        };

        html5QrCode.start(
            { facingMode: 'environment' },
            config,
            onScanSuccess,
            onScanFailure
        ).then(function () {
            scanning = true;
            btnScanQR.classList.add('d-none');
            btnStopScan.classList.remove('d-none');
            qrResults.textContent = 'Camara activa. Enfoque el codigo QR.';
        }).catch(function (err) {
            console.error('Error al iniciar camara:', err);
            qrResults.textContent = 'Error: ' + err;
        });
    });

    btnStopScan.addEventListener('click', function () {
        stopScanner();
    });

    function stopScanner() {
        if (html5QrCode && scanning) {
            html5QrCode.stop().then(function () {
                scanning = false;
                btnScanQR.classList.remove('d-none');
                btnStopScan.classList.add('d-none');
                qrResults.textContent = '';
            }).catch(function (err) {
                console.error('Error al detener camara:', err);
            });
        }
    }

    async function onScanSuccess(decodedText) {
        // decodedText es el qr_token (UUID hex)
        stopScanner();
        qrResults.textContent = 'QR detectado. Iniciando atencion...';
        qrResultDisplay.classList.remove('d-none');
        qrResultText.textContent = 'Token: ' + decodedText.substring(0, 16) + '...';

        try {
            const data = await apiFetch('/api/ejecutivo/iniciar-atencion', {
                method: 'POST',
                body: JSON.stringify({ qr_token: decodedText })
            });

            qrResults.textContent = 'Atencion iniciada: ' + (data.turno ? data.turno.codigo : 'OK');

            // Cambiar a vista de atencion
            mostrarVista('atencion');
            ticketActual.textContent = data.turno.codigo;
            tramiteActual.textContent = data.turno.tipo_tramite || '---';
            rutActual.textContent = data.turno.rut_cliente || '---';
            iniciarTimer();

            // Ocultar resultado QR despues de 3 segundos
            setTimeout(function () {
                qrResultDisplay.classList.add('d-none');
            }, 3000);

            await loadCola();
        } catch (err) {
            qrResults.textContent = 'Error: ' + err.message;
            qrResultDisplay.classList.remove('d-none');
            qrResultText.textContent = 'Error: ' + err.message;
        }
    }

    function onScanFailure(err) {
        // Ignorar errores de escaneo intermedio
    }

    // --- Inicializacion ---
    document.addEventListener('DOMContentLoaded', function () {
        loadEstado();

        // Recargar estado cada 10 segundos (fallback si SSE falla)
        setInterval(loadEstado, 10000);

        // Recargar cola cada 15 segundos
        setInterval(loadCola, 15000);
    });

})();
