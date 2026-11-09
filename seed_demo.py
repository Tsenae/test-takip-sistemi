"""İsteğe bağlı: Uygulamayı denemek için örnek veri ekler.

Kullanım:  python seed_demo.py
Veritabanında zaten paket varsa hiçbir şey yapmaz (mevcut verinize dokunmaz).
"""
import random
import sqlite3
from datetime import date, timedelta

from app import app

SUITES = {
    "Giriş ve Yetkilendirme": ["Kimlik Doğrulama", "Şifre Sıfırlama", "Yetki"],
    "Sipariş Yönetimi": ["Sepet", "Ödeme", "Sipariş Takibi"],
    "Raporlama": ["Dashboard", "Excel Rapor"],
}
STATUSES = ["passed"] * 5 + ["failed"] * 2 + ["blocked"] + ["not_run"] * 3


def main():
    random.seed(42)
    with sqlite3.connect(app.config["DATABASE"]) as db:
        if db.execute("SELECT COUNT(*) FROM suites").fetchone()[0]:
            print("Veritabanında zaten veri var; örnek veri eklenmedi.")
            return
        n = 1
        for suite, modules in SUITES.items():
            sid = db.execute("INSERT INTO suites (name, description) VALUES (?, ?)",
                             (suite, f"{suite} test senaryoları")).lastrowid
            for module in modules:
                for i in range(random.randint(3, 6)):
                    status = random.choice(STATUSES)
                    db.execute(
                        """INSERT INTO cases (suite_id, test_code, title, module, steps, expected, actual, status, bug_link)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (sid, f"TC-{n:03d}", f"{module} senaryosu {i + 1}", module,
                         "1. Sayfayı aç\n2. Gerekli bilgileri gir\n3. İşlemi onayla",
                         "İşlem başarıyla tamamlanır",
                         {"passed": "Beklendiği gibi çalıştı", "failed": "Hata mesajı alındı",
                          "blocked": "Ortam erişilemez durumda", "not_run": ""}[status],
                         status,
                         f"https://jira.example.com/browse/PRJ-{100 + n}" if status == "failed" else ""),
                    )
                    n += 1
        today = date.today()
        for title, prio, days in [
            ("Ödeme modülü regresyon testlerini tamamla", "critical", 1),
            ("Test ortamı erişim sorununu altyapı ekibine ilet", "high", -1),
            ("Raporlama senaryolarını gözden geçir", "medium", 5),
            ("Test sonuç raporunu hazırla", "low", 10),
        ]:
            db.execute("INSERT INTO todos (title, priority, due_date) VALUES (?, ?, ?)",
                       (title, prio, (today + timedelta(days=days)).isoformat()))
        print(f"{len(SUITES)} paket, {n - 1} senaryo ve 4 görev eklendi.")


if __name__ == "__main__":
    main()
