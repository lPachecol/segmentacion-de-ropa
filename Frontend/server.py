#!/usr/bin/env python3
"""
Servidor HTTP simple para servir el frontend
Ubicación: /Frontend/server.py

Uso:
    python server.py

Luego abre: http://localhost:8080
"""

import http.server
import socketserver
import os
from pathlib import Path
import webbrowser
import threading
import time

PORT = 8080
HOST = "localhost"

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Agregar headers CORS para desarrollo
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_GET(self):
        # Responder favicon.ico para evitar 404 en el navegador
        if self.path == "/favicon.ico":
            svg = (
                "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'>"
                "<rect width='32' height='32' rx='6' ry='6' fill='#4F46E5'/>"
                "<text x='16' y='21' text-anchor='middle' font-size='16' fill='white' font-family='Arial, Helvetica, sans-serif'>FS</text>"
                "</svg>"
            )
            data = svg.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'image/svg+xml')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        # Para cualquier otra ruta usa el comportamiento por defecto
        return super().do_GET()

    def log_message(self, format, *args):
        # Mejorar logs - Ignorar favicon.ico
        if len(args) > 0:
            first_arg = str(args[0])
            if "favicon.ico" in first_arg:
                return  # Ignorar logs de favicon
            print(f"[{self.client_address[0]}] {format % args}")

def open_browser():
    """Abre el navegador después de iniciar el servidor"""
    time.sleep(1)  # Esperar a que el servidor esté listo
    url = f"http://{HOST}:{PORT}"
    print(f"\n✅ Abriendo navegador: {url}\n")
    webbrowser.open(url)

def main():
    # Cambiar a la carpeta del script
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    # Crear servidor
    with socketserver.TCPServer((HOST, PORT), MyHTTPRequestHandler) as httpd:
        url = f"http://{HOST}:{PORT}"

        print("=" * 60)
        print("🚀 Servidor HTTP iniciado")
        print("=" * 60)
        print(f"📍 Dirección: {url}")
        print(f"📁 Carpeta: {script_dir}")
        print("\n✨ Archivos disponibles:")
        print("   - index.html")
        print("   - style.css")
        print("   - script.js")
        print("\n⏹️  Presiona CTRL+C para detener el servidor")
        print("=" * 60 + "\n")

        # Abrir navegador en un thread separado
        thread = threading.Thread(target=open_browser, daemon=True)
        thread.start()

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n⏹️  Servidor detenido")
            print("Adiós! 👋\n")

if __name__ == "__main__":
    main()
