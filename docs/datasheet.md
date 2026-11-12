# Datasheet — Sistema Turnero

**Documentación técnica de usuario para el Sistema de Gestión de Turnos**

Versión: 1.1.0 | Última actualización: Noviembre 2026

---

## Índice

1. [Especificaciones Técnicas](#especificaciones-tecnicas)
2. [Requisitos de Servidor y Red](#requisitos-de-servidor)
3. [Dependencias](#dependencias)
4. [Operación Detallada por Página](#operacion-detallada-por-pagina)
   - [Pantalla Display](#1-pantalla-display)
   - [Consola Ejecutivo](#2-consola-ejecutivo)
   - [Kiosco Cliente](#3-kiosco-cliente)
5. [API REST — Referencia Completa](#api-rest--referencia-completa)
6. [Campos y Formularios](#campos-y-formularios)
7. [Estados de Turno](#estados-de-turno)
8. [Códigos de Error](#codigos-de-error)
9. [Guía de Solución de Problemas](#guia-de-solucion-de-problemas)
10. [Preguntas Frecuentes](#preguntas-frecuentes)
11. [Mantenimiento](#mantenimiento)
12. [Roles y Responsabilidades](#roles-y-responsabilidades)
13. [Procedimientos Operativos](#procedimientos-operativos)
14. [Indicadores Operativos](#indicadores-operativos)
15. [Contingencia y Continuidad](#contingencia-y-continuidad)
16. [Seguridad Operativa](#seguridad-operativa)
17. [Glosario](#glosario)

---

## Especificaciones Técnicas

### Generales

| Parámetro | Valor |
|-----------|-------|
| Nombre del sistema | Turnero — Sistema de Gestión de Turnos |
| Versión | 1.0.0 |
| Tipo de aplicación | Aplicación web monolítica (Flask) |
| Modelo de despliegue | Servidor local (intranet) o cloud |
| Base de datos | SQLite 3 (archivo: `instance/turnero.db`) |
| Tiempo real | Server-Sent Events (SSE) sobre HTTP |
| Frontend | HTML5, CSS3, JavaScript (Vanilla ES6+) |
| Framework CSS | Bootstrap 5.3.3 |
| Autenticación | Sesiones Flask firmadas + bcrypt |
| Idioma interfaz | Español |
| Codificación | UTF-8 |

### Requisitos de Servidor

| Componente | Especificación Mínima | Recomendada |
|------------|----------------------|--------------|
| CPU | 1 núcleo @ 1.5 GHz | 2 núcleos @ 2.0 GHz |
| RAM | 256 MB | 1 GB |
| Disco duro | 100 MB libres | 500 MB libres |
| Sistema operativo | Linux, macOS, Windows | Linux (Ubuntu 22.04 LTS+) |
| Python | 3.10 | 3.11+ |

### Requisitos de Red

| Parámetro | Valor |
|-----------|-------|
| Protocolo | HTTP/1.1 |
| Puerto por defecto | 5000 (configurable vía `PORT`) |
| Conexiones simultáneas | Limitado por SQLite (recomendar <10 escritores concurrentes) |
| Ancho de banda | Mínimo: 1 Mbps (por cliente web) |
| Latencia máxima recomendada | <100 ms entre cliente y servidor |

### Páginas Web

| Página | Ruta URL | Proceso | Tipo de Usuario |
|--------|----------|---------|-----------------|
| Pantalla Display | `GET /` | Visualización pública | Clientes en sala de espera |
| Kiosco Cliente | `GET /kiosco` | Solicitud de turnos | Clientes (nuevo ingreso) |
| Login Ejecutivo | `GET /ejecutivo` (no auth) | Autenticación | Ejecutivos |
| Consola Ejecutivo | `GET /ejecutivo` (auth) | Gestión de atención | Ejecutivos autenticados |

### Endpoints de API

| Método | Ruta | Autenticación | Protección CSRF | Propósito |
|--------|------|---------------|-----------------|-----------|
| `POST` | `/api/auth/login` | No | Sí | Iniciar sesión ejecutivo |
| `POST` | `/api/auth/logout` | No | Sí | Cerrar sesión ejecutivo |
| `GET` | `/api/turnos/display` | No | No | Obtener estado del display |
| `GET` | `/api/turnos/eventos` | No | No | Conectar a SSE (streaming) |
| `POST` | `/api/turnos/solicitar` | No | Sí | Crear nuevo turno |
| `GET` | `/api/ejecutivo/siguiente` | Sí | No | Llamar siguiente turno |
| `POST` | `/api/ejecutivo/iniciar-atencion` | Sí | Sí | Iniciar atención (QR) |
| `POST` | `/api/ejecutivo/finalizar-atencion` | Sí | Sí | Finalizar atención |
| `GET` | `/api/ejecutivo/cola` | Sí | No | Ver cola de espera |
| `GET` | `/api/ejecutivo/estado` | Sí | No | Ver estado del ejecutivo |
| `GET` | `/api/tramites` | No | No | Listar tipos de trámite |
| `GET` | `/api/modulos` | No | No | Listar módulos activos |

---

## Dependencias

### Backend (Python)

Las dependencias están declaradas en `requirements.txt`:

```text
Flask==3.1.*
Flask-SQLAlchemy==3.1.*
bcrypt==4.*
```

| Paquete | Versión | Propósito | Licencia |
|---------|---------|-----------|----------|
| Flask | 3.1.* | Framework web | BSD |
| Flask-SQLAlchemy | 3.1.* | ORM para base de datos | BSD |
| bcrypt | 4.* | Hashing de contraseñas | Apache 2.0 |

**Instalación en el entorno virtual del proyecto:**

```bash
python3 -m venv venv
source venv/bin/activate        # Linux / macOS
venv\Scripts\activate           # Windows
pip install -r requirements.txt
```

### Frontend

| Librería | Versión | Propósito | Origen |
|----------|---------|-----------|--------|
| Bootstrap | 5.3.3 | Framework CSS / UI | CDN jsDelivr (requiere internet) |
| qrcodejs | local | Generación QR en el kiosco | `static/js/qrcode.min.js` |
| html5-qrcode | local | Escaneo QR con cámara | `static/js/html5-qrcode.min.js` |

Solo Bootstrap se carga desde CDN. Las dos librerías QR están vendorizadas en el repositorio y funcionan sin conexión; si se actualiza Bootstrap, hay que respetar el SRI declarado en `templates/base.html`.

### Dependencias de desarrollo (opcionales)

El generador del manual PDF (`generate_marketing_pdf.py`) requiere `fpdf2` y `playwright`, que **no** forman parte de `requirements.txt` porque no son necesarios para ejecutar la aplicación. Instalarlos solo si se va a regenerar el PDF:

```bash
pip install fpdf2 playwright
playwright install chromium
```

---

## Operación Detallada por Página

### 1. Pantalla Display

#### Descripción
Pantalla pública destinada a verse en un monitor o TV grande en la sala de espera. Muestra en tiempo real los turnos siendo llamados, organizados por módulo de atención.

#### Acceso
```
http://<direccion-servidor>:5000/
```

#### Elementos de la Interfaz

| Elemento | Descripción |
|----------|-------------|
| **Header** | Logo corporativo + "Sistema de Turnos" + "Sucursal Central" |
| **Grid de Módulos** | Tarjetas de módulo en columnas responsivas (3 columnas en desktop) |
| **Cola de Espera** | Sección colapsable que muestra los siguientes turnos (solo si hay >0) |
| **Overlay "Sin turnos"** | Pantalla completa animada que aparece cuando no hay turnos activos |

#### Cada tarjeta de módulo contiene:

| Campo | Descripción |
|-------|-------------|
| **Nombre del Módulo** | Ej: "Módulo 1" |
| **Badge de Estado** | `🟡 Llamando...` / `🟢 En Atención` / `⚪ Sin turno` |
| **Nombre del Ejecutivo** | Ej: "Carlos Muñoz" |
| **Ticket Actual** | Código del ticket en tamaño grande (ej: **B43**) |

#### Comportamiento Tiempo Real (SSE)

| Evento | Acción en Display |
|--------|-------------------|
| `turno_creado` | Recarga estado completo (nuevo ticket en cola) |
| `turno_llamado` | Actualiza módulo con el ticket llamado + animación de entrada |
| `turno_atendido` | Badge cambia a "En Atención" + ticket en verde |
| `turno_finalizado` | Módulo vuelve a estado "Sin turno" (si no hay siguiente) |
| `ejecutivo_logout` | Módulo se oculta del grid |
| Heartbeat (c/30s) | Mantiene conexión activa (sin cambios visibles) |

#### Indicadores Visuales

| Estado | Color | Animación |
|--------|-------|-----------|
| Llamando... | 🟡 Amarillo (`#F57F17`) | Pulso infinito (escala 1 → 1.05) |
| En Atención | 🟢 Verde (`#2E7D32`) | Estático |
| Sin turno | ⚪ Gris (`#6C757D`) | Texto "---" |

#### Solución de Problemas — Display

| Problema | Causa Posible | Solución |
|----------|---------------|----------|
| Pantalla en blanco | Servidor no iniciado | Ejecute `python3 app.py` en el directorio del proyecto |
| No se ven cambios | Error de conexión SSE | Abra F12 → Console: verifique errores. Recargue F5. |
| Overlay "Sin turnos" no desaparece | Estado no sincronizado | Recargue la página. Verifique que ejecutivos estén logueados. |
| Módulos no aparecen | Ejecutivos no han iniciado sesión | Los ejecutivos deben iniciar sesión en `/ejecutivo` |
| Error 404 | URL incorrecta | Verifique que sea exactamente `http://localhost:5000/` |
| Animaciones lentas | GPU / navegador antiguo | Actualice el navegador. Desactive aceleración hardware. |

---

### 2. Consola Ejecutivo

#### Descripción
Dashboard para que los ejecutivos gestionen la atención al cliente. Requiere autenticación.

#### Acceso
```
http://<direccion-servidor>:5000/ejecutivo
```

#### Proceso de Login

1. Ingrese su **nombre de usuario** en el campo correspondiente.
2. Ingrese su **contraseña**.
3. Presione el botón **"Ingresar"**.
4. Si las credenciales son correctas, será redirigido al dashboard.
5. Si son incorrectas, verá un mensaje de error en rojo debajo del formulario.

> **⏱️ Sesión**: La sesión permanece activa hasta que cierre sesión explícitamente o cierre el navegador. No hay tiempo de expiración automático.

#### Dashboard — Panel Superior (Info del Ejecutivo)

| Elemento | Descripción |
|----------|-------------|
| Badge "Módulo X" | Módulo asignado al ejecutivo (determinado por el administrador) |
| "Bienvenido, [Nombre]" | Nombre completo del ejecutivo autenticado |
| Botón "Cerrar Sesión" | Finaliza la sesión y redirige al login |

#### Dashboard — Panel Central (Atención Actual)

##### Vista "Sin turno activo"

| Elemento | Acción |
|----------|--------|
| Mensaje "Sin turno activo" | Indicador de disponibilidad |
| Botón 🟢 **"Llamar Siguiente Turno"** | Asigna el siguiente ticket de la cola a este módulo (FIFO) |

**¿Qué sucede al llamar?**
1. El sistema busca el ticket más antiguo en estado `esperando`.
2. Cambia su estado a `llamado`.
3. Asigna el módulo y ejecutivo al ticket.
4. La pantalla display se actualiza instantáneamente vía SSE.
5. La consola cambia a la vista "Turno llamado".

##### Vista "Turno llamado" (esperando cliente)

| Elemento | Descripción |
|----------|-------------|
| Alerta 🟡 **"Turno llamado. Esperando que el cliente llegue..."** | Estado actual |
| **Código del ticket** (ej: **B43**) | En tamaño grande, color primario |
| Info del ticket | Trámite y RUT del cliente |
| *No hay botones de acción* | Debe esperar a que el cliente se acerque |

##### Vista "Turno en atención"

| Sección | Elementos |
|---------|-----------|
| **Panel Izquierdo** | Código del ticket (verde, grande), Tipo de trámite, RUT del cliente, Tiempo transcurrido (MM:SS) |
| **Panel Derecho** | Select "Tipo de Atención", Textarea "Comentarios", Botón 🔴 **"Finalizar Atención"** |

**Campos del formulario de atención:**

| Campo | Tipo | Opciones | Requerido |
|-------|------|----------|-----------|
| Tipo de Atención | `select` | Consulta, Contratación, Cobranza, Otro | **Sí** |
| Comentarios | `textarea` | Texto libre (máx. ~500 caracteres) | No |

**¿Qué sucede al finalizar?**
1. Valida que se haya seleccionado un tipo de atención.
2. Cambia el estado del ticket a `completado`.
3. Registra `tipo_atencion`, `comentarios` y `fecha_completado`.
4. **Automáticamente llama al siguiente turno** en espera (si existe).
5. La pantalla display se actualiza vía SSE.
6. La consola vuelve a la vista correspondiente.

#### Dashboard — Panel Lateral (Escáner QR)

**Requisitos previos:**
- Dispositivo con cámara funcional.
- Navegador con permisos de cámara concedidos.
- Iluminación adecuada para el escaneo.

**Procedimiento:**

| Paso | Acción | Resultado Esperado |
|------|--------|-------------------|
| 1 | Presione **"Activar Cámara"** | El navegador solicita permiso de cámara. El feed de video aparece. |
| 2 | Enfoque el código QR del ticket | El sistema detecta automáticamente el QR. |
| 3 | — | La cámara se detiene. El ticket cambia a estado `en_atencion`. |
| 4 | Complete el formulario de atención | — |
| 5 | Presione **"Finalizar Atención"** | Atención completada. |

**Errores comunes del escáner QR:**

| Error en Pantalla | Causa | Solución |
|-------------------|-------|----------|
| "QR detectado pero no se pudo iniciar atención" | QR no corresponde al ticket llamado | Verifique que el QR sea del ticket actual |
| "El turno X no está en estado 'llamado'" | QR de un ticket ya atendido o en espera | Solo escanee tickets en estado "llamado" |
| "Este turno fue llamado por otro ejecutivo" | QR de un ticket asignado a otro módulo | Cada ejecutivo solo atiende su propio módulo |
| "Camara no disponible" | Sin cámara o permiso denegado | Verifique permisos del navegador |
| "Error al iniciar cámara" | Hardware no disponible | Conecte una cámara externa o use otro dispositivo |

#### Dashboard — Panel Inferior (Cola de Espera)

| Elemento | Descripción |
|----------|-------------|
| **Título** | "Cola de Espera" |
| **Badge total** | Número total de turnos esperando (ej: `5`) |
| **Grupos** | Turnos agrupados por tipo de trámite |
| **Cada grupo** | Nombre del trámite, badge con cantidad, lista de códigos |

La cola se actualiza automáticamente cada 15 segundos mediante polling. No requiere interacción manual.

#### Solución de Problemas — Consola Ejecutivo

| Problema | Causa Posible | Solución |
|----------|---------------|----------|
| **No puedo iniciar sesión** | Credenciales incorrectas | Use las credenciales de prueba. Contacte al administrador. |
| **Error "Ya tienes un turno activo"** | Turno previo en estado `llamado` o `en_atencion` | Finalice la atención actual o pida al admin que resetee el turno. |
| **Error "No hay turnos en espera"** | Cola vacía | Espere nuevos clientes o verifique que el kiosco esté generando tickets. |
| **Error "No hay un turno en atención para este ejecutivo"** | Sin turno activo | Llame o escanee un turno primero. |
| **El botón "Llamar siguiente" no responde** | Error de red o servidor | Abra F12 → Console. Verifique que el servidor esté corriendo. |
| **La cámara no se activa** | Permiso denegado | Vaya a Configuración del navegador → Privacidad → Cámara → Permitir. |
| **El QR no se escanea** | Mala iluminación o QR dañado | Mejore la iluminación. Limpie la pantalla del cliente. |
| **Se ve "Error: No autenticado"** | Sesión expirada | Recargue la página. Si persiste, vaya a `/ejecutivo` e inicie sesión. |
| **Error "Content-Type debe ser application/json"** | Error de programación | Reporte al administrador. |
| **El cronómetro no avanza** | Bug de frontend | Recargue la página. El estado se recupera automáticamente. |

#### Cierre de Sesión

Presione el botón **"Cerrar Sesión"** en el panel superior. Esto:
1. Envía una solicitud `POST /api/auth/logout`.
2. Limpia la sesión del servidor.
3. Redirige a la página de login.
4. Emite un evento SSE `ejecutivo_logout` para que el display oculte el módulo.

---

### 3. Kiosco Cliente

#### Descripción
Interfaz de autoservicio para que los clientes soliciten turnos. Diseñada para pantallas táctiles con navegación paso a paso.

#### Acceso
```
http://<direccion-servidor>:5000/kiosco
```

#### Flujo de 3 Pasos

##### Paso 1 — Selección de Trámite

El sistema carga dinámicamente los tipos de trámite desde `GET /api/tramites`. Si la API falla, usa datos de respaldo (fallback).

**Trámites disponibles (por defecto):**

| Código | Nombre | Icono |
|--------|--------|-------|
| **A** | Créditos | Círculo con "A" |
| **B** | Consultas Generales | Círculo con "B" |
| **C** | Retiro de Documentos | Círculo con "C" |

**Interacción:**
- Toque la tarjeta del trámite deseado.
- La tarjeta seleccionada se resalta con borde azul (`#1565C0`).
- Automáticamente avanza al Paso 2.

##### Paso 2 — Ingreso de RUT

**Campo: RUT**
- Formato automático mientras escribe: `XX.XXX.XXX-Y`
- Validación en cliente antes de enviar (dígito verificador, módulo 11).
- Validación en servidor (no se puede eludir).

**Formato aceptado:**
| Ejemplo | Válido |
|---------|--------|
| `12.345.678-5` | ✅ |
| `12345678-5` | ✅ |
| `1.000.005-K` | ✅ |
| `1000005k` | ✅ |
| `12.345.678-9` | ❌ (dígito incorrecto) |
| `123` | ❌ (muy corto) |

> Los RUT de esta tabla son ficticios. `12.345.678-5` es el ejemplo canónico del proyecto: cumple el módulo 11 y no corresponde a una persona real identificable.

**Validaciones:**
- Largo mínimo: 2 caracteres (cuerpo + dígito verificador).
- Cuerpo: solo dígitos numéricos.
- Dígito verificador: calculado con algoritmo módulo 11.
- Puede ser número (0-9) o letra (K).

**Botón "Solicitar Turno":**
- Deshabilitado durante el envío (spinner).
- Si el RUT es inválido: muestra mensaje de error en rojo debajo del campo.
- Si el RUT es válido: envía `POST /api/turnos/solicitar` al servidor.
- Si el servidor rechaza: muestra el error del servidor.

**Botón "Volver":** Regresa al Paso 1.

##### Paso 3 — Ticket Generado

| Elemento | Descripción |
|----------|-------------|
| Badge "Turno Generado" | Indicador verde |
| Código del ticket | En tamaño `display-1` (ej: **B43**), color primario |
| Nombre del trámite | Trámite seleccionado |
| **Código QR** | Único por ticket, generado con `qrcodejs` |
| Mensaje | "Presente este código QR al ejecutivo cuando lo llamen" |
| Botón "Nuevo Turno" | Reinicia el flujo al Paso 1 |

**El código QR contiene:**
- El `qr_token` del ticket (UUID hexadecimal de 64 caracteres).
- Es único por ticket (generado con `uuid.uuid4().hex`).
- Solo es válido para el ticket asignado.
- Una vez escaneado, no puede reutilizarse.

#### Solución de Problemas — Kiosco

| Problema | Causa Posible | Solución |
|----------|---------------|----------|
| **Las tarjetas de trámite no aparecen** | Error de conexión al servidor | El sistema usa fallback automático. Si no funciona, recargue. |
| **Error "RUT inválido" en cliente** | RUT no cumple formato chileno | Verifique el RUT y el dígito verificador. Use el formato `12.345.678-9`. |
| **Error "RUT inválido" en servidor** | Misma validación en backend | El error puede ocurrir si se manipula la solicitud. |
| **Error "Tipo de trámite no encontrado"** | ID de trámite incorrecto | Vuelva al Paso 1 y seleccione un trámite. |
| **Error de red al solicitar turno** | Servidor no disponible | Verifique que el servidor esté en ejecución. |
| **El QR no se genera** | Error en librería `qrcodejs` | Recargue la página. Verifique la consola del navegador. |
| **Pantalla no responde al tacto** | Navegador no configurado para táctil | Use Chrome o Edge con soporte táctil. |

---

## API REST — Referencia Completa

### Convenciones Generales

- **Base URL**: `http://<servidor>:<puerto>/api`
- **Formato de request**: `Content-Type: application/json`
- **Formato de response**: `Content-Type: application/json`
- **Autenticación**: Cookie de sesión Flask (HTTP-only)
- **CSRF**: Headers requeridos en POST:
  - `Content-Type: application/json`
  - `X-Requested-With: XMLHttpRequest`
- **Errores**: Código HTTP 4xx/5xx + `{"error": "mensaje"}`

### POST /api/auth/login

Autentica un ejecutivo.

**Request:**
```json
{
  "username": "carlos",
  "password": "carlos123"
}
```

**Response 200:**
```json
{
  "mensaje": "Login exitoso",
  "ejecutivo": {
    "id": 1,
    "username": "carlos",
    "nombre": "Carlos Munoz",
    "modulo_id": 1,
    "modulo_nombre": "Modulo 1",
    "activo": true,
    "logged_in": true
  }
}
```

**Response 401:**
```json
{ "error": "Usuario o contrase\u00f1a incorrectos" }
```

### POST /api/auth/logout

Cierra la sesión.

**Response 200:**
```json
{ "mensaje": "Sesión cerrada" }
```

### GET /api/turnos/display

Estado actual del display (módulos + cola).

**Response 200:**
```json
{
  "modulos": [
    {
      "modulo": { "id": 1, "nombre": "Modulo 1", "activo": true },
      "ejecutivo": { "id": 1, "username": "carlos", "nombre": "Carlos Munoz", "modulo_nombre": "Modulo 1" },
      "turno_actual": {
        "id": 5, "codigo": "B43", "tipo_tramite": "Consultas Generales",
        "rut_cliente": "12345678-5", "estado": "llamado",
        "modulo_nombre": "Modulo 1", "ejecutivo_nombre": "Carlos Munoz"
      }
    }
  ],
  "cola": [
    {
      "tipo_tramite_id": 1, "tipo_tramite": "Creditos", "codigo": "A",
      "total": 3, "turnos": [ { "codigo": "A5" }, { "codigo": "A6" } ]
    }
  ]
}
```

> ℹ️ `turno_actual` **nunca** incluye `qr_token` (protegido por `to_display_dict()`).

### GET /api/turnos/eventos

Conexión SSE (streaming). Mantiene la conexión abierta.

**Response:** `Content-Type: text/event-stream`

**Formato de eventos:**
```
data: {"type":"turno_llamado","data":{"codigo":"B43","modulo_id":1,"modulo_nombre":"Modulo 1","ejecutivo":"Carlos Munoz","turno":{...}}}

data: {"type":"turno_atendido","data":{"codigo":"B43","modulo_id":1,"turno":{...}}}

data: {"type":"turno_finalizado","data":{"codigo":"B43","modulo_id":1,"turno":{...}}}

: heartbeat

```

**Tipos de eventos:**
| Tipo | Disparado por | Descripción |
|------|---------------|-------------|
| `turno_creado` | `POST /api/turnos/solicitar` | Nuevo ticket en kiosco |
| `turno_llamado` | `GET /api/ejecutivo/siguiente` o al finalizar | Ticket asignado a módulo |
| `turno_atendido` | `POST /api/ejecutivo/iniciar-atencion` | Atención iniciada |
| `turno_finalizado` | `POST /api/ejecutivo/finalizar-atencion` | Atención completada |
| `ejecutivo_logout` | `POST /api/auth/logout` | Ejecutivo cerró sesión |

### POST /api/turnos/solicitar

Crea un nuevo turno (kiosco).

**Request:**
```json
{
  "tipo_tramite_id": 2,
  "rut": "12345678-5"
}
```

**Response 201:**
```json
{
  "mensaje": "Turno creado exitosamente",
  "turno": {
    "id": 6, "codigo": "B44", "tipo_tramite": "Consultas Generales",
    "rut_cliente": "12345678-5", "estado": "esperando",
    "qr_token": "a1b2c3d4e5f67890a1b2c3d4e5f67890"
  }
}
```

**Response 400:**
```json
{ "error": "RUT inv\u00e1lido" }
```
```json
{ "error": "Tipo de tr\u00e1mite no encontrado" }
```

### GET /api/ejecutivo/siguiente

Llama al siguiente turno. Requiere autenticación.

**Response 200 (con turno):**
```json
{
  "mensaje": "Turno llamado exitosamente",
  "turno": { "id": 5, "codigo": "B43", "estado": "llamado", "modulo_nombre": "Modulo 1", ... }
}
```

**Response 200 (sin turnos):**
```json
{ "mensaje": "No hay turnos en espera", "turno": null }
```

**Response 400:**
```json
{ "error": "Ya tienes un turno activo. Finaliza la atencion actual primero." }
```

### POST /api/ejecutivo/iniciar-atencion

Inicia atención escaneando QR. Requiere autenticación.

**Request:**
```json
{ "qr_token": "a1b2c3d4e5f67890a1b2c3d4e5f67890" }
```

**Response 200:**
```json
{
  "mensaje": "Atención iniciada",
  "turno": { "id": 5, "codigo": "B43", "estado": "en_atencion", ... }
}
```

**Response 400:**
```json
{ "error": "El turno B43 no esta en estado 'llamado' (actual: esperando)" }
```

**Response 404:**
```json
{ "error": "Turno no encontrado" }
```

### POST /api/ejecutivo/finalizar-atencion

Finaliza atención y llama al siguiente. Requiere autenticación.

**Request:**
```json
{
  "tipo_atencion": "Consulta",
  "comentarios": "Cliente satisfecho"
}
```

**Response 200 (con siguiente turno):**
```json
{
  "mensaje": "Atención finalizada",
  "turno_completado": { "id": 5, "codigo": "B43", "estado": "completado", ... },
  "turno_siguiente": { "id": 6, "codigo": "B44", "estado": "llamado", ... }
}
```

**Response 200 (sin siguiente turno):**
```json
{
  "mensaje": "Atención finalizada",
  "turno_completado": { ... },
  "turno_siguiente": null
}
```

**Response 400:**
```json
{ "error": "No hay un turno en atencion para este ejecutivo" }
```

### GET /api/ejecutivo/cola

Cola de espera. Requiere autenticación.

**Response 200:**
```json
{
  "cola": [
    {
      "tipo_tramite_id": 1,
      "tipo_tramite": "Creditos",
      "codigo": "A",
      "total": 3,
      "turnos": [{ "codigo": "A5" }, { "codigo": "A6" }, { "codigo": "A7" }]
    }
  ]
}
```

### GET /api/ejecutivo/estado

Estado del ejecutivo. Requiere autenticación.

**Response 200:**
```json
{
  "ejecutivo": { "id": 1, "nombre": "Carlos Munoz", "modulo_nombre": "Modulo 1", ... },
  "turno_activo": {
    "id": 5, "codigo": "B43", "estado": "llamado",
    "tipo_tramite": "Consultas Generales", "rut_cliente": "12345678-5",
    "fecha_llamado": "2025-01-15T10:35:00+00:00"
  }
}
```

### GET /api/tramites

Lista de tipos de trámite.

**Response 200:**
```json
{
  "tramites": [
    { "id": 1, "codigo": "A", "nombre": "Creditos", "prefijo": "A" },
    { "id": 2, "codigo": "B", "nombre": "Consultas Generales", "prefijo": "B" },
    { "id": 3, "codigo": "C", "nombre": "Retiro de Documentos", "prefijo": "C" }
  ]
}
```

### GET /api/modulos

Lista de módulos activos.

**Response 200:**
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

## Campos y Formularios

### Formulario de Login

| Campo | Tipo HTML | Requerido | Restricciones |
|-------|-----------|-----------|---------------|
| Usuario | `text` | Sí | Mín. 1 carácter |
| Contraseña | `password` | Sí | Mín. 1 carácter |

### Formulario de Solicitud de Turno (Kiosco)

| Campo | Tipo | Requerido | Validación |
|-------|------|-----------|------------|
| Tipo de Trámite | Tarjeta clickeable | Sí | ID numérico válido de `tipo_tramite` |
| RUT | `text` con formateo automático | Sí | RUT chileno válido (módulo 11) |

### Formulario de Atención (Ejecutivo)

| Campo | Tipo | Requerido | Valores / Restricciones |
|-------|------|-----------|-------------------------|
| Tipo de Atención | `select` | **Sí** | Consulta, Contratación, Cobranza, Otro |
| Comentarios | `textarea` | No | Texto libre, filas=3, sin límite estricto |

---

## Estados de Turno

| Estado | Descripción | Transiciones Posibles |
|--------|-------------|-----------------------|
| `esperando` | Ticket en cola, no ha sido llamado | `llamado` |
| `llamado` | Ticket asignado a módulo, esperando cliente | `en_atencion` |
| `en_atencion` | Cliente siendo atendido por ejecutivo | `completado` |
| `completado` | Atención finalizada exitosamente | *(terminal)* |
| `cancelado` | Turno cancelado (no implementado en UI) | *(terminal)* |

**Reglas de negocio:**
1. Las transiciones son unidireccionales: no se puede retroceder.
2. Un ejecutivo solo puede tener UN turno activo (estado `llamado` o `en_atencion`).
3. Un turno solo puede ser atendido por el ejecutivo que lo llamó.
4. La cola es FIFO (First In, First Out).
5. Al finalizar un turno, el sistema llama automáticamente al siguiente (si existe).

---

## Códigos de Error

### Errores HTTP

| Código | Significado | Causas Comunes |
|--------|-------------|----------------|
| `200` | OK | Solicitud exitosa |
| `201` | Creado | Turno creado exitosamente |
| `400` | Bad Request | Datos inválidos, RUT incorrecto, parámetros faltantes |
| `401` | Unauthorized | Credenciales inválidas o sesión expirada |
| `404` | Not Found | URL incorrecta, turno no encontrado |
| `500` | Internal Server Error | Error inesperado en el servidor |

### Errores de la API

| Error | Código HTTP | Causa |
|-------|-------------|-------|
| `"Usuario o contraseña incorrectos"` | 401 | Credenciales de login inválidas |
| `"No autenticado"` | 401 | Sesión no iniciada o expirada |
| `"Content-Type debe ser application/json"` | 400 | Header Content-Type incorrecto |
| `"Header X-Requested-With requerido"` | 400 | Header CSRF faltante |
| `"Origen no permitido"` | 400 | CSRF: origen no coincide |
| `"Referer no permitido"` | 400 | CSRF: referer no coincide |
| `"Datos JSON requeridos"` | 400 | Body vacío o no es JSON válido |
| `"Usuario y contraseña requeridos"` | 400 | Campos de login vacíos |
| `"tipo_tramite_id requerido"` | 400 | Falta el tipo de trámite |
| `"RUT requerido"` | 400 | RUT no ingresado |
| `"RUT inválido"` | 400 | RUT no pasa validación chilena |
| `"Tipo de trámite no encontrado"` | 400 | ID de trámite no existe |
| `"Ya tienes un turno activo..."` | 400 | Ejecutivo ya tiene turno en curso |
| `"No hay turnos en espera"` | 200 (con turno=null) | Cola vacía |
| `"Turno no encontrado"` | 404 | qr_token no existe en BD |
| `"El turno X no está en estado 'llamado'"` | 400 | QR escaneado incorrecto |
| `"Este turno fue llamado por otro ejecutivo"` | 400 | QR de otro módulo |
| `"No hay un turno en atención para este ejecutivo"` | 400 | No hay turno activo para finalizar |
| `"Error interno del servidor"` | 500 | Error no manejado (revisar logs) |

---

## Guía de Solución de Problemas

### Problemas de Instalación

| Problema | Solución |
|----------|----------|
| `pip install` falla | Verifique que Python 3.10+ esté instalado. Use `python3 -m pip install -r requirements.txt`. |
| `bcrypt` no se instala | Instale dependencias del sistema: `sudo apt install python3-dev build-essential` (Linux). |
| Puerto 5000 en uso | Use `export PORT=5001` para cambiar de puerto. |
| Error `No module named 'flask'` | Active el entorno virtual o instale dependencias globalmente. |

### Problemas de Base de Datos

| Problema | Solución |
|----------|----------|
| Error `no such table` | Elimine `instance/turnero.db` y reinicie el servidor para regenerar. |
| Error `database is locked` | SQLite no soporta escritura concurrente. Reinicie el servidor. |
| Datos corruptos | Restaure desde backup o elimine la BD y reinicie (se regenera con seed). |

### Problemas de Red

| Problema | Solución |
|----------|----------|
| No se puede conectar desde otro equipo | Verifique que el servidor esté en `0.0.0.0` (no `127.0.0.1`). Revise firewall. |
| Error de conexión desde el kiosco | Verifique que ambos equipos estén en la misma red. |
| SSE no funciona | Algunos proxies (Nginx) requieren `proxy_buffering off;` para SSE. |

### Problemas de Navegador

| Problema | Solución |
|----------|----------|
| Pantalla en blanco | Abra F12 → Console. Busque errores JavaScript. |
| CSS no cargado | Verifique conexión a CDN de Bootstrap. |
| QR no se genera | Verifique que `qrcode.min.js` se cargó (F12 → Network). |
| Cámara no se activa | Chrome: Configuración → Privacidad → Cámara → Permitir. |

---

## Preguntas Frecuentes

### Generales

**P: ¿Cuántos ejecutivos pueden usar el sistema al mismo tiempo?**
R: No hay límite teórico, pero SQLite tiene limitaciones de concurrencia de escritura. Para más de 5 ejecutivos concurrentes o más de 500 turnos/día, considere migrar a PostgreSQL.

**P: ¿Los datos se pierden al reiniciar?**
R: No. Los datos persisten en `instance/turnero.db`. Mientras este archivo no se elimine, los datos sobreviven a reinicios.

**P: ¿Funciona sin internet?**
R: Parcialmente. Las librerías QR (`qrcodejs` y `html5-qrcode`) están vendorizadas en `static/js/` y funcionan sin conexión; Bootstrap se carga desde jsDelivr, así que sin internet la interfaz pierde estilos pero las funciones principales (crear turnos, llamar, escanear, SSE) siguen operativas. Para un despliegue sin internet, descargue Bootstrap y sirva los archivos localmente, ajustando `templates/base.html`.

**P: ¿Cómo cambio el logo de la empresa?**
R: Reemplace el archivo `static/img/logo.svg` con su propio logo en formato SVG. También puede cambiar el nombre de la sucursal en `templates/display.html`.

### Kiosco

**P: ¿Cuántos tipos de trámite puedo tener?**
R: No hay límite, pero la interfaz está diseñada para 3-6 tarjetas. Para más, requeriría modificar el diseño.

**P: ¿El kiosco guarda datos del cliente además del RUT?**
R: No. Solo se almacena el RUT y el tipo de trámite. No se guardan nombres, direcciones ni otros datos personales.

**P: ¿Qué pasa si el cliente ingresa un RUT falso?**
R: El sistema valida el dígito verificador, pero no verifica contra el Registro Civil. Un RUT con formato válido pero inexistente será aceptado.

### Ejecutivo

**P: ¿Puedo atender sin escanear el QR?**
R: No. El escaneo QR es el mecanismo obligatorio para cambiar el estado a `en_atencion`. Sin él, no se puede iniciar la atención formalmente.

**P: ¿Qué pasa si cierro el navegador sin finalizar la atención?**
R: El turno queda en estado `llamado` o `en_atencion`. Al volver a iniciar sesión, el sistema recupera el estado. Si necesita liberar el turno, contacte al administrador.

**P: ¿Puedo llamar un turno sin tener la cámara?**
R: Sí. Puede llamar turnos con el botón "Llamar Siguiente". Para iniciar la atención, necesita la cámara para escanear el QR.

**P: ¿Puedo usar el mismo ejecutivo en dos módulos?**
R: No. Cada ejecutivo está asignado a un módulo específico en la base de datos.

### Display

**P: ¿Puedo mostrar el display en una TV?**
R: Sí. Conecte una computadora (Raspberry Pi, NUC, PC) a la TV vía HDMI. Abra el navegador en pantalla completa (F11).

**P: ¿El display tiene sonido?**
R: No por defecto, pero el código JavaScript incluye soporte para Web Audio API. Puede implementarse fácilmente.

### Administración

**P: ¿Cómo agrego un nuevo ejecutivo?**
R: Actualmente debe hacerlo mediante el script `seed.py` o directamente en la base de datos. No hay interfaz de administración web.

**P: ¿Cómo hago una copia de seguridad?**
R: Copie el archivo `instance/turnero.db` a un lugar seguro. Para restaurar, reemplace el archivo y reinicie el servidor.

**P: ¿Cómo actualizo el sistema?**
R: Reemplace los archivos del proyecto (sin borrar `instance/turnero.db` para conservar datos). Reinicie el servidor.

---

## Mantenimiento

### Respaldos Periódicos

```bash
# Respaldar base de datos
cp instance/turnero.db backups/turnero-$(date +%Y%m%d).db

# Restaurar respaldo
cp backups/turnero-20260101.db instance/turnero.db
```

### Limpieza de Turnos Antiguos

Para evitar que la base de datos crezca indefinidamente, puede eliminar turnos completados antiguos:

```bash
# Acceder a la base de datos
sqlite3 instance/turnero.db

# Eliminar turnos completados de hace más de 30 días
DELETE FROM turno WHERE estado = 'completado' 
AND fecha_completado < datetime('now', '-30 days');

# Vaciar espacio (opcional)
VACUUM;
```

### Logs del Sistema

El servidor Flask imprime logs en la consola estándar. Para guardarlos en un archivo:

```bash
python3 app.py > logs/turnero-$(date +%Y%m%d).log 2>&1
```

---

## Roles y Responsabilidades

El sistema no implementa roles internos: todos los ejecutivos autenticados tienen los mismos permisos. Los roles siguientes son **organizativos** y definen quién hace qué en la operación diaria.

| Rol | Responsabilidad principal | Acceso | Tareas clave |
|---|---|---|---|
| **Administrador de sucursal** | Configurar el servicio y los datos maestros | Servidor y base de datos | Altas de ejecutivos, módulos y trámites; respaldos; cambios de configuración. |
| **Encargado de turno** | Coordinar la sala y resolver excepciones | Consola y display | Reasignar módulos, autorizar cierres, validar que la cola avance. |
| **Ejecutivo** | Atender clientes | Consola (`/ejecutivo`) | Iniciar sesión, llamar, escanear QR, finalizar, cerrar sesión. |
| **Operador de kiosco** | Asistir a los clientes en el kiosco | Kiosco (`/kiosco`) | Explicar el uso, verificar el ticket, limpiar la pantalla entre clientes. |
| **Responsable técnico** | Mantener el servidor y la red | SSH / servidor | Monitoreo, actualizaciones, backups, diagnóstico. |

**Regla de oro:** el administrador no atiende clientes con la cuenta de un ejecutivo y el ejecutivo no modifica la base por su cuenta. La trazabilidad depende de que cada acción se haga desde la interfaz correspondiente.

---

## Procedimientos Operativos

### Apertura de la sucursal

| # | Paso | Responsable | Verificación |
|---|---|---|---|
| 1 | Encender el servidor y confirmar que el servicio Flask responde. | Responsable técnico | `curl -s http://<IP-DEL-SERVIDOR>:5000/api/tramites` devuelve JSON. |
| 2 | Abrir el display en el monitor de sala. | Encargado | Se ve el logo y el mensaje "Sin turnos en espera". |
| 3 | Abrir el kiosco en la tablet y ponerlo en pantalla completa. | Operador de kiosco | Se ven las tarjetas de trámite. |
| 4 | Iniciar sesión en cada consola de ejecutivo. | Cada ejecutivo | La consola muestra su módulo y "Sin turno activo". |
| 5 | Verificar que el display muestra los módulos conectados. | Encargado | Aparecen tantas tarjetas como ejecutivos con sesión. |
| 6 | Probar un turno de extremo a extremo con un RUT ficticio. | Encargado | Ticket con QR, llamado, escaneo y cierre correctos. |
| 7 | Confirmar la hora del servidor. | Responsable técnico | `date` coincide con la hora local de la sucursal. |

**No abrir la sucursal** si el paso 6 falla. Un turno de prueba fallido suele indicar un problema de base, de cámara o de sesión que afectará a todos los clientes.

### Operación normal

- Mantener el display visible y sin ventanas superpuestas.
- Revisar cada hora que la cola del display coincide con la consola.
- No recargar el display durante un llamado: el SSE reconecta, pero se pierde el instante del evento.
- Si un cliente no se presenta tras el llamado, el ejecutivo debe decidir el criterio de la sucursal. El sistema **no tiene rellamado ni cancelación**: la única salida es finalizar la atención (si ya la inició) o, si quedó en `llamado`, pedir al responsable técnico que corrija el estado por SQL.
- No compartir usuarios entre ejecutivos: el historial y el módulo quedarían mezclados.

### Cierre de la sucursal

| # | Paso | Verificación |
|---|---|---|
| 1 | Finalizar todas las atenciones en curso. | Ninguna consola muestra cronómetro activo. |
| 2 | Cerrar sesión en cada consola con el botón **Cerrar sesión**. | El módulo desaparece del display. |
| 3 | Confirmar que no quedan turnos `llamado` ni `en_atencion`. | Consulta SQL de la sección de indicadores. |
| 4 | Cerrar el kiosco y el display. | — |
| 5 | Ejecutar el respaldo diario de la base. | Archivo `.db` con fecha y tamaño razonable. |
| 6 | Registrar incidentes del día. | Bitácora de sucursal. |

Cerrar la pestaña sin usar **Cerrar sesión** deja el módulo visible en el display. Es el incidente más frecuente y se explica en [Contingencia](#contingencia-y-continuidad).

### Relevo de ejecutivo

1. El ejecutivo saliente finaliza su atención y cierra sesión.
2. El entrante inicia sesión con **su propia cuenta**.
3. El encargado verifica que el display actualice el nombre del módulo.
4. Si el saliente dejó un turno `llamado`, el entrante no puede iniciarlo: el token pertenece al ejecutivo anterior. El encargado debe decidir si se atiende igual (corrigiendo el estado) o si el cliente vuelve a la cola.

### Alta de un ejecutivo

No hay panel de administración. El alta se hace en la base, con un hash bcrypt generado por el propio proyecto:

```bash
python3
>>> from app import create_app
>>> from models import db, Ejecutivo
>>> from services.auth_service import hash_password
>>> app = create_app()
>>> with app.app_context():
...     nuevo = Ejecutivo(
...         username="ejecutivo4",
...         password_hash=hash_password("ClaveTemporalCambiar"),
...         nombre="Nombre Apellido",
...         modulo_id=1,
...         activo=True,
...     )
...     db.session.add(nuevo)
...     db.session.commit()
```

Buenas prácticas: usuario en minúsculas, sin espacios; contraseña temporal entregada en mano; cambio inmediato; un usuario por persona. Para dar de baja, marcar `activo = False` en lugar de borrar, así se conserva el historial de turnos.

### Alta de un módulo o trámite

```sql
-- Nuevo módulo
INSERT INTO modulo (nombre, activo) VALUES ('Módulo 4', 1);

-- Nuevo trámite (el prefijo debe ser único y de un carácter)
INSERT INTO tipo_tramite (codigo, nombre, prefijo) VALUES ('D', 'Certificados', 'D');
```

El kiosco toma los trámites de `/api/tramites`; el display solo muestra módulos con un ejecutivo conectado. Tras un alta, recargar el kiosco y el display.

### Checklist diario y semanal

**Diario**

- [ ] Servicio arriba y base accesible.
- [ ] Display, kiosco y consolas abiertos.
- [ ] Turno de prueba completo.
- [ ] Respaldo de la base.
- [ ] Cero turnos en `llamado` o `en_atencion` al cierre.
- [ ] Incidentes registrados.

**Semanal**

- [ ] Revisar crecimiento de `instance/turnero.db`.
- [ ] Verificar espacio en disco (> 20 % libre).
- [ ] Revisar logs en busca de errores 500 repetidos.
- [ ] Confirmar que los respaldos se pueden restaurar en un entorno de prueba.
- [ ] Revisar usuarios activos y módulos huérfanos (`logged_in = 1` sin ejecutivo real).
- [ ] Actualizar dependencias en una rama de prueba, nunca en producción sin validar.

---

## Indicadores Operativos

Los indicadores se calculan sobre la tabla `turno`. No hay dashboard; estas consultas se ejecutan con `sqlite3` o desde un cliente SQL.

| Indicador | Fórmula | Uso |
|---|---|---|
| Turnos del día | `COUNT(*) WHERE date(fecha_creacion) = date('now')` | Volumen de demanda. |
| Turnos completados | `COUNT(*) WHERE estado = 'completado'` | Atenciones efectivas. |
| Tasa de abandono | `(creados - completados) / creados` | Calidad del flujo. |
| Espera media | `avg(fecha_llamado - fecha_creacion)` | Tiempo en cola. |
| Atención media | `avg(fecha_completado - fecha_inicio_atencion)` | Duración del servicio. |
| Cola actual | `COUNT(*) WHERE estado = 'esperando'` | Presión instantánea. |
| Módulos activos | `COUNT(*) WHERE logged_in = 1 AND activo = 1` | Capacidad real. |

Consultas de referencia:

```sql
-- Turnos por estado (foto actual)
SELECT estado, COUNT(*) FROM turno GROUP BY estado;

-- Espera media de los turnos llamados hoy (segundos)
SELECT AVG(strftime('%s', fecha_llamado) - strftime('%s', fecha_creacion))
FROM turno
WHERE date(fecha_creacion) = date('now') AND fecha_llamado IS NOT NULL;

-- Atención media de los turnos completados hoy (segundos)
SELECT AVG(strftime('%s', fecha_completado) - strftime('%s', fecha_inicio_atencion))
FROM turno
WHERE date(fecha_completado) = date('now') AND fecha_inicio_atencion IS NOT NULL;

-- Turnos que quedaron colgados (más de 2 horas sin avanzar)
SELECT codigo, estado, fecha_creacion
FROM turno
WHERE estado IN ('llamado', 'en_atencion')
  AND fecha_creacion < datetime('now', '-2 hours');
```

**Lectura honesta:** con pocos turnos los promedios son ruidosos. Úsalos para detectar tendencias semanales, no para evaluar a una persona en un día. El sistema no mide satisfacción ni calidad percibida.

---

## Contingencia y Continuidad

### Matriz de incidentes

| Incidente | Síntoma | Acción inmediata | Responsable |
|---|---|---|---|
| Servicio caído | Display y kiosco no cargan; consola devuelve error de red | Reiniciar el proceso; revisar logs; si persiste, restaurar desde el último respaldo. | Técnico |
| Base bloqueada o corrupta | Errores 500, `database is locked` | Detener el servicio, copiar el archivo, ejecutar `PRAGMA integrity_check`, restaurar respaldo si falla. | Técnico |
| Corte de internet | Bootstrap sin estilos; el resto funciona | Continuar la operación; el sistema es local. | Cualquiera |
| Cámara no funciona | El escáner no inicia | Iniciar la atención manualmente no está soportado: el flujo exige QR. Alternativa: corregir el estado por SQL o reiniciar el navegador y probar otro dispositivo. | Técnico |
| Display congelado | No cambian los turnos | Recargar la página; si no reconecta, revisar SSE y proxy. | Encargado |
| Módulo fantasma | Tarjeta de un ejecutivo ausente | Pedir logout; si no es posible, `UPDATE ejecutivo SET logged_in = 0 WHERE id = ...`. | Técnico |
| Turno colgado en `llamado` | El cliente no se presentó | Decidir criterio; corregir por SQL (`completado` o volver a `esperando` con nueva fecha). | Encargado + técnico |
| Corte de energía | Todo apagado | Al volver, seguir el procedimiento de apertura; la base persiste. | Técnico |
| QR ilegible | El escáner no lee | Limpiar pantalla, subir brillo, acercar; si el ticket se perdió, el cliente debe solicitar otro turno. | Operador |

### Respaldo y restauración

**Respaldo en caliente.** SQLite permite copiar el archivo si no hay escrituras en curso; para mayor seguridad, usar la API de backup:

```bash
mkdir -p backups
sqlite3 instance/turnero.db ".backup 'backups/turnero-$(date +%Y%m%d-%H%M).db'"
```

**Restauración:**

```bash
# 1. Detener el servicio
# 2. Guardar la base actual por si acaso
mv instance/turnero.db instance/turnero.db.incidente
# 3. Copiar el respaldo
cp backups/turnero-20260101-2000.db instance/turnero.db
# 4. Verificar integridad
sqlite3 instance/turnero.db "PRAGMA integrity_check;"
# 5. Arrancar y probar un turno completo
```

**Objetivos sugeridos:** RPO de 24 horas (respaldo diario) y RTO de 30 minutos para una sucursal. Si el negocio exige menos, aumentar la frecuencia y probar la restauración al menos una vez al mes.

### Plan de comunicación

1. Avisar a los clientes en sala con un mensaje verbal claro.
2. Informar al encargado y al responsable técnico.
3. Si la interrupción supera 15 minutos, pasar a atención manual con tickets de papel y registrar los turnos para carga posterior (no hay importación automática; es una limitación).
4. Al restablecer, comunicar el reinicio de la cola.

---

## Seguridad Operativa

- **Contraseñas:** nunca reutilizar la del correo o la del dominio. Cambiar las claves del seed antes de cualquier uso real. No escribirlas en el repositorio ni en el README.
- **Sesiones:** cerrar sesión al dejar la consola, incluso por unos minutos. La sesión no expira sola y `logged_in` queda persistido.
- **Kiosco:** el cliente no debe poder salir del navegador ni abrir otras pestañas. Usar modo kiosco del sistema operativo.
- **RUT:** el display no lo muestra, pero la API pública lo devuelve. No proyectar herramientas de red ni el JSON en la sala. Para producción, enmascararlo en `to_display_dict()`.
- **QR:** el token es un testigo de posesión. No publicarlo en pantallas ni en chats. Si se sospecha una fuga, el turno debe finalizarse y el cliente solicitar uno nuevo.
- **Servidor:** ejecutar con un usuario sin privilegios, firewall que solo permita la LAN, SSH con clave y sin contraseña. No exponer el servidor de desarrollo a internet.
- **Respaldos:** tratar el archivo `.db` como dato sensible; contiene hashes bcrypt y RUT. Cifrar el medio de respaldo y restringir permisos (`chmod 600`).
- **Incidentes:** si se detecta acceso no autorizado, rotar `SECRET_KEY` (invalida sesiones), cambiar contraseñas, revisar logs y restaurar desde un respaldo confiable.

---

## Glosario

| Término | Definición |
|---|---|
| **API REST** | Interfaz HTTP que devuelve JSON y permite operar el sistema desde el navegador. |
| **bcrypt** | Función de hash lenta con salt, usada para almacenar contraseñas. |
| **Blueprint** | Módulo de rutas de Flask; el proyecto tiene `display`, `kiosco`, `executive` y `api`. |
| **Cola FIFO** | Orden de atención por llegada: el primero en entrar es el primero en salir. |
| **CSRF** | Ataque que fuerza acciones no deseadas desde otro sitio; se mitiga con headers y validación de origen. |
| **Display** | Pantalla pública que muestra módulos y turnos. |
| **Ejecutivo** | Usuario autenticado que atiende clientes desde la consola. |
| **Estado** | Situación de un turno: `esperando`, `llamado`, `en_atencion` o `completado`. |
| **Kiosco** | Interfaz de autoatención donde el cliente solicita su turno. |
| **Módulo** | Puesto de atención física asociado a un ejecutivo. |
| **QR** | Código bidimensional que contiene el `qr_token` del ticket. |
| **qr_token** | Identificador aleatorio de 128 bits que prueba la posesión del ticket. |
| **RUT** | Rol Único Tributario chileno; se valida con módulo 11. |
| **Seed** | Carga inicial de datos de demostración (ejecutivos y trámites). |
| **SSE** | Server-Sent Events; canal unidireccional servidor → navegador sobre HTTP. |
| **Ticket** | Comprobante en pantalla con código, trámite y QR. |
| **Turno** | Unidad de atención identificada por un código (`A1`, `B2`…). |
| **UTC** | Tiempo universal coordinado; la base guarda fechas en UTC. |

---

<div align="center">
  <p><strong>Turnero</strong> — Sistema de Gestión de Turnos v1.1.0</p>
  <p>¿Encontraste un error? Reporta en el repositorio del proyecto.</p>
</div>
