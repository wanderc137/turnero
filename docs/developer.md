# Developer Guide - Sistema Turnero

Guia tecnica para desarrolladores que deseen modificar, extender o desplegar el Sistema de Gestion de Turnos.

---

## Indice

1. [Arquitectura General](#arquitectura-general)
2. [Stack Tecnologico](#stack-tecnologico)
3. [Estructura del Proyecto](#estructura-del-proyecto)
4. [Modelo de Datos](#modelo-de-datos)
5. [API REST Completa](#api-rest-completa)
6. [Flujo de Estados de Turno](#flujo-de-estados-de-turno)
7. [Sistema de Eventos SSE](#sistema-de-eventos-sse)
8. [Concurrencia y Transacciones](#concurrencia-y-transacciones)
9. [Contratos de los Servicios](#contratos-de-los-servicios)
10. [SSE en Multiples Workers](#sse-en-multiples-workers)
11. [Seguridad](#seguridad)
12. [Personalizacion](#personalizacion)
13. [Guia de Deploy en Produccion](#guia-de-deploy-en-produccion)
14. [Agregar Nuevos Tipos de Tramite](#agregar-nuevos-tipos-de-tramite)
15. [Explicacion del Codigo Fuente](#explicacion-del-codigo-fuente)
16. [Guia de Modificacion y Extension](#guia-de-modificacion-y-extension)
17. [Pruebas](#pruebas)
18. [Deuda Tecnica](#deuda-tecnica)
19. [Contribucion](#contribucion)

---

## Arquitectura General

Turnero es una aplicacion web monolitica construida con Flask que sirve tres interfaces de usuario y una API REST, todo desde un unico proceso servidor.

### Diagrama de Arquitectura

```
                         +-------------------+
                         |    Navegador      |
                         |   (Cliente Web)   |
                         +---------+---------+
                                   |
                    +--------------+--------------+
                    |              |              |
              +-----v-----+ +-----v-----+ +-----v-----+
              |  Display  | |  Kiosco   | | Ejecutivo |
              |  (/ + SSE)| |  (/kiosco)| |(/ejecutivo)|
              +-----------+ +-----------+ +------+----+
                                                  |
                    +-----------------------------+
                    |           HTTP/JSON         |
                    v                             v
          +------------------+          +------------------+
          |  Flask Routes    |          |  Flask Routes    |
          |  (display,       |          |  (api.py)        |
          |   kiosco,        |          |  REST + SSE      |
          |   executive)     |          +--------+---------+
          +--------+---------+                   |
                   |                             |
                   v                             v
          +------------------+          +------------------+
          |  auth_service    |          |  turno_service   |
          |  (sesiones,      |          |  (logica de      |
          |   bcrypt)        |          |   negocio)       |
          +--------+---------+          +--------+---------+
                   |                             |
                   +------------+----------------+
                                |
                                v
                   +---------------------------+
                   |     SQLAlchemy ORM        |
                   |     (models.py)           |
                   +-------------+-------------+
                                 |
                                 v
                   +---------------------------+
                   |      SQLite Database      |
                   |    (instance/turnero.db)  |
                   +---------------------------+
```

### Flujo de una Solicitud Tipica

1. El cliente (navegador) realiza una peticion HTTP a una ruta de Flask.
2. Flask enruta la peticion al blueprint correspondiente.
3. El blueprint puede:
   - Renderizar un template HTML (paginas completas).
   - Llamar a un servicio para procesar la logica de negocio.
   - Retornar JSON (API REST).
4. Los servicios (`services/`) interactuan con la base de datos a traves de SQLAlchemy.
5. Los servicios de API pueden emitir eventos SSE a los clientes conectados.
6. La respuesta se envia de vuelta al cliente.

---

## Stack Tecnologico

| Componente | Tecnologia | Proposito |
|------------|-----------|-----------|
| Backend | Python 3.10+ / Flask 3.1.x | Servidor web y API |
| Base de datos | SQLite 3 via Flask-SQLAlchemy 3.1.x | Persistencia de datos |
| ORM | SQLAlchemy (integrado en Flask-SQLAlchemy) | Mapeo objeto-relacional |
| Autenticacion | Flask session + bcrypt 4.x | Login de ejecutivos |
| Tiempo real | Server-Sent Events (SSE) nativo | Actualizacion display |
| Frontend | HTML5, CSS3, JavaScript vanilla | Interfaces de usuario |
| CSS Framework | Bootstrap 5.3 (CDN jsDelivr) | Estilos y componentes UI |
| QR Generation | qrcodejs (local, `static/js/qrcode.min.js`) | Generacion QR en kiosco |
| QR Scanning | html5-qrcode (local, `static/js/html5-qrcode.min.js`) | Escaneo QR en ejecutivo |

---

## Estructura del Proyecto

```
proyectos/turnero/
|
+-- app.py                   # Punto de entrada. Factory create_app(), inicializa BD y blueprints.
|
+-- config.py                # Clase Config con SECRET_KEY, DATABASE_URL, etc.
|
+-- models.py                # Modelos SQLAlchemy: Modulo, Ejecutivo, TipoTramite, Turno.
|
+-- seed.py                  # Datos iniciales: 3 modulos, 3 ejecutivos, 3 tipos de tramite.
|
+-- requirements.txt         # Dependencias Python (pip install -r requirements.txt).
|
+-- instance/
|   +-- turnero.db           # Base de datos SQLite (se crea en el primer inicio).
|
+-- routes/
|   +-- __init__.py          # Docstring del paquete.
|   +-- display.py           # Blueprint "display": GET / -> renderiza display.html.
|   +-- kiosco.py            # Blueprint "kiosco": GET /kiosco -> renderiza kiosco.html.
|   +-- executive.py         # Blueprint "executive": GET /ejecutivo, GET /login.
|   +-- api.py               # Blueprint "api": API REST + SSE (autenticacion, turnos, etc.).
|
+-- services/
|   +-- __init__.py          # Docstring del paquete.
|   +-- auth_service.py      # Login, logout, hash/check password, decoradores (@login_required, @csrf_protected).
|   +-- turno_service.py     # Logica de turnos: solicitar, llamar, iniciar, finalizar, cola, display.
|
+-- templates/
|   +-- base.html            # Layout base con Bootstrap 5 CDN y bloques para contenido/scripts.
|   +-- display.html         # Pantalla de visualizacion publica (hereda base.html).
|   +-- executive.html       # Consola del ejecutivo con paneles de atencion, QR, cola.
|   +-- kiosco.html          # Kiosco cliente con 3 pasos (seleccion, RUT, ticket+QR).
|   +-- login.html           # Pagina login con formulario y fetch a /api/auth/login.
|
+-- static/
|   +-- css/
|   |   +-- styles.css       # Estilos CSS: tema azul corporativo, animaciones, responsive.
|   +-- js/
|   |   +-- display.js       # Logica display: SSE, renderizado modulos, animaciones.
|   |   +-- executive.js     # Logica ejecutivo: estado, llamado, QR, atencion, cola.
|   |   +-- kiosco.js        # Logica kiosco: tramites, RUT, solicitud, QR.
|   +-- img/
|       +-- logo.svg         # Logo corporativo (placeholder, personalizable).
|
+-- docs/
|   +-- datasheet.md         # Documentacion tecnica de usuario.
|   +-- developer.md         # Guia para desarrolladores (este archivo).
|
+-- README.md                # Documentacion completa del proyecto.
```

---

## Modelo de Datos

### Diagrama Entidad-Relacion

```
+------------------+          +------------------+          +------------------+
|     Modulo       |          |    Ejecutivo     |          |   TipoTramite    |
+------------------+          +------------------+          +------------------+
| PK id: Integer   |<---------| FK modulo_id     |          | PK id: Integer   |
| nombre: String   |   1:N    | PK id: Integer   |          | codigo: String(1)|
| activo: Boolean  |          | username: String  |          | nombre: String   |
+------------------+          | password_hash: Str|          | prefijo: String  |
                              | nombre: String   |          +------------------+
                              | activo: Boolean  |                |
                              +------------------+                | 1:N
                                    |                             |
                                    | 1:N                         |
                                    v                             v
                              +--------------------------------------------------+
                              |                    Turno                         |
                              +--------------------------------------------------+
                              | PK id: Integer                                   |
                              | codigo: String(10) UNIQUE                        |
                              | FK tipo_tramite_id: Integer                      |
                              | rut_cliente: String(20)                          |
                              | estado: String(20) [esperando|llamado|           |
                              |                       en_atencion|completado]    |
                              | FK modulo_id: Integer (nullable)                 |
                              | FK ejecutivo_id: Integer (nullable)              |
                              | fecha_creacion: DateTime                          |
                              | fecha_llamado: DateTime (nullable)                |
                              | fecha_inicio_atencion: DateTime (nullable)        |
                              | fecha_completado: DateTime (nullable)             |
                              | tipo_atencion: String(50) (nullable)              |
                              | comentarios: Text (nullable)                      |
                              | qr_token: String(64) UNIQUE                      |
                              +--------------------------------------------------+
```

### Descripcion de Tablas

#### Tabla: `modulo`

Representa un modulo de atencion fisico en la sucursal.

| Columna | Tipo | Restricciones | Descripcion |
|---------|------|---------------|-------------|
| `id` | Integer | PK, autoincrement | Identificador unico |
| `nombre` | String(100) | NOT NULL | Nombre del modulo (ej: "Modulo 1") |
| `activo` | Boolean | NOT NULL, default=True | Indica si el modulo esta en servicio |

Relaciones:
- Un modulo tiene muchos ejecutivos (`Ejecutivo.modulo_id`).
- Un modulo tiene muchos turnos (`Turno.modulo_id`).

#### Tabla: `ejecutivo`

Representa un ejecutivo que atiende turnos en un modulo.

| Columna | Tipo | Restricciones | Descripcion |
|---------|------|---------------|-------------|
| `id` | Integer | PK, autoincrement | Identificador unico |
| `username` | String(50) | UNIQUE, NOT NULL | Nombre de usuario para login |
| `password_hash` | String(256) | NOT NULL | Hash bcrypt de la contrasena |
| `nombre` | String(150) | NOT NULL | Nombre completo del ejecutivo |
| `modulo_id` | Integer | FK -> modulo.id, NOT NULL | Modulo asignado |
| `activo` | Boolean | NOT NULL, default=True | Indica si el ejecutivo esta activo |

Relaciones:
- Muchos ejecutivos pertenecen a un modulo (`Modulo.id`).
- Un ejecutivo tiene muchos turnos (`Turno.ejecutivo_id`).

#### Tabla: `tipo_tramite`

Representa un tipo de tramite ofrecido por la sucursal.

| Columna | Tipo | Restricciones | Descripcion |
|---------|------|---------------|-------------|
| `id` | Integer | PK, autoincrement | Identificador unico |
| `codigo` | String(1) | UNIQUE, NOT NULL | Codigo corto (A, B, C) |
| `nombre` | String(100) | NOT NULL | Nombre del tramite |
| `prefijo` | String(1) | NOT NULL | Prefijo para generar codigos de ticket |

Relaciones:
- Un tipo de tramite tiene muchos turnos (`Turno.tipo_tramite_id`).

#### Tabla: `turno`

Representa un ticket (turno) generado por el kiosco.

| Columna | Tipo | Restricciones | Descripcion |
|---------|------|---------------|-------------|
| `id` | Integer | PK, autoincrement | Identificador unico |
| `codigo` | String(10) | UNIQUE, NOT NULL | Codigo del ticket (ej: "B43") |
| `tipo_tramite_id` | Integer | FK -> tipo_tramite.id, NOT NULL | Tipo de tramite solicitado |
| `rut_cliente` | String(20) | NOT NULL | RUT del cliente |
| `estado` | String(20) | NOT NULL, default='esperando', indexed | Estado actual del turno |
| `modulo_id` | Integer | FK -> modulo.id, nullable | Modulo asignado (al llamar) |
| `ejecutivo_id` | Integer | FK -> ejecutivo.id, nullable | Ejecutivo que atiende |
| `fecha_creacion` | DateTime | NOT NULL | Momento de creacion del ticket |
| `fecha_llamado` | DateTime | nullable | Momento en que fue llamado |
| `fecha_inicio_atencion` | DateTime | nullable | Momento en que empezo la atencion |
| `fecha_completado` | DateTime | nullable | Momento en que se finalizo |
| `tipo_atencion` | String(50) | nullable | Tipo de atencion (Consulta, Contratacion, etc.) |
| `comentarios` | Text | nullable | Notas de la atencion |
| `qr_token` | String(64) | UNIQUE, NOT NULL | Token UUID unico codificado en QR |

Relaciones:
- Muchos turnos pertenecen a un tipo de tramite (`TipoTramite.id`).
- Muchos turnos son atendidos en un modulo (`Modulo.id`).
- Muchos turnos son atendidos por un ejecutivo (`Ejecutivo.id`).

### Metodos del Modelo

#### `Turno.to_dict()`
Retorna un diccionario completo del turno, **incluyendo** `qr_token`. Usado para respuestas internas (ejecutivo, kiosco).

#### `Turno.to_display_dict()`
Retorna un diccionario del turno **excluyendo** `qr_token`. Usado para endpoints publicos (pantalla display, cola publica).

#### `Modulo.to_dict()`, `Ejecutivo.to_dict()`, `TipoTramite.to_dict()`
Retornan diccionarios con los campos de cada modelo.

---

## API REST Completa

### Convenciones

- **Base URL**: `http://<servidor>:<puerto>/api`
- **Formato**: JSON (request y response).
- **Autenticacion**: Sesion Flask via cookie. Algunos endpoints requieren `@api_login_required`.
- **CSRF**: Endpoints POST requieren headers `Content-Type: application/json` y `X-Requested-With: XMLHttpRequest`.
- **Errores**: Respuesta con codigo HTTP 4xx/5xx y body `{"error": "mensaje"}`.

### Endpoints

#### 1. POST `/api/auth/login`

Autentica un ejecutivo y crea una sesion.

**Request:**
```json
{
    "username": "carlos",
    "password": "carlos123"
}
```

**Response (200):**
```json
{
    "mensaje": "Login exitoso",
    "ejecutivo": {
        "id": 1,
        "username": "carlos",
        "nombre": "Carlos Munoz",
        "modulo_id": 1,
        "modulo_nombre": "Modulo 1",
        "activo": true
    }
}
```

**Response (401):**
```json
{
    "error": "Usuario o contrasena incorrectos"
}
```

---

#### 2. POST `/api/auth/logout`

Cierra la sesion del ejecutivo autenticado.

**Request:** (body vacio)

**Response (200):**
```json
{
    "mensaje": "Sesion cerrada"
}
```

---

#### 3. GET `/api/turnos/display`

Retorna el estado actual de todos los modulos para la pantalla display.

**Response (200):**
```json
{
    "modulos": [
        {
            "modulo": {
                "id": 1,
                "nombre": "Modulo 1",
                "activo": true
            },
            "ejecutivo": {
                "id": 1,
                "username": "carlos",
                "nombre": "Carlos Munoz",
                "modulo_id": 1,
                "modulo_nombre": "Modulo 1",
                "activo": true
            },
            "turno_actual": {
                "id": 5,
                "codigo": "B43",
                "tipo_tramite_id": 2,
                "tipo_tramite": "Consultas Generales",
                "tipo_tramite_codigo": "B",
                "rut_cliente": "12345678-5",
                "estado": "llamado",
                "modulo_id": 1,
                "modulo_nombre": "Modulo 1",
                "ejecutivo_id": 1,
                "ejecutivo_nombre": "Carlos Munoz",
                "fecha_creacion": "2025-01-15T10:30:00+00:00",
                "fecha_llamado": "2025-01-15T10:35:00+00:00",
                "fecha_inicio_atencion": null,
                "fecha_completado": null,
                "tipo_atencion": null,
                "comentarios": null
            }
        },
        {
            "modulo": { ... },
            "ejecutivo": { ... },
            "turno_actual": null
        }
    ]
}
```

> Nota: `turno_actual` no incluye el campo `qr_token` (usando `to_display_dict()`).

---

#### 4. GET `/api/turnos/eventos`

Conexion SSE (Server-Sent Events) para actualizaciones en tiempo real.

**Response:** `text/event-stream`

**Formato de eventos:**
```
data: {"type": "turno_llamado", "data": {"codigo": "B43", "modulo_id": 1, ...}}

data: {"type": "turno_atendido", "data": {"codigo": "B43", "modulo_id": 1, ...}}

data: {"type": "turno_finalizado", "data": {"codigo": "B43", "modulo_id": 1, ...}}
```

**Heartbeat:** Cada 30 segundos se envia un comentario SSE (`: heartbeat\n\n`) para mantener la conexion activa.

---

#### 5. POST `/api/turnos/solicitar`

Crea un nuevo turno desde el kiosco.

**Request:**
```json
{
    "tipo_tramite_id": 2,
    "rut": "12345678-5"
}
```

**Response (201):**
```json
{
    "mensaje": "Turno creado exitosamente",
    "turno": {
        "id": 6,
        "codigo": "B44",
        "tipo_tramite_id": 2,
        "tipo_tramite": "Consultas Generales",
        "tipo_tramite_codigo": "B",
        "rut_cliente": "12345678-5",
        "estado": "esperando",
        "modulo_id": null,
        "modulo_nombre": null,
        "ejecutivo_id": null,
        "ejecutivo_nombre": null,
        "fecha_creacion": "2025-01-15T10:40:00+00:00",
        "fecha_llamado": null,
        "fecha_inicio_atencion": null,
        "fecha_completado": null,
        "tipo_atencion": null,
        "comentarios": null,
        "qr_token": "a1b2c3d4e5f6..."
    }
}
```

**Response (400 - RUT invalido):**
```json
{
    "error": "RUT invalido"
}
```

---

#### 6. GET `/api/ejecutivo/siguiente`

Llama al siguiente turno en espera para el ejecutivo autenticado. Requiere autenticacion.

**Response (200 - con turno):**
```json
{
    "mensaje": "Turno llamado exitosamente",
    "turno": {
        "id": 5,
        "codigo": "B43",
        "estado": "llamado",
        "modulo_id": 1,
        "modulo_nombre": "Modulo 1",
        "ejecutivo_id": 1,
        "ejecutivo_nombre": "Carlos Munoz",
        ...
    }
}
```

**Response (200 - sin turnos):**
```json
{
    "mensaje": "No hay turnos en espera",
    "turno": null
}
```

**Response (400 - ya tiene turno activo):**
```json
{
    "error": "Ya tienes un turno activo. Finaliza la atencion actual primero."
}
```

---

#### 7. POST `/api/ejecutivo/iniciar-atencion`

Inicia la atencion de un turno escaneando su QR. Requiere autenticacion.

**Request:**
```json
{
    "qr_token": "a1b2c3d4e5f6..."
}
```

**Response (200):**
```json
{
    "mensaje": "Atencion iniciada",
    "turno": {
        "id": 5,
        "codigo": "B43",
        "estado": "en_atencion",
        ...
    }
}
```

**Response (400):**
```json
{
    "error": "El turno B43 no esta en estado 'llamado' (actual: esperando)"
}
```

---

#### 8. POST `/api/ejecutivo/finalizar-atencion`

Finaliza la atencion actual y llama al siguiente turno automaticamente. Requiere autenticacion.

**Request:**
```json
{
    "tipo_atencion": "Consulta",
    "comentarios": "Cliente satisfecho con la atencion"
}
```

**Response (200 - con siguiente turno):**
```json
{
    "mensaje": "Atencion finalizada",
    "turno_completado": {
        "id": 5,
        "codigo": "B43",
        "estado": "completado",
        ...
    },
    "turno_siguiente": {
        "id": 6,
        "codigo": "B44",
        "estado": "llamado",
        ...
    }
}
```

**Response (200 - sin siguiente turno):**
```json
{
    "mensaje": "Atencion finalizada",
    "turno_completado": { ... },
    "turno_siguiente": null
}
```

---

#### 9. GET `/api/ejecutivo/cola`

Retorna la cola de turnos en espera agrupados por tipo de tramite. Requiere autenticacion.

**Response (200):**
```json
{
    "cola": [
        {
            "tipo_tramite_id": 1,
            "tipo_tramite": "Creditos",
            "codigo": "A",
            "total": 3,
            "turnos": [
                { "id": 10, "codigo": "A5", ... },
                { "id": 11, "codigo": "A6", ... },
                { "id": 12, "codigo": "A7", ... }
            ]
        },
        {
            "tipo_tramite_id": 2,
            "tipo_tramite": "Consultas Generales",
            "codigo": "B",
            "total": 1,
            "turnos": [
                { "id": 13, "codigo": "B44", ... }
            ]
        }
    ]
}
```

---

#### 10. GET `/api/ejecutivo/estado`

Retorna el estado actual del ejecutivo autenticado y su turno activo. Requiere autenticacion.

**Response (200 - sin turno activo):**
```json
{
    "ejecutivo": {
        "id": 1,
        "nombre": "Carlos Munoz",
        "modulo_id": 1,
        "modulo_nombre": "Modulo 1",
        ...
    },
    "turno_activo": null
}
```

**Response (200 - con turno activo):**
```json
{
    "ejecutivo": { ... },
    "turno_activo": {
        "id": 5,
        "codigo": "B43",
        "estado": "llamado",
        ...
    }
}
```

---

#### 11. GET `/api/tramites`

Retorna la lista de tipos de tramite disponibles.

**Response (200):**
```json
{
    "tramites": [
        { "id": 1, "codigo": "A", "nombre": "Creditos", "prefijo": "A" },
        { "id": 2, "codigo": "B", "nombre": "Consultas Generales", "prefijo": "B" },
        { "id": 3, "codigo": "C", "nombre": "Retiro de Documentos", "prefijo": "C" }
    ]
}
```

---

#### 12. GET `/api/modulos`

Retorna la lista de modulos activos.

**Response (200):**
```json
{
    "modulos": [
        { "id": 1, "nombre": "Modulo 1", "activo": true },
        { "id": 2, "nombre": "Modulo 2", "activo": true },
        { "id": 3, "nombre": "Modulo 3", "activo": true }
    ]
}
```

---

## Flujo de Estados de Turno

### Diagrama de Estados

```
                  +-----------+
                  | Cliente   |
                  | solicita  |
                  +-----+-----+
                        |
                        v
                 +-------------+
                 |  esperando  |
                 | (en cola)   |
                 +------+------+
                        |
                +-------v-------+
                | Ejecutivo     |
                | llama turno   |
                +-------+-------+
                        |
                        v
                  +-----------+
                  |  llamado  |<---------+
                  | (asignado |          |
                  |  a modulo)|          |
                  +-----+-----+          |
                        |                |
                +-------v-------+        |
                | Cliente       |        |
                | presenta QR   |        |
                +-------+-------+        |
                        |                |
                        v                |
                 +-------------+         |
                 | en_atencion |         |
                 | (atendiendo)|         |
                 +------+------+         |
                        |                |
                +-------v-------+        |
                | Ejecutivo     |        |
                | finaliza      +--------+
                +-------+-------+
                        |
                        v
                 +-------------+
                 | completado  |
                 | (finalizado)|
                 +-------------+
```

### Transiciones

| Estado Inicial | Accion | Estado Final | Quien Ejecuta |
|----------------|--------|--------------|---------------|
| - (nuevo) | Solicitar turno | `esperando` | Cliente (kiosco) |
| `esperando` | Llamar siguiente | `llamado` | Ejecutivo (sistema) |
| `llamado` | Escanear QR | `en_atencion` | Ejecutivo (sistema) |
| `en_atencion` | Finalizar atencion | `completado` | Ejecutivo (sistema) |
| `completado` | (Llamar siguiente automatico) | `llamado` | Sistema |

### Reglas de Negocio

1. Un turno solo puede avanzar en un sentido: `esperando -> llamado -> en_atencion -> completado`.
2. No se puede saltar estados.
3. Un ejecutivo solo puede tener UN turno activo (en estado `llamado` o `en_atencion`) a la vez.
4. Al finalizar un turno, el sistema llama automaticamente al siguiente turno en espera.
5. Un turno solo puede ser atendido por el ejecutivo que lo llamo.
6. La cola es FIFO (First In, First Out): el turno mas antiguo se atiende primero.

---

## Sistema de Eventos SSE

### Descripcion

El sistema utiliza Server-Sent Events (SSE) para enviar actualizaciones en tiempo real desde el servidor a la pantalla display. SSE es una tecnologia web estandar que permite al servidor enviar datos al cliente a traves de una conexion HTTP persistente.

### Implementacion

**Servidor** (`routes/api.py`):

```python
# Colas de mensajes por cliente
_event_listeners: list[queue.Queue] = []
_listeners_lock = threading.Lock()

def broadcast_event(event_type: str, data: dict) -> None:
    """Envia un evento SSE a todos los clientes conectados."""
    payload = json.dumps({"type": event_type, "data": data})
    with _listeners_lock:
        for q in _event_listeners:
            try:
                q.put_nowait(payload)
            except queue.Full:
                # Eliminar listeners muertos
                pass
```

**Endpoint SSE** (`GET /api/turnos/eventos`):

```python
def event_stream():
    q = register_listener()
    try:
        last_heartbeat = time.time()
        while True:
            try:
                payload = q.get(timeout=5)
                yield f"data: {payload}\n\n"
            except queue.Empty:
                if time.time() - last_heartbeat >= 30:
                    yield f": heartbeat\n\n"
                    last_heartbeat = time.time()
                continue
    except GeneratorExit:
        pass
    finally:
        unregister_listener(q)
```

**Cliente** (`static/js/display.js`):

```javascript
function connectSSE() {
    const eventSource = new EventSource('/api/turnos/eventos');
    eventSource.onmessage = function (event) {
        const parsed = JSON.parse(event.data);
        switch (parsed.type) {
            case 'turno_llamado':
                actualizarModulo(parsed.data);
                break;
            case 'turno_atendido':
                actualizarModulo(parsed.data);
                break;
            case 'turno_finalizado':
                loadInitialState();  // Recargar estado completo
                break;
        }
    };
    eventSource.onerror = function () {
        eventSource.close();
        setTimeout(connectSSE, 3000);  // Reintentar en 3 segundos
    };
}
```

### Tipos de Eventos

| Tipo | Descripcion | Disparado por | Payload |
|------|-------------|---------------|---------|
| `turno_creado` | Se creo un turno nuevo | `POST /api/turnos/solicitar` | `{ turno }` (incluye `qr_token`) |
| `turno_llamado` | Un turno ha sido llamado | `GET /api/ejecutivo/siguiente` o `POST /api/ejecutivo/finalizar-atencion` (siguiente turno) | `{ codigo, modulo_id, modulo_nombre, ejecutivo, turno }` |
| `turno_atendido` | Un turno ha comenzado a ser atendido | `POST /api/ejecutivo/iniciar-atencion` | `{ codigo, modulo_id, turno }` |
| `turno_finalizado` | Un turno ha sido completado | `POST /api/ejecutivo/finalizar-atencion` | `{ codigo, modulo_id, turno }` |
| `ejecutivo_logout` | Un ejecutivo cerro sesion | `POST /api/auth/logout` | `{ ejecutivo_id }` |

### Heartbeat

Para mantener la conexion activa (evitar timeouts de proxies/balanceadores), el servidor envia un comentario SSE (`: heartbeat\n\n`) cada 30 segundos si no ha habido eventos. Los comentarios SSE son ignorados por el API `EventSource` del navegador.

### Reconexion

Si la conexion SSE se pierde, el cliente:
1. Cierra la conexion actual.
2. Espera 3 segundos.
3. Intenta reconectar.
4. Al reconectar, carga el estado completo via `GET /api/turnos/display` para sincronizarse.

---

## Concurrencia y Transacciones

El sistema es de un solo proceso y SQLite, pero eso no elimina las carreras lógicas. Esta sección documenta las que existen y cómo mitigarlas.

### Escrituras serializadas, decisiones no

SQLite permite un solo escritor a la vez. Flask-SQLAlchemy abre una transacción por request y hace `commit` al final; si dos requests escriben a la vez, uno espera. Eso protege la integridad física, **no** la secuencia lógica:

```python
# services/turno_service.py — llamar_siguiente (simplificado)
turno = Turno.query.filter_by(estado="esperando") \
                   .order_by(Turno.fecha_creacion.asc()).first()
if turno:
    turno.estado = "llamado"
    turno.ejecutivo_id = ejecutivo_id
    db.session.commit()
```

Dos ejecutivos pueden ejecutar el `SELECT` antes de que el primero haga `commit`; ambos ven el mismo turno y el segundo `UPDATE` pisa al primero. El turno queda asignado a uno, pero el otro recibe una respuesta exitosa con el mismo código. No hay `SELECT ... FOR UPDATE` (SQLite no lo soporta) ni una restricción que impida dos turnos activos por ejecutivo.

**Mitigaciones, de menor a mayor esfuerzo:**

1. **Lock de aplicación:** un `threading.Lock` alrededor de `llamar_siguiente`. Funciona con un worker y un proceso, que es el despliegue actual.
2. **Transacción inmediata:** `BEGIN IMMEDIATE` para tomar el lock de escritura antes de leer. SQLAlchemy permite `with db.engine.begin()` o ejecutar `BEGIN IMMEDIATE` explícito.
3. **Índice único parcial:** impedir más de un turno activo por ejecutivo a nivel de base.
4. **Reintento optimista:** `UPDATE ... WHERE id = ? AND estado = 'esperando'` y verificar `rowcount == 1`; si es 0, reintentar con el siguiente.

La opción 4 es la más portable y la recomendada si se migra a PostgreSQL.

### Otras carreras y estados inconsistentes

| Situación | Efecto | Mitigación |
|---|---|---|
| Dos `solicitar_turno` del mismo tipo a la vez | `COUNT + 1` puede generar el mismo código; el `unique` rechaza uno con `IntegrityError`. | Secuencia por tipo o reintento con `MAX(codigo)`. |
| Finalizar y llamar siguiente a la vez | Dos turnos `llamado` en el mismo módulo. | Lock de aplicación o índice parcial. |
| Logout mientras se escanea | El turno queda `en_atencion` sin ejecutivo. | Validar sesión en cada request y limpiar al hacer logout. |
| Borrado de turnos | El contador retrocede y colisiona. | No borrar; archivar en tabla histórica. |

### Fechas y zonas horarias

Los modelos usan `datetime.now(timezone.utc)`, pero la columna es `DateTime` sin `timezone=True`; SQLite guarda el valor sin offset. Las comparaciones funcionan porque todos los registros siguen el mismo criterio, pero **no** mezclar fechas locales y UTC. Para mostrar horas locales, convertir en el cliente o agregar una capa de presentación; el servidor no lo hace.

### Bloqueos y diagnóstico

Si aparece `database is locked`:

```bash
# Ver conexiones y locks (requiere sqlite3)
sqlite3 instance/turnero.db "PRAGMA busy_timeout=5000; PRAGMA journal_mode;"
```

Recomendaciones: `PRAGMA busy_timeout`, modo WAL para lecturas concurrentes, y no mantener transacciones abiertas durante llamadas HTTP externas (no las hay en este proyecto). WAL no se habilita por defecto en el código; es una mejora pendiente.

---

## Contratos de los Servicios

Los servicios son la API interna del proyecto. Estas son las firmas y los contratos que deben respetarse al extender el código.

### `services/turno_service.py`

| Función | Entrada | Salida | Errores |
|---|---|---|---|
| `validar_rut(rut: str) -> bool` | RUT con o sin puntos/guion | `True`/`False` | No lanza; tolera `None` solo si se valida antes. |
| `solicitar_turno(tipo_tramite_id: int, rut_cliente: str) -> Turno` | IDs y RUT | Turno persistido en `esperando` | `ValueError("RUT inválido")`, `ValueError` si el tipo no existe. |
| `llamar_siguiente(ejecutivo_id: int) -> Turno \| None` | ID de ejecutivo | Turno `llamado` o `None` | `ValueError` si el ejecutivo no existe o ya tiene turno activo. |
| `iniciar_atencion(qr_token: str, ejecutivo_id: int) -> Turno \| None` | Token y ejecutivo | Turno `en_atencion` o `None` si el token no existe | `ValueError` por estado incorrecto o ejecutivo ajeno. |
| `finalizar_atencion(ejecutivo_id: int, tipo_atencion: str \| None, comentarios: str \| None) -> tuple[Turno, Turno \| None]` | Ejecutivo y datos de cierre | `(completado, siguiente)` | `ValueError` si no hay turno en atención. |
| `get_cola() -> list[dict]` | — | Grupos por trámite con totales y turnos serializados para display | — |
| `get_estado_display() -> list[dict]` | — | Módulos activos con ejecutivo conectado y turno actual | — |
| `get_ejecutivo_estado(ejecutivo_id: int) -> dict` | ID | `{ejecutivo, turno_activo}` | — |

**Invariantes que el servicio garantiza:** el código se genera con el prefijo del trámite; todo turno nuevo nace `esperando`; `qr_token` es único; las fechas se guardan en UTC; un turno solo avanza de estado.

**Invariantes que NO garantiza:** exclusión mutua entre dos llamadas concurrentes; expiración de tokens; cancelación; prioridad; multi-sucursal.

### `services/auth_service.py`

| Función | Entrada | Salida | Efecto lateral |
|---|---|---|---|
| `hash_password(password: str) -> str` | Texto plano | Hash bcrypt `$2b$...` | — |
| `check_password(password, password_hash) -> bool` | Texto y hash | `True`/`False` | — |
| `login_ejecutivo(username, password) -> Ejecutivo \| None` | Credenciales | Ejecutivo o `None` | Marca `logged_in=True`; escribe sesión. |
| `logout_ejecutivo() -> None` | — | — | Marca `logged_in=False`; limpia sesión. |
| `get_current_ejecutivo() -> Ejecutivo \| None` | — | Ejecutivo de la sesión | — |
| `login_required(f)` | Vista | Redirige a `/login` si no hay sesión | — |
| `api_login_required(f)` | Vista API | `401 {"error": "No autenticado"}` | — |
| `csrf_protected(f)` | Vista API | `400` si falla JSON/header/origen | — |

`login_ejecutivo` solo considera usuarios `activo=True`. No hay bloqueo por intentos fallidos ni expiración de sesión.

### Contrato de serialización

| Método | Uso | Incluye `qr_token` | Incluye `rut_cliente` |
|---|---|---|---|
| `Turno.to_dict()` | Consola autenticada, SSE, respuestas de creación | Sí | Sí |
| `Turno.to_display_dict()` | Display público y cola pública | No | Sí |

Cualquier campo nuevo debe decidirse en ambos métodos. La regla es: **lo que se muestra en una pantalla pública no puede contener secretos ni identificadores reutilizables**.

---

## SSE en Múltiples Workers

El bus SSE es una lista de `queue.Queue` en memoria del proceso. Con `gunicorn -w 4`, cada worker importa su propia copia de `routes/api.py` y tiene su propia lista. Consecuencias:

- Un cliente conectado al worker A no recibe eventos generados en el worker B.
- El display puede quedar desactualizado de forma intermitente, sin errores visibles.
- Aumentar workers no mejora la entrega de eventos; la empeora.

**Opciones de despliegue:**

| Opción | Configuración | Ventaja | Límite |
|---|---|---|---|
| Un worker | `gunicorn -w 1 --threads 8 'app:create_app()'` | Simple, bus consistente | Un proceso; sin escala horizontal. |
| Sticky sessions | Balanceador por cookie | Cada cliente siempre al mismo worker | No sirve para eventos de otros workers; insuficiente. |
| Bus externo | Redis Pub/Sub + adaptador | Escala horizontal | Complejidad y una dependencia nueva. |
| Cola por proceso + polling | Cada worker consulta la base | Sin dependencias | Latencia y carga de consultas. |

Para este prototipo, **un worker con threads** es la recomendación. Si se migra a Redis, el endpoint SSE debe suscribirse al canal y reenviar a su cola local; el resto del código no cambia.

**Nginx:** el stream necesita `proxy_buffering off`, `proxy_cache off`, `proxy_read_timeout` mayor que el heartbeat (por ejemplo 3600 s) y HTTP/1.1. Sin eso, el proxy acumula eventos y el display parece congelado.

---

## Seguridad

### Autenticacion

- Las contrasenas se almacenan con hash bcrypt (salt automatico).
- Las sesiones se almacenan en cookies firmadas con `SECRET_KEY`.
- El decorador `@api_login_required` protege los endpoints que requieren autenticacion.
- El decorador `@login_required` redirige a la pagina de login para rutas HTML.

### Proteccion CSRF

El decorador `@csrf_protected` se aplica a todos los endpoints POST y verifica:

1. **Content-Type**: Debe incluir `application/json`.
2. **X-Requested-With**: Debe ser `XMLHttpRequest`.
3. **Origin/Referer**: Debe coincidir con el origen del servidor.

```python
def csrf_protected(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        content_type = request.headers.get("Content-Type", "")
        if "application/json" not in content_type:
            return jsonify({"error": "Content-Type debe ser application/json"}), 400

        requested_with = request.headers.get("X-Requested-With", "")
        if requested_with != "XMLHttpRequest":
            return jsonify({"error": "Header X-Requested-With requerido"}), 400

        origin = request.headers.get("Origin", "")
        referer = request.headers.get("Referer", "")
        server_origin = request.host_url.rstrip("/")

        if origin and not origin.startswith(server_origin):
            return jsonify({"error": "Origen no permitido"}), 400
        if referer and not referer.startswith(server_origin):
            return jsonify({"error": "Referer no permitido"}), 400

        return f(*args, **kwargs)
    return decorated_function
```

### Validacion de RUT

Tanto el cliente (JavaScript) como el servidor (Python) validan el RUT chileno usando el algoritmo de modulo 11 (digito verificador). La validacion en servidor es obligatoria y no se puede eludir.

### Exclusion de Datos Sensibles

El metodo `Turno.to_display_dict()` excluye el campo `qr_token` para evitar exponer tokens unicos en endpoints publicos como la pantalla display.

### Manejo de Errores

La aplicacion incluye un manejador global de error 500 que retorna JSON para rutas `/api/*` y una pagina HTML simple para el resto, evitando que se muestren trazas de error al usuario.

---

## Personalizacion

### Cambiar el Logo

Reemplace el archivo `static/img/logo.svg` con su propio logo en formato SVG.

### Cambiar el Nombre de la Sucursal

Edite `templates/display.html`:

```html
<p class="lead text-light-emphasis mb-0 mt-1">
    Sucursal Central  <-- Cambie este texto
</p>
```

### Cambiar Colores

Edite las variables CSS en `static/css/styles.css`:

```css
:root {
    --color-primary: #1565C0;       /* Color principal (azul) */
    --color-primary-dark: #0D47A1;  /* Azul oscuro */
    --color-primary-light: #42A5F5; /* Azul claro */
    --color-success: #2E7D32;       /* Verde exito */
    --color-warning: #F57F17;       /* Amarillo advertencia */
    --color-danger: #C62828;        /* Rojo error */
    --color-bg: #F5F7FA;            /* Fondo general */
    --color-surface: #FFFFFF;       /* Superficie (tarjetas) */
}
```

### Cambiar el Titulo del Sistema

Edite el elemento `<title>` en `templates/base.html`:

```html
<title>{% block title %}Sistema Turnero{% endblock %}</title>
```

Y el header en `templates/display.html`:

```html
<h1 class="display-4 fw-bold mb-0">
    Sistema de Turnos  <-- Cambie este texto
</h1>
```

---

## Guia de Deploy en Produccion

### 1. Configurar Variables de Entorno

```bash
export SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
export PORT=8000
```

### 2. Instalar Servidor WSGI

```bash
pip install gunicorn
```

### 3. Crear Script de Inicio

Cree un archivo `run.py` en la raiz del proyecto:

```python
from app import create_app
import os

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
```

O use el archivo `app.py` directamente con gunicorn.

### 4. Ejecutar con Gunicorn

```bash
gunicorn -w 1 --threads 8 -b 0.0.0.0:8000 "app:create_app()"
```

Parametros recomendados:
- `-w 1`: **un solo worker** para que el bus SSE en memoria sea consistente. Con mas de un worker, cada proceso tiene su propia lista de listeners y los eventos no cruzan.
- `--threads 8`: atiende requests concurrentes dentro de ese proceso.
- `-b 0.0.0.0:8000`: Bind a todas las interfaces en puerto 8000.
- `--timeout 120`: Timeout de 120 segundos para workers.
- `--access-logfile -`: Logs de acceso a stdout.
- `--error-logfile -`: Logs de error a stdout.

Si necesita escala horizontal, mueva el bus a Redis Pub/Sub o use polling; no aumente workers a ciegas (ver [SSE en Multiples Workers](#sse-en-multiples-workers)).

### 5. Configurar Proxy Inverso (Nginx)

```
server {
    listen 80;
    server_name turnero.miempresa.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE necesita buffering desactivado
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400s;
    }
}
```

### 6. Configurar HTTPS con Certbot

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d turnero.miempresa.com
```

### 7. Migracion a Base de Datos Robusta (Opcional)

Para entornos con alta concurrencia, migre de SQLite a PostgreSQL:

Instale dependencias:
```bash
pip install psycopg2-binary
```

Modifique `config.py`:
```python
import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "fallback-dev-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql://usuario:password@localhost:5432/turnero"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
```

Cree la base de datos PostgreSQL:
```bash
createdb turnero
```

**Importante**: La migracion requiere ajustar el esquema de tipos de datos (SQLite no tiene tipos estrictos, PostgreSQL si). Se recomienda usar Alembic/Flask-Migrate para gestionar migraciones.

### 8. Systemd Service (Linux)

Cree `/etc/systemd/system/turnero.service`:

```
[Unit]
Description=Sistema Turnero
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/turnero
Environment="SECRET_KEY=<clave-secreta>"
Environment="PORT=8000"
ExecStart=/usr/local/bin/gunicorn -w 1 --threads 8 -b 127.0.0.1:8000 "app:create_app()"
Restart=always

[Install]
WantedBy=multi-user.target
```

Habilite e inicie:
```bash
sudo systemctl daemon-reload
sudo systemctl enable turnero
sudo systemctl start turnero
```

---

## Agregar Nuevos Tipos de Tramite

Para agregar un nuevo tipo de tramite (ej: "D: Cobranzas"), siga estos pasos:

### 1. Agregar a la Base de Datos (directamente)

```sql
INSERT INTO tipo_tramite (codigo, nombre, prefijo)
VALUES ('D', 'Cobranzas', 'D');
```

O modifique `seed.py`:

```python
# Agregar en run_seed()
tipos = [
    TipoTramite(codigo="A", nombre="Creditos", prefijo="A"),
    TipoTramite(codigo="B", nombre="Consultas Generales", prefijo="B"),
    TipoTramite(codigo="C", nombre="Retiro de Documentos", prefijo="C"),
    TipoTramite(codigo="D", nombre="Cobranzas", prefijo="D"),  # Nuevo
]
```

### 2. El kiosco lo cargara automaticamente

El kiosco carga los tipos de tramite desde `GET /api/tramites` al iniciar. No requiere cambios en el frontend. Si la API falla, tiene un fallback estatico que tambien debe actualizarse en `static/js/kiosco.js`:

```javascript
function usarTramitesFallback() {
    const fallback = [
        { id: 1, codigo: 'A', nombre: 'Creditos' },
        { id: 2, codigo: 'B', nombre: 'Consultas Generales' },
        { id: 3, codigo: 'C', nombre: 'Retiro de Documentos' },
        { id: 4, codigo: 'D', nombre: 'Cobranzas' },  // Nuevo
    ];
    // ...
}
```

### 3. Consideraciones

- El `codigo` y `prefijo` pueden ser letras o digitos, pero deben ser unicos.
- El sistema genera codigos de ticket usando el prefijo + numero secuencial (ej: "D1", "D2", ...).
- No hay limite teorico de tipos de tramite, pero la interfaz del kiosco esta disenada para 3-6 tarjetas.
- Para mas de 6 tipos, considere modificar el diseno del kiosco para incluir scrolling o paginacion.

---

---

## Explicacion del Codigo Fuente

### Punto de Entrada: `app.py`

La aplicacion sigue el patron **Application Factory** de Flask. La funcion `create_app()` es la responsable de construir y configurar la instancia de la aplicacion.

```python
def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    # Inicializar extensiones
    db.init_app(app)

    # Registrar blueprints
    from routes.display import display_bp
    from routes.kiosco import kiosco_bp
    from routes.executive import executive_bp
    from routes.api import api_bp

    app.register_blueprint(display_bp)
    app.register_blueprint(kiosco_bp)
    app.register_blueprint(executive_bp)
    app.register_blueprint(api_bp)

    # Manejador global de error 500
    @app.errorhandler(500)
    def internal_error(error):
        if request.path.startswith('/api/'):
            return {"error": "Error interno del servidor"}, 500
        return render_template('base.html', error="Error interno del servidor"), 500

    # Crear tablas y sembrar datos si es necesario
    with app.app_context():
        _initialize_database(app)

    return app
```

**Flujo de inicializacion:**

1. Se crea la app Flask con la configuracion de `Config`.
2. Se inicializa SQLAlchemy (`db.init_app(app)`).
3. Se registran los 4 blueprints (display, kiosco, executive, api).
4. Se registra el manejador global de error 500.
5. Se inicializa la base de datos (crea tablas + seed si esta vacia).
6. Se retorna la app lista para ejecutar.

### Modulos (`models.py`)

Define 4 modelos SQLAlchemy que reflejan las tablas de la base de datos:

| Modelo | Tabla | Proposito |
|--------|-------|-----------|
| `Modulo` | `modulo` | Modulo de atencion fisico |
| `Ejecutivo` | `ejecutivo` | Ejecutivo que atiende turnos |
| `TipoTramite` | `tipo_tramite` | Tipo de tramite ofrecido |
| `Turno` | `turno` | Ticket generado por el kiosco |

**Metodos importantes:**

```python
# En Turno:
def to_dict(self) -> dict:
    """Retorna dict COMPLETO del turno (incluye qr_token)."""
    return { ... }

def to_display_dict(self) -> dict:
    """Retorna dict SIN qr_token (para endpoints publicos)."""
    d = self.to_dict()
    d.pop("qr_token", None)
    return d
```

**Relaciones entre modelos:**

```
Modulo (1) ──< (N) Ejecutivo
Modulo (1) ──< (N) Turno
Ejecutivo (1) ──< (N) Turno
TipoTramite (1) ──< (N) Turno
```

### Servicios (`services/`)

#### `auth_service.py` — Autenticacion

**Funciones:**

| Funcion | Proposito |
|---------|-----------|
| `hash_password(password)` | Genera hash bcrypt de una contrasena |
| `check_password(password, hash)` | Verifica contrasena contra hash |
| `login_ejecutivo(username, password)` | Autentica y crea sesion |
| `logout_ejecutivo()` | Cierra sesion |
| `get_current_ejecutivo()` | Retorna ejecutivo de la sesion actual |

**Decoradores:**

| Decorador | Proposito |
|-----------|-----------|
| `@login_required` | Redirige a login si no hay sesion (rutas HTML) |
| `@api_login_required` | Retorna 401 si no hay sesion (rutas API) |
| `@csrf_protected` | Verifica headers CSRF en POST |

**Flujo de autenticacion:**

```
POST /api/auth/login
  ├─ Recibe username + password
  ├─ Busca ejecutivo por username
  ├─ Verifica password con bcrypt
  ├─ Crea sesion Flask: session["ejecutivo_id"] = id
  ├─ Marca logged_in = True en BD
  └─ Retorna datos del ejecutivo
```

**Mecanismo CSRF:**

El decorador `@csrf_protected` verifica 3 condiciones:
1. `Content-Type` incluye `application/json`
2. `X-Requested-With` es `XMLHttpRequest`
3. `Origin` o `Referer` coinciden con el servidor

Esto previene ataques CSRF desde sitios externos que intenten enviar solicitudes POST maliciosas.

#### `turno_service.py` — Logica de Negocio

**Funciones principales:**

| Funcion | Proposito | Validaciones |
|---------|-----------|--------------|
| `solicitar_turno(tipo_tramite_id, rut_cliente)` | Crear nuevo turno | RUT valido, tipo tramite existe |
| `llamar_siguiente(ejecutivo_id)` | Asignar siguiente turno | Sin turno activo, hay turnos en cola |
| `iniciar_atencion(qr_token, ejecutivo_id)` | Iniciar atencion | Turno en estado `llamado`, pertenece al ejecutivo |
| `finalizar_atencion(ejecutivo_id, tipo, comentarios)` | Finalizar y llamar siguiente | Turno en estado `en_atencion` |
| `get_cola()` | Listar cola | — |
| `get_estado_display()` | Estado para display | — |
| `get_ejecutivo_estado(ejecutivo_id)` | Estado del ejecutivo | — |
| `validar_rut(rut)` | Validar RUT chileno | — |

**Flujo interno de `solicitar_turno()`:**

```python
def solicitar_turno(tipo_tramite_id: int, rut_cliente: str) -> Turno:
    # 1. Validar RUT
    if not validar_rut(rut_cliente):
        raise ValueError("RUT invalido")

    # 2. Generar codigo secuencial (ej: "B43")
    codigo = _generar_codigo_turno(tipo_tramite_id)

    # 3. Generar qr_token unico (UUID hex de 32 caracteres)
    qr_token = uuid.uuid4().hex

    # 4. Crear y persistir turno
    turno = Turno(codigo=codigo, ..., qr_token=qr_token)
    db.session.add(turno)
    db.session.commit()

    return turno
```

**Flujo interno de `llamar_siguiente()`:**

```python
def llamar_siguiente(ejecutivo_id: int) -> Turno | None:
    ejecutivo = Ejecutivo.query.get(ejecutivo_id)

    # 1. Validar que no tenga turno activo
    turno_activo = Turno.query.filter(
        Turno.ejecutivo_id == ejecutivo_id,
        Turno.estado.in_(["llamado", "en_atencion"]),
    ).first()
    if turno_activo:
        raise ValueError("Ya tienes un turno activo")

    # 2. Buscar siguiente turno en cola (FIFO)
    turno = Turno.query.filter_by(estado="esperando")\
                       .order_by(Turno.fecha_creacion.asc())\
                       .first()
    if not turno:
        return None

    # 3. Asignar a modulo del ejecutivo
    turno.estado = "llamado"
    turno.modulo_id = ejecutivo.modulo_id
    turno.ejecutivo_id = ejecutivo.id
    turno.fecha_llamado = datetime.now(timezone.utc)
    db.session.commit()

    return turno
```

**Validacion de RUT chileno:**

```python
def validar_rut(rut: str) -> bool:
    """
    Algoritmo de digito verificador (modulo 11):
      1. Limpiar RUT (quitar puntos, guion, espacios)
      2. Separar cuerpo y DV
      3. Multiplicar cada digito del cuerpo por
         secuencia 2,3,4,5,6,7 (reinicia a 2 despues de 7)
      4. Sumar productos
      5. Calcular resto modulo 11
      6. DV = 11 - resto (si 11 -> 0, si 10 -> K)
      7. Comparar con DV ingresado
    """
```

### Rutas (`routes/`)

#### `display.py` — Pantalla Publica

```python
display_bp = Blueprint("display", __name__)

@display_bp.route("/")
def index():
    """Renderiza la pantalla de visualizacion."""
    return render_template("display.html")
```

Blueprint simple que solo renderiza un template. Toda la logica dinamica se maneja via JavaScript (SSE + API).

#### `kiosco.py` — Kiosco Cliente

```python
kiosco_bp = Blueprint("kiosco", __name__)

@kiosco_bp.route("/kiosco")
def index():
    """Renderiza la interfaz del kiosco."""
    return render_template("kiosco.html")
```

Igual que display, es un template estatico. Los tipos de tramite se cargan dinamicamente desde `GET /api/tramites`.

#### `executive.py` — Consola Ejecutivo

```python
executive_bp = Blueprint("executive", __name__)

@executive_bp.route("/ejecutivo")
def index():
    """Renderiza login o dashboard segun autenticacion."""
    ejecutivo = get_current_ejecutivo()
    if ejecutivo is None:
        return render_template("login.html")
    return render_template("executive.html", ejecutivo=ejecutivo.to_dict())
```

Verifica sesion activa. Si no hay sesion, muestra login. Si hay sesion, pasa datos del ejecutivo al template.

#### `api.py` — API REST + SSE

Es el blueprint mas complejo. Contiene:

1. **Sistema SSE**: Colas thread-safe para broadcasting de eventos.
2. **Endpoints de autenticacion**: login/logout.
3. **Endpoints de turnos**: display, eventos, solicitar.
4. **Endpoints de ejecutivo**: siguiente, iniciar, finalizar, cola, estado.
5. **Endpoints de consulta**: tramites, modulos.

**Patron SSE:**

```python
# Colas de mensajes por cliente conectado
_event_listeners: list[queue.Queue] = []
_listeners_lock = threading.Lock()

def broadcast_event(event_type: str, data: dict) -> None:
    """Envia un evento a TODOS los clientes SSE."""
    payload = json.dumps({"type": event_type, "data": data})
    with _listeners_lock:
        for q in _event_listeners:
            try:
                q.put_nowait(payload)
            except queue.Full:
                _event_listeners.remove(q)  # Eliminar muertos
```

### Templates (`templates/`)

#### `base.html` — Layout Base

Define la estructura HTML base con Bootstrap 5 CDN y bloques para personalizacion:

```html
{% block title %}Sistema Turnero{% endblock %}
{% block extra_head %}{% endblock %}
{% block content %}{% endblock %}
{% block extra_scripts %}{% endblock %}
```

#### `display.html` — Pantalla Display

- Header con logo y titulo.
- Grid de modulos (se renderiza via JavaScript).
- Seccion de cola de espera (oculta si no hay turnos).
- Overlay "Sin turnos en espera".

#### `executive.html` — Consola Ejecutivo

Divide la pantalla en:
- Panel superior: info del ejecutivo.
- Panel central: atencion actual (3 vistas: sin turno / llamado / atencion).
- Panel lateral: escaner QR.
- Panel inferior: cola de espera.

#### `kiosco.html` — Kiosco Cliente

3 pasos con `d-none` para mostrar/ocultar:
- Paso 1: tarjetas de tramite (cargadas dinamicamente).
- Paso 2: formulario de RUT.
- Paso 3: ticket + QR generado.

#### `login.html` — Login Ejecutivo

Formulario simple con fetch a `/api/auth/login`.

### Frontend JavaScript

#### `display.js` — Logica del Display

**Arquitectura:**
- Estado global `state = { modulos: [], cola: [] }`.
- `loadInitialState()`: fetch a `GET /api/turnos/display`.
- `render()`: renderiza cola, modulos y overlay.
- `connectSSE()`: conecta a SSE y maneja eventos.
- Reconexion automatica cada 3 segundos si falla SSE.

**Manejo de eventos SSE:**
```javascript
// Cada tipo de evento tiene una accion especifica
case 'turno_llamado':
    actualizarModulo(data);  // Actualiza el modulo localmente
    loadInitialState();       // Recarga estado completo
    break;
case 'turno_finalizado':
    loadInitialState();       // Recarga todo (podria haber cambiado la cola)
    break;
```

#### `executive.js` — Logica de la Consola Ejecutivo

**Arquitectura:**
- Funciones modulares: `loadEstado()`, `loadCola()`, `mostrarVista()`.
- `apiFetch()`: wrapper de fetch con headers CSRF.
- Escaner QR con `html5-qrcode`.
- Timer de atencion con `setInterval`.

**Flujo de llamado de turno:**
1. Usuario presiona "Llamar Siguiente Turno".
2. `apiFetch('GET /api/ejecutivo/siguiente')`.
3. Si hay turno: mostrar vista "llamado".
4. Si no hay: mostrar mensaje "No hay turnos en espera".

**Flujo de escaneo QR:**
1. Usuario presiona "Activar Camara".
2. `html5QrCode.start()` con configuracion `{ facingMode: 'environment' }`.
3. Al detectar QR: `onScanSuccess(decodedText)`.
4. Envia `POST /api/ejecutivo/iniciar-atencion` con `{ qr_token: decodedText }`.
5. Si exito: muestra vista "atencion" con datos del turno.

#### `kiosco.js` — Logica del Kiosco

**Arquitectura:**
- Estado local: `tramiteSeleccionado`, `turnoActual`, `TRAMITES`.
- `cargarTramites()`: fetch a `GET /api/tramites`, renderiza tarjetas.
- Fallback estatico si la API falla.
- Validacion de RUT con algoritmo modulo 11 (duplicado del servidor).
- Generacion de QR con `qrcodejs`.

---

## Guia de Modificacion y Extension

### Agregar un Nuevo Campo al Modelo Turno

Ejemplo: agregar un campo `satisfaccion` (encuesta de satisfaccion al finalizar).

**1. Modelo (`models.py`):**
```python
class Turno(db.Model):
    # ... campos existentes ...
    satisfaccion = db.Column(db.Integer, nullable=True)  # 1-5
```

**2. Migracion de BD:**
```bash
sqlite3 instance/turnero.db
ALTER TABLE turno ADD COLUMN satisfaccion INTEGER;
```

**3. Servicio (`turno_service.py`):**
```python
def finalizar_atencion(ejecutivo_id, tipo_atencion=None, comentarios=None, satisfaccion=None):
    turno = Turno.query.filter_by(ejecutivo_id=ejecutivo_id, estado="en_atencion").first()
    turno.estado = "completado"
    turno.satisfaccion = satisfaccion
    # ...
```

**4. Modelo `to_dict()`:**
```python
def to_dict(self) -> dict:
    return {
        # ... campos existentes ...
        "satisfaccion": self.satisfaccion,
    }
```

**5. Template (`executive.html`):**
```html
<div class="mb-3">
    <label class="form-label fw-semibold">Satisfaccion (1-5)</label>
    <select class="form-select" id="satisfaccion">
        <option value="">Seleccione...</option>
        <option value="1">1 - Muy insatisfecho</option>
        <option value="5">5 - Muy satisfecho</option>
    </select>
</div>
```

**6. JavaScript (`executive.js`):**
```javascript
btnFinalizar.addEventListener('click', async function () {
    const satisfaccion = document.getElementById('satisfaccion').value;
    const data = await apiFetch('/api/ejecutivo/finalizar-atencion', {
        method: 'POST',
        body: JSON.stringify({ tipo_atencion: tipo, comentarios: comentarios, satisfaccion: satisfaccion })
    });
});
```

### Agregar un Nuevo Endpoint API

Ejemplo: un endpoint para obtener estadisticas del dia.

**1. Servicio (`turno_service.py`):**
```python
def get_estadisticas_dia() -> dict:
    """Retorna estadisticas del dia actual."""
    hoy = datetime.now(timezone.utc).date()
    total = Turno.query.filter(
        func.date(Turno.fecha_creacion) == hoy
    ).count()
    completados = Turno.query.filter(
        func.date(Turno.fecha_creacion) == hoy,
        Turno.estado == "completado"
    ).count()
    return {
        "total": total,
        "completados": completados,
        "en_espera": total - completados,
        "fecha": hoy.isoformat(),
    }
```

**2. Ruta (`routes/api.py`):**
```python
@api_bp.route("/api/estadisticas/hoy")
def estadisticas_hoy():
    """Retorna estadisticas del dia."""
    from services.turno_service import get_estadisticas_dia
    return get_estadisticas_dia(), 200
```

### Agregar Soporte para Websockets (Alternativa a SSE)

Si necesita comunicacion bidireccional (ej: chat ejecutivo-cliente), puede migrar de SSE a WebSockets con Flask-SocketIO:

**1. Instalar:**
```bash
pip install flask-socketio
```

**2. Configurar (`app.py`):**
```python
from flask_socketio import SocketIO
socketio = SocketIO(app)

@socketio.on('connect')
def handle_connect():
    print('Cliente conectado')

@socketio.on('llamar_turno')
def handle_llamar_turno(data):
    # Logica de negocio
    socketio.emit('turno_llamado', data)
```

**3. Ejecutar:**
```python
socketio.run(app, host="0.0.0.0", port=5000)
```

### Agregar Soporte para Multiples Sucursales

Para extender el sistema a multiples sucursales:

**1. Nuevo modelo `Sucursal`:**
```python
class Sucursal(db.Model):
    __tablename__ = "sucursal"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    direccion = db.Column(db.String(300))
    # Relacion con modulo
    modulos = db.relationship("Modulo", backref="sucursal", lazy=True)
```

**2. Agregar FK a `Modulo`:**
```python
class Modulo(db.Model):
    # ...
    sucursal_id = db.Column(db.Integer, db.ForeignKey("sucursal.id"), nullable=True)
```

**3. Filtrar por sucursal en consultas:**
```python
turnos = Turno.query.join(Modulo).filter(Modulo.sucursal_id == sucursal_id).all()
```

### Agregar Pruebas Unitarias con pytest

**1. Instalar:**
```bash
pip install pytest pytest-flask
```

**2. Crear `tests/conftest.py`:**
```python
import pytest
from app import create_app
from models import db as _db

@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    with app.app_context():
        _db.create_all()
        yield app

@pytest.fixture
def client(app):
    return app.test_client()
```

**3. Crear `tests/test_turno_service.py`:**
```python
def test_validar_rut_valido():
    from services.turno_service import validar_rut
    assert validar_rut("12345678-5") == True
    assert validar_rut("11111111-1") == True

def test_validar_rut_invalido():
    from services.turno_service import validar_rut
    assert validar_rut("12345678-0") == False
    assert validar_rut("12") == False

def test_solicitar_turno(app, client):
    from services.turno_service import solicitar_turno
    with app.app_context():
        turno = solicitar_turno(tipo_tramite_id=1, rut_cliente="12345678-5")
        assert turno.estado == "esperando"
        assert turno.codigo.startswith("A")
```

### Configurar Integracion Continua (CI)

**GitHub Actions (`.github/workflows/test.yml`):**
```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-flask
      - run: python -m pytest tests/
```

---

## Pruebas

### Pruebas Manuales

No hay suite automatizada en el repositorio. La siguiente matriz cubre los flujos críticos y debe ejecutarse antes de cada release:

| ID | Caso | Pasos resumidos | Resultado esperado |
|---|---|---|---|
| CP-01 | Solicitud de turno | Kiosco → trámite → RUT `12.345.678-5` → Solicitar | Ticket con código, trámite y QR. |
| CP-02 | Llamar siguiente | Login → Llamar siguiente | Turno asignado al módulo; display actualizado. |
| CP-03 | Escanear QR | Llamar → Escanear QR del ticket | Vista "En atención" con cronómetro. |
| CP-04 | Finalizar y encadenar | Finalizar con tipo de atención | Turno `completado`; siguiente llamado si existe. |
| CP-05 | Display en tiempo real | Crear/llamar/finalizar con el display abierto | Cambios sin recargar; SSE activo. |
| CP-06 | Cola vacía | Solicitar sin turnos pendientes | "Sin turnos en espera"; `turno: null` en la API. |
| CP-07 | RUT inválido | Ingresar `12.345.678-9` | Rechazo en cliente y en servidor. |
| CP-08 | Login fallido | Contraseña incorrecta | `401`; mensaje genérico; sin sesión. |
| CP-09 | Doble llamado | Llamar dos veces sin finalizar | `400` "Ya tienes un turno activo". |
| CP-10 | QR ajeno | Escanear un token de otro módulo | `400` "Este turno fue llamado por otro ejecutivo". |
| CP-11 | Logout | Cerrar sesión | Módulo desaparece del display. |
| CP-12 | CSRF | POST sin `X-Requested-With` | `400`; no se modifica el estado. |

**Pruebas automatizadas sugeridas.** El proyecto no las incluye, pero la estructura de servicios las facilita: `validar_rut` es una función pura y `turno_service` recibe IDs. Un `conftest.py` con una base `sqlite:///:memory:` y el `test_client` de Flask permite cubrir CP-01 a CP-12 en pocos segundos. La ausencia de tests es deuda técnica declarada, no una omisión accidental.

### Pruebas de API con curl

```bash
# Login
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -H "X-Requested-With: XMLHttpRequest" \
  -d '{"username":"carlos","password":"carlos123"}' \
  -c cookies.txt

# Ver estado del ejecutivo
curl http://localhost:5000/api/ejecutivo/estado \
  -b cookies.txt

# Ver cola
curl http://localhost:5000/api/ejecutivo/cola \
  -b cookies.txt

# Llamar siguiente turno
curl http://localhost:5000/api/ejecutivo/siguiente \
  -b cookies.txt

# Ver display
curl http://localhost:5000/api/turnos/display

# Listar tramites
curl http://localhost:5000/api/tramites
```

### Pruebas de SSE

```bash
curl -N http://localhost:5000/api/turnos/eventos
```

### Extensiones Posibles

- **Pruebas unitarias**: Agregar tests con `pytest` para los servicios.
- **Pruebas de integracion**: Usar `Flask test client` para probar las rutas.
- **Pruebas E2E**: Usar `Playwright` o `Selenium` para pruebas de interfaz.

---

## Deuda Tecnica

La deuda está priorizada por impacto real, no por elegancia. Un prototipo puede vivir con ella; un despliegue con clientes reales no.

### Prioridad alta (antes de producción)

| # | Deuda | Riesgo | Propuesta |
|---|---|---|---|
| 1 | Sin tests automatizados | Regresiones silenciosas | `pytest` + base en memoria + CI. |
| 2 | Carrera en `llamar_siguiente` | Turno duplicado o asignación incorrecta | `UPDATE ... WHERE estado='esperando'` con `rowcount` o lock. |
| 3 | `SECRET_KEY` por defecto y `debug=True` | Sesiones falsificables, consola expuesta | Variables de entorno obligatorias; Gunicorn. |
| 4 | RUT en la API pública | Exposición de dato personal | Enmascarar en `to_display_dict()`. |
| 5 | `qr_token` en SSE y en `to_dict()` de eventos | Suplantación si se escucha el stream | Emitir solo código/módulo; token solo en la respuesta al cliente. |
| 6 | Sin rate limiting | Fuerza bruta, spam de turnos | Límites en Nginx o Flask-Limiter. |

### Prioridad media

| # | Deuda | Riesgo | Propuesta |
|---|---|---|---|
| 7 | `logged_in` persistente | Módulos fantasma | Expiración por inactividad o heartbeat. |
| 8 | Código por `COUNT + 1` | Colisiones al borrar | Secuencia por tipo o `MAX(codigo)`. |
| 9 | Sin migraciones formales | Cambios de esquema frágiles | Alembic. |
| 10 | Bus SSE en memoria | No escala a varios workers | Redis Pub/Sub o un worker. |
| 11 | Sin cancelación/rellamado | Casos reales sin salida | Estado `cancelado` y endpoint. |
| 12 | Sin panel de administración | Altas por SQL | CRUD mínimo de usuarios/trámites/módulos. |
| 13 | Sin expiración de token QR | Ticket viejo reutilizable | TTL y validación de ventana. |
| 14 | Dependencias con pin de major | Actualizaciones no reproducibles | Fijar versiones exactas y lockfile. |

### Prioridad baja

| # | Deuda | Riesgo | Propuesta |
|---|---|---|---|
| 15 | Sin i18n | Solo español | Archivos de traducción. |
| 16 | Accesibilidad parcial | Usuarios con lectores de pantalla | Auditoría WCAG y foco visible. |
| 17 | Sin audio en display | Sala ruidosa | Anuncio por voz con Web Speech API. |
| 18 | Sin Docker | Onboarding manual | `Dockerfile` y `compose` con volumen para `instance/`. |
| 19 | Sin métricas | Operación a ciegas | Endpoint `/metrics` o logs estructurados. |
| 20 | Sin multi-sucursal | Una instancia por sucursal | `sucursal_id` en todas las tablas. |

### Lo que no es deuda

No faltan cosas por pereza: el proyecto eligió deliberadamente SQLite, SSE, seed y un solo proceso para mantener el alcance. La deuda es lo que impide usarlo con clientes reales sin supervisión, no la ausencia de features empresariales.

---

## Contribucion

### Guia para Contribuir

1. **Fork** el repositorio.
2. Cree una rama para su feature: `git checkout -b feature/nueva-funcionalidad`.
3. Implemente los cambios siguiendo el estilo del codigo existente.
4. **Actualice** la documentacion en `docs/` si su cambio afecta la interfaz de usuario o la API.
5. Ejecute la matriz de pruebas manuales (CP-01 a CP-12) para verificar que no haya regresiones.
6. Envie un Pull Request con descripcion clara de los cambios.

### Estandares de Codigo

- **Python**: Siga PEP 8. Use type hints en todas las funciones.
- **JavaScript**: Use `'use strict'`, funciones con nombre, y `const`/`let` (no `var`).
- **HTML**: Use templates Jinja2 con herencia de `base.html`.
- **CSS**: Use variables CSS para colores y valores reutilizables.
- **Commits**: Mensajes claros en español o ingles, formato: `tipo(alcance): descripcion`.

### Checklist de Pull Request

- [ ] El codigo funciona en desarrollo (`python3 app.py`)
- [ ] No hay errores en la consola del navegador (F12)
- [ ] La matriz de pruebas manuales (CP-01 a CP-12) se ejecuto sin regresiones
- [ ] La documentacion relevante esta actualizada
- [ ] No se introdujeron vulnerabilidades de seguridad
- [ ] El codigo sigue los estandares del proyecto

---

<div align="center">
  <p><strong>Turnero</strong> — Sistema de Gestion de Turnos v1.0.0</p>
  <p>¿Preguntas? Abre un issue en el repositorio del proyecto.</p>
</div>
