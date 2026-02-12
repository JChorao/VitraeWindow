"""Utilitários de rede e certificados SSL"""

import socket
import os
from pathlib import Path


def get_local_ip():
    """
    Obtém o IP local da máquina na rede
    
    Returns:
        str: Endereço IP local (ex: '192.168.1.100')
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "192.168.1.100"  # Fallback


def generate_self_signed_cert(cert_file="server.crt", key_file="server.key"):
    """
    Gera certificado SSL auto-assinado
    
    Args:
        cert_file: Nome do ficheiro do certificado (default: 'server.crt')
        key_file: Nome do ficheiro da chave (default: 'server.key')
    
    Returns:
        tuple: (caminho_certificado, caminho_chave)
    """
    cert_path = Path(cert_file)
    key_path = Path(key_file)
    
    # Se já existem, retornar
    if cert_path.exists() and key_path.exists():
        return str(cert_path), str(key_path)
    
    try:
        from OpenSSL import crypto
        
        # Obter IP local
        local_ip = get_local_ip()
        
        # Criar par de chaves
        key = crypto.PKey()
        key.generate_key(crypto.TYPE_RSA, 2048)
        
        # Criar certificado
        cert = crypto.X509()
        cert.get_subject().C = "PT"
        cert.get_subject().ST = "Portugal"
        cert.get_subject().L = "Lisboa"
        cert.get_subject().O = "VitraeView"
        cert.get_subject().OU = "Dashboard"
        cert.get_subject().CN = local_ip
        
        cert.set_serial_number(1000)
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(365*24*60*60)  # Válido por 1 ano
        cert.set_issuer(cert.get_subject())
        cert.set_pubkey(key)
        cert.sign(key, 'sha256')
        
        # Guardar ficheiros
        with open(cert_path, "wb") as f:
            f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
        
        with open(key_path, "wb") as f:
            f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key))
        
        print("✓ Certificado SSL gerado!")
        return str(cert_path), str(key_path)
        
    except ImportError:
        print("⚠️ pyOpenSSL não instalado. A instalar...")
        os.system("pip install pyOpenSSL")
        return generate_self_signed_cert(cert_file, key_file)


def cleanup_certificates(cert_file="server.crt", key_file="server.key"):
    """
    Remove os certificados SSL
    
    Args:
        cert_file: Nome do ficheiro do certificado (default: 'server.crt')
        key_file: Nome do ficheiro da chave (default: 'server.key')
    """
    cert_path = Path(cert_file)
    key_path = Path(key_file)
    
    try:
        if cert_path.exists():
            cert_path.unlink()
            print("✓ Certificado apagado")
        
        if key_path.exists():
            key_path.unlink()
            print("✓ Chave privada apagada")
    except Exception as e:
        print(f"⚠️ Erro ao apagar certificados: {e}")
