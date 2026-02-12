from flask import Flask, request
import threading
import ssl
from pathlib import Path

app = Flask(__name__)
auth_code = None

@app.route('/callback')
def callback():
    global auth_code
    auth_code = request.args.get('code')
    return "<h1>Conectado!</h1><p>Podes fechar esta aba e voltar ao Dashboard.</p>"

def run_server_thread(cert_file, key_file, port=8888):
    def run():
        # Caminhos absolutos para evitar o Erro 2
        base = Path(__file__).parent.parent
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(str(base / cert_file), str(base / key_file))
        
        # Corre em 0.0.0.0 para ser visível por outros dispositivos
        app.run(host='0.0.0.0', port=port, ssl_context=context, debug=False, use_reloader=False)

    threading.Thread(target=run, daemon=True).start()

def wait_for_auth_code(timeout=300):
    import time
    start = time.time()
    while auth_code is None and (time.time() - start) < timeout:
        time.sleep(1)
    return auth_code