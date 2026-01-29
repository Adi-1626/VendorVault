"""
Mobile Scanner Integration Module.
Allows using a smartphone as a wireless barcode scanner via HTTP.
Works with apps like "Barcode to PC", "QR Scanner to PC", or any HTTP-capable scanner app.
"""
from typing import Callable, Optional
import threading
import socket
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import logging

logger = logging.getLogger(__name__)


class MobileScannerHandler(BaseHTTPRequestHandler):
    """HTTP handler for receiving barcode scans from mobile apps."""
    
    callback: Optional[Callable] = None
    last_scan: str = ""
    
    def log_message(self, format, *args):
        """Suppress default logging."""
        pass
    
    def _send_response(self, status: int, message: str):
        """Send HTTP response."""
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        response = json.dumps({'status': 'ok' if status == 200 else 'error', 'message': message})
        self.wfile.write(response.encode())
    
    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self._send_response(200, 'OK')
    
    def do_GET(self):
        """Handle GET requests - for simple scan submissions."""
        parsed = urlparse(self.path)
        
        # Health check
        if parsed.path == '/':
            self._send_response(200, 'Mobile Scanner Server Running')
            return
        
        # Scan endpoint: /scan?code=BARCODE123
        if parsed.path == '/scan':
            params = parse_qs(parsed.query)
            barcode = params.get('code', params.get('barcode', [None]))[0]
            
            if barcode:
                self._process_scan(barcode)
                self._send_response(200, f'Scanned: {barcode}')
            else:
                self._send_response(400, 'Missing barcode parameter')
            return
        
        self._send_response(404, 'Not found')
    
    def do_POST(self):
        """Handle POST requests - for JSON payloads."""
        content_length = int(self.headers.get('Content-Length', 0))
        
        if content_length > 0:
            body = self.rfile.read(content_length).decode('utf-8')
            
            try:
                data = json.loads(body)
                barcode = data.get('code') or data.get('barcode') or data.get('text')
                
                if barcode:
                    self._process_scan(barcode)
                    self._send_response(200, f'Scanned: {barcode}')
                else:
                    self._send_response(400, 'Missing barcode in payload')
            except json.JSONDecodeError:
                # Treat as plain text barcode
                barcode = body.strip()
                if barcode:
                    self._process_scan(barcode)
                    self._send_response(200, f'Scanned: {barcode}')
                else:
                    self._send_response(400, 'Invalid request')
        else:
            self._send_response(400, 'Empty request')
    
    def _process_scan(self, barcode: str):
        """Process received barcode."""
        MobileScannerHandler.last_scan = barcode
        logger.info(f"Mobile scan received: {barcode}")
        
        if MobileScannerHandler.callback:
            try:
                MobileScannerHandler.callback(barcode)
            except Exception as e:
                logger.error(f"Scan callback error: {e}")


class MobileScannerServer:
    """
    HTTP server for receiving barcode scans from mobile devices.
    
    Usage:
        1. Start the server: server.start()
        2. Note the IP address shown
        3. On mobile, use any barcode scanner app that can send HTTP requests
        4. Configure app to send GET request to: http://YOUR_IP:8765/scan?code={barcode}
        5. Or POST JSON to: http://YOUR_IP:8765/scan with body {"code": "barcode"}
    
    Compatible apps:
        - "Barcode to PC" (Android/iOS) - set HTTP mode
        - "QR Scanner to PC" 
        - "Remote Barcode Scanner"
        - Any app with HTTP/webhook support
    """
    
    DEFAULT_PORT = 8765
    
    def __init__(self, port: int = None):
        self.port = port or self.DEFAULT_PORT
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[threading.Thread] = None
        self.running = False
        self._scan_callback: Optional[Callable] = None
    
    def get_local_ip(self) -> str:
        """Get local IP address for mobile connection."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"
    
    def set_scan_callback(self, callback: Callable):
        """
        Set callback function for when a scan is received.
        Callback receives the barcode string.
        """
        self._scan_callback = callback
        MobileScannerHandler.callback = callback
    
    def start(self) -> dict:
        """
        Start the mobile scanner server.
        Returns connection info for the mobile app.
        """
        if self.running:
            return self.get_connection_info()
        
        try:
            self.server = HTTPServer(('0.0.0.0', self.port), MobileScannerHandler)
            self.thread = threading.Thread(target=self._run_server, daemon=True)
            self.thread.start()
            self.running = True
            
            logger.info(f"Mobile scanner server started on port {self.port}")
            return self.get_connection_info()
            
        except Exception as e:
            logger.error(f"Failed to start mobile scanner server: {e}")
            return {'error': str(e)}
    
    def _run_server(self):
        """Run server in background thread."""
        try:
            self.server.serve_forever()
        except Exception as e:
            logger.error(f"Server error: {e}")
            self.running = False
    
    def stop(self):
        """Stop the mobile scanner server."""
        if self.server:
            self.server.shutdown()
            self.running = False
            logger.info("Mobile scanner server stopped")
    
    def get_connection_info(self) -> dict:
        """Get connection info for mobile app setup."""
        ip = self.get_local_ip()
        return {
            'ip': ip,
            'port': self.port,
            'url': f"http://{ip}:{self.port}/scan",
            'get_example': f"http://{ip}:{self.port}/scan?code=BARCODE123",
            'post_body': '{"code": "BARCODE123"}',
            'instructions': [
                f"1. Connect your phone to the same WiFi network",
                f"2. Open your barcode scanner app",
                f"3. Set HTTP/Webhook mode with URL: http://{ip}:{self.port}/scan",
                f"4. For GET request, use: http://{ip}:{self.port}/scan?code={{barcode}}",
                f"5. For POST request, send JSON: {{\"code\": \"barcode\"}}",
                f"6. Scan any barcode - it will appear in the POS instantly!"
            ]
        }
    
    def get_last_scan(self) -> str:
        """Get the last scanned barcode."""
        return MobileScannerHandler.last_scan
    
    def is_running(self) -> bool:
        """Check if server is running."""
        return self.running


# Global instance
mobile_scanner = MobileScannerServer()


def start_mobile_scanner(callback: Callable = None) -> dict:
    """
    Convenience function to start mobile scanner.
    Returns connection info.
    """
    if callback:
        mobile_scanner.set_scan_callback(callback)
    return mobile_scanner.start()


def stop_mobile_scanner():
    """Stop mobile scanner server."""
    mobile_scanner.stop()
