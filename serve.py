"""Uygulamayı yerel ağda paylaşmak için üretim sunucusu (waitress).

    python serve.py

- Debug modu KAPALI çalışır (ağa açık debug modu güvenlik açığıdır).
- 0.0.0.0:5000 üzerinde dinler; aynı ağdaki bilgisayarlar http://<bu-bilgisayarın-IP>:5000 ile erişir.
- Port değiştirmek için:  $env:PORT = "8080"; python serve.py
"""
import os
import socket

from waitress import serve

import settings
from app import app


def lan_addresses():
    addrs = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            addrs.add(info[4][0])
    except socket.gaierror:
        pass
    try:  # varsayılan ağ arayüzünün IP'si (bağlantı kurmadan)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        addrs.add(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    return sorted(a for a in addrs if not a.startswith("127.") and not a.startswith("169.254."))


def main():
    port = int(os.environ.get("PORT", "5000"))
    host = os.environ.get("HOST", "0.0.0.0")
    print("=" * 62)
    print(" Test Takip Dashboard - ağ paylaşım modu")
    print("=" * 62)
    print(f" Bu bilgisayardan      : http://127.0.0.1:{port}")
    for ip in lan_addresses():
        print(f" İş arkadaşlarınız için: http://{ip}:{port}")
    if settings.password_enabled():
        print(" Giriş                 : paylaşım şifresi gerekli (bu bilgisayardan şifresiz)")
    else:
        print(" UYARI: Şifre belirlenmemiş! Ağdaki herkes erişebilir.")
        print("        Belirlemek için: python sifre_belirle.py")
    print(" Durdurmak için CTRL+C")
    print("=" * 62, flush=True)
    serve(app, host=host, port=port, threads=8)


if __name__ == "__main__":
    main()
