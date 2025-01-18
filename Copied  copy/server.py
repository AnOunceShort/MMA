from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import glob
import os

class CustomHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        SimpleHTTPRequestHandler.end_headers(self)
        
    def do_GET(self):
        print(f"Received request for: {self.path}")  # Debug print
        
        if self.path == '/list_files':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            files = glob.glob('*.csv')
            print(f"Found files: {files}")  # Debug print
            self.wfile.write(json.dumps(files).encode())
            return
        
        return SimpleHTTPRequestHandler.do_GET(self)

port = 8081
print(f"Starting server on port {port}")
print(f"Current directory: {os.getcwd()}")
print(f"Available CSV files: {glob.glob('*.csv')}")
httpd = HTTPServer(('localhost', port), CustomHandler)
httpd.serve_forever() 