"""Uygulama ayarları: instance/settings.json

- secret_key   : Oturum çerezlerini imzalamak için rastgele anahtar (ilk çalıştırmada üretilir).
- password_hash: Paylaşım şifresinin özeti (şifrenin kendisi saklanmaz). Boşsa giriş ekranı kapalıdır.
"""
import json
import os
import secrets

from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_PATH = os.environ.get("TEST_TAKIP_SETTINGS", os.path.join(BASE_DIR, "instance", "settings.json"))


def load():
    try:
        with open(SETTINGS_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    if not data.get("secret_key"):
        data["secret_key"] = secrets.token_hex(32)
        save(data)
    return data


def save(data):
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    tmp = SETTINGS_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, SETTINGS_PATH)


def set_password(password):
    data = load()
    data["password_hash"] = generate_password_hash(password) if password else ""
    save(data)


def password_enabled():
    return bool(load().get("password_hash"))


def check_password(password):
    h = load().get("password_hash")
    return bool(h) and check_password_hash(h, password or "")
