#!/usr/bin/env python3
"""
PetroFlow v3.0 - Minimal Test Server
Quick test to verify Backend + Frontend can launch without heavy dependencies.
"""
import http.server
import socketserver
import json
from urllib.parse import urlparse, parse_qs
import threading
import time
import webbrowser

PORT = 8000

class PetroFlowHandler(http.server.SimpleHTTPRequestHandler):
    """Simple HTTP handler for testing"""
    
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {
                "message": "PetroFlow v3.0 Backend - Test Server",
                "version": "3.0.0",
                "status": "running",
                "endpoints": {
                    "health": "/health",
                    "docs": "/docs",
                    "api": "/api/v1"
                }
            }
            self.wfile.write(json.dumps(response, indent=2).encode())
            
        elif parsed_path.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {"status": "healthy", "version": "3.0.0"}
            self.wfile.write(json.dumps(response).encode())
            
        elif parsed_path.path == '/docs':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            html = """
            <html>
            <head><title>PetroFlow API Documentation</title></head>
            <body>
                <h1>PetroFlow v3.0 - Test Server</h1>
                <p>This is a minimal test server to verify Backend + Frontend can launch.</p>
                <h2>Endpoints:</h2>
                <ul>
                    <li><a href="/">/</a> - API Root</li>
                    <li><a href="/health">/health</a> - Health Check</li>
                    <li><a href="http://localhost:3000">http://localhost:3000</a> - Frontend (React)</li>
                </ul>
                <p>Full requirements installation needed for production.</p>
            </body>
            </html>
            """
            self.wfile.write(html.encode())
        else:
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not found"}).encode())
    
    def log_message(self, format, *args):
        """Custom logging"""
        print(f"[{self.client_address[0]}] {format%args}")

def run_test_server(port=PORT):
    """Run minimal test HTTP server"""
    with socketserver.TCPServer(("", port), PetroFlowHandler) as httpd:
        print(f"\n{'='*60}")
        print(f"  PetroFlow v3.0 - Test Server")
        print(f"{'='*60}")
        print(f"Backend running on: http://localhost:{port}")
        print(f"Health check:       http://localhost:{port}/health")
        print(f"API Docs:           http://localhost:{port}/docs")
        print(f"Frontend:           http://localhost:3000")
        print(f"\nPress Ctrl+C to stop")
        print(f"{'='*60}\n")
        httpd.serve_forever()

if __name__ == "__main__":
    try:
        run_test_server()
    except KeyboardInterrupt:
        print("\nServer stopped.")
