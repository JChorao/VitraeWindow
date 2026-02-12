"""Servidor HTTPS para autenticação Spotify"""

from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import ssl
import threading
from .html_templates import SUCCESS_PAGE, ERROR_PAGE

# Variáveis globais para autenticação
auth_code = None
auth_event = threading.Event()


class CallbackHandler(BaseHTTPRequestHandler):
    """Handler para receber o callback do Spotify"""
    
    def do_GET(self):
        global auth_code
        
        # Parse do URL
        query = urlparse(self.path).query
        params = parse_qs(query)
        
        if 'code' in params:
            auth_code = params['code'][0]
            auth_event.set()
            
            # Enviar página de sucesso
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(SUCCESS_PAGE.encode('utf-8'))
        else:
            # Enviar página de erro
            self.send_response(400)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(ERROR_PAGE.encode('utf-8'))
    
    def log_message(self, format, *args):
        # Silenciar logs do servidor
        pass


def start_https_server(cert_file, key_file, port=8888):
    """
    Inicia o servidor HTTPS
    
    Args:
        cert_file: Caminho para o certificado SSL
        key_file: Caminho para a chave privada
        port: Porta do servidor (default: 8888)
    
    Returns:
        HTTPServer instance
    """
    server = HTTPServer(('0.0.0.0', port), CallbackHandler)
    
    # Configurar SSL
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_file, key_file)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    
    return server


def run_server_thread(cert_file, key_file, port=8888):
    """
    Inicia o servidor HTTPS em background thread
    
    Args:
        cert_file: Caminho para o certificado SSL
        key_file: Caminho para a chave privada
        port: Porta do servidor (default: 8888)
    """
    def run():
        try:
            server = start_https_server(cert_file, key_file, port)
            print(f"✓ Servidor HTTPS a correr na porta {port}")
            server.serve_forever()
        except Exception as e:
            print(f"❌ Erro ao iniciar servidor: {e}")
    
    thread = threading.Thread(target=run, daemon=True)
    thread.start()


def wait_for_auth_code(timeout=300):
    """
    Aguarda o código de autenticação
    
    Args:
        timeout: Tempo máximo de espera em segundos (default: 300 = 5min)
    
    Returns:
        str: Código de autenticação ou None se timeout
    """
    global auth_code, auth_event
    
    if auth_event.wait(timeout=timeout):
        code = auth_code
        # Reset para próxima autenticação
        auth_code = None
        auth_event.clear()
        return code
    
    return None