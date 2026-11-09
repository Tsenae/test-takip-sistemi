"""Test Takip Dashboard - Flask uygulaması."""
import math
import os
import re
import time
import uuid
from datetime import date, datetime, timedelta

from flask import (Flask, abort, flash, redirect, render_template, request,
                   send_file, session, url_for)
from werkzeug.datastructures import MultiDict

import excel_utils
import settings
from constants import (CASE_FIELDS, PRIORITY_BADGES, PRIORITY_LABELS,
                       PRIORITY_ORDER, STATUS_COLORS, STATUS_ICONS,
                       STATUS_LABELS, STATUS_ORDER, TODO_STATUS_ICONS,
                       TODO_STATUS_LABELS, TODO_STATUS_ORDER, normalize_status)
from database import get_db, init_db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY") or settings.load()["secret_key"],
    DATABASE=os.environ.get("TEST_TAKIP_DB", os.path.join(BASE_DIR, "instance", "test_takip.db")),
    UPLOAD_FOLDER=os.path.join(BASE_DIR, "uploads"),
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,
    PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
init_db(app)


# --------------------------------------------------------------------------- #
# Giriş (paylaşım şifresi)
# --------------------------------------------------------------------------- #
LOCAL_ADDRS = {"127.0.0.1", "::1"}
PUBLIC_ENDPOINTS = {"login", "static"}


def is_local_request():
    """Uygulamanın çalıştığı bilgisayardan (localhost) gelen istekler şifre istemez."""
    return request.remote_addr in LOCAL_ADDRS


@app.before_request
def require_login():
    if request.endpoint in PUBLIC_ENDPOINTS or is_local_request():
        return None
    if not settings.password_enabled() or session.get("auth"):
        return None
    if request.is_json or request.path.startswith("/kanban/reorder"):
        return {"ok": False, "error": "Oturum süresi doldu, lütfen tekrar giriş yapın."}, 401
    return redirect(url_for("login", next=request.full_path if request.method == "GET" else None))


@app.route("/login", methods=["GET", "POST"])
def login():
    if not settings.password_enabled() or is_local_request() or session.get("auth"):
        return redirect(safe_next(url_for("dashboard")))
    error = None
    if request.method == "POST":
        if settings.check_password(request.form.get("password")):
            session.clear()
            session.permanent = True
            session["auth"] = True
            return redirect(safe_next(url_for("dashboard")))
        time.sleep(1)  # kaba kuvvet denemelerini yavaşlat
        error = "Şifre hatalı."
    return render_template("login.html", error=error)


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))

PER_PAGE = 50
CASE_COLUMNS = ["test_code", "title", "module", "steps", "expected", "actual", "status", "bug_link", "tester"]


# --------------------------------------------------------------------------- #
# Yardımcılar
# --------------------------------------------------------------------------- #
def compute_stats(row):
    """Sayım satırından istatistik sözlüğü üretir.

    Tamamlanma = (Başarılı + Başarısız + Engellendi) / Toplam × 100
    Başarı     = Başarılı / (Başarılı + Başarısız + Engellendi) × 100
    """
    total = row["total"] or 0
    passed = row["passed"] or 0
    failed = row["failed"] or 0
    blocked = row["blocked"] or 0
    not_run = row["not_run"] or 0
    executed = passed + failed + blocked
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "blocked": blocked,
        "not_run": not_run,
        "executed": executed,
        "completion": round(executed / total * 100, 1) if total else 0.0,
        "success": round(passed / executed * 100, 1) if executed else 0.0,
    }


COUNT_SQL = """
    COUNT(c.id) AS total,
    SUM(CASE WHEN c.status='passed'  THEN 1 ELSE 0 END) AS passed,
    SUM(CASE WHEN c.status='failed'  THEN 1 ELSE 0 END) AS failed,
    SUM(CASE WHEN c.status='blocked' THEN 1 ELSE 0 END) AS blocked,
    SUM(CASE WHEN c.status='not_run' THEN 1 ELSE 0 END) AS not_run
"""


def case_filters(args):
    """Filtre parametrelerinden WHERE koşulu üretir."""
    clauses, params = [], []
    active = {
        "suite_id": args.get("suite_id", type=int),
        "module": (args.get("module") or "").strip(),
        "status": (args.get("status") or "").strip(),
        "q": (args.get("q") or "").strip(),
    }
    if active["suite_id"]:
        clauses.append("c.suite_id = ?")
        params.append(active["suite_id"])
    if active["module"]:
        clauses.append("c.module = ?")
        params.append(active["module"])
    if active["status"] in STATUS_LABELS:
        clauses.append("c.status = ?")
        params.append(active["status"])
    else:
        active["status"] = ""
    if active["q"]:
        clauses.append("(c.title LIKE ? OR c.test_code LIKE ? OR c.actual LIKE ? OR c.expected LIKE ?)")
        params.extend([f"%{active['q']}%"] * 4)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, params, active


def all_suites():
    return get_db().execute("SELECT id, name FROM suites ORDER BY name").fetchall()


def all_modules(suite_id=None):
    sql = "SELECT DISTINCT module FROM cases WHERE module <> ''"
    params = []
    if suite_id:
        sql += " AND suite_id = ?"
        params.append(suite_id)
    return [r["module"] for r in get_db().execute(sql + " ORDER BY module", params)]


def get_or_404(table, item_id):
    row = get_db().execute(f"SELECT * FROM {table} WHERE id = ?", (item_id,)).fetchone()
    if row is None:
        abort(404)
    return row


def safe_next(default):
    target = request.form.get("next") or request.args.get("next") or ""
    return target if target.startswith("/") and not target.startswith("//") else default


@app.context_processor
def inject_globals():
    return {
        "STATUS_LABELS": STATUS_LABELS,
        "STATUS_COLORS": STATUS_COLORS,
        "STATUS_ICONS": STATUS_ICONS,
        "STATUS_ORDER": STATUS_ORDER,
        "PRIORITY_LABELS": PRIORITY_LABELS,
        "PRIORITY_BADGES": PRIORITY_BADGES,
        "PRIORITY_ORDER": PRIORITY_ORDER,
        "TODO_STATUS_ORDER": TODO_STATUS_ORDER,
        "TODO_STATUS_LABELS": TODO_STATUS_LABELS,
        "TODO_STATUS_ICONS": TODO_STATUS_ICONS,
        "show_logout": bool(session.get("auth")) and not is_local_request(),
        "today": date.today().isoformat(),
    }


@app.template_filter("datefmt")
def datefmt(value):
    if not value:
        return ""
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").strftime("%d.%m.%Y")
    except ValueError:
        return value


# --------------------------------------------------------------------------- #
# Dashboard
# --------------------------------------------------------------------------- #
@app.route("/")
def dashboard():
    db = get_db()
    args = request.args.to_dict()
    args.pop("status", None)  # dashboard durum filtresi kullanmaz
    args.pop("q", None)
    where, params, active = case_filters(MultiDict(args))
    stats = compute_stats(db.execute(f"SELECT {COUNT_SQL} FROM cases c {where}", params).fetchone())

    suite_where = where.replace("WHERE", "AND", 1) if where else ""
    suite_rows = db.execute(
        f"""SELECT s.id, s.name, {COUNT_SQL}
            FROM suites s LEFT JOIN cases c ON c.suite_id = s.id {suite_where}
            GROUP BY s.id ORDER BY s.name""",
        params,
    ).fetchall()
    suite_stats = [dict(id=r["id"], name=r["name"], **compute_stats(r)) for r in suite_rows]
    if active["suite_id"]:
        suite_stats = [s for s in suite_stats if s["id"] == active["suite_id"]]

    module_rows = db.execute(
        f"""SELECT CASE WHEN c.module = '' THEN '(Modül yok)' ELSE c.module END AS name, {COUNT_SQL}
            FROM cases c {where} GROUP BY name ORDER BY total DESC LIMIT 15""",
        params,
    ).fetchall()
    module_stats = [dict(name=r["name"], **compute_stats(r)) for r in module_rows]

    failed_where = (where + " AND " if where else "WHERE ") + "c.status IN ('failed','blocked')"
    recent_failed = db.execute(
        f"""SELECT c.*, s.name AS suite_name FROM cases c JOIN suites s ON s.id = c.suite_id
            {failed_where} ORDER BY c.updated_at DESC LIMIT 6""",
        params,
    ).fetchall()

    upcoming_todos = db.execute(
        """SELECT * FROM todos WHERE done = 0
           ORDER BY CASE WHEN due_date = '' THEN 1 ELSE 0 END, due_date,
                    CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END
           LIMIT 5"""
    ).fetchall()

    return render_template(
        "dashboard.html",
        stats=stats,
        suite_stats=suite_stats,
        module_stats=module_stats,
        recent_failed=recent_failed,
        upcoming_todos=upcoming_todos,
        suites=all_suites(),
        modules=all_modules(active["suite_id"]),
        filters=active,
        filter_args={k: v for k, v in active.items() if v},
    )


# --------------------------------------------------------------------------- #
# Test Paketleri
# --------------------------------------------------------------------------- #
@app.route("/suites")
def suites():
    rows = get_db().execute(
        f"""SELECT s.*, {COUNT_SQL} FROM suites s LEFT JOIN cases c ON c.suite_id = s.id
            GROUP BY s.id ORDER BY s.name"""
    ).fetchall()
    items = [dict(**dict(r), stats=compute_stats(r)) for r in rows]
    overall = compute_stats(get_db().execute(f"SELECT {COUNT_SQL} FROM cases c").fetchone())
    return render_template("suites.html", suites=items, overall=overall)


def _suite_form_values():
    return {
        "name": (request.form.get("name") or "").strip(),
        "description": (request.form.get("description") or "").strip(),
    }


@app.route("/suites/new", methods=["GET", "POST"])
def suite_new():
    if request.method == "POST":
        v = _suite_form_values()
        if not v["name"]:
            flash("Paket adı zorunludur.", "danger")
        elif get_db().execute("SELECT 1 FROM suites WHERE name = ?", (v["name"],)).fetchone():
            flash("Bu isimde bir paket zaten var.", "danger")
        else:
            db = get_db()
            db.execute("INSERT INTO suites (name, description) VALUES (?, ?)", (v["name"], v["description"]))
            db.commit()
            flash(f"“{v['name']}” paketi oluşturuldu.", "success")
            return redirect(url_for("suites"))
        return render_template("suite_form.html", suite=v, is_new=True)
    return render_template("suite_form.html", suite={"name": "", "description": ""}, is_new=True)


@app.route("/suites/<int:suite_id>/edit", methods=["GET", "POST"])
def suite_edit(suite_id):
    suite = get_or_404("suites", suite_id)
    if request.method == "POST":
        v = _suite_form_values()
        dup = get_db().execute("SELECT 1 FROM suites WHERE name = ? AND id <> ?", (v["name"], suite_id)).fetchone()
        if not v["name"]:
            flash("Paket adı zorunludur.", "danger")
        elif dup:
            flash("Bu isimde bir paket zaten var.", "danger")
        else:
            db = get_db()
            db.execute("UPDATE suites SET name = ?, description = ? WHERE id = ?",
                       (v["name"], v["description"], suite_id))
            db.commit()
            flash("Paket güncellendi.", "success")
            return redirect(url_for("suites"))
        return render_template("suite_form.html", suite=dict(v, id=suite_id), is_new=False)
    return render_template("suite_form.html", suite=suite, is_new=False)


@app.route("/suites/<int:suite_id>/delete", methods=["POST"])
def suite_delete(suite_id):
    suite = get_or_404("suites", suite_id)
    db = get_db()
    db.execute("DELETE FROM suites WHERE id = ?", (suite_id,))
    db.commit()
    flash(f"“{suite['name']}” paketi ve içindeki tüm senaryolar silindi.", "warning")
    return redirect(url_for("suites"))


# --------------------------------------------------------------------------- #
# Test Senaryoları
# --------------------------------------------------------------------------- #
@app.route("/cases")
def cases():
    db = get_db()
    where, params, active = case_filters(request.args)
    total = db.execute(f"SELECT COUNT(*) FROM cases c {where}", params).fetchone()[0]
    pages = max(1, math.ceil(total / PER_PAGE))
    page = min(max(1, request.args.get("page", 1, type=int)), pages)
    rows = db.execute(
        f"""SELECT c.*, s.name AS suite_name FROM cases c JOIN suites s ON s.id = c.suite_id
            {where} ORDER BY s.name, c.test_code, c.id LIMIT ? OFFSET ?""",
        params + [PER_PAGE, (page - 1) * PER_PAGE],
    ).fetchall()
    stats = compute_stats(db.execute(f"SELECT {COUNT_SQL} FROM cases c {where}", params).fetchone())
    query_args = {k: v for k, v in active.items() if v}
    return render_template(
        "cases.html", cases=rows, stats=stats, suites=all_suites(),
        modules=all_modules(active["suite_id"]), filters=active,
        page=page, pages=pages, total=total, query_args=query_args,
    )


def _case_form_values():
    v = {k: (request.form.get(k) or "").strip() for k in CASE_COLUMNS}
    v["suite_id"] = request.form.get("suite_id", type=int)
    if v["status"] not in STATUS_LABELS:
        v["status"] = "not_run"
    return v


def _validate_case(v):
    if not v["suite_id"] or not get_db().execute("SELECT 1 FROM suites WHERE id = ?", (v["suite_id"],)).fetchone():
        return "Lütfen geçerli bir test paketi seçin."
    if not v["title"]:
        return "Test adı zorunludur."
    if v["bug_link"] and not re.match(r"^https?://", v["bug_link"], re.I):
        return "Hata linki http:// veya https:// ile başlamalıdır."
    return None


@app.route("/cases/new", methods=["GET", "POST"])
def case_new():
    suites_list = all_suites()
    if not suites_list:
        flash("Senaryo eklemeden önce bir test paketi oluşturun.", "info")
        return redirect(url_for("suite_new"))
    if request.method == "POST":
        v = _case_form_values()
        error = _validate_case(v)
        if error:
            flash(error, "danger")
        else:
            db = get_db()
            db.execute(
                f"INSERT INTO cases (suite_id, {', '.join(CASE_COLUMNS)}) VALUES (?{', ?' * len(CASE_COLUMNS)})",
                [v["suite_id"]] + [v[k] for k in CASE_COLUMNS],
            )
            db.commit()
            flash("Test senaryosu eklendi.", "success")
            if request.form.get("add_another"):
                return redirect(url_for("case_new", suite_id=v["suite_id"], module=v["module"]))
            return redirect(safe_next(url_for("cases")))
        return render_template("case_form.html", case=v, suites=suites_list, modules=all_modules(), is_new=True)
    case = {k: "" for k in CASE_COLUMNS}
    case.update(status="not_run", suite_id=request.args.get("suite_id", type=int),
                module=request.args.get("module", ""))
    return render_template("case_form.html", case=case, suites=suites_list, modules=all_modules(), is_new=True)


@app.route("/cases/<int:case_id>/edit", methods=["GET", "POST"])
def case_edit(case_id):
    case = get_or_404("cases", case_id)
    if request.method == "POST":
        v = _case_form_values()
        error = _validate_case(v)
        if error:
            flash(error, "danger")
            return render_template("case_form.html", case=dict(v, id=case_id), suites=all_suites(),
                                   modules=all_modules(), is_new=False)
        db = get_db()
        db.execute(
            f"""UPDATE cases SET suite_id = ?, {', '.join(f'{k} = ?' for k in CASE_COLUMNS)},
                updated_at = datetime('now','localtime') WHERE id = ?""",
            [v["suite_id"]] + [v[k] for k in CASE_COLUMNS] + [case_id],
        )
        db.commit()
        flash("Test senaryosu güncellendi.", "success")
        return redirect(safe_next(url_for("cases")))
    return render_template("case_form.html", case=case, suites=all_suites(), modules=all_modules(), is_new=False)


@app.route("/cases/<int:case_id>/status", methods=["POST"])
def case_status(case_id):
    get_or_404("cases", case_id)
    status = request.form.get("status")
    if status in STATUS_LABELS:
        db = get_db()
        db.execute("UPDATE cases SET status = ?, updated_at = datetime('now','localtime') WHERE id = ?",
                   (status, case_id))
        db.commit()
        flash(f"Durum “{STATUS_LABELS[status]}” olarak güncellendi.", "success")
    return redirect(safe_next(url_for("cases")))


@app.route("/cases/<int:case_id>/delete", methods=["POST"])
def case_delete(case_id):
    get_or_404("cases", case_id)
    db = get_db()
    db.execute("DELETE FROM cases WHERE id = ?", (case_id,))
    db.commit()
    flash("Test senaryosu silindi.", "warning")
    return redirect(safe_next(url_for("cases")))


@app.route("/cases/bulk", methods=["POST"])
def cases_bulk():
    ids = [int(i) for i in request.form.getlist("ids") if i.isdigit()]
    action = request.form.get("action", "")
    if not ids:
        flash("Lütfen en az bir senaryo seçin.", "info")
        return redirect(safe_next(url_for("cases")))
    db = get_db()
    marks = ",".join("?" * len(ids))
    if action == "delete":
        db.execute(f"DELETE FROM cases WHERE id IN ({marks})", ids)
        flash(f"{len(ids)} senaryo silindi.", "warning")
    elif action in STATUS_LABELS:
        db.execute(f"UPDATE cases SET status = ?, updated_at = datetime('now','localtime') WHERE id IN ({marks})",
                   [action] + ids)
        flash(f"{len(ids)} senaryonun durumu “{STATUS_LABELS[action]}” yapıldı.", "success")
    db.commit()
    return redirect(safe_next(url_for("cases")))


# --------------------------------------------------------------------------- #
# Excel
# --------------------------------------------------------------------------- #
TOKEN_RE = re.compile(r"^[0-9a-f]{32}$")


def _upload_path(token):
    if not TOKEN_RE.match(token or ""):
        abort(404)
    path = os.path.join(app.config["UPLOAD_FOLDER"], f"{token}.xlsx")
    if not os.path.exists(path):
        flash("Yüklenen dosya bulunamadı, lütfen tekrar yükleyin.", "danger")
        return None
    return path


@app.route("/excel")
def excel():
    return render_template("excel.html", suites=all_suites(), modules=all_modules())


@app.route("/excel/upload", methods=["POST"])
def excel_upload():
    file = request.files.get("file")
    if not file or not file.filename:
        flash("Lütfen bir Excel dosyası seçin.", "danger")
        return redirect(url_for("excel"))
    if not file.filename.lower().endswith((".xlsx", ".xlsm")):
        flash("Yalnızca .xlsx / .xlsm dosyaları desteklenir. (.xls dosyasını Excel'de .xlsx olarak kaydedin.)",
              "danger")
        return redirect(url_for("excel"))
    token = uuid.uuid4().hex
    path = os.path.join(app.config["UPLOAD_FOLDER"], f"{token}.xlsx")
    file.save(path)
    try:
        excel_utils.sheet_names(path)
    except Exception:  # bozuk / geçersiz dosya
        os.remove(path)
        flash("Dosya okunamadı. Geçerli bir Excel dosyası olduğundan emin olun.", "danger")
        return redirect(url_for("excel"))
    return redirect(url_for("excel_map", token=token, name=file.filename))


@app.route("/excel/map/<token>", methods=["GET", "POST"])
def excel_map(token):
    path = _upload_path(token)
    if path is None:
        return redirect(url_for("excel"))
    header_row = max(1, request.values.get("header_row", 1, type=int))
    all_data = excel_utils.read_all_sheets(path, header_row)  # {sayfa: (başlıklar, satırlar)}
    sheets = list(all_data)
    sheet = request.values.get("sheet")
    if sheet not in all_data:
        sheet = sheets[0]
    headers, rows = all_data[sheet]

    if request.method == "POST":
        mapping = {}
        for field in CASE_FIELDS:
            raw = request.form.get(f"map_{field}", "")
            if raw.isdigit() and int(raw) < len(headers):
                mapping[field] = int(raw)

        # Kullanıcının seçtiği durum değeri eşleştirmesi
        status_map = {}
        for i in range(request.form.get("sval_count", 0, type=int)):
            raw = (request.form.get(f"sval_{i}") or "").strip().lower()
            target = request.form.get(f"smap_{i}")
            if raw and target in STATUS_LABELS:
                status_map[raw] = target

        # Hangi sayfalar aktarılacak? Diğer sayfalarda kolonlar başlık adına göre bulunur.
        selected = request.form.getlist("sheets") if request.form.get("all_sheets") == "1" else [sheet]
        batches = []
        for name in sheets:
            if name not in selected:
                continue
            h, r = all_data[name]
            m = mapping if name == sheet else excel_utils.remap_by_header(mapping, headers, h)
            batches.append((name, m, r))

        result = _run_import(batches, mapping, status_map, request.form)
        if result is None:
            return redirect(url_for("excel_map", token=token, sheet=sheet, header_row=header_row,
                                    name=request.args.get("name", "")))
        os.remove(path)
        return render_template("excel_result.html", result=result)

    guess = excel_utils.guess_mapping(headers)
    value_sets = excel_utils.column_value_sets(list(all_data.values()), headers)
    return render_template(
        "excel_map.html",
        token=token, filename=request.args.get("name", ""), sheets=sheets, sheet=sheet,
        header_row=header_row, headers=headers, preview=rows[:5], row_count=len(rows),
        sheet_counts={n: len(d[1]) for n, d in all_data.items()},
        fields=CASE_FIELDS, guess=guess, suites=all_suites(),
        value_sets=value_sets,
        status_guess={v: normalize_status(v) for vals in value_sets.values() if vals for v in vals},
        known_status={v for vals in value_sets.values() if vals for v in vals if _is_known_status(v)},
        clean_names={n: excel_utils.clean_sheet_name(n) for n in sheets},
    )


def _is_known_status(value):
    text = value.strip().lower()
    return normalize_status(text) != "not_run" or text in (
        "çalıştırılmadı", "calistirilmadi", "not run", "not_run", "notrun", "yapılmadı", "yapilmadi",
        "koşulmadı", "kosulmadi", "-", "n/a", "uygulanamaz", "uygulanmadı", "uygulanmadi",
        "çalıştırılamadı", "calistirilamadi")


def _run_import(batches, mapping, status_map, form):
    """batches: [(sayfa adı, kolon eşleştirmesi, satırlar), ...]"""
    db = get_db()
    if not batches:
        flash("En az bir sayfa seçin.", "danger")
        return None
    if "title" not in mapping and "test_code" not in mapping:
        flash("En azından “Test Adı” veya “Test Kodu” alanını bir kolonla eşleştirmelisiniz.", "danger")
        return None

    suite_mode = form.get("suite_mode", "fixed")
    fixed_suite_id = None
    if suite_mode == "column":
        if "suite_name" not in mapping:
            flash("“Paketi Excel kolonundan al” seçeneği için Test Paketi kolonunu eşleştirin.", "danger")
            return None
    else:
        choice = form.get("suite_id", "")
        if choice == "new":
            name = (form.get("new_suite_name") or "").strip()
            if not name:
                flash("Yeni paket adı girin.", "danger")
                return None
            fixed_suite_id = _suite_id_by_name(name)
        elif choice.isdigit() and db.execute("SELECT 1 FROM suites WHERE id = ?", (int(choice),)).fetchone():
            fixed_suite_id = int(choice)
        else:
            flash("Lütfen hedef test paketini seçin.", "danger")
            return None

    update_existing = form.get("update_existing") == "1"
    keep_existing_on_blank = form.get("keep_blank") == "1"
    match_by = form.get("match_by", "test_code")
    key_field = match_by if match_by in ("test_code", "title") else "test_code"
    module_from_sheet = form.get("module_from_sheet") == "1" and "module" not in mapping
    first_line = (form.get("header_row", 1, type=int) or 1) + 1
    multi = len(batches) > 1
    result = {"inserted": 0, "updated": 0, "skipped": 0, "errors": [],
              "total": sum(len(r) for _, _, r in batches), "sheets": []}
    touched = set()  # bu içe aktarmada eşleşen/eklenen kayıtlar (aynı adlı satırlar birbirini ezmesin)

    for sheet_name, sheet_map, rows in batches:
        if "title" not in sheet_map and "test_code" not in sheet_map:
            result["skipped"] += len(rows)
            result["errors"].append(f"“{sheet_name}”: Test adı/kodu kolonu bulunamadı, sayfa atlandı.")
            continue
        fields = [f for f in sheet_map if f != "suite_name"]
        if module_from_sheet:
            fields.append("module")
        sheet_res = {"name": sheet_name, "inserted": 0, "updated": 0, "skipped": 0}
        prefix = f"“{sheet_name}” " if multi else ""

        for line_no, row in enumerate(rows, start=first_line):
            data = excel_utils.map_row(row, sheet_map, status_map)
            if module_from_sheet:
                data["module"] = excel_utils.clean_sheet_name(sheet_name)
            if not data.get("title") and not data.get("test_code"):
                sheet_res["skipped"] += 1
                result["errors"].append(f"{prefix}Satır {line_no}: Test adı/kodu boş, atlandı.")
                continue

            if suite_mode == "column":
                suite_id = _suite_id_by_name(data.get("suite_name") or "Genel")
            else:
                suite_id = fixed_suite_id

            existing = None
            if data.get(key_field):
                sql = f"SELECT id FROM cases WHERE suite_id = ? AND {key_field} = ?"
                params = [suite_id, data[key_field]]
                if key_field == "title":  # aynı ad farklı modüllerde tekrar edebilir
                    sql += " AND module = ?"
                    params.append(data.get("module", ""))
                if touched:
                    sql += f" AND id NOT IN ({','.join('?' * len(touched))})"
                    params.extend(touched)
                existing = db.execute(sql + " ORDER BY id LIMIT 1", params).fetchone()

            if existing:
                touched.add(existing["id"])
                if not update_existing:
                    sheet_res["skipped"] += 1
                    continue
                cols = [f for f in fields if not (keep_existing_on_blank and data.get(f, "") == "")]
                if "title" in cols and not data.get("title"):
                    cols.remove("title")  # test adı hiçbir zaman boşaltılmaz
                if "status" in cols and keep_existing_on_blank and _raw_blank(row, sheet_map.get("status")):
                    cols.remove("status")
                if cols:
                    db.execute(
                        f"""UPDATE cases SET {', '.join(f'{c} = ?' for c in cols)},
                            updated_at = datetime('now','localtime') WHERE id = ?""",
                        [data.get(c, "") for c in cols] + [existing["id"]],
                    )
                sheet_res["updated"] += 1
            else:
                values = {k: data.get(k, "") for k in CASE_COLUMNS}
                values["status"] = data.get("status", "not_run")
                values["title"] = data.get("title") or data.get("test_code", "")
                new_id = db.execute(
                    f"INSERT INTO cases (suite_id, {', '.join(CASE_COLUMNS)}) VALUES (?{', ?' * len(CASE_COLUMNS)})",
                    [suite_id] + [values[k] for k in CASE_COLUMNS],
                ).lastrowid
                touched.add(new_id)
                sheet_res["inserted"] += 1

        for k in ("inserted", "updated", "skipped"):
            result[k] += sheet_res[k]
        result["sheets"].append(sheet_res)
    db.commit()
    return result


def _raw_blank(row, idx):
    return idx is None or idx >= len(row) or excel_utils.cell_text(row[idx]) == ""


def _suite_id_by_name(name):
    db = get_db()
    row = db.execute("SELECT id FROM suites WHERE name = ?", (name,)).fetchone()
    if row:
        return row["id"]
    return db.execute("INSERT INTO suites (name) VALUES (?)", (name,)).lastrowid


@app.route("/excel/export")
def excel_export():
    db = get_db()
    where, params, _ = case_filters(request.args)
    rows = db.execute(
        f"""SELECT c.*, s.name AS suite_name FROM cases c JOIN suites s ON s.id = c.suite_id
            {where} ORDER BY s.name, c.test_code, c.id""",
        params,
    ).fetchall()
    stats = compute_stats(db.execute(f"SELECT {COUNT_SQL} FROM cases c {where}", params).fetchone())
    buf = excel_utils.export_cases(rows, stats)
    filename = f"test_raporu_{datetime.now():%Y%m%d_%H%M}.xlsx"
    return send_file(buf, as_attachment=True, download_name=filename,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def _quick_import_file(path, filename, target_suite_id=None):
    """Bir Excel dosyasını otomatik eşleştirmeyle içe aktarır.

    Paket adı = dosya adı (varsa güncellenir) veya target_suite_id. Tüm dolu sayfalar aktarılır;
    birden fazla sayfa varsa ve Modül kolonu yoksa sayfa adı modül olur.
    """
    stem = os.path.splitext(os.path.basename(filename))[0].strip() or "Yeni Paket"
    summary = {"file": filename, "suite": stem, "suite_id": None, "error": None, "result": None,
               "unknown_status": [], "existed": False}
    all_data = excel_utils.read_all_sheets(path, 1)
    filled = [(n, h, r) for n, (h, r) in all_data.items() if h and r]
    if not filled:
        summary["error"] = "Dosyada veri içeren sayfa bulunamadı."
        return summary
    ref_name, ref_headers, _ = filled[0]
    mapping = excel_utils.guess_mapping(ref_headers)
    if "title" not in mapping and "test_code" not in mapping:
        summary["error"] = ("Test adı / kodu kolonu tanınamadı (başlıklar: " + ", ".join(h for h in ref_headers if h)
                            + "). Bu dosyayı Excel sayfasındaki eşleştirmeli içe aktarma ile yükleyin.")
        return summary

    batches, unknown = [], []
    for name, h, r in filled:
        m = mapping if name == ref_name else excel_utils.remap_by_header(mapping, ref_headers, h)
        batches.append((name, m, r))
        if "status" in m:
            for row in r:
                v = excel_utils.cell_text(row[m["status"]]) if m["status"] < len(row) else ""
                if v and not _is_known_status(v) and v not in unknown:
                    unknown.append(v)
    summary["unknown_status"] = unknown

    db = get_db()
    if target_suite_id:
        suite = db.execute("SELECT id, name FROM suites WHERE id = ?", (target_suite_id,)).fetchone()
        summary.update(suite=suite["name"], suite_id=suite["id"], existed=True)
        suite_choice = str(suite["id"])
    else:
        existing = db.execute("SELECT id FROM suites WHERE name = ?", (stem,)).fetchone()
        summary["existed"] = existing is not None
        suite_choice = "new"

    form = MultiDict({
        "header_row": "1", "suite_mode": "fixed", "suite_id": suite_choice, "new_suite_name": stem,
        "match_by": "test_code" if "test_code" in mapping else "title",
        "update_existing": "1", "keep_blank": "1",
        "module_from_sheet": "1" if len(filled) > 1 else "",
    })
    summary["result"] = _run_import(batches, mapping, {}, form)
    if summary["suite_id"] is None:
        row = db.execute("SELECT id FROM suites WHERE name = ?", (stem,)).fetchone()
        summary["suite_id"] = row["id"] if row else None
    return summary


@app.route("/suites/import", methods=["POST"])
def suites_import():
    """Paketler sayfası: bir veya birden fazla Excel dosyasını paket olarak ekle / güncelle."""
    files = [f for f in request.files.getlist("files") if f and f.filename]
    target = request.form.get("suite_id", type=int)
    if target:
        get_or_404("suites", target)
    if not files:
        flash("Lütfen en az bir Excel dosyası seçin.", "danger")
        return redirect(url_for("suites"))

    summaries = []
    for f in files:
        if not f.filename.lower().endswith((".xlsx", ".xlsm")):
            summaries.append({"file": f.filename, "error": "Yalnızca .xlsx / .xlsm desteklenir.", "result": None})
            continue
        path = os.path.join(app.config["UPLOAD_FOLDER"], f"{uuid.uuid4().hex}.xlsx")
        f.save(path)
        try:
            summaries.append(_quick_import_file(path, f.filename, target))
        except Exception as exc:  # bozuk dosya vb.
            get_db().rollback()
            summaries.append({"file": f.filename, "error": f"Dosya okunamadı: {exc}", "result": None})
        finally:
            if os.path.exists(path):
                os.remove(path)
        if target:
            break  # tek pakete güncelleme yalnızca bir dosya ile yapılır

    stats = compute_stats(get_db().execute(f"SELECT {COUNT_SQL} FROM cases c").fetchone())
    return render_template("suites_import_result.html", summaries=summaries, stats=stats,
                           suite_count=get_db().execute("SELECT COUNT(*) FROM suites").fetchone()[0])


@app.route("/excel/template")
def excel_template():
    return send_file(excel_utils.template_workbook(), as_attachment=True,
                     download_name="test_ice_aktarma_sablonu.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# --------------------------------------------------------------------------- #
# To-Do
# --------------------------------------------------------------------------- #
@app.route("/todos")
def todos():
    show = request.args.get("show", "open")
    sort = request.args.get("sort", "due")
    where = {"open": "WHERE done = 0", "done": "WHERE done = 1"}.get(show, "")
    prio = "CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END"
    due = "CASE WHEN due_date = '' THEN 1 ELSE 0 END, due_date"
    order = f"{prio}, {due}" if sort == "priority" else f"{due}, {prio}"
    items = get_db().execute(f"SELECT * FROM todos {where} ORDER BY done, {order}, id DESC").fetchall()
    counts = get_db().execute(
        "SELECT COUNT(*) AS total, SUM(done = 0) AS open, SUM(done = 1) AS done, "
        "SUM(done = 0 AND due_date <> '' AND due_date < date('now','localtime')) AS overdue FROM todos"
    ).fetchone()
    return render_template("todos.html", todos=items, show=show, sort=sort, counts=counts)


def _todo_form_values():
    v = {
        "title": (request.form.get("title") or "").strip(),
        "description": (request.form.get("description") or "").strip(),
        "priority": request.form.get("priority", "medium"),
        "due_date": (request.form.get("due_date") or "").strip(),
    }
    if v["priority"] not in PRIORITY_LABELS:
        v["priority"] = "medium"
    if v["due_date"] and not re.match(r"^\d{4}-\d{2}-\d{2}$", v["due_date"]):
        v["due_date"] = ""
    v["status"] = request.form.get("status", "todo")
    if v["status"] not in TODO_STATUS_LABELS:
        v["status"] = "todo"
    return v


def _next_position(status):
    row = get_db().execute("SELECT COALESCE(MAX(position), 0) + 1 FROM todos WHERE status = ?", (status,)).fetchone()
    return row[0]


def _set_todo_status(todo_id, status, position=None):
    """Durumu değiştirir; 'done' kolonu kanban durumuyla senkron tutulur."""
    if position is None:
        position = _next_position(status)
    get_db().execute("UPDATE todos SET status = ?, done = ?, position = ? WHERE id = ?",
                     (status, 1 if status == "done" else 0, position, todo_id))


@app.route("/todos/new", methods=["POST"])
def todo_new():
    v = _todo_form_values()
    if not v["title"]:
        flash("Görev başlığı zorunludur.", "danger")
    else:
        db = get_db()
        db.execute(
            "INSERT INTO todos (title, description, priority, due_date, status, done, position) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (v["title"], v["description"], v["priority"], v["due_date"], v["status"],
             1 if v["status"] == "done" else 0, _next_position(v["status"])),
        )
        db.commit()
        flash("Görev eklendi.", "success")
    return redirect(safe_next(url_for("todos")))


@app.route("/todos/<int:todo_id>/edit", methods=["GET", "POST"])
def todo_edit(todo_id):
    todo = get_or_404("todos", todo_id)
    if request.method == "POST":
        v = _todo_form_values()
        if not v["title"]:
            flash("Görev başlığı zorunludur.", "danger")
            return render_template("todo_form.html", todo=dict(v, id=todo_id))
        db = get_db()
        db.execute("UPDATE todos SET title = ?, description = ?, priority = ?, due_date = ? WHERE id = ?",
                   (v["title"], v["description"], v["priority"], v["due_date"], todo_id))
        if v["status"] != todo["status"]:
            _set_todo_status(todo_id, v["status"])
        db.commit()
        flash("Görev güncellendi.", "success")
        return redirect(safe_next(url_for("todos")))
    return render_template("todo_form.html", todo=todo)


@app.route("/todos/<int:todo_id>/toggle", methods=["POST"])
def todo_toggle(todo_id):
    todo = get_or_404("todos", todo_id)
    _set_todo_status(todo_id, "todo" if todo["status"] == "done" else "done")
    get_db().commit()
    return redirect(safe_next(url_for("todos")))


@app.route("/todos/<int:todo_id>/move", methods=["POST"])
def todo_move(todo_id):
    """Kanban: kartı başka sütuna taşı (sürükle-bırak olmayan cihazlar için menüden)."""
    get_or_404("todos", todo_id)
    status = request.form.get("status")
    if status in TODO_STATUS_LABELS:
        _set_todo_status(todo_id, status)
        get_db().commit()
    return redirect(safe_next(url_for("kanban")))


@app.route("/kanban")
def kanban():
    rows = get_db().execute("SELECT * FROM todos ORDER BY position, id").fetchall()
    columns = {s: [] for s in TODO_STATUS_ORDER}
    for r in rows:
        columns.get(r["status"], columns["todo"]).append(r)
    return render_template("kanban.html", columns=columns)


@app.route("/kanban/reorder", methods=["POST"])
def kanban_reorder():
    """Sürükle-bırak sonrası bir sütunun yeni sırası: {"status": "...", "ids": [3, 1, 7]}"""
    payload = request.get_json(silent=True) or {}
    status = payload.get("status")
    ids = [int(i) for i in payload.get("ids", []) if str(i).isdigit()]
    if status not in TODO_STATUS_LABELS:
        return {"ok": False, "error": "Geçersiz durum"}, 400
    db = get_db()
    for pos, todo_id in enumerate(ids, start=1):
        db.execute("UPDATE todos SET status = ?, done = ?, position = ? WHERE id = ?",
                   (status, 1 if status == "done" else 0, pos, todo_id))
    db.commit()
    counts = {s: 0 for s in TODO_STATUS_ORDER}
    for r in db.execute("SELECT status, COUNT(*) AS n FROM todos GROUP BY status"):
        counts[r["status"]] = r["n"]
    return {"ok": True, "counts": counts}


@app.route("/todos/<int:todo_id>/delete", methods=["POST"])
def todo_delete(todo_id):
    get_or_404("todos", todo_id)
    db = get_db()
    db.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
    db.commit()
    flash("Görev silindi.", "warning")
    return redirect(safe_next(url_for("todos")))


# --------------------------------------------------------------------------- #
@app.errorhandler(404)
def not_found(_e):
    return render_template("404.html"), 404


@app.errorhandler(413)
def too_large(_e):
    flash("Dosya çok büyük (en fazla 16 MB).", "danger")
    return redirect(url_for("excel"))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
