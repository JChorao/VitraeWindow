import socket
import os
import shutil
from pathlib import Path

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "127.0.0.1"

def generate_self_signed_cert(cert_file="server.crt", key_file="server.key"):
    base_path = Path(__file__).parent.parent
    cert_path = base_path / cert_file
    key_path = base_path / key_file
    
    if cert_path.exists() and key_path.exists():
        return str(cert_path), str(key_path)
    
    try:
        from OpenSSL import crypto
        local_ip = get_local_ip()
        key = crypto.PKey()
        key.generate_key(crypto.TYPE_RSA, 2048)
        cert = crypto.X509()
        cert.get_subject().CN = local_ip
        cert.set_serial_number(1000)
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(365*24*60*60)
        cert.set_issuer(cert.get_subject())
        cert.set_pubkey(key)
        cert.sign(key, 'sha256')
        
        with open(cert_path, "wb") as f:
            f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
        with open(key_path, "wb") as f:
            f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key))
            
        return str(cert_path), str(key_path)
    except ImportError:
        os.system("pip install pyOpenSSL")
        return generate_self_signed_cert(cert_file, key_file)

def cleanup_app_data(cert_file="server.crt", key_file="server.key"):
    base_path = Path(__file__).parent.parent 
    for f in [cert_file, key_file, ".spotify_cache"]:
        p = base_path / f
        if p.exists():
            try: p.unlink()
            except: pass

    for root, dirs, files in os.walk(base_path):
        if "__pycache__" in dirs:
            pycache_path = Path(root) / "__pycache__"
            try: shutil.rmtree(pycache_path)
            except: pass