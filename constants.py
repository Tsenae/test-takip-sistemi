"""Uygulama genelinde kullanılan sabitler."""

STATUS_ORDER = ["passed", "failed", "blocked", "not_run"]

STATUS_LABELS = {
    "passed": "Başarılı",
    "failed": "Başarısız",
    "blocked": "Engellendi",
    "not_run": "Çalıştırılmadı",
}

# Durum renkleri CSS değişkenlerinden gelir (static/css/style.css: --st-*), açık/koyu temaya göre değişir.
# Renk tek başına anlam taşımaz; her yerde etiket/ikon ile birlikte kullanılır.
STATUS_COLORS = {key: f"var(--st-{key})" for key in ("passed", "failed", "blocked", "not_run")}

# Kanban (To-Do) sütunları
TODO_STATUS_ORDER = ["todo", "in_progress", "review", "done"]
TODO_STATUS_LABELS = {
    "todo": "Yapılacak",
    "in_progress": "Devam Ediyor",
    "review": "İncelemede",
    "done": "Tamamlandı",
}
TODO_STATUS_ICONS = {
    "todo": "bi-circle",
    "in_progress": "bi-arrow-repeat",
    "review": "bi-eye",
    "done": "bi-check-circle-fill",
}

STATUS_ICONS = {
    "passed": "bi-check-circle-fill",
    "failed": "bi-x-circle-fill",
    "blocked": "bi-slash-circle-fill",
    "not_run": "bi-dash-circle",
}

# Excel'den gelen serbest metin durumları -> iç anahtar
_STATUS_ALIASES = {
    "passed": ["başarılı", "basarili", "passed", "pass", "geçti", "gecti", "ok", "success", "başarili"],
    "failed": ["başarısız", "basarisiz", "failed", "fail", "kaldı", "kaldi", "hata", "error", "başarisiz"],
    "blocked": ["engellendi", "engelli", "blocked", "bloke", "block", "beklemede"],
    "not_run": ["çalıştırılmadı", "calistirilmadi", "not run", "not_run", "notrun", "yapılmadı",
                "yapilmadi", "koşulmadı", "kosulmadi", "", "-", "n/a",
                "uygulanamaz", "uygulanmadı", "uygulanmadi", "çalıştırılamadı", "calistirilamadi"],
}


def normalize_status(value):
    text = str(value or "").strip().lower().replace("İ", "i")
    if text in STATUS_LABELS:
        return text
    for key, aliases in _STATUS_ALIASES.items():
        if text in aliases:
            return key
    return "not_run"


PRIORITY_ORDER = ["critical", "high", "medium", "low"]
PRIORITY_LABELS = {
    "critical": "Kritik",
    "high": "Yüksek",
    "medium": "Orta",
    "low": "Düşük",
}
PRIORITY_BADGES = {
    "critical": "text-bg-danger",
    "high": "text-bg-warning",
    "medium": "text-bg-primary",
    "low": "text-bg-secondary",
}

# Excel kolon eşleştirmesinde kullanılan alanlar ve otomatik tahmin için başlık takma adları
CASE_FIELDS = {
    "suite_name": {"label": "Test Paketi", "aliases": ["test paketi", "paket", "suite", "test suite"]},
    "test_code": {"label": "Test Kodu", "aliases": ["test kodu", "test id", "id", "kod", "test no", "case id", "tc"]},
    "title": {"label": "Test Adı", "aliases": ["test adı", "test adi", "senaryo", "test senaryosu", "başlık", "title", "test case", "test name", "ad",
                                               "kontrol edilecek alan", "kontrol", "kontrol noktası", "test konusu"]},
    "module": {"label": "Modül", "aliases": ["modül", "modul", "module", "bileşen", "component", "ekran"]},
    "steps": {"label": "Test Adımları", "aliases": ["test adımları", "adımlar", "adimlar", "steps", "test steps",
                                                    "yapılacak işlem", "yapılacak işlemler", "işlem", "işlem adımları"]},
    "expected": {"label": "Beklenen Sonuç", "aliases": ["beklenen sonuç", "beklenen", "expected", "expected result"]},
    "actual": {"label": "Gerçekleşen Sonuç", "aliases": ["gerçekleşen sonuç", "gerçekleşen", "gerceklesen", "actual", "actual result", "sonuç",
                                                         "hata / not", "hata/not", "not", "notlar", "açıklama", "yorum"]},
    "status": {"label": "Durum", "aliases": ["durum", "test durumu", "status", "sonuç durumu"]},
    "bug_link": {"label": "Hata Linki", "aliases": ["hata linki", "hata", "bug", "bug link", "jira", "defect", "issue"]},
    "tester": {"label": "Test Eden", "aliases": ["test eden", "testçi", "tester", "sorumlu", "assignee"]},
}
