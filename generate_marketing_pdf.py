#!/usr/bin/env python3
"""
Genera un PDF comercial con capturas de pantalla del Sistema Turnero.
Inicia el servidor, toma screenshots, y genera el documento.
"""

import os, sys, time, json, subprocess, signal, threading, atexit
from pathlib import Path
from fpdf import FPDF

BASE = Path(__file__).parent
OUTPUT = BASE / "docs" / "Manual_Sistema_Turnero.pdf"
SCREENSHOTS_DIR = BASE / "docs" / "screenshots"
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
os.makedirs(BASE / "docs", exist_ok=True)

# ── Colors ──
BLUE = "#1565C0"
DARK_BLUE = "#0D47A1"
WHITE = "#FFFFFF"
GRAY = "#757590"
LIGHT_GRAY = "#F8F9FA"
DARK = "#212529"
ACCENT = "#FF8F00"

def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

# ── Screenshots ──
server_proc = None

def start_server():
    global server_proc
    env = os.environ.copy()
    env["PORT"] = "9876"
    server_proc = subprocess.Popen(
        [sys.executable, "app.py"],
        cwd=str(BASE),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for i in range(30):
        time.sleep(0.5)
        try:
            import urllib.request
            urllib.request.urlopen("http://127.0.0.1:9876/", timeout=2)
            return True
        except:
            continue
    return False

def stop_server():
    global server_proc
    if server_proc:
        server_proc.terminate()
        try:
            server_proc.wait(timeout=5)
        except:
            server_proc.kill()

atexit.register(stop_server)

def take_screenshots():
    """Toma screenshots de todas las pantallas usando playwright."""
    from playwright.sync_api import sync_playwright

    screenshots = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            device_scale_factor=2,
        )
        page = context.new_page()

        # ── 1. Display público ──
        print("[1/6] Display público...")
        page.goto("http://127.0.0.1:9876/", wait_until="load", timeout=15000)
        time.sleep(2)
        page.screenshot(path=str(SCREENSHOTS_DIR / "01_display.png"), full_page=True)
        screenshots["display"] = str(SCREENSHOTS_DIR / "01_display.png")

        # ── 2. Kiosco - Paso 1 ──
        print("[2/6] Kiosco paso 1 (seleccion)...")
        page.goto("http://127.0.0.1:9876/kiosco", wait_until="load", timeout=15000)
        time.sleep(2)
        page.screenshot(path=str(SCREENSHOTS_DIR / "02_kiosco_paso1.png"), full_page=True)
        screenshots["kiosco1"] = str(SCREENSHOTS_DIR / "02_kiosco_paso1.png")

        # ── 3. Kiosco - Paso 2 (RUT) ──
        print("[3/6] Kiosco paso 2 (RUT)...")
        # Click en primera tarjeta de tramite para avanzar al paso 2
        try:
            page.click(".tramite-card:first-child", timeout=3000)
            time.sleep(1)
        except:
            pass
        page.screenshot(path=str(SCREENSHOTS_DIR / "03_kiosco_paso2.png"), full_page=True)
        screenshots["kiosco2"] = str(SCREENSHOTS_DIR / "03_kiosco_paso2.png")

        # ── 4. Login ──
        print("[4/6] Login ejecutivo...")
        page.goto("http://127.0.0.1:9876/login", wait_until="load", timeout=15000)
        time.sleep(1)
        page.screenshot(path=str(SCREENSHOTS_DIR / "04_login.png"), full_page=True)
        screenshots["login"] = str(SCREENSHOTS_DIR / "04_login.png")

        # ── 5. Consola ejecutiva (logueada) ──
        print("[5/6] Consola ejecutiva...")
        page.goto("http://127.0.0.1:9876/ejecutivo", wait_until="load", timeout=15000)
        page.wait_for_selector("#username", timeout=10000)
        # llenar formulario login
        page.fill("#username", "carlos")
        page.fill("#password", "carlos123")
        page.click("#login-btn")
        page.wait_for_selector("#btn-llamar-siguiente", timeout=10000)
        time.sleep(1)
        page.screenshot(path=str(SCREENSHOTS_DIR / "05_consola.png"), full_page=True)
        screenshots["consola"] = str(SCREENSHOTS_DIR / "05_consola.png")

        # ── 6. Consola con cola y llamando ──
        print("[6/6] Consola con llamada activa...")
        # Primero crear un turno desde kiosco
        page.goto("http://127.0.0.1:9876/kiosco", wait_until="load", timeout=15000)
        page.wait_for_selector(".tramite-card", timeout=10000)
        time.sleep(1)
        page.click(".tramite-card:first-child")
        time.sleep(0.5)
        # llenar RUT valido
        page.wait_for_selector("#rut-input", timeout=5000)
        page.fill("#rut-input", "11111111-1")
        time.sleep(0.3)
        page.click("#btn-solicitar-turno")
        page.wait_for_selector("#btn-nuevo-turno", timeout=10000)
        time.sleep(1)

        # ir a consola y llamar siguiente
        page.goto("http://127.0.0.1:9876/ejecutivo", wait_until="load", timeout=15000)
        page.wait_for_selector("#btn-llamar-siguiente", timeout=10000)
        time.sleep(0.5)
        page.click("#btn-llamar-siguiente")
        time.sleep(2)
        page.screenshot(path=str(SCREENSHOTS_DIR / "06_consola_atencion.png"), full_page=True)
        screenshots["consola_atencion"] = str(SCREENSHOTS_DIR / "06_consola_atencion.png")

        browser.close()

    return screenshots


# ── PDF Class ──
class ComercialPDF(FPDF):
    def __init__(self):
        super().__init__("P", "mm", "A4")
        self.set_auto_page_break(auto=True, margin=25)

    def header(self):
        if self.page_no() <= 1:
            return
        self.set_font("Helvetica", "I", 7.5)
        self.set_text_color(*hex_rgb(GRAY))
        self.cell(0, 5, "Sistema Turnero - Gestion Inteligente de Turnos", align="L")
        self.cell(0, 5, f"Pág. {self.page_no()}", align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*hex_rgb(BLUE))
        self.set_line_width(0.3)
        self.line(10, 12, 200, 12)
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(*hex_rgb(GRAY))
        self.cell(0, 10, f"Documento generado el {time.strftime('%d/%m/%Y')}", align="C")

    def seccion_titulo(self, num, titulo):
        self.ln(3)
        self.set_font("Helvetica", "B", 20)
        self.set_text_color(*hex_rgb(DARK_BLUE))
        self.cell(0, 11, f"{num}. {titulo}", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*hex_rgb(BLUE))
        self.set_line_width(0.7)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def texto(self, txt):
        self.set_font("Helvetica", "", 10.5)
        self.set_text_color(*hex_rgb(DARK))
        self.multi_cell(0, 5.8, txt)
        self.ln(2)

    def subtitulo(self, txt):
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*hex_rgb(BLUE))
        self.ln(2)
        self.cell(0, 8, txt, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def destacado(self, txt):
        self.set_fill_color(*hex_rgb(LIGHT_GRAY))
        self.set_draw_color(*hex_rgb(BLUE))
        self.set_line_width(0.4)
        y0 = self.get_y()
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*hex_rgb(DARK_BLUE))
        self.cell(0, 7, "  " + txt, new_x="LMARGIN", new_y="NEXT", fill=True)
        self.ln(2)

    def bullet_list(self, items):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*hex_rgb(DARK))
        for item in items:
            self.set_x(self.l_margin + 5)
            self.cell(4, 5.5, "-")
            self.set_x(self.l_margin + 9)
            self.multi_cell(0, 5.5, item)
            self.set_x(self.l_margin)
        self.ln(2)

    def screenshot(self, path, caption="", w=170):
        if not os.path.exists(path):
            self.texto(f"[Imagen no disponible: {path}]")
            return
        self.ln(2)
        x_center = (210 - w) / 2
        self.image(path, x=x_center, w=w)
        if caption:
            self.set_font("Helvetica", "I", 8.5)
            self.set_text_color(*hex_rgb(GRAY))
            self.ln(2)
            self.cell(0, 5, caption, align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

    def check(self, txt):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*hex_rgb(DARK))
        self.set_x(self.l_margin + 5)
        self.set_text_color(46, 125, 50)
        self.cell(5, 5.5, "v")
        self.set_text_color(*hex_rgb(DARK))
        self.multi_cell(0, 5.5, txt)
        self.set_x(self.l_margin)

    def spacer(self, h=5):
        self.ln(h)


# ── BUILD PDF ──
def build_pdf(screenshots):
    pdf = ComercialPDF()

    # =========== PORTADA ===========
    pdf.add_page()
    pdf.set_fill_color(*hex_rgb(BLUE))
    pdf.rect(0, 0, 210, 297, style="F")
    pdf.ln(55)
    pdf.set_font("Helvetica", "B", 38)
    pdf.set_text_color(*hex_rgb(WHITE))
    pdf.cell(0, 14, "SISTEMA TURNERO", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 20)
    pdf.cell(0, 12, "Gestión Inteligente de Turnos", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 9, "para Sucursales de Atención al Cliente", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(12)
    pdf.set_draw_color(*hex_rgb(WHITE))
    pdf.set_line_width(0.6)
    pdf.line(65, pdf.get_y(), 145, pdf.get_y())
    pdf.ln(12)
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, "Kiosco de Autoservicio  |  Consola Ejecutiva  |  Pantalla Pública", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, "Tres interfaces integradas en una plataforma moderna y eficiente", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(35)
    pdf.set_font("Helvetica", "I", 9)
    pdf.cell(0, 6, "www.turnero.cl  |  Versión 1.0", align="C", new_x="LMARGIN", new_y="NEXT")

    # =========== PÁG 2: INTRO ===========
    pdf.add_page()
    pdf.seccion_titulo("1", "¿Qué es el Sistema Turnero?")
    pdf.texto(
        "El Sistema Turnero es una plataforma digital integral que transforma la experiencia de atención "
        "al cliente en sucursales físicas. Olvídese de los tickets de papel, las confuciones con los números "
        "y las largas esperas sin información. Con Turnero, todo el proceso de gestión de turnos es digital, "
        "transparente y en tiempo real."
    )
    pdf.texto(
        "Nuestra solución cubre todo el ciclo de atención: el cliente solicita su turno en un kiosco táctil, "
        "recibe un código QR único, sigue el llamado en una pantalla pública, y el ejecutivo gestiona la "
        "atención desde una consola web moderna. Todo sincronizado al instante."
    )

    pdf.destacado("Beneficios Clave")
    pdf.bullet_list([
        "Sin papeles: elimina los tickets impresos y el desperdicio de recursos",
        "Tiempo real: display público actualizado al instante vía SSE",
        "Cero confusiones: cada cliente tiene un QR único e intransferible",
        "Eficiencia operativa: ejecutivos llaman y gestionan turnos con un clic",
        "Métrica y control: registro completo de tiempos de atención",
        "Fácil de usar: interfaz táctil intuitiva para clientes de todas las edades",
    ])

    pdf.destacado("¿Cómo funciona en 3 pasos?")
    pdf.bullet_list([
        "PASO 1 - El cliente solicita su turno en el kiosco digital (menos de 30 segundos)",
        "PASO 2 - La pantalla pública muestra en vivo qué turno está siendo llamado y a qué módulo dirigirse",
        "PASO 3 - El ejecutivo atiende, escanea el QR y finaliza la atención con un formulario simple",
    ])

    # =========== PÁG 3: ARQUITECTURA ===========
    pdf.add_page()
    pdf.seccion_titulo("2", "Visión General del Sistema")
    pdf.texto(
        "El sistema está compuesto por tres interfaces de usuario independientes que se comunican "
        "con un único servidor central. Esto garantiza sincronización perfecta entre todos los "
        "componentes sin necesidad de configuraciones complejas."
    )

    pdf.subtitulo("Las Tres Interfaces")
    pdf.bullet_list([
        "Kiosco de Autoservicio: pantalla táctil para que los clientes soliciten turnos",
        "Consola Ejecutiva: dashboard para que el personal gestione la atención",
        "Pantalla Pública: monitor/TV en sala de espera con información en vivo",
    ])

    pdf.destacado("Tecnología Moderna y Confiable")
    pdf.texto(
        "Turnero está construido con tecnologías web de última generación: Python Flask en el backend, "
        "Bootstrap 5 en el frontend, comunicación en tiempo real mediante Server-Sent Events, y "
        "generación/escaneo de códigos QR integrados. Todo funciona en un solo servidor, "
        "ideal para instalaciones en sucursales con recursos limitados."
    )

    # =========== PÁG 4: DISPLAY ===========
    pdf.add_page()
    pdf.seccion_titulo("3", "Pantalla Pública (Sala de Espera)")
    pdf.texto(
        "Diseñada para monitores o televisores de gran formato, la pantalla pública muestra en tiempo real "
        "el estado de cada módulo de atención. Los clientes pueden ver claramente qué turno está siendo "
        "llamado y a qué módulo deben dirigirse, eliminando la ansiedad de la espera."
    )
    pdf.screenshot(screenshots.get("display", ""), "Pantalla pública mostrando módulos y cola de espera", w=175)
    pdf.texto(
        "Características destacadas: indicador visual 'Llamando...' con animación de pulso para captar la "
        "atención, códigos de ticket en tamaño gigante para visibilidad desde lejos, y un overlay inteligente "
        "que muestra 'Sin turnos en espera' cuando no hay actividad."
    )

    # =========== PÁG 5-6: KIOSCO ===========
    pdf.add_page()
    pdf.seccion_titulo("4", "Kiosco de Autoservicio")
    pdf.texto(
        "El kiosco digital es la puerta de entrada al sistema. Con una interfaz táctil diseñada para ser "
        "intuitiva, los clientes pueden solicitar su turno en menos de 30 segundos siguiendo tres simples pasos."
    )

    pdf.subtitulo("Paso 1: Seleccione su trámite")
    pdf.screenshot(screenshots.get("kiosco1", ""), "Paso 1 - Selección del tipo de trámite", w=175)
    pdf.texto(
        "El cliente elige entre los tipos de trámite disponibles (Créditos, Consultas Generales, "
        "Retiro de Documentos, etc.). Cada opción se presenta con un icono claro y un código "
        "alfabético (A, B, C) para identificación rápida."
    )

    pdf.add_page()
    pdf.subtitulo("Paso 2: Ingrese su RUT")
    pdf.screenshot(screenshots.get("kiosco2", ""), "Paso 2 - Ingreso de RUT con formato automático", w=175)
    pdf.texto(
        "El sistema formatea automáticamente el RUT mientras el cliente escribe, insertando puntos y guión "
        "en las posiciones correctas. La validación del dígito verificador (módulo 11) se realiza al instante, "
        "tanto en el kiosco como en el servidor, garantizando que solo se registren RUT válidos."
    )

    pdf.subtitulo("Paso 3: Reciba su ticket")
    pdf.texto(
        "El kiosco genera un ticket digital con un código único (ej: B43) y un código QR asociado. "
        "El cliente solo debe presentar este QR al ejecutivo cuando sea llamado. El código QR contiene "
        "un token único e irrepetible, garantizando la seguridad y autenticidad de cada turno."
    )

    # =========== PÁG 7: LOGIN ===========
    pdf.add_page()
    pdf.seccion_titulo("5", "Acceso Ejecutivo (Login)")
    pdf.screenshot(screenshots.get("login", ""), "Pantalla de inicio de sesión para ejecutivos", w=150)
    pdf.texto(
        "Los ejecutivos acceden a su consola personal mediante un formulario de inicio de sesión seguro. "
        "Cada ejecutivo tiene credenciales únicas y está asociado a un módulo de atención específico. "
        "El diseño limpio y profesional permite un acceso rápido y sin distracciones."
    )

    # =========== PÁG 8-9: CONSOLA EJECUTIVA ===========
    pdf.add_page()
    pdf.seccion_titulo("6", "Consola Ejecutiva")
    pdf.texto(
        "El corazón operativo del sistema. Desde su dashboard, el ejecutivo gestiona todo el ciclo "
        "de atención: llama al siguiente cliente, escanea su QR para iniciar la atención, y finaliza "
        "registrando el tipo de atención y comentarios. Todo con una interfaz clara y eficiente."
    )
    pdf.screenshot(screenshots.get("consola", ""), "Dashboard ejecutivo con panel de atención y cola de espera", w=175)
    pdf.texto(
        "El panel de atención cambia dinámicamente entre tres vistas: 'Sin turno activo' (con botón para llamar), "
        "'Turno llamado' (esperando al cliente), y 'Turno en atención' (con cronómetro en vivo y formulario "
        "de finalización)."
    )

    pdf.add_page()
    pdf.subtitulo("Atención en Acción")
    pdf.screenshot(screenshots.get("consola_atencion", ""), "Consola con turno llamado y cola de espera visible", w=175)
    pdf.texto(
        "En la parte lateral, el escáner QR integrado permite al ejecutivo escanear el código del cliente "
        "usando la cámara del dispositivo. Al detectar un QR válido, la atención comienza automáticamente "
        "y el cronómetro se activa. En la parte inferior, la cola de espera muestra todos los turnos "
        "pendientes agrupados por tipo de trámite, con contadores en tiempo real."
    )

    pdf.destacado("Funcionalidades Clave de la Consola")
    pdf.bullet_list([
        "Llamar siguiente turno automáticamente desde la cola",
        "Escáner QR con cámara (compatible con notebooks, tablets y PCs con cámara)",
        "Cronómetro de atención en vivo para medir tiempos",
        "Formulario de finalización con tipo de atención y notas",
        "Cola de espera actualizada automáticamente cada 15 segundos",
        "Cierre de sesión seguro con un clic",
    ])

    # =========== PÁG 10: FLUJO COMPLETO ===========
    pdf.add_page()
    pdf.seccion_titulo("7", "El Ciclo de Atención Paso a Paso")
    pdf.texto(
        "Desde que el cliente ingresa a la sucursal hasta que la atención finaliza, el sistema Turnero "
        "orquesta cada etapa del proceso de forma automática y sincronizada."
    )

    pdf.subtitulo("Paso 1 - Solicitud")
    pdf.texto("El cliente usa el kiosco táctil, selecciona su trámite e ingresa su RUT. En segundos, recibe "
              "su ticket con QR único. El sistema registra el turno y lo muestra en la cola de espera.")

    pdf.subtitulo("Paso 2 - Llamado")
    pdf.texto("El ejecutivo presiona 'Llamar Siguiente Turno'. El sistema asigna el turno más antiguo a su "
              "módulo. La pantalla pública se actualiza al instante mostrando 'Llamando...' con el código "
              "del ticket en tamaño gigante.")

    pdf.subtitulo("Paso 3 - Atención")
    pdf.texto("El cliente se acerca al módulo, el ejecutivo escanea su QR y la atención comienza. "
              "El display público cambia a 'En Atención' y la consola muestra el cronómetro en vivo.")

    pdf.subtitulo("Paso 4 - Finalización")
    pdf.texto("El ejecutivo registra el tipo de atención y finaliza. El sistema completa el turno y, "
              "si hay más clientes esperando, llama automáticamente al siguiente. El ciclo se repite "
              "de forma fluida y eficiente.")

    pdf.destacado("Beneficios del Ciclo Automatizado")
    pdf.bullet_list([
        "Tiempos de espera reducidos: el sistema optimiza la asignación de turnos",
        "Trazabilidad completa: cada turno tiene su historial con fechas y ejecutivo responsable",
        "Sin errores humanos: el QR elimina confusiones de números o nombres",
        "Cliente informado: la pantalla pública brinda visibilidad total del proceso",
    ])

    # =========== PÁG 11: TECNOLOGÍA ===========
    pdf.add_page()
    pdf.seccion_titulo("8", "Especificaciones Técnicas")

    pdf.subtitulo("Requisitos del Sistema")
    pdf.bullet_list([
        "Servidor: cualquier equipo con Python 3.10+ (desde una Raspberry Pi hasta un servidor dedicado)",
        "Kiosco: navegador web en modo quiosco (tablet, PC táctil, o smartphone)",
        "Display público: cualquier monitor o TV con navegador web",
        "Consola ejecutiva: PC, notebook o tablet con cámara para escanear QR",
        "Red: red local (intranet) - no requiere internet para funcionar",
    ])

    pdf.subtitulo("Seguridad Integrada")
    pdf.bullet_list([
        "Contraseñas protegidas con bcrypt (estándar de la industria)",
        "Protección CSRF en todas las operaciones POST",
        "Validación de RUT en cliente y servidor (módulo 11)",
        "Tokens QR únicos de 32 caracteres hexadecimales",
        "Sesiones firmadas criptográficamente",
    ])

    pdf.subtitulo("Tecnologías Utilizadas")
    pdf.bullet_list([
        "Backend: Python Flask con SQLAlchemy",
        "Base de datos: SQLite (sin necesidad de instalar motores adicionales)",
        "Frontend: HTML5, CSS3, Bootstrap 5, JavaScript moderno",
        "Tiempo real: Server-Sent Events (SSE) para actualizaciones instantáneas",
        "QR: qrcodejs (generación) + html5-qrcode (escaneo con cámara)",
    ])

    # =========== PÁG 12: CIERRE ===========
    pdf.add_page()
    pdf.set_fill_color(*hex_rgb(BLUE))
    pdf.rect(0, 0, 210, 297, style="F")
    pdf.ln(60)
    pdf.set_font("Helvetica", "B", 28)
    pdf.set_text_color(*hex_rgb(WHITE))
    pdf.cell(0, 14, "¿Listo para modernizar", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 14, "su atención al cliente?", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(12)
    pdf.set_draw_color(*hex_rgb(WHITE))
    pdf.set_line_width(0.5)
    pdf.line(70, pdf.get_y(), 140, pdf.get_y())
    pdf.ln(12)
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 7, "El Sistema Turnero es la solución que su sucursal necesita:", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 11)
    features = [
        "Fácil de instalar y configurar",
        "Intuitivo para clientes y ejecutivos",
        "Sin costos recurrentes de licencia",
        "Funciona sin conexión a internet",
        "Personalizable con los colores y logo de su empresa",
    ]
    for f in features:
        pdf.cell(0, 8, f"  {f}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(15)
    pdf.set_font("Helvetica", "I", 10)
    pdf.cell(0, 7, "Sistema Turnero v1.0  |  Documentación Comercial", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.output(str(OUTPUT))
    print(f"\nPDF generado exitosamente: {OUTPUT}")
    print(f"Tamaño: {os.path.getsize(OUTPUT) / 1024:.0f} KB")


# ── MAIN ──
if __name__ == "__main__":
    print("Iniciando servidor...")
    if not start_server():
        print("ERROR: No se pudo iniciar el servidor")
        sys.exit(1)
    print("Servidor listo en http://127.0.0.1:9876")

    print("Tomando screenshots...")
    try:
        screenshots = take_screenshots()
    finally:
        stop_server()

    print("Generando PDF comercial...")
    build_pdf(screenshots)

    # Cleanup
    for f in SCREENSHOTS_DIR.glob("*.png"):
        f.unlink()
    SCREENSHOTS_DIR.rmdir()
    print("Screenshots temporales eliminados.")
