import os
from http.server import SimpleHTTPRequestHandler, HTTPServer

class GzipStaticFileHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        script_dir = os.path.dirname(__file__)
        server_root = os.path.dirname(script_dir)
        static_dir = os.path.join(server_root, 'static')
        os.chdir(static_dir)
        super().__init__(*args, directory='.', **kwargs)

    def end_headers(self):
        # Gzipファイルに対してContent-Encodingを設定
        if self.path.endswith('.gz'):
            self.send_header('Content-Encoding', 'gzip')

            # Content-Typeを適切に設定
            if self.path.endswith('.wasm.gz'):
                self.send_header('Content-Type', 'application/wasm')
            elif self.path.endswith('.js.gz'):
                self.send_header('Content-Type', 'application/javascript')
            elif self.path.endswith('.data.gz'):
                self.send_header('Content-Type', 'application/octet-stream')
        
        super().end_headers()

    def do_GET(self):
        # .gzファイルが存在する場合、それを提供
        if self.path.endswith('.js') or self.path.endswith('.wasm') or self.path.endswith('.data'):
            if os.path.exists(self.path + '.gz'):
                self.path += '.gz'
        
        return super().do_GET()

def run_http_server():
    server_address = ('', 8000)
    httpd = HTTPServer(server_address, GzipStaticFileHandler)
    print("Starting HTTP server on port 8000...")
    httpd.serve_forever()

if __name__ == '__main__':
    run_http_server()
