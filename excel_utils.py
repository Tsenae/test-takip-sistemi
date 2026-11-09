"""Excel içe/dışa aktarma yardımcıları (openpyxl)."""
import io
import re
import unicodedata
from datetime import datetime

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from constants import CASE_FIELDS, STATUS_LABELS, normalize_status


def _norm(text):
    """Başlık karşılaştırması için metni sadeleştirir (Türkçe karakter, boşluk, büyük/küçük)."""
    text = str(text or "").strip().lower()
    text = text.replace("ı", "i").replace("İ", "i")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return "".join(ch for ch in text if ch.isalnum())


def sheet_names(path):
    wb = load_workbook(path, read_only=True)
    try:
        return wb.sheetnames
    finally:
        wb.close()


def read_sheet(path, sheet=None, header_row=1):
    """(başlıklar, satırlar) döndürür. Satırlar başlık indeksine göre liste."""
    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb[sheet] if sheet and sheet in wb.sheetnames else wb.worksheets[0]
        rows = list(ws.iter_rows(values_only=True))
    finally:
        wb.close()
    if len(rows) < header_row:
        return [], []
    headers = [str(h).strip() if h is not None else "" for h in rows[header_row - 1]]
    data = []
    for row in rows[header_row:]:
        if row is None or all(v is None or str(v).strip() == "" for v in row):
            continue
        values = list(row) + [None] * (len(headers) - len(row))
        data.append(values[: len(headers)])
    return headers, data


def read_all_sheets(path, header_row=1):
    """Tüm sayfaları tek seferde okur: {sayfa adı: (başlıklar, satırlar)}"""
    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        raw = {ws.title: list(ws.iter_rows(values_only=True)) for ws in wb.worksheets}
    finally:
        wb.close()
    result = {}
    for name, rows in raw.items():
        if len(rows) < header_row:
            result[name] = ([], [])
            continue
        headers = [str(h).strip() if h is not None else "" for h in rows[header_row - 1]]
        while headers and headers[-1] == "":
            headers.pop()
        data = []
        for row in rows[header_row:]:
            if row is None or all(v is None or str(v).strip() == "" for v in row):
                continue
            values = list(row) + [None] * (len(headers) - len(row))
            data.append(values[: len(headers)])
        result[name] = (headers, data)
    return result


def guess_mapping(headers):
    """Her alan için en uygun Excel kolon indeksini tahmin eder."""
    normalized = [_norm(h) for h in headers]
    mapping = {}
    for field, info in CASE_FIELDS.items():
        aliases = [_norm(a) for a in info["aliases"]]
        for idx, h in enumerate(normalized):
            if h and h in aliases and idx not in mapping.values():
                mapping[field] = idx
                break
    return mapping


def cell_text(value):
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def map_row(row, mapping, status_map=None):
    """Excel satırını alan sözlüğüne dönüştürür.

    status_map: {excel'deki ham durum metni (küçük harf): iç durum anahtarı} - kullanıcının seçtiği eşleştirme.
    """
    result = {}
    for field, idx in mapping.items():
        if idx is None or idx >= len(row):
            continue
        result[field] = cell_text(row[idx])
    if "status" in result:
        raw = result["status"].strip().lower()
        result["status"] = (status_map or {}).get(raw) or normalize_status(raw)
    return result


def remap_by_header(mapping, ref_headers, headers):
    """Referans sayfadaki kolon eşleştirmesini, başlık adına göre başka bir sayfaya uyarlar."""
    normed = [_norm(h) for h in headers]
    result = {}
    for field, idx in mapping.items():
        name = _norm(ref_headers[idx]) if idx < len(ref_headers) else ""
        if name and name in normed:
            result[field] = normed.index(name)
    return result


def column_value_sets(sheets_data, ref_headers, limit=30):
    """Referans sayfanın her kolonu için tüm sayfalardaki farklı değerleri toplar.

    sheets_data: [(headers, rows), ...]. Farklı değer sayısı `limit`i aşan kolonlar None döner
    (durum kolonu olamayacak kadar çeşitli).
    """
    result = {}
    for idx, ref in enumerate(ref_headers):
        key = _norm(ref)
        values, seen = [], set()
        for headers, rows in sheets_data:
            normed = [_norm(h) for h in headers]
            if key not in normed:
                continue
            col = normed.index(key)
            for row in rows:
                text = cell_text(row[col]) if col < len(row) else ""
                low = text.lower()
                if text and low not in seen:
                    seen.add(low)
                    values.append(text)
        result[idx] = values if len(values) <= limit else None
    return result


def clean_sheet_name(name):
    """'01 Üyelik Ana Sayfa' -> 'Üyelik Ana Sayfa'"""
    cleaned = re.sub(r"^\s*\d+[\s.\-_)]*", "", name or "").strip()
    return cleaned or name


EXPORT_COLUMNS = [
    ("suite_name", "Test Paketi", 22),
    ("test_code", "Test Kodu", 14),
    ("title", "Test Adı", 40),
    ("module", "Modül", 18),
    ("steps", "Test Adımları", 40),
    ("expected", "Beklenen Sonuç", 36),
    ("actual", "Gerçekleşen Sonuç", 36),
    ("status", "Durum", 16),
    ("bug_link", "Hata Linki", 30),
    ("tester", "Test Eden", 16),
    ("updated_at", "Güncellenme", 18),
]

HEADER_FILL = PatternFill("solid", fgColor="1F3A5F")
STATUS_FILLS = {
    "passed": "D7F2D7",
    "failed": "F8D7D7",
    "blocked": "FDEBC4",
    "not_run": "E9E9E7",
}


def export_cases(cases, stats):
    """Test senaryolarını ve özet istatistikleri xlsx olarak döndürür (BytesIO)."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Test Senaryoları"

    for col, (_, header, width) in enumerate(EXPORT_COLUMNS, start=1):
        c = ws.cell(row=1, column=col, value=header)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = HEADER_FILL
        c.alignment = Alignment(vertical="center")
        ws.column_dimensions[get_column_letter(col)].width = width

    for r, case in enumerate(cases, start=2):
        for col, (key, _, _) in enumerate(EXPORT_COLUMNS, start=1):
            value = case[key]
            if key == "status":
                value = STATUS_LABELS.get(value, value)
            c = ws.cell(row=r, column=col, value=value)
            c.alignment = Alignment(wrap_text=True, vertical="top")
            if key == "status":
                c.fill = PatternFill("solid", fgColor=STATUS_FILLS.get(case["status"], "FFFFFF"))
            if key == "bug_link" and value and str(value).startswith("http"):
                c.hyperlink = value
                c.font = Font(color="0563C1", underline="single")

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    summary = wb.create_sheet("Özet")
    summary.column_dimensions["A"].width = 28
    summary.column_dimensions["B"].width = 14
    rows = [
        ("Rapor Tarihi", datetime.now().strftime("%Y-%m-%d %H:%M")),
        ("Toplam Test", stats["total"]),
        ("Başarılı", stats["passed"]),
        ("Başarısız", stats["failed"]),
        ("Engellendi", stats["blocked"]),
        ("Çalıştırılmadı", stats["not_run"]),
        ("Tamamlanma Oranı (%)", stats["completion"]),
        ("Başarı Oranı (%)", stats["success"]),
    ]
    for i, (k, v) in enumerate(rows, start=1):
        summary.cell(row=i, column=1, value=k).font = Font(bold=True)
        summary.cell(row=i, column=2, value=v)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def template_workbook():
    """Boş içe aktarma şablonu."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Test Senaryoları"
    for col, (_, header, width) in enumerate(EXPORT_COLUMNS[:-1], start=1):
        c = ws.cell(row=1, column=col, value=header)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = HEADER_FILL
        ws.column_dimensions[get_column_letter(col)].width = width
    ws.append(["Giriş", "TC-001", "Geçerli kullanıcı ile giriş", "Kimlik Doğrulama",
               "1. Giriş sayfasını aç\n2. Bilgileri gir\n3. Giriş'e tıkla",
               "Kullanıcı ana sayfaya yönlenir", "", "Çalıştırılmadı", "", ""])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf
