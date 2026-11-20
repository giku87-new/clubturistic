"""
Server Web & REST API de producție (FastAPI + SQLite FTS5) pentru ClubTuristic.md.
Servește exclusiv fișierele statice publice din `/static`, pagini SEO server-rendered
pentru `/eveniment/{slug}` și `/locatie/{slug}`, API public cu căutare FTS5 și export `.ics`,
precum și API de administrare protejat prin HTTP Basic Auth.
"""

from contextlib import contextmanager
from datetime import datetime, timedelta
import html
import json
import os
import re
import secrets
import sqlite3
import sys
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.responses import FileResponse, HTMLResponse, Response, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
import uvicorn

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "clubturistic.db")
STATIC_DIR = os.path.join(BASE_DIR, "static")

ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "clubturistic2026")

app = FastAPI(title="ClubTuristic.md", version="2.0.0", docs_url=None, redoc_url=None)
# Enable GZIP compression for faster transfers
from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=500)
# Optional HTTPS redirect (only when behind a reverse proxy terminating TLS, never on localhost)
@app.middleware("http")
async def https_redirect(request: Request, call_next):
    if request.headers.get("x-forwarded-proto") == "http" and request.url.hostname not in ("localhost", "127.0.0.1"):
        url = request.url.replace(scheme="https")
        return RedirectResponse(url=str(url), status_code=301)
    return await call_next(request)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

security = HTTPBasic()

from search_utils import build_fts_query, delete_fts_entry, strip_diacritics, upsert_fts_entry  # noqa: E402


@contextmanager
def get_db_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def require_admin(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    """Autentificare HTTP Basic sigură (timing-safe) pentru toate rutele /api/admin/*."""
    user_ok = secrets.compare_digest(credentials.username.encode("utf-8"), ADMIN_USER.encode("utf-8"))
    pass_ok = secrets.compare_digest(credentials.password.encode("utf-8"), ADMIN_PASS.encode("utf-8"))
    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autentificare necesară pentru administrare.",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


def make_slug(text: str, prefix: str = "item") -> str:
    norm = strip_diacritics(text)
    slug = re.sub(r"\s+", "-", norm).strip("-")
    return slug or f"{prefix}-{int(datetime.utcnow().timestamp())}"


def serialize_row(row: sqlite3.Row) -> dict[str, Any]:
    """Convertește un rând SQLite în dict API și parsează `surse_media_json`."""
    d = dict(row)
    raw_surse = d.pop("surse_media_json", "[]")
    try:
        d["surse_media"] = json.loads(raw_surse) if raw_surse else []
    except json.JSONDecodeError:
        d["surse_media"] = []
    return d


def build_query_clauses(
    conn: sqlite3.Connection,
    table_alias: str,
    fts_type: str,
    q: str,
) -> tuple[str, str, list[Any], bool]:
    """
    Construiește clauzele JOIN + WHERE + ORDER pentru căutare FTS5
    (cu fallback sigur la potrivire pe coloane normalizate dacă interogarea FTS e goală).
    """
    q_clean = (q or "").strip()
    if not q_clean:
        return "", "", [], False

    fts_expr = build_fts_query(q_clean)
    if not fts_expr:
        return "", "", [], False

    join_sql = f" JOIN search_fts f ON f.item_type = '{fts_type}' AND f.item_id = {table_alias}.id"
    where_sql = " AND search_fts MATCH ?"
    return join_sql, where_sql, [fts_expr], True


# ==============================================================================
# MODELE PYDANTIC PENTRU VALIDARE
# ==============================================================================


class PropunereCreate(BaseModel):
    tip_entitate: str = Field(default="Eveniment / Festival", max_length=80)
    titlu: str = Field(..., min_length=3, max_length=180)
    localitate: str = Field(..., min_length=2, max_length=120)
    raion: str = Field(default="", max_length=80)
    data_text: str = Field(default="", max_length=120)
    descriere: str = Field(default="", max_length=1200)
    link_sursa: str = Field(..., min_length=8, max_length=400)
    contact_expeditor: str = Field(default="", max_length=120)

    @field_validator("link_sursa")
    @classmethod
    def validate_url(cls, v: str) -> str:
        val = v.strip()
        if not (val.startswith("http://") or val.startswith("https://")):
            raise ValueError("Link-ul sursă trebuie să înceapă cu http:// sau https://")
        return val


class PropunereStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(In asteptare|Aprobat|Respins)$")


class EvenimentPayload(BaseModel):
    id: Optional[str] = None
    slug: Optional[str] = None
    titlu: str = Field(..., min_length=2, max_length=220)
    tip: str = Field(default="Festival Gastronomic", max_length=80)
    organizator: str = Field(default="Organizator Local", max_length=180)
    regiune: str = Field(default="Centru", max_length=60)
    raion: str = Field(default="Chișinău", max_length=80)
    localitate: str = Field(default="mun. Chișinău", max_length=100)
    locatie_exacta: str = Field(default="", max_length=220)
    lat: float = 47.0105
    lng: float = 28.8638
    distanta_chisinau_km: int = 0
    data_text: str = Field(default="Anual (de confirmat)", max_length=160)
    data_start: str = Field(default="", max_length=20)
    data_end: str = Field(default="", max_length=20)
    regula_recurenta: str = Field(default="Anual", max_length=240)
    tip_recurenta: str = Field(default="Recurență relativă", max_length=80)
    luna_principala: str = Field(default="Iunie", max_length=40)
    luni_active: str = Field(default="Iunie", max_length=200)
    sezon: str = Field(default="Vară", max_length=40)
    ultima_editie_verificata: str = Field(default="Confirmat prin sursă publică", max_length=160)
    urmatoarea_data_estimata: str = Field(default="2027-06-15", max_length=20)
    status_data: str = Field(default="Estimat după tradiție", max_length=60)
    pret_intrare: str = Field(default="Gratuit", max_length=120)
    descriere_scurta: str = Field(default="", max_length=600)
    cum_a_fost_real: str = Field(default="", max_length=3000)
    ce_gusti: str = Field(default="", max_length=500)
    taguri: str = Field(default="", max_length=400)
    link_oficial: str = Field(default="https://moldova.travel/ro", max_length=400)
    facebook_url: str = Field(default="", max_length=400)
    instagram_url: str = Field(default="", max_length=400)
    bilete_url: str = Field(default="", max_length=400)
    ultima_verificare_la: str = Field(default="", max_length=30)
    sursa_confirmarii: str = Field(default="", max_length=400)
    surse_media: list[dict[str, str]] = Field(default_factory=list)
    imagine_url: str = Field(default="/static/images/chisinau.jpg", max_length=400)
    imagine_credit: str = Field(default="Arhivă verificată ClubTuristic.md", max_length=200)
    este_recomandat: int = 0


class LocatiePayload(BaseModel):
    id: Optional[str] = None
    slug: Optional[str] = None
    titlu: str = Field(..., min_length=2, max_length=220)
    categorie: str = Field(default="Cramă & Resort Turistic", max_length=80)
    regiune: str = Field(default="Centru", max_length=60)
    raion: str = Field(default="Chișinău", max_length=80)
    localitate: str = Field(default="", max_length=100)
    adresa: str = Field(default="", max_length=220)
    lat: float = 47.0105
    lng: float = 28.8638
    distanta_chisinau_km: int = 0
    program_vizita: str = Field(default="Cu programare", max_length=160)
    rezervare_necesara: str = Field(default="Recomandată", max_length=120)
    buget_orientativ: str = Field(default="300 - 700 MDL", max_length=120)
    descriere_scurta: str = Field(default="", max_length=600)
    ce_merita_vazut: str = Field(default="", max_length=3000)
    ce_gusti: str = Field(default="", max_length=500)
    taguri: str = Field(default="", max_length=400)
    link_oficial: str = Field(default="https://moldova.travel/ro", max_length=400)
    facebook_url: str = Field(default="", max_length=400)
    instagram_url: str = Field(default="", max_length=400)
    surse_media: list[dict[str, str]] = Field(default_factory=list)
    imagine_url: str = Field(default="/static/images/vineyard_moldova.jpg", max_length=400)
    imagine_credit: str = Field(default="Arhivă verificată ClubTuristic.md", max_length=200)
    este_recomandat: int = 0


def _index_event(conn: sqlite3.Connection, row_id: str, data: dict[str, Any]) -> None:
    upsert_fts_entry(
        conn,
        "eveniment",
        row_id,
        data["slug"],
        data["titlu"],
        [
            data["tip"], data["organizator"], data["regiune"], data["raion"],
            data["localitate"], data["locatie_exacta"], data["data_text"],
            data["luni_active"], data["descriere_scurta"], data["cum_a_fost_real"],
            data["ce_gusti"],
        ],
        data["taguri"],
    )


def _index_location(conn: sqlite3.Connection, row_id: str, data: dict[str, Any]) -> None:
    upsert_fts_entry(
        conn,
        "locatie",
        row_id,
        data["slug"],
        data["titlu"],
        [
            data["categorie"], data["regiune"], data["raion"], data["localitate"],
            data["adresa"], data["descriere_scurta"], data["ce_merita_vazut"],
            data["ce_gusti"],
        ],
        data["taguri"],
    )


# ==============================================================================
# RUTE HTML PUBLICE (INCL. SERVER-SIDE SEO / OPENGRAPH)
# ==============================================================================


@app.get("/", include_in_schema=False)
def serve_home():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"), media_type="text/html; charset=utf-8")


@app.get("/admin", include_in_schema=False)
def serve_admin():
    return FileResponse(os.path.join(STATIC_DIR, "admin.html"), media_type="text/html; charset=utf-8")


@app.get("/robots.txt", include_in_schema=False)
def serve_robots(request: Request):
    base_url = str(request.base_url).rstrip("/")
    body = f"User-agent: *\nAllow: /\nDisallow: /admin\nDisallow: /api/admin/\nSitemap: {base_url}/sitemap.xml\n"
    return Response(content=body, media_type="text/plain; charset=utf-8")


@app.get("/sitemap.xml", include_in_schema=False)
def serve_sitemap(request: Request):
    base_url = str(request.base_url).rstrip("/")
    today = datetime.utcnow().strftime("%Y-%m-%d")
    with get_db_conn() as conn:
        ev_rows = conn.execute("SELECT slug, actualizat_la FROM evenimente ORDER BY slug").fetchall()
        loc_rows = conn.execute("SELECT slug, actualizat_la FROM locatii ORDER BY slug").fetchall()

    urls = [
        f"  <url><loc>{html.escape(base_url)}/</loc><lastmod>{today}</lastmod><changefreq>daily</changefreq><priority>1.0</priority></url>"
    ]
    for r in ev_rows:
        lastmod = (r["actualizat_la"] or today)[:10]
        loc_url = html.escape(f"{base_url}/eveniment/{r['slug']}")
        urls.append(
            f"  <url><loc>{loc_url}</loc><lastmod>{lastmod}</lastmod><changefreq>weekly</changefreq><priority>0.8</priority></url>"
        )
    for r in loc_rows:
        lastmod = (r["actualizat_la"] or today)[:10]
        loc_url = html.escape(f"{base_url}/locatie/{r['slug']}")
        urls.append(
            f"  <url><loc>{loc_url}</loc><lastmod>{lastmod}</lastmod><changefreq>monthly</changefreq><priority>0.8</priority></url>"
        )

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>\n"
    )
    return Response(content=xml, media_type="application/xml; charset=utf-8")


def _build_json_ld(item_type: str, item: dict[str, Any], desc: str, abs_img: str, canonical: str, base_url: str) -> str:
    if item_type == "eveniment":
        start_date = (item.get("data_start") or item.get("urmatoarea_data_estimata") or "2027-06-01")[:10]
        end_date = (item.get("data_end") or start_date)[:10]
        is_free = "gratuit" in (item.get("pret_intrare") or "").lower()
        ld_obj = {
            "@context": "https://schema.org",
            "@type": "Event",
            "name": item["titlu"],
            "description": desc[:300],
            "startDate": start_date,
            "endDate": end_date,
            "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
            "eventStatus": "https://schema.org/EventScheduled",
            "isAccessibleForFree": is_free,
            "image": [abs_img],
            "url": canonical,
            "location": {
                "@type": "Place",
                "name": item.get("locatie_exacta") or item.get("localitate") or "Republica Moldova",
                "address": {
                    "@type": "PostalAddress",
                    "addressLocality": item.get("localitate") or "",
                    "addressRegion": item.get("raion") or item.get("regiune") or "",
                    "addressCountry": "MD",
                },
                "geo": {
                    "@type": "GeoCoordinates",
                    "latitude": item.get("lat", 47.0105),
                    "longitude": item.get("lng", 28.8638),
                },
            },
            "organizer": {
                "@type": "Organization",
                "name": item.get("organizator") or "ClubTuristic.md",
                "url": item.get("link_oficial") or base_url,
            },
        }
    else:
        ld_obj = {
            "@context": "https://schema.org",
            "@type": "TouristAttraction",
            "name": item["titlu"],
            "description": desc[:300],
            "image": [abs_img],
            "url": canonical,
            "address": {
                "@type": "PostalAddress",
                "streetAddress": item.get("adresa") or "",
                "addressLocality": item.get("localitate") or "",
                "addressRegion": item.get("raion") or item.get("regiune") or "",
                "addressCountry": "MD",
            },
            "geo": {
                "@type": "GeoCoordinates",
                "latitude": item.get("lat", 47.0105),
                "longitude": item.get("lng", 28.8638),
            },
        }
    return json.dumps(ld_obj, ensure_ascii=False).replace("</", "<\\/").replace("<!--", "<\\!--")


def _render_detail_page(item_type: str, item: dict[str, Any], request: Request) -> HTMLResponse:
    """Randează server-side meta tag-urile SEO/OpenGraph, JSON-LD și datele inițiale în `static/detail.html`."""
    detail_path = os.path.join(STATIC_DIR, "detail.html")
    with open(detail_path, "r", encoding="utf-8") as f:
        tpl = f.read()

    base_url = str(request.base_url).rstrip("/")
    page_title = f"{item['titlu']} — ClubTuristic.md"
    desc = item.get("descriere_scurta") or item.get("cum_a_fost_real") or item.get("ce_merita_vazut") or ""
    img_url = item.get("imagine_url", "/static/images/chisinau.jpg")
    abs_img = img_url if img_url.startswith("http") else f"{base_url}{img_url}"
    canonical = str(request.url)

    payload_json = json.dumps({"item_type": item_type, "item": item}, ensure_ascii=False)
    # Prevenim ieșirea prematură din blocul <script>
    payload_safe = payload_json.replace("</", "<\\/").replace("<!--", "<\\!--")
    json_ld_safe = _build_json_ld(item_type, item, desc, abs_img, canonical, base_url)

    replacements = {
        "__META_TITLE__": html.escape(page_title, quote=True),
        "__META_DESCRIPTION__": html.escape(desc[:220], quote=True),
        "__OG_IMAGE__": html.escape(abs_img, quote=True),
        "__OG_URL__": html.escape(canonical, quote=True),
        "__JSON_LD__": json_ld_safe,
        "__INITIAL_ITEM_JSON__": payload_safe,
    }
    rendered = tpl
    for marker, val in replacements.items():
        rendered = rendered.replace(marker, val)
    return HTMLResponse(content=rendered, status_code=200)


@app.get("/eveniment/{slug}", include_in_schema=False)
def serve_event_detail(slug: str, request: Request):
    with get_db_conn() as conn:
        row = conn.execute("SELECT * FROM evenimente WHERE slug = ?", (slug,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Evenimentul nu a fost găsit")
    return _render_detail_page("eveniment", serialize_row(row), request)


@app.get("/locatie/{slug}", include_in_schema=False)
def serve_location_detail(slug: str, request: Request):
    with get_db_conn() as conn:
        row = conn.execute("SELECT * FROM locatii WHERE slug = ?", (slug,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Locația nu a fost găsită")
    return _render_detail_page("locatie", serialize_row(row), request)


# ==============================================================================
# RUTE API PUBLICE (CĂUTARE FTS5, FILTRARE, STATISTICI, .ICS, PROPUNERI)
# ==============================================================================


@app.get("/api/evenimente")
def api_get_evenimente(
    q: str = "",
    tip: str = "",
    regiune: str = "",
    sezon: str = "",
    luna: str = "",
    gratuit: str = "",
    doar_confirmate: str = "",
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    with get_db_conn() as conn:
        join_sql, where_sql, args, used_fts = build_query_clauses(conn, "e", "eveniment", q)
        base_from = f"FROM evenimente e{join_sql} WHERE 1=1{where_sql}"

        if tip and tip != "Toate":
            base_from += " AND e.tip = ?"
            args.append(tip)
        if regiune and regiune != "Toate":
            base_from += " AND e.regiune = ?"
            args.append(regiune)
        if sezon and sezon != "Toate":
            base_from += " AND e.sezon = ?"
            args.append(sezon)
        if luna and luna != "Toate":
            base_from += (
                " AND (e.luna_principala = ? OR (',' || REPLACE(e.luni_active, ', ', ',') || ',') LIKE ? "
                "OR e.luni_active LIKE '%Tot anul%')"
            )
            args.extend([luna, f"%,{luna},%"])
        if gratuit in ("1", "true", "True"):
            base_from += " AND LOWER(e.pret_intrare) LIKE '%gratuit%'"
        if doar_confirmate in ("1", "true", "True"):
            base_from += " AND (e.data_start != '' OR e.status_data LIKE '%Săptămânal%')"

        total = conn.execute(f"SELECT COUNT(*) {base_from}", args).fetchone()[0]
        order_sql = (
            " ORDER BY bm25(search_fts, 10.0, 2.0, 4.0) ASC, e.este_recomandat DESC"
            if used_fts
            else """ ORDER BY
                CASE
                    WHEN e.data_start != '' AND e.data_start >= date('now') THEN 0
                    WHEN e.status_data LIKE '%Săptămânal%' THEN 1
                    WHEN e.data_start != '' THEN 2
                    ELSE 3
                END ASC,
                CASE WHEN e.data_start != '' THEN e.data_start ELSE e.urmatoarea_data_estimata END ASC,
                e.este_recomandat DESC"""
        )
        rows = conn.execute(
            f"SELECT e.* {base_from}{order_sql} LIMIT ? OFFSET ?",
            [*args, limit, offset],
        ).fetchall()

    return {"total": total, "items": [serialize_row(r) for r in rows]}


@app.get("/api/evenimente/{slug}")
def api_get_single_eveniment(slug: str):
    with get_db_conn() as conn:
        row = conn.execute("SELECT * FROM evenimente WHERE slug = ?", (slug,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Evenimentul nu a fost găsit")
    return serialize_row(row)


def _ics_escape(val: str) -> str:
    return (
        (val or "")
        .replace("\\", "\\\\")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
        .replace(",", "\\,")
        .replace(";", "\\;")
    )


@app.get("/api/evenimente/{slug}/ics")
def api_get_eveniment_ics(slug: str):
    """Generează fișier calendar RFC 5545 (.ics) pentru adăugare cu un click în Google/Apple Calendar."""
    with get_db_conn() as conn:
        row = conn.execute("SELECT * FROM evenimente WHERE slug = ?", (slug,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Evenimentul nu a fost găsit")

    item = dict(row)
    date_str = item.get("urmatoarea_data_estimata") or "2027-06-01"
    try:
        dt_start = datetime.strptime(date_str[:10], "%Y-%m-%d")
    except ValueError:
        dt_start = datetime(2027, 6, 1)
    dt_end = dt_start + timedelta(days=1)

    summary = _ics_escape(item["titlu"])
    loc = _ics_escape(f"{item['locatie_exacta']}, {item['localitate']}, Moldova")
    desc = _ics_escape(
        f"{item['descriere_scurta']} | Recurență: {item['regula_recurenta']} | Mai multe detalii: {item['link_oficial']}"
    )
    dtstamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    ics_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//ClubTuristic.md//Calendar Evenimente Moldova//RO",
        "CALSCALE:GREGORIAN",
        "BEGIN:VEVENT",
        f"UID:{item['id']}@clubturistic.md",
        f"DTSTAMP:{dtstamp}",
        f"DTSTART;VALUE=DATE:{dt_start.strftime('%Y%m%d')}",
        f"DTEND;VALUE=DATE:{dt_end.strftime('%Y%m%d')}",
        f"SUMMARY:{summary}",
        f"LOCATION:{loc}",
        f"DESCRIPTION:{desc}",
        f"URL:{item['link_oficial']}",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    body = "\r\n".join(ics_lines) + "\r\n"
    return Response(
        content=body.encode("utf-8"),
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{slug}.ics"'},
    )


@app.get("/api/locatii")
def api_get_locatii(
    q: str = "",
    categorie: str = "",
    regiune: str = "",
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    with get_db_conn() as conn:
        join_sql, where_sql, args, used_fts = build_query_clauses(conn, "l", "locatie", q)
        base_from = f"FROM locatii l{join_sql} WHERE 1=1{where_sql}"

        if categorie and categorie != "Toate":
            base_from += " AND l.categorie = ?"
            args.append(categorie)
        if regiune and regiune != "Toate":
            base_from += " AND l.regiune = ?"
            args.append(regiune)

        total = conn.execute(f"SELECT COUNT(*) {base_from}", args).fetchone()[0]
        order_sql = (
            " ORDER BY bm25(search_fts, 10.0, 2.0, 4.0) ASC, l.este_recomandat DESC"
            if used_fts
            else " ORDER BY l.este_recomandat DESC, l.distanta_chisinau_km ASC"
        )
        rows = conn.execute(
            f"SELECT l.* {base_from}{order_sql} LIMIT ? OFFSET ?",
            [*args, limit, offset],
        ).fetchall()

    return {"total": total, "items": [serialize_row(r) for r in rows]}


@app.get("/api/locatii/{slug}")
def api_get_single_locatie(slug: str):
    with get_db_conn() as conn:
        row = conn.execute("SELECT * FROM locatii WHERE slug = ?", (slug,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Locația nu a fost găsită")
    return serialize_row(row)


@app.get("/api/hramuri")
def api_get_hramuri(q: str = "", regiune: str = "", luna: str = ""):
    with get_db_conn() as conn:
        join_sql, where_sql, args, _ = build_query_clauses(conn, "h", "hram", q)
        base_from = f"FROM hramuri_notabile h{join_sql} WHERE 1=1{where_sql}"
        if regiune and regiune != "Toate":
            base_from += " AND h.regiune = ?"
            args.append(regiune)
        if luna and luna != "Toate":
            base_from += " AND h.luna_principala = ?"
            args.append(luna)

        total = conn.execute(f"SELECT COUNT(*) {base_from}", args).fetchone()[0]
        rows = conn.execute(f"SELECT h.* {base_from} ORDER BY h.titlu ASC", args).fetchall()

    return {"total": total, "items": [serialize_row(r) for r in rows]}


@app.get("/api/stats")
def api_get_stats():
    with get_db_conn() as conn:
        c = conn.cursor()
        ev_cnt = c.execute("SELECT COUNT(*) FROM evenimente").fetchone()[0]
        ev_conf = c.execute("SELECT COUNT(*) FROM evenimente WHERE data_start != ''").fetchone()[0]
        try:
            mon_pending = c.execute(
                "SELECT COUNT(*) FROM actualizari_detectate WHERE status = 'De verificat'"
            ).fetchone()[0]
        except sqlite3.OperationalError:
            mon_pending = 0
        loc_cnt = c.execute("SELECT COUNT(*) FROM locatii").fetchone()[0]
        hrm_cnt = c.execute("SELECT COUNT(*) FROM hramuri_notabile").fetchone()[0]
        prop_pending = c.execute("SELECT COUNT(*) FROM propuneri_comunitate WHERE status = 'In asteptare'").fetchone()[0]
        by_tip = {r[0]: r[1] for r in c.execute("SELECT tip, COUNT(*) FROM evenimente GROUP BY tip").fetchall()}
        by_reg = {r[0]: r[1] for r in c.execute("SELECT regiune, COUNT(*) FROM evenimente GROUP BY regiune").fetchall()}
        by_sez = {r[0]: r[1] for r in c.execute("SELECT sezon, COUNT(*) FROM evenimente GROUP BY sezon").fetchall()}
        by_luna = {
            r[0]: r[1]
            for r in c.execute("SELECT luna_principala, COUNT(*) FROM evenimente GROUP BY luna_principala").fetchall()
        }
    return {
        "evenimente": ev_cnt,
        "evenimente_confirmate": ev_conf,
        "actualizari_de_verificat": mon_pending,
        "locatii": loc_cnt,
        "hramuri_notabile": hrm_cnt,
        "propuneri_in_asteptare": prop_pending,
        "by_tip": by_tip,
        "by_regiune": by_reg,
        "by_sezon": by_sez,
        "by_luna": by_luna,
    }


@app.post("/api/propuneri", status_code=status.HTTP_201_CREATED)
def api_create_propunere(payload: PropunereCreate):
    with get_db_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO propuneri_comunitate (
                tip_entitate, titlu, localitate, raion, data_text, descriere, link_sursa, contact_expeditor
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.tip_entitate.strip(),
                payload.titlu.strip(),
                payload.localitate.strip(),
                payload.raion.strip(),
                payload.data_text.strip(),
                payload.descriere.strip(),
                payload.link_sursa.strip(),
                payload.contact_expeditor.strip(),
            ),
        )
        conn.commit()
        new_id = cur.lastrowid
    return {"success": True, "id": new_id, "message": "Propunerea a fost trimisă spre verificare editorială."}


# ==============================================================================
# RUTE ADMIN PROTEJATE (HTTP BASIC AUTH)
# ==============================================================================


@app.get("/api/admin/me")
def admin_me(user: str = Depends(require_admin)):
    return {"user": user, "authenticated": True}


@app.post("/api/admin/evenimente", status_code=status.HTTP_201_CREATED)
def admin_create_eveniment(payload: EvenimentPayload, user: str = Depends(require_admin)):
    data = payload.model_dump()
    item_id = data.get("id") or f"evt-{make_slug(data['titlu'], 'evt')}-{int(datetime.utcnow().timestamp()) % 10000}"
    slug = data.get("slug") or make_slug(data["titlu"], "evt")
    surse_json = json.dumps(data.get("surse_media", []), ensure_ascii=False)

    with get_db_conn() as conn:
        if conn.execute("SELECT 1 FROM evenimente WHERE slug = ?", (slug,)).fetchone():
            slug = f"{slug}-{int(datetime.utcnow().timestamp()) % 10000}"
        data["id"] = item_id
        data["slug"] = slug
        try:
            conn.execute(
                """
                INSERT INTO evenimente (
                    id, slug, titlu, tip, organizator, regiune, raion, localitate, locatie_exacta,
                    lat, lng, distanta_chisinau_km, data_text, data_start, data_end, regula_recurenta, tip_recurenta,
                    luna_principala, luni_active, sezon, ultima_editie_verificata, urmatoarea_data_estimata,
                    status_data, pret_intrare, descriere_scurta, cum_a_fost_real, ce_gusti, taguri,
                    link_oficial, facebook_url, instagram_url, bilete_url, ultima_verificare_la, sursa_confirmarii,
                    surse_media_json, imagine_url, imagine_credit, este_recomandat
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item_id, slug, data["titlu"], data["tip"], data["organizator"], data["regiune"],
                    data["raion"], data["localitate"], data["locatie_exacta"], data["lat"], data["lng"],
                    data["distanta_chisinau_km"], data["data_text"], data["data_start"], data["data_end"],
                    data["regula_recurenta"], data["tip_recurenta"],
                    data["luna_principala"], data["luni_active"], data["sezon"], data["ultima_editie_verificata"],
                    data["urmatoarea_data_estimata"], data["status_data"], data["pret_intrare"],
                    data["descriere_scurta"], data["cum_a_fost_real"], data["ce_gusti"], data["taguri"],
                    data["link_oficial"], data["facebook_url"], data["instagram_url"], data["bilete_url"],
                    data["ultima_verificare_la"], data["sursa_confirmarii"], surse_json, data["imagine_url"],
                    data["imagine_credit"], data["este_recomandat"],
                ),
            )
            _index_event(conn, item_id, data)
            conn.commit()
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=400, detail=f"Eroare integritate: {exc}")
        row = conn.execute("SELECT * FROM evenimente WHERE id = ?", (item_id,)).fetchone()
    return {"success": True, "item": serialize_row(row)}


@app.put("/api/admin/evenimente/{item_id}")
def admin_update_eveniment(item_id: str, payload: EvenimentPayload, user: str = Depends(require_admin)):
    data = payload.model_dump()
    with get_db_conn() as conn:
        existing = conn.execute("SELECT slug FROM evenimente WHERE id = ?", (item_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Evenimentul nu există")
        slug = data.get("slug") or existing["slug"]
        data["slug"] = slug
        surse_json = json.dumps(data.get("surse_media", []), ensure_ascii=False)
        conn.execute(
            """
            UPDATE evenimente SET
                slug = ?, titlu = ?, tip = ?, organizator = ?, regiune = ?, raion = ?,
                localitate = ?, locatie_exacta = ?, lat = ?, lng = ?, distanta_chisinau_km = ?,
                data_text = ?, data_start = ?, data_end = ?, regula_recurenta = ?, tip_recurenta = ?, luna_principala = ?,
                luni_active = ?, sezon = ?, ultima_editie_verificata = ?, urmatoarea_data_estimata = ?,
                status_data = ?, pret_intrare = ?, descriere_scurta = ?, cum_a_fost_real = ?,
                ce_gusti = ?, taguri = ?, link_oficial = ?, facebook_url = ?, instagram_url = ?,
                bilete_url = ?, ultima_verificare_la = ?, sursa_confirmarii = ?, surse_media_json = ?,
                imagine_url = ?, imagine_credit = ?, este_recomandat = ?,
                actualizat_la = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                slug, data["titlu"], data["tip"], data["organizator"], data["regiune"], data["raion"],
                data["localitate"], data["locatie_exacta"], data["lat"], data["lng"], data["distanta_chisinau_km"],
                data["data_text"], data["data_start"], data["data_end"], data["regula_recurenta"], data["tip_recurenta"],
                data["luna_principala"], data["luni_active"], data["sezon"], data["ultima_editie_verificata"],
                data["urmatoarea_data_estimata"], data["status_data"], data["pret_intrare"],
                data["descriere_scurta"], data["cum_a_fost_real"], data["ce_gusti"], data["taguri"],
                data["link_oficial"], data["facebook_url"], data["instagram_url"], data["bilete_url"],
                data["ultima_verificare_la"], data["sursa_confirmarii"], surse_json,
                data["imagine_url"], data["imagine_credit"], data["este_recomandat"], item_id,
            ),
        )
        _index_event(conn, item_id, data)
        conn.commit()
        row = conn.execute("SELECT * FROM evenimente WHERE id = ?", (item_id,)).fetchone()
    return {"success": True, "item": serialize_row(row)}


@app.delete("/api/admin/evenimente/{item_id}")
def admin_delete_eveniment(item_id: str, user: str = Depends(require_admin)):
    with get_db_conn() as conn:
        cur = conn.execute("DELETE FROM evenimente WHERE id = ?", (item_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Evenimentul nu există")
        delete_fts_entry(conn, "eveniment", item_id)
        conn.commit()
    return {"success": True, "deleted": item_id}


@app.post("/api/admin/locatii", status_code=status.HTTP_201_CREATED)
def admin_create_locatie(payload: LocatiePayload, user: str = Depends(require_admin)):
    data = payload.model_dump()
    item_id = data.get("id") or f"loc-{make_slug(data['titlu'], 'loc')}-{int(datetime.utcnow().timestamp()) % 10000}"
    slug = data.get("slug") or make_slug(data["titlu"], "loc")
    surse_json = json.dumps(data.get("surse_media", []), ensure_ascii=False)

    with get_db_conn() as conn:
        if conn.execute("SELECT 1 FROM locatii WHERE slug = ?", (slug,)).fetchone():
            slug = f"{slug}-{int(datetime.utcnow().timestamp()) % 10000}"
        data["id"] = item_id
        data["slug"] = slug
        try:
            conn.execute(
                """
                INSERT INTO locatii (
                    id, slug, titlu, categorie, regiune, raion, localitate, adresa,
                    lat, lng, distanta_chisinau_km, program_vizita, rezervare_necesara, buget_orientativ,
                    descriere_scurta, ce_merita_vazut, ce_gusti, taguri,
                    link_oficial, facebook_url, instagram_url, surse_media_json, imagine_url, imagine_credit, este_recomandat
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item_id, slug, data["titlu"], data["categorie"], data["regiune"], data["raion"],
                    data["localitate"], data["adresa"], data["lat"], data["lng"], data["distanta_chisinau_km"],
                    data["program_vizita"], data["rezervare_necesara"], data["buget_orientativ"],
                    data["descriere_scurta"], data["ce_merita_vazut"], data["ce_gusti"], data["taguri"],
                    data["link_oficial"], data["facebook_url"], data["instagram_url"], surse_json,
                    data["imagine_url"], data["imagine_credit"], data["este_recomandat"],
                ),
            )
            _index_location(conn, item_id, data)
            conn.commit()
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=400, detail=f"Eroare integritate: {exc}")
        row = conn.execute("SELECT * FROM locatii WHERE id = ?", (item_id,)).fetchone()
    return {"success": True, "item": serialize_row(row)}


@app.put("/api/admin/locatii/{item_id}")
def admin_update_locatie(item_id: str, payload: LocatiePayload, user: str = Depends(require_admin)):
    data = payload.model_dump()
    with get_db_conn() as conn:
        existing = conn.execute("SELECT slug FROM locatii WHERE id = ?", (item_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Locația nu există")
        slug = data.get("slug") or existing["slug"]
        data["slug"] = slug
        surse_json = json.dumps(data.get("surse_media", []), ensure_ascii=False)
        conn.execute(
            """
            UPDATE locatii SET
                slug = ?, titlu = ?, categorie = ?, regiune = ?, raion = ?, localitate = ?,
                adresa = ?, lat = ?, lng = ?, distanta_chisinau_km = ?, program_vizita = ?,
                rezervare_necesara = ?, buget_orientativ = ?, descriere_scurta = ?,
                ce_merita_vazut = ?, ce_gusti = ?, taguri = ?, link_oficial = ?,
                facebook_url = ?, instagram_url = ?, surse_media_json = ?,
                imagine_url = ?, imagine_credit = ?, este_recomandat = ?,
                actualizat_la = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                slug, data["titlu"], data["categorie"], data["regiune"], data["raion"],
                data["localitate"], data["adresa"], data["lat"], data["lng"], data["distanta_chisinau_km"],
                data["program_vizita"], data["rezervare_necesara"], data["buget_orientativ"],
                data["descriere_scurta"], data["ce_merita_vazut"], data["ce_gusti"], data["taguri"],
                data["link_oficial"], data["facebook_url"], data["instagram_url"], surse_json,
                data["imagine_url"], data["imagine_credit"], data["este_recomandat"], item_id,
            ),
        )
        _index_location(conn, item_id, data)
        conn.commit()
        row = conn.execute("SELECT * FROM locatii WHERE id = ?", (item_id,)).fetchone()
    return {"success": True, "item": serialize_row(row)}


@app.delete("/api/admin/locatii/{item_id}")
def admin_delete_locatie(item_id: str, user: str = Depends(require_admin)):
    with get_db_conn() as conn:
        cur = conn.execute("DELETE FROM locatii WHERE id = ?", (item_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Locația nu există")
        delete_fts_entry(conn, "locatie", item_id)
        conn.commit()
    return {"success": True, "deleted": item_id}


@app.get("/api/admin/propuneri")
def admin_get_propuneri(user: str = Depends(require_admin)):
    with get_db_conn() as conn:
        rows = conn.execute("SELECT * FROM propuneri_comunitate ORDER BY id DESC").fetchall()
    return {"total": len(rows), "items": [dict(r) for r in rows]}


@app.post("/api/admin/propuneri/{pid}/status")
def admin_update_propunere_status(pid: int, payload: PropunereStatusUpdate, user: str = Depends(require_admin)):
    with get_db_conn() as conn:
        cur = conn.execute("UPDATE propuneri_comunitate SET status = ? WHERE id = ?", (payload.status, pid))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Propunerea nu există")
        conn.commit()
    return {"success": True, "id": pid, "status": payload.status}


@app.delete("/api/admin/propuneri/{pid}")
def admin_delete_propunere(pid: int, user: str = Depends(require_admin)):
    with get_db_conn() as conn:
        cur = conn.execute("DELETE FROM propuneri_comunitate WHERE id = ?", (pid,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Propunerea nu există")
        conn.commit()
    return {"success": True, "deleted": pid}


if __name__ == "__main__":
    print("=" * 60)
    print(" 🚀 CLUBTURISTIC.MD v2.0 (FastAPI + SQLite FTS5) ACTIV!")
    print(" 👉 Portal Public:   http://localhost:8080/")
    print(" 👉 Panou Admin:     http://localhost:8080/admin")
    print(" 👉 Stats API:       http://localhost:8080/api/stats")
    print("=" * 60)
    uvicorn.run("server:app", host="0.0.0.0", port=8080, log_level="info")
