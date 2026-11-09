"""Paylaşım şifresini belirler / değiştirir / kaldırır.

Kullanım:
    python sifre_belirle.py            # yeni şifre belirle veya değiştir
    python sifre_belirle.py --kaldir   # şifreyi kaldır (giriş ekranı kapanır - önerilmez)
"""
import getpass
import sys

import settings


def main():
    if "--kaldir" in sys.argv:
        settings.set_password("")
        print("Şifre kaldırıldı. Ağdaki herkes uygulamaya şifresiz erişebilir!")
        return
    if "--yoksa" in sys.argv and settings.password_enabled():
        return  # paylas.bat: şifre zaten varsa sorma
    print("Ağdaki kullanıcıların gireceği paylaşım şifresini belirleyin (en az 6 karakter).")
    print("Yazarken ekranda görünmez.\n")
    while True:
        pw = getpass.getpass("Şifre: ")
        if len(pw) < 6:
            print("Şifre en az 6 karakter olmalı.\n")
            continue
        if getpass.getpass("Şifre (tekrar): ") != pw:
            print("Şifreler eşleşmedi, tekrar deneyin.\n")
            continue
        break
    settings.set_password(pw)
    print("\nŞifre kaydedildi. Bu şifreyi iş arkadaşınızla paylaşın.")


if __name__ == "__main__":
    main()
