(function () {
    'use strict';

    let state = { modulos: [], cola: [] };

    const modulosGrid = document.getElementById('modulos-grid');
    const noTurnosOverlay = document.getElementById('no-turnos-overlay');
    const colaSection = document.getElementById('cola-section');
    const colaBody = document.getElementById('cola-body');

    async function loadInitialState() {
        try {
            const resp = await fetch('/api/turnos/display');
            const data = await resp.json();
            state.modulos = data.modulos || [];
            state.cola = data.cola || [];
            render();
        } catch (err) {
            console.error('Error al cargar estado inicial:', err);
        }
    }

    function render() {
        renderCola();
        renderModulos();
        renderOverlay();
    }

    function renderCola() {
        if (!colaBody || !colaSection) return;

        const totalCola = state.cola.reduce(function (sum, g) { return sum + (g.total || 0); }, 0);

        if (totalCola === 0) {
            colaSection.classList.add('d-none');
            return;
        }

        colaSection.classList.remove('d-none');

        let html = '<div class="d-flex flex-wrap gap-2 justify-content-center">';
        state.cola.forEach(function (grupo) {
            if (grupo.total === 0) return;
            html += '<div class="text-center mx-3">';
            html += '<h5 class="text-primary mb-2">' + grupo.tipo_tramite + ' (' + grupo.codigo + ')</h5>';
            html += '<div class="d-flex flex-wrap gap-2 justify-content-center">';
            (grupo.turnos || []).forEach(function (t) {
                html += '<span class="badge bg-secondary fs-5 px-3 py-2">' + t.codigo + '</span>';
            });
            html += '</div></div>';
        });
        html += '</div>';
        colaBody.innerHTML = html;
    }

    function renderModulos() {
        if (!modulosGrid) return;

        if (state.modulos.length === 0) {
            modulosGrid.innerHTML = '';
            return;
        }

        let html = '';
        state.modulos.forEach(function (item) {
            const modulo = item.modulo || {};
            const ejecutivo = item.ejecutivo || {};
            const turno = item.turno_actual || {};

            const tieneTurno = turno && turno.codigo;
            const ticketCode = tieneTurno ? turno.codigo : '---';
            const estado = turno ? turno.estado : null;
            const ejecutivoNombre = ejecutivo.nombre || 'Sin asignar';

            let estadoLabel = 'Disponible';
            let estadoClass = 'bg-secondary';
            let ticketClass = 'vacio';

            if (estado === 'llamado') {
                estadoLabel = 'Llamando...';
                estadoClass = 'bg-warning text-dark';
                ticketClass = 'llamando';
            } else if (estado === 'en_atencion') {
                estadoLabel = 'En Atencion';
                estadoClass = 'bg-success';
                ticketClass = 'en-atencion';
            }

            html += '<div class="col-lg-4 col-md-6">';
            html += '<div class="card modulo-card" data-modulo-id="' + (modulo.id || 0) + '">';
            html += '<div class="card-header d-flex justify-content-between align-items-center">';
            html += '<h5 class="mb-0">' + (modulo.nombre || 'Modulo') + '</h5>';
            html += '<span class="badge estado-badge ' + estadoClass + '">' + estadoLabel + '</span>';
            html += '</div>';
            html += '<div class="card-body text-center">';
            html += '<p class="text-muted mb-2">' + ejecutivoNombre + '</p>';
            html += '<div class="ticket-display ' + ticketClass + '" id="ticket-' + (modulo.id || 0) + '">';
            html += ticketCode;
            html += '</div>';
            html += '</div>';
            html += '</div>';
            html += '</div>';
        });

        modulosGrid.innerHTML = html;
    }

    function renderOverlay() {
        if (!noTurnosOverlay) return;

        const totalCola = state.cola.reduce(function (sum, g) { return sum + (g.total || 0); }, 0);
        const hayModulosActivos = state.modulos.length > 0;
        const hayTurnosEnModulos = state.modulos.some(function (item) {
            return item.turno_actual && item.turno_actual.codigo;
        });

        if (totalCola === 0 && !hayModulosActivos) {
            noTurnosOverlay.classList.remove('d-none');
        } else {
            noTurnosOverlay.classList.add('d-none');
        }
    }

    function actualizarModulo(eventData) {
        const turno = eventData.turno || eventData;
        const moduloId = turno.modulo_id;

        const item = state.modulos.find(function (m) {
            return m.modulo && m.modulo.id === moduloId;
        });
        if (item) {
            item.turno_actual = turno;
        }
    }

    function connectSSE() {
        const eventSource = new EventSource('/api/turnos/eventos');

        eventSource.onmessage = function (event) {
            try {
                const parsed = JSON.parse(event.data);
                const type = parsed.type;
                const data = parsed.data;

                switch (type) {
                    case 'turno_creado':
                        console.log('[SSE] Turno creado:', data.turno ? data.turno.codigo : '');
                        loadInitialState();
                        break;
                    case 'turno_llamado':
                        console.log('[SSE] Turno llamado:', data.codigo);
                        actualizarModulo(data);
                        loadInitialState();
                        break;
                    case 'turno_atendido':
                        console.log('[SSE] Turno atendido:', data.codigo);
                        actualizarModulo(data);
                        loadInitialState();
                        break;
                    case 'turno_finalizado':
                        console.log('[SSE] Turno finalizado:', data.codigo);
                        loadInitialState();
                        break;
                    case 'ejecutivo_logout':
                        console.log('[SSE] Ejecutivo cerro sesion');
                        loadInitialState();
                        break;
                    default:
                        break;
                }
            } catch (err) {
                console.error('[SSE] Error al procesar evento:', err);
            }
        };

        eventSource.onerror = function () {
            console.error('[SSE] Error de conexion. Reintentando en 3s...');
            eventSource.close();
            setTimeout(connectSSE, 3000);
        };
    }

    document.addEventListener('DOMContentLoaded', function () {
        loadInitialState();
        connectSSE();
    });

})();