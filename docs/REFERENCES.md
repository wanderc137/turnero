# Referencias — Turnero

**Fuentes técnicas, normativas y de diseño consultadas para construir y documentar el Sistema de Gestión de Turnos.**

Versión: 1.0.0 | Última actualización: Noviembre 2026

---

## Índice

1. [Cómo leer este documento](#cómo-leer-este-documento)
2. [Documentación interna](#documentación-interna)
3. [Backend y persistencia](#backend-y-persistencia)
4. [Tiempo real y frontend](#tiempo-real-y-frontend)
5. [Identificación chilena](#identificación-chilena)
6. [Seguridad](#seguridad)
7. [Despliegue y operación](#despliegue-y-operación)
8. [Herramientas de documentación](#herramientas-de-documentación)
9. [Estándares y licencias](#estándares-y-licencias)
10. [Verificación de enlaces](#verificación-de-enlaces)

---

## Cómo leer este documento

Cada referencia indica **qué se consultó** y **dónde se aplicó** en el proyecto. No es una bibliografía decorativa: los enlaces explican decisiones concretas del código o de los manuales.

Las URLs apuntan a documentación oficial o a fuentes comunmente citadas. Los números de versión corresponden a las versiones usadas o consultadas durante el desarrollo; una versión posterior puede cambiar la redacción aunque el concepto se mantenga.

**Convención de acceso:** todas las fuentes se consultaron entre junio y noviembre de 2026. Si un enlace deja de responder, se recomienda buscar el título exacto en el sitio oficial antes que usar copias informales.

---

## Documentación interna

| Documento | Ruta | Contenido | Para quién |
|---|---|---|---|
| README | [`../README.md`](../README.md) | Visión general, instalación, uso, API, seguridad y límites. | Todos |
| Manual del operador | [`datasheet.md`](datasheet.md) | Especificaciones, procedimientos, contingencia y glosario. | Operación y soporte |
| Guía del desarrollador | [`developer.md`](developer.md) | Arquitectura, rutas, modelos, servicios, SSE y deuda técnica. | Desarrollo |
| Bitácora | [`BITACORA.md`](BITACORA.md) | Decisiones, problemas, descartes y lecciones. | Desarrollo y revisión |
| Manual PDF | [`Manual_Sistema_Turnero.pdf`](Manual_Sistema_Turnero.pdf) | Versión comercial ilustrada del manual. | Difusión |
| Diagramas | [`assets/`](assets/) | Arquitectura, flujo, SSE y despliegue en SVG. | Documentación |

Estos documentos se mantienen sincronizados con el código. Si una referencia interna y el código discrepan, **el código es la fuente de verdad** y la documentación debe corregirse.

---

## Backend y persistencia

### Flask

- **Sitio:** <https://flask.palletsprojects.com/>
- **Versión consultada:** 3.1.x
- **Uso en el proyecto:** application factory (`create_app`), blueprints por interfaz, `render_template`, `jsonify`, manejo de errores con `@app.errorhandler(500)`, sesiones y cookies firmadas.
- **Documentación específica:**
  - Application factories: <https://flask.palletsprojects.com/en/stable/patterns/appfactories/>
  - Blueprints: <https://flask.palletsprojects.com/en/stable/blueprints/>
  - Error handlers: <https://flask.palletsprojects.com/en/stable/errorhandling/>
  - Sessions: <https://flask.palletsprojects.com/en/stable/quickstart/#sessions>

### Flask-SQLAlchemy

- **Sitio:** <https://flask-sqlalchemy.palletsprojects.com/>
- **Versión consultada:** 3.1.x
- **Uso:** inicialización de `db`, modelos declarativos, relaciones, consultas con `query`, `db.session.commit()` y `db.create_all()` en el arranque.
- **Documentación específica:**
  - Quickstart: <https://flask-sqlalchemy.palletsprojects.com/en/stable/quickstart/>
  - Relaciones: <https://flask-sqlalchemy.palletsprojects.com/en/stable/models/#relationships>
  - Contexto de aplicación: <https://flask-sqlalchemy.palletsprojects.com/en/stable/contexts/>

### SQLAlchemy

- **Sitio:** <https://docs.sqlalchemy.org/>
- **Uso:** tipos de columna (`String`, `Boolean`, `DateTime`, `Text`), `ForeignKey`, índices (`index=True`), `unique=True` y ordenamiento.
- **Documentación específica:**
  - Tipos de datos: <https://docs.sqlalchemy.org/en/20/core/type_basics.html>
  - Motor SQLite: <https://docs.sqlalchemy.org/en/20/dialects/sqlite.html>

### SQLite

- **Sitio:** <https://www.sqlite.org/docs.html>
- **Uso:** base de datos embebida en `instance/turnero.db`; transacciones ACID, un escritor a la vez, respaldo con `.backup`, `PRAGMA integrity_check`.
- **Documentación específica:**
  - Atomic commit: <https://www.sqlite.org/atomiccommit.html>
  - Backup API: <https://www.sqlite.org/backup.html>
  - WAL: <https://www.sqlite.org/wal.html>
  - Locks: <https://www.sqlite.org/lockingv3.html>

### bcrypt

- **PyPI:** <https://pypi.org/project/bcrypt/>
- **Uso:** `bcrypt.hashpw` con `gensalt` y `bcrypt.checkpw` en `services/auth_service.py`; nunca se almacena la contraseña en claro.
- **Referencia conceptual:** <https://en.wikipedia.org/wiki/Bcrypt>
- **Nota:** el costo por defecto de la librería es adecuado para un prototipo; para producción se recomienda revisar el parámetro de costo y el tiempo de login esperado.

### Python

- **Sitio:** <https://docs.python.org/3/>
- **Uso:** 3.10+; `venv`, `datetime` con zona UTC, `uuid.uuid4().hex`, `threading.Lock`, `queue.Queue`.
- **Documentación específica:**
  - `venv`: <https://docs.python.org/3/library/venv.html>
  - `datetime`: <https://docs.python.org/3/library/datetime.html>
  - `uuid`: <https://docs.python.org/3/library/uuid.html>

---

## Tiempo real y frontend

### Server-Sent Events (SSE)

- **MDN:** <https://developer.mozilla.org/es/docs/Web/API/Server-sent_events>
- **Especificación WHATWG:** <https://html.spec.whatwg.org/multipage/server-sent-events.html>
- **Uso:** stream `GET /api/turnos/eventos`, formato `data: ...\n\n`, comentario `: heartbeat`, reconexión con `EventSource`.
- **Consulta específica:** <https://developer.mozilla.org/es/docs/Web/API/EventSource>

**Por qué SSE y no WebSocket:** el flujo es unidireccional (servidor → display), SSE viaja sobre HTTP/1.1, no requiere handshake de upgrade y el navegador reintenta solo. WebSocket sería necesario si el display tuviera que enviar comandos.

### Bootstrap

- **Sitio:** <https://getbootstrap.com/docs/5.3/>
- **Versión:** 5.3.3, cargada desde jsDelivr con `integrity` (SRI).
- **Uso:** grid, cards, badges, alerts, botones, utilidades `d-none`, tema claro.
- **Componentes consultados:**
  - Cards: <https://getbootstrap.com/docs/5.3/components/card/>
  - Alerts: <https://getbootstrap.com/docs/5.3/components/alerts/>
  - Utilities: <https://getbootstrap.com/docs/5.3/utilities/display/>

### qrcodejs

- **Repositorio:** <https://github.com/davidshimjs/qrcodejs>
- **Uso:** generación del QR del ticket en `static/js/qrcode.min.js`; nivel de corrección `H`, 200×200 px, colores `#1565C0` sobre blanco.
- **Nota:** la librería está vendorizada; no se carga desde CDN.

### html5-qrcode

- **Repositorio:** <https://github.com/mebjas/html5-qrcode>
- **Uso:** escaneo con cámara en `static/js/html5-qrcode.min.js`; `facingMode: environment`, 10 fps, recuadro 250×250.
- **Documentación:** <https://github.com/mebjas/html5-qrcode#api>
- **Requisito del navegador:** `getUserMedia` exige contexto seguro (`https://` o `localhost`).

### JavaScript

- **MDN:** <https://developer.mozilla.org/es/docs/Web/JavaScript>
- **Uso:** IIFEs con `'use strict'`, `fetch`, `EventSource`, `setInterval`, manipulación del DOM.
- **Consultas específicas:**
  - `fetch`: <https://developer.mozilla.org/es/docs/Web/API/Fetch_API>
  - `EventSource`: <https://developer.mozilla.org/es/docs/Web/API/EventSource>

### Jinja2

- **Sitio:** <https://jinja.palletsprojects.com/>
- **Uso:** herencia de `base.html`, bloques `content`, `extra_head` y `extra_scripts`, interpolación de datos del ejecutivo.
- **Documentación:** <https://jinja.palletsprojects.com/en/stable/templates/>

---

## Identificación chilena

### RUT y módulo 11

- **Servicio de Impuestos Internos (SII):** <https://www.sii.cl/>
- **Referencia del algoritmo:** <https://es.wikipedia.org/wiki/Anexo:Algoritmo_para_obtener_el_d%C3%ADgito_verificador>
- **Uso:** `validar_rut` en `services/turno_service.py` y `validarRUT` en `static/js/kiosco.js`.

**Resumen del algoritmo aplicado:**

1. Se eliminan puntos, guiones y espacios.
2. El cuerpo son todos los dígitos menos el último.
3. Se multiplica cada dígito del cuerpo, de derecha a izquierda, por la secuencia cíclica 2, 3, 4, 5, 6, 7.
4. Se suman los productos y se calcula `resto = suma % 11`.
5. `dv = 11 - resto`; si `dv == 11` → `0`; si `dv == 10` → `K`; si no, el dígito.
6. Se compara con el dígito verificador ingresado, en mayúscula.

**Ejemplo válido ficticio:** `12.345.678-5`. **Ejemplo inválido:** `12.345.678-9`.

**Advertencia:** el RUT es un dato personal. El proyecto lo usa solo para identificar el turno; no lo valida contra el SII ni verifica que la persona exista. Para producción corresponde evaluar base legal, minimización y enmascaramiento.

### Normativa de protección de datos

- **Ley 19.628 (Chile), protección de la vida privada:** <https://www.bcn.cl/leychile/navegar?idNorma=141599>
- **Ley 21.719 (Chile), nueva ley de datos personales:** <https://www.bcn.cl/leychile/navegar?idNorma=1209272>
- **Uso:** criterio para limitar la exposición del RUT en el display y para la recomendación de enmascararlo.

---

## Seguridad

### OWASP

- **Sitio:** <https://owasp.org/>
- **Uso:** modelo de amenaza, CSRF, almacenamiento de contraseñas, configuración segura y manejo de errores.
- **Referencias específicas:**
  - Top 10: <https://owasp.org/www-project-top-ten/>
  - Password Storage Cheat Sheet: <https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html>
  - CSRF Prevention Cheat Sheet: <https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html>
  - Session Management Cheat Sheet: <https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html>

### Cabeceras y cookies

- **MDN Set-Cookie:** <https://developer.mozilla.org/es/docs/Web/HTTP/Headers/Set-Cookie>
- **MDN HttpOnly:** <https://developer.mozilla.org/es/docs/Web/HTTP/Cookies>
- **Uso:** la sesión de Flask usa cookie firmada; `HttpOnly` viene por defecto, `Secure` requiere HTTPS y no está configurado en el prototipo.

### CORS y origen

- **MDN CORS:** <https://developer.mozilla.org/es/docs/Web/HTTP/CORS>
- **Uso:** `csrf_protected` compara `Origin`/`Referer` con `request.host_url`; no es un CORS completo, es una verificación de origen para mutaciones.

### Rate limiting

- **Flask-Limiter:** <https://flask-limiter.readthedocs.io/>
- **Uso:** recomendación para producción; no implementado.

---

## Despliegue y operación

### Gunicorn

- **Sitio:** <https://gunicorn.org/>
- **Documentación:** <https://docs.gunicorn.org/en/stable/>
- **Uso:** recomendación de WSGI para producción. Para SSE, un worker con threads o un bus externo; ver [SSE en múltiples workers](developer.md#sse-en-múltiples-workers).

### Nginx

- **Sitio:** <https://nginx.org/>
- **Documentación:** <https://nginx.org/en/docs/>
- **Uso:** proxy inverso, TLS, `proxy_buffering off` para SSE, `proxy_read_timeout` largo.
- **Referencia de buffering:** <https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_buffering>

### Let's Encrypt / Certbot

- **Sitio:** <https://certbot.eff.org/>
- **Uso:** HTTPS gratuito para habilitar cámara y proteger credenciales.
- **Requisito:** un dominio válido; una IP privada no puede emitir certificado público.

### systemd

- **Documentación:** <https://www.freedesktop.org/software/systemd/man/systemd.service.html>
- **Uso:** unidad de servicio para arrancar Gunicorn y reiniciar ante fallos.

### PostgreSQL

- **Sitio:** <https://www.postgresql.org/docs/>
- **Uso:** alternativa a SQLite si la concurrencia de escritura o el multi-sucursal lo exigen.
- **Driver:** <https://pypi.org/project/psycopg/>

### Docker

- **Documentación:** <https://docs.docker.com/>
- **Uso:** recomendación de empaquetado; no implementado. El volumen persistente debe cubrir `instance/`.

---

## Herramientas de documentación

### Mermaid

- **Sitio:** <https://mermaid.js.org/>
- **Uso:** diagramas de secuencia y de estados en Markdown. GitHub los renderiza de forma nativa.
- **Sintaxis:** <https://mermaid.js.org/syntax/sequenceDiagram.html> y <https://mermaid.js.org/syntax/stateDiagram.html>

### SVG

- **MDN SVG:** <https://developer.mozilla.org/es/docs/Web/SVG>
- **Uso:** diagramas de `docs/assets/` escritos a mano, sin recursos externos, con fondo oscuro y texto legible.
- **Validación:** `python3 -c "import xml.etree.ElementTree as ET; ET.parse('archivo.svg')"`.

### Shields.io

- **Sitio:** <https://shields.io/>
- **Uso:** badges del README (Python, Flask, SQLite, Bootstrap, licencia, estado).

### fpdf2 y Playwright

- **fpdf2:** <https://py-pdf.github.io/fpdf2/>
- **Playwright:** <https://playwright.dev/python/>
- **Uso:** `generate_marketing_pdf.py` genera el manual PDF con capturas de pantalla. Son dependencias de desarrollo, no de ejecución.

---

## Estándares y licencias

### Markdown

- **CommonMark:** <https://commonmark.org/>
- **GitHub Flavored Markdown:** <https://github.github.com/gfm/>
- **Uso:** README, manuales y este documento. Las tablas, bloques de código y anclas siguen GFM.

### SemVer

- **Sitio:** <https://semver.org/lang/es/>
- **Uso:** versión 1.0.0 del proyecto y 1.1.0 de la documentación ampliada.

### Licencia MIT

- **Texto oficial:** <https://opensource.org/license/mit>
- **Uso:** [`../LICENSE`](../LICENSE), con copyright 2026 wanderc137.
- **Alcance:** permite uso, copia, modificación y distribución con atribución; se entrega "tal cual", sin garantía.

### Convenciones de commits

- **Conventional Commits:** <https://www.conventionalcommits.org/es/v1.0.0/>
- **Uso:** mensajes como `feat:`, `fix:`, `docs:`.

---

## Verificación de enlaces

Antes de publicar una nueva versión de la documentación:

```bash
# Listar todas las URLs externas del README y docs
grep -RhoE 'https?://[^ )>]+' README.md docs/*.md | sort -u

# Verificar respuesta HTTP (una por una)
while read -r url; do
  code=$(curl -o /dev/null -s -w '%{http_code}' -L --max-time 10 "$url")
  echo "$code  $url"
done < <(grep -RhoE 'https?://[^ )>]+' README.md docs/*.md | sort -u)
```

Criterios:

- `200`: enlace vivo.
- `301`/`302`: redirección aceptable; actualizar la URL canónica.
- `403`: puede ser bloqueo anti-bot; verificar en navegador antes de eliminarlo.
- `404`: enlace roto; corregir o retirar.

**Nota de honestidad:** este documento incluye fuentes que explican conceptos, no una auditoría legal ni una certificación técnica. Las decisiones de cumplimiento normativo requieren asesoría especializada.

---

<div align="center">

**Turnero** — Referencias técnicas v1.0.0

[Volver al README](../README.md) · [Manual del operador](datasheet.md) · [Guía del desarrollador](developer.md)

</div>
