import os
from http.server import SimpleHTTPRequestHandler, HTTPServer

class StaticFileHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        script_dir = os.path.dirname(__file__)  # 現在のファイルのディレクトリ
        server_root = os.path.dirname(script_dir)  # 'server' ディレクトリ
        static_dir = os.path.join(server_root, 'static')  # 'static' ディレクトリへのパス
        os.chdir(static_dir)
        super().__init__(*args, directory='.', **kwargs)

def run_http_server():
    server_address = ('', 8000)
    httpd = HTTPServer(server_address, StaticFileHandler)
    print("Starting HTTP server on port 8000...")
    httpd.serve_forever()
