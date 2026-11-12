# Bitácora — Turnero

**Registro de decisiones, problemas y lecciones del desarrollo del Sistema de Gestión de Turnos.**

Versión: 1.0.0 | Última actualización: Noviembre 2026

---

## Índice

1. [Propósito](#propósito)
2. [Línea de tiempo](#línea-de-tiempo)
3. [Problemas encontrados y soluciones](#problemas-encontrados-y-soluciones)
4. [Enfoques descartados](#enfoques-descartados)
5. [Decisiones técnicas y su justificación](#decisiones-técnicas-y-su-justificación)
6. [Lecciones aprendidas](#lecciones-aprendidas)
7. [Deuda asumida conscientemente](#deuda-asumida-conscientemente)
8. [Cómo usar esta bitácora](#cómo-usar-esta-bitácora)

---

## Propósito

Esta bitácora existe para que la próxima persona no repita los mismos errores. No es un changelog: no lista cada commit, sino las decisiones que cambiaron el rumbo, los problemas que costaron tiempo y las alternativas que se evaluaron y se descartaron.

Criterio de honestidad: si algo se probó y falló, se registra; si algo se descartó por tiempo, también. Un proyecto de portfolio que solo muestra aciertos no enseña nada.

---

## Línea de tiempo

| Etapa | Qué se hizo | Resultado |
|---|---|---|
| 1. Análisis | Definición de las tres vistas, modelo de datos, API, estados y casos de prueba. | Alcance acotado: una sucursal, tres trámites, cuatro estados. |
| 2. Implementación base | Flask + SQLAlchemy, blueprints, servicios, templates y JavaScript vanilla. | Flujo completo kiosco → cola → ejecutivo → display. |
| 3. Tiempo real | Bus SSE en memoria y reconexión del display. | Actualización sin polling del cliente. |
| 4. Auditoría | Revisión estática de seguridad, estados y consistencia. | Nueve hallazgos corregidos antes de documentar. |
| 5. Documentación | README, manual del operador, guía técnica, referencias, diagramas y PDF. | Documentación de nivel portfolio. |
| 6. Publicación | Repositorio público, licencia MIT y limpieza de datos locales. | `wanderc137/turnero`. |

---

## Problemas encontrados y soluciones

### 1. El `qr_token` viajaba al display

**Síntoma:** el endpoint público `/api/turnos/display` devolvía el turno completo, incluido el token que sirve para iniciar la atención. Cualquiera con acceso a la API podía leerlo.

**Causa:** se reutilizaba `to_dict()` para todas las respuestas.

**Solución:** se creó `to_display_dict()`, que llama a `to_dict()` y elimina `qr_token`. El display y la cola pública lo usan; la consola autenticada sigue recibiendo el token.

**Lección:** una sola función de serialización no puede servir a públicos con permisos distintos. La regla "público ≠ autenticado" debe estar en el código, no en la disciplina del desarrollador.

**Pendiente:** los eventos SSE `turno_creado`, `turno_atendido` y `turno_finalizado` todavía emiten `turno.to_dict()`. Es la misma fuga por otro canal y está documentada como riesgo.

### 2. RUT validado solo en el navegador

**Síntoma:** el kiosco validaba el RUT, pero un `curl` con un RUT inválido creaba el turno igual.

**Causa:** la validación estaba en `kiosco.js`, no en el servicio.

**Solución:** `validar_rut()` en `services/turno_service.py` aplica el módulo 11 antes de crear el turno; la API responde `400` si falla. El cliente conserva la validación para dar feedback inmediato.

**Lección:** toda validación de cliente es UX; la validación de servidor es seguridad. Se necesitan ambas, no una.

### 3. Mutaciones sin protección CSRF

**Síntoma:** un POST desde otro origen podía crear turnos o cerrar sesión si el navegador tenía la cookie.

**Causa:** no había token CSRF ni verificación de origen.

**Solución:** `csrf_protected` exige `Content-Type: application/json`, `X-Requested-With: XMLHttpRequest` y, si están presentes, `Origin`/`Referer` coherentes con el host. Los tres frontends envían los headers.

**Limitación:** no es un token CSRF de un solo uso. Un atacante que pueda ejecutar JavaScript en el mismo origen ya tiene control; la protección cubre el escenario clásico de formulario cross-site.

### 4. Un ejecutivo podía llamar dos turnos

**Síntoma:** al pulsar dos veces "Llamar siguiente" se podían asignar dos turnos al mismo módulo.

**Causa:** `llamar_siguiente` no verificaba si el ejecutivo ya tenía un turno `llamado` o `en_atencion`.

**Solución:** se consulta el turno activo antes de asignar y se lanza `ValueError` con "Ya tienes un turno activo". La API lo traduce a `400`.

**Lección:** las reglas de negocio deben vivir en el servicio, no solo en la interfaz. El botón deshabilitado no es una garantía.

### 5. `SECRET_KEY` fija sin advertencia

**Síntoma:** la clave de desarrollo estaba en `config.py` y no había señal de que fuera insegura.

**Solución:** se lee de `SECRET_KEY`; si conserva el valor por defecto, se emite un `RuntimeWarning` al importar la configuración. Sigue siendo un default, pero ya no es silencioso.

**Pendiente:** en producción la variable debe ser obligatoria y el arranque debería fallar si falta.

### 6. El nombre del módulo no llegaba a la plantilla

**Síntoma:** la consola mostraba el módulo vacío o con `None`.

**Causa:** `Ejecutivo.to_dict()` no incluía `modulo_nombre` y la plantilla lo esperaba.

**Solución:** se agregó el campo calculado a la serialización, con `if self.modulo` para evitar errores cuando la relación es nula.

**Lección:** los contratos de serialización deben documentarse; un campo faltante en un diccionario es un bug silencioso en Jinja.

### 7. Trámites hardcodeados en el kiosco

**Síntoma:** agregar un trámite en la base no aparecía en el kiosco.

**Causa:** las tarjetas se generaban desde un objeto `TRAMITES` fijo en JavaScript.

**Solución:** `GET /api/tramites` alimenta las tarjetas; se conserva un fallback local con `A`, `B`, `C` para que el kiosco no quede inutilizable si la API falla.

**Trade-off:** el fallback puede mostrar trámites que ya no existen. Es preferible a una pantalla vacía, pero debe documentarse.

### 8. Errores 500 en HTML dentro de la API

**Síntoma:** un fallo interno en `/api/*` devolvía una página HTML, lo que rompía el `JSON.parse` del cliente.

**Solución:** `@app.errorhandler(500)` detecta el prefijo `/api/` y responde `{"error": "Error interno del servidor"}`; en las vistas normales renderiza `base.html` con un mensaje.

**Lección:** el contrato de errores forma parte de la API. Un 500 también debe ser JSON si el consumidor espera JSON.

### 9. Faltaba `X-Requested-With` en un frontend

**Síntoma:** una mutación funcionaba en un navegador y fallaba en otro; el servidor respondía `400`.

**Causa:** uno de los tres clientes no enviaba el header exigido por `csrf_protected`.

**Solución:** se agregó el header en `kiosco.js`, `executive.js` y el formulario de login. Se verificó con `curl` que sin header la respuesta fuera `400`.

**Lección:** si una protección se implementa en el servidor, hay que auditar **todos** los clientes, no solo el que se está probando.

### 10. Cámara bloqueada en la LAN

**Síntoma:** el escáner QR no encendía al abrir la consola desde `http://192.0.2.10:5000`.

**Causa:** `getUserMedia` exige contexto seguro; los navegadores solo lo permiten en `https://` o `localhost`.

**Solución:** se documentó el requisito y se recomendó HTTPS o probar en localhost. No se agregó un fallback de entrada manual de token.

**Lección:** una función que depende del navegador puede fallar por la URL, no por el código. El contexto de seguridad es parte de los requisitos.

### 11. El display mostraba módulos fantasma

**Síntoma:** un módulo seguía visible después de que el ejecutivo cerrara la pestaña.

**Causa:** `logged_in` es un estado persistido y solo se limpia con logout explícito; cerrar el navegador no ejecuta nada.

**Solución:** se documentó el uso obligatorio de "Cerrar sesión" y se agregó el evento `ejecutivo_logout` para que el display reaccione. No se implementó expiración por inactividad.

**Lección:** el estado de presencia necesita un heartbeat o un TTL. Un booleano en la base no representa "estoy conectado ahora".

### 12. Códigos de turno que colisionan

**Síntoma:** tras borrar turnos de prueba, el contador retrocedía y el `unique` de `codigo` rechazaba el nuevo turno.

**Causa:** `codigo = prefijo + (COUNT(tipo) + 1)`.

**Solución:** se documentó como limitación y se recomendó reiniciar la base de desarrollo. Para producción queda pendiente una secuencia por tipo.

**Lección:** los contadores derivados de `COUNT` no son estables si se borran filas. Un código correlativo necesita una fuente que no retroceda.

---

## Enfoques descartados

| Enfoque | Por qué se evaluó | Por qué se descartó |
|---|---|---|
| **WebSocket** | Bidireccional, estándar para tiempo real | El display solo recibe; SSE es más simple, viaja sobre HTTP y reconecta solo. |
| **React/Vue + bundler** | Componentes y estado | Tres pantallas pequeñas no justifican Node, build y despliegue adicional. |
| **PostgreSQL desde el día uno** | Concurrencia y robustez | Una sucursal no lo necesita; SQLite reduce la operación a un archivo. La migración queda abierta por `DATABASE_URL`. |
| **Redis para el bus SSE** | Escalar a varios workers | Agrega un servicio y complejidad; el despliegue actual usa un worker. |
| **Token JWT en localStorage** | Stateless | La sesión por cookie HttpOnly es más simple y no expone el token a JavaScript. |
| **Validar RUT solo en el cliente** | Menos código | Inseguro: cualquiera puede saltarse el navegador. |
| **Entrada manual del token QR** | Fallback si la cámara falla | Abre la puerta a suplantación; se prefirió documentar el requisito de cámara. |
| **Polling cada segundo** | Más simple que SSE | Carga innecesaria y latencia; SSE ya es nativo. |
| **Panel de administración completo** | Autogestión | Fuera del alcance; el seed y SQL cubren la demo. |
| **Multi-sucursal** | Producto más ambicioso | Duplica el modelo y las pruebas; se dejó como extensión. |
| **Docker** | Onboarding reproducible | El proyecto se instala con venv en dos comandos; Docker se documenta como mejora. |

---

## Decisiones técnicas y su justificación

### SQLite en lugar de un servidor de base de datos

**Contexto:** una sucursal, pocos turnos por día, un solo servidor.

**Decisión:** SQLite con Flask-SQLAlchemy.

**Por qué:** cero administración, archivo único, backups triviales, transacciones ACID. La URI es configurable, así que migrar a PostgreSQL no exige reescribir los modelos.

**Costo:** un escritor a la vez y carrera lógica en `llamar_siguiente`. Se documentó y se propuso mitigación.

### SSE en lugar de WebSocket

**Contexto:** el display solo necesita recibir cambios.

**Decisión:** SSE con un bus de colas en memoria.

**Por qué:** menos piezas, reconexión automática del navegador, compatible con proxies HTTP si se configura `proxy_buffering off`.

**Costo:** unidireccional y atado al proceso. Un worker o un bus externo si se escala.

### Aplicación factory y blueprints

**Contexto:** varias interfaces y una API en el mismo proyecto.

**Decisión:** `create_app()` y un blueprint por interfaz.

**Por qué:** permite instanciar la app con otra configuración (tests, producción), evita imports circulares y separa responsabilidades.

**Costo:** un poco más de indirección para quien lee por primera vez.

### Servicios separados de las rutas

**Contexto:** reglas de negocio reutilizables y testeables.

**Decisión:** `auth_service` y `turno_service` concentran la lógica; las rutas validan entrada y traducen errores.

**Por qué:** `turno_service` no depende de `request` (salvo `auth_service` por la sesión) y se puede probar con una base en memoria.

**Costo:** las rutas y los servicios deben mantener contratos claros; se documentaron en `developer.md`.

### JavaScript vanilla en lugar de un framework

**Contexto:** tres pantallas con interactividad acotada.

**Decisión:** IIFEs, `fetch` y `EventSource`.

**Por qué:** sin build, sin dependencias de Node, carga inmediata y depuración directa en el navegador.

**Costo:** código repetido y manejo manual del DOM; aceptable para el tamaño actual.

### bcrypt en lugar de SHA-256

**Contexto:** almacenamiento de contraseñas.

**Decisión:** bcrypt con salt por usuario.

**Por qué:** es lento por diseño y resistente a fuerza bruta con hardware; SHA-256 es rápido y no debe usarse para passwords.

**Costo:** el login tiene un costo computacional; es el comportamiento deseado.

### Seed idempotente

**Contexto:** demostración sin panel de administración.

**Decisión:** crear datos solo si la tabla de ejecutivos está vacía.

**Por qué:** el primer arranque funciona sin pasos manuales y reiniciar no duplica usuarios.

**Costo:** si se borra un usuario, el seed no lo recrea; la gestión posterior es manual.

### Librerías QR locales, Bootstrap por CDN

**Contexto:** el kiosco y la consola deben funcionar en una LAN, no necesariamente con internet.

**Decisión:** vendorizar `qrcodejs` y `html5-qrcode`; dejar Bootstrap en CDN.

**Por qué:** las funciones críticas (generar y escanear QR) no dependen de la red; Bootstrap es solo presentación y se puede localizar después.

**Costo:** sin internet se pierde el estilo. Se documentó cómo servirlo localmente.

---

## Lecciones aprendidas

1. **Serializar es una decisión de seguridad.** Un `to_dict()` reutilizado filtra datos. Separar público y autenticado desde el primer día evita parches.
2. **El estado persistido no es presencia.** `logged_in` en la base no equivale a "conectado"; hace falta un heartbeat o un TTL.
3. **Las carreras existen aunque haya un solo proceso.** `SELECT` + `UPDATE` no es atómico; el lock de SQLite protege la escritura, no la decisión.
4. **Los contadores derivados mienten.** `COUNT + 1` retrocede al borrar. Un código correlativo necesita una secuencia o un `MAX`.
5. **La cámara depende de la URL.** `getUserMedia` falla en HTTP sobre IP; el requisito es HTTPS o localhost, no un permiso.
6. **CSRF no es solo un token.** Verificar JSON, header y origen cubre el caso cross-site sin sesiones stateful complejas; hay que aplicar el mismo contrato a todos los clientes.
7. **Los errores también son contrato.** Un 500 en HTML rompe un cliente que espera JSON.
8. **El fallback mejora la disponibilidad y oculta la verdad.** El kiosco con trámites hardcodeados evita una pantalla vacía, pero puede mostrar datos obsoletos.
9. **Documentar los límites es parte del producto.** Un README que dice "prototipo" y enumera lo que falta genera más confianza que uno que promete producción.
10. **Un solo worker es una decisión arquitectónica.** El bus SSE en memoria obliga a desplegar un worker; ignorarlo produce bugs intermitentes difíciles de diagnosticar.

---

## Deuda asumida conscientemente

| Deuda | Por qué se aceptó | Cuándo pagarla |
|---|---|---|
| Sin tests automatizados | El alcance era demostrar el flujo; la matriz manual cubre los casos. | Antes de un uso real o de aceptar contribuciones. |
| Sin panel de administración | Seed + SQL son suficientes para la demo. | Cuando haya usuarios no técnicos. |
| Sin expiración de sesión ni de token QR | Simplifica el prototipo. | Antes de exponer el sistema a clientes reales. |
| Sin rate limiting | La red es local y controlada. | Al conectar a internet o a una red compartida. |
| Sin multi-sucursal | Una instancia por sucursal es viable. | Si se centraliza la operación. |
| Sin audio en el display | El display visual cumple. | Si la sala es ruidosa o hay accesibilidad visual. |
| Sin migraciones formales | Una sola migración manual (`logged_in`). | Al cambiar el esquema con datos en producción. |

---

## Cómo usar esta bitácora

- **Antes de cambiar el modelo:** revisa las lecciones 1, 2 y 4.
- **Antes de escalar el despliegue:** revisa la decisión de SSE y la deuda del bus en memoria.
- **Antes de agregar un endpoint público:** revisa el problema 1 y el contrato de serialización.
- **Antes de tocar la cámara o el QR:** revisa el problema 10 y el requisito de contexto seguro.
- **Antes de prometer producción:** revisa la deuda asumida y la sección de limitaciones del README.

Si agregas una decisión relevante, registra: contexto, alternativas, decisión, costo y fecha. La bitácora se lee mejor como una conversación con quien construyó el sistema que como un informe.

---

<div align="center">

**Turnero** — Bitácora v1.0.0

[Volver al README](../README.md) · [Referencias](REFERENCES.md) · [Guía del desarrollador](developer.md)

</div>
