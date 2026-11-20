"""
Crawler incremental local (0 tokeni AI) pentru ClubTuristic.md:
- Scaneaza exclusiv sursele scadente (`next_check_at <= now` si fereastra sezoniera).
- Trimite `If-None-Match` (ETag) / `If-Modified-Since` si aplica backoff la erori.
- Suporta: Agende (Fest.md, iTicket, Sporter), Google News RSS, Canale publice Telegram
  (`t.me/s/...`), portaluri RSS + Radio Moldova / Moldova 1, site-uri de crame & Linktree.
- Sare 100% articolele deja prezente in `surse_articole_vazute` (SHA-256).
- Grupeaza alertele duplicate din surse multiple prin `event_fingerprint`.
- Scrie `data/new_candidates.json` (max 20 candidati noi) si `data/review_queue.md`.
"""

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import html as html_lib
import json
import os
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from apply_review_triage import render_review_queue  # noqa: E402
from search_utils import strip_diacritics  # noqa: E402

DB_PATH = os.path.join(BASE_DIR, "clubturistic.db")
CANDIDATES_PATH = os.path.join(BASE_DIR, "data", "new_candidates.json")

RO_MONTHS = {
    "ianuarie": 1, "ian": 1,
    "februarie": 2, "feb": 2,
    "martie": 3, "mar": 3,
    "aprilie": 4, "apr": 4,
    "mai": 5,
    "iunie": 6, "iun": 6,
    "iulie": 7, "iul": 7,
    "august": 8, "aug": 8,
    "septembrie": 9, "sep": 9, "sept": 9,
    "octombrie": 10, "oct": 10,
    "noiembrie": 11, "noi": 11, "nov": 11,
    "decembrie": 12, "dec": 12,
}

KNOWN_EVENT_PHRASES = [
    ("evt-ia-mania-holercani", ["ia mania", "iamania"]),
    ("evt-bostaniada-balabanesti", ["bostaniada"]),
    ("evt-descopera-butuceni", ["descopera butuceni", "festivalul descopera"]),
    ("evt-gustar-orheiul-vechi", ["gustar music", "festivalul gustar"]),
    ("evt-festivalul-lupilor-orheiul-vechi", ["festivalul lupilor", "lupii lui calancea"]),
    ("evt-underland-cricova", ["underland"]),
    ("evt-vernisajul-vinului-chisinau", ["vernisajul vinului"]),
    ("evt-ziua-nationala-a-vinului", ["ziua nationala a vinului", "ziua vinului"]),
    ("evt-mai-dulce-chisinau", ["mai dulce"]),
    ("evt-lavender-fest-cobusca", ["lavender fest"]),
    ("evt-ciresar-truseni", ["festivalul ciresar", "ciresar truseni"]),
    ("evt-cireselor-varzarilor-rusestii-noi", ["rusestii noi", "varzarilor"]),
    ("evt-festivalul-zemii-sipoteni", ["festivalul zemii", "zemii sipoteni"]),
    ("evt-festivalul-marului-soroca", ["festivalul marului", "festivalul national al marului"]),
    ("evt-festivalul-prunei-nisporeni", ["festivalul prunei", "festivalul national al prunei"]),
    ("evt-capsunilor-mierii-sadova", ["festivalul capsunilor", "capsuni sadova"]),
    ("evt-hai-la-piersici-tudora", ["hai la piersici", "festivalul piersicilor"]),
    ("evt-iprosop-selemet", ["iprosop"]),
    ("evt-frumos-covor-basarabean-clisova", ["frumos covor basarabean", "arta rustica clisova"]),
    ("evt-vatra-olarului-hoginesti", ["vatra olarului", "targul olarilor hoginesti"]),
    ("evt-festivalul-patlagica-dubasarii-vechi", ["festivalul patlagica", "patlagica dubasarii"]),
    ("evt-festivalul-cartofului-corjeuti", ["festivalul cartofului"]),
    ("evt-hederlez-ceadir-lunga", ["hederlez"]),
    ("evt-gagauz-sarap-yortusu-comrat", ["sarap yortusu", "vinului gagauz"]),
    ("evt-vinopera-castel-mimi", ["vinopera", "rose day castel mimi"]),
    ("evt-milestii-mici-winerun", ["milestii mici winerun", "winerun"]),
    ("evt-purcari-wine-run", ["purcari wine run", "nocturne night run purcari"]),
    ("evt-ecolocal-chisinau", ["ecolocal farmers", "piata ecolocal"]),
    ("evt-yard-sale-chisinau", ["yard sale", "yardsale"]),
    ("evt-ziua-portului-popular", ["ziua portului popular", "ziua nationala a portului"]),
    ("evt-festivalul-padurilor-condrita", ["festivalul padurilor"]),
    ("evt-festivalul-martisor-chisinau", ["festivalul martisor", "festivalul international martisor"]),
    ("evt-ethno-jazz-chisinau", ["ethno jazz"]),
    ("evt-targul-de-craciun-chisinau", ["targul de craciun chisinau", "oraselul sarbatorilor"]),
    ("evt-festivalul-bach-2026", ["festivalul j s bach", "festivalul international bach"]),
    ("evt-satul-meu-vatra-aleasa-cahul-2026", ["satul meu vatra aleasa"]),
    ("evt-moldova-accordion-days-2026", ["accordion days", "rapsodia romana"]),
    ("evt-targul-international-caritate-2026", ["targul international de caritate"]),
    ("evt-joc-cricova-subteran-2026", ["ansamblul joc cricova", "joc in orasul subteran"]),
    ("evt-covorul-dorului-2026", ["covorul dorului"]),
]

TOURISM_RELEVANCE_TERMS = [
    "festival", "targ", "crama", "vinuri", "degustare", "usilor deschise",
    "hram", "folclor", "traditional", "placinte", "zeama", "mamaliga", "bostan",
    "lavanda", "cires", "craciun", "turism", "orheiul vechi", "butuceni",
    "cricova", "castel mimi", "purcari", "milestii mici", "moldexpo",
    "concert simfonic", "expozitie", "mestesugar", "olarii", "vinicol", "maraton",
]

NOISE_TERMS = [
    "accident", "politie", "incendiu", "dosar penal", "retinut", "coruptie",
    "procuratura", "salmonella", "decedat", "tragedie", "perchezitii",
    "contrabanda", "arest", "inculpat", "sentinta", "omor",
    "spatiului aerian", "aparat de zbor", "drona", "razboi",
]

AGENDA_SKIP_TERMS = [
    "cinema", "imax", "bilete film", "avatar", "desene animate",
    "cursa taxi", "reducere black friday", "cursuri online",
    "filmul", " 2d", " 3d", "friday party", "friday night", "dj set",
    "karaoke", "stand-up", "standup", "teatrul", "improvizatie",
    "vixen", "house culture",
]

STATIC_SITE_SKIP_TERMS = [
    "materiale informative", "mediu si ecologie", "pgs cert",
    "principii de admitere", "comunicarea corecta", "alte proiecte",
    "politica de confidentialitate", "termeni si conditii", "despre noi",
    "echipa noastra", "contacte",
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def sha256_hex(val: str, length: int = 32) -> str:
    return hashlib.sha256((val or "").encode("utf-8")).hexdigest()[:length]


def strip_tags(raw: str) -> str:
    txt = re.sub(r"<!\[CDATA\[([\s\S]*?)\]\]>", r"\1", raw or "")
    txt = re.sub(r"<script[\s\S]*?</script>", " ", txt, flags=re.I)
    txt = re.sub(r"<style[\s\S]*?</style>", " ", txt, flags=re.I)
    txt = re.sub(r"<[^>]+>", " ", txt)
    txt = html_lib.unescape(txt)
    return re.sub(r"\s+", " ", txt).strip()


def resolve_url(href: str, base_url: str) -> str:
    try:
        u = urllib.parse.urljoin(base_url, href)
        p = urllib.parse.urlsplit(u)
        if p.scheme not in ("http", "https"):
            return ""
        return urllib.parse.urlunsplit((p.scheme, p.netloc, p.path, p.query, ""))
    except Exception:
        return ""


def valid_ymd(y: int, m: int, d: int) -> str:
    if not (2025 <= y <= 2030 and 1 <= m <= 12 and 1 <= d <= 31):
        return ""
    try:
        datetime(y, m, d)
        return f"{y:04d}-{m:02d}-{d:02d}"
    except ValueError:
        return ""


def extract_romanian_dates(text: str, fallback_year: int | None = None) -> tuple[str, str, str]:
    if not text:
        return "", "", ""
    now = utc_now()
    fy = fallback_year or now.year
    raw = str(text)
    norm = strip_diacritics(raw)

    m_iso = re.search(r"\b(202[5-9])-(\d{2})-(\d{2})\b", raw)
    if m_iso:
        s = valid_ymd(int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3)))
        if s:
            return s, s, m_iso.group(0)

    m_dot = re.search(r"\b(\d{1,2})\.(\d{1,2})\.(202[5-9])\b", raw)
    if m_dot:
        s = valid_ymd(int(m_dot.group(3)), int(m_dot.group(2)), int(m_dot.group(1)))
        if s:
            return s, s, m_dot.group(0)

    m_pat = "|".join(RO_MONTHS.keys())
    m_rng = re.search(rf"\b(\d{{1,2}})\s*(?:si\s+)?(\d{{1,2}})\s+({m_pat})(?:\s+(202[5-9]))?\b", norm, re.I)
    if m_rng:
        d1, d2 = int(m_rng.group(1)), int(m_rng.group(2))
        mo = RO_MONTHS[m_rng.group(3).lower()]
        yr = int(m_rng.group(4)) if m_rng.group(4) else fy
        s = valid_ymd(yr, mo, d1)
        e = valid_ymd(yr, mo, d2)
        if s:
            return s, e or s, f"{d1}-{d2} {m_rng.group(3)} {yr}"

    m_one = re.search(rf"\b(\d{{1,2}})\s+({m_pat})(?:\s+(202[5-9]))?\b", norm, re.I)
    if m_one:
        d = int(m_one.group(1))
        mo = RO_MONTHS[m_one.group(2).lower()]
        yr = int(m_one.group(3)) if m_one.group(3) else fy
        if not m_one.group(3) and mo + 1 < now.month:
            yr += 1
        s = valid_ymd(yr, mo, d)
        if s:
            return s, s, f"{d} {m_one.group(2)} {yr}"

    return "", "", ""


def parse_rss_items(xml_text: str, base_url: str) -> list[dict]:
    items = []
    for m in re.finditer(r"<(item|entry)\b[^>]*>([\s\S]*?)</\1>", xml_text, flags=re.I):
        if len(items) >= 40:
            break
        block = m.group(2)

        def tag_val(tag: str) -> str:
            r = re.search(rf"<{tag}\b[^>]*>([\s\S]*?)</{tag}>", block, flags=re.I)
            return strip_tags(r.group(1)) if r else ""

        link = tag_val("link")
        if not link:
            hm = re.search(r'<link\b[^>]*href=["\']([^"\']+)["\']', block, flags=re.I)
            if hm:
                link = hm.group(1)
        url = resolve_url(link, base_url)
        titlu = tag_val("title")
        if not url or not titlu:
            continue
        guid = tag_val("guid") or tag_val("id") or url
        desc = tag_val("description") or tag_val("content:encoded") or tag_val("summary") or ""
        pub = tag_val("pubDate") or tag_val("updated") or tag_val("published") or ""
        items.append({
            "guid": guid,
            "url": url,
            "titlu": titlu[:220],
            "snippet": desc[:320],
            "date_hint": f"{titlu} {desc} {pub}",
            "locatie": "",
        })
    return items


def parse_fest_html_items(html_text: str, base_url: str) -> list[dict]:
    items = []
    blocks = re.split(r'<div[^>]*class=["\'][^"\']*block-item', html_text, flags=re.I)
    for chunk in blocks[1:]:
        if len(items) >= 45:
            break
        snippet_chunk = chunk[:3500]
        tm = re.search(r'<a[^>]*class=["\'][^"\']*\btitle\b[^"\']*["\'][^>]*href=["\']([^"\']+)["\'][^>]*>([\s\S]*?)</a>', snippet_chunk, flags=re.I)
        if not tm:
            continue
        raw_href = tm.group(1).strip()
        if len([p for p in raw_href.split("/") if p]) < 4:
            continue
        low_href = raw_href.lower()
        if any(p in low_href for p in ("/filme/", "/cluburi/", "/teatre/", "/stand-up/", "/cursuri/", "/traininguri/")):
            continue
        url = resolve_url(raw_href, base_url)
        titlu = strip_tags(tm.group(2))[:220]
        if not url or len(titlu) < 4:
            continue
        cm = re.search(r"icon-calendar[\s\S]*?<span[^>]*>([\s\S]*?)</span>", snippet_chunk, flags=re.I)
        date_raw = strip_tags(cm.group(1)) if cm else ""
        pm = re.search(r"icon-pinpoint[\s\S]*?<a[^>]*>([\s\S]*?)</a>", snippet_chunk, flags=re.I)
        loc_raw = strip_tags(pm.group(1))[:140] if pm else ""
        items.append({
            "guid": url,
            "url": url,
            "titlu": titlu,
            "snippet": " • ".join(x for x in (date_raw, loc_raw) if x)[:320],
            "date_hint": f"{date_raw} {titlu}",
            "locatie": loc_raw,
        })
    return items


def parse_telegram_html(html_text: str, base_url: str) -> list[dict]:
    items = []
    chunks = html_text.split('data-post="')
    for chunk in chunks[1:]:
        if len(items) >= 25:
            break
        post_id = chunk.split('"', 1)[0].strip()
        if not post_id or "/" not in post_id:
            continue
        msg_m = re.search(r'class="tgme_widget_message_text[^"]*"[^>]*>([\s\S]*?)</div>', chunk, flags=re.I)
        if not msg_m:
            continue
        text = strip_tags(msg_m.group(1))
        if len(text) < 20:
            continue
        tm = re.search(r'<time[^>]*datetime="([^"]+)"', chunk, flags=re.I)
        dt_attr = tm.group(1) if tm else ""
        first_line = re.split(r"[.!?\n]", text, maxsplit=1)[0].strip()[:180] or text[:140]
        url = f"https://t.me/{post_id}"
        items.append({
            "guid": url,
            "url": url,
            "titlu": first_line,
            "snippet": text[:320],
            "date_hint": f"{text[:280]} {dt_attr}",
            "locatie": "",
        })
    return items


def _collect_jsonld_events(node, out: list[dict], base_url: str) -> None:
    if isinstance(node, list):
        for x in node:
            _collect_jsonld_events(x, out, base_url)
        return
    if not isinstance(node, dict):
        return
    tp = node.get("@type")
    tp_str = " ".join(str(x) for x in tp) if isinstance(tp, list) else str(tp or "")
    if "event" in tp_str.lower() and node.get("name"):
        url = resolve_url(node.get("url") or "", base_url) or base_url
        loc_val = node.get("location")
        loc_name = loc_val if isinstance(loc_val, str) else (
            (loc_val or {}).get("name") or ((loc_val or {}).get("address") or {}).get("addressLocality") or ""
        )
        sd = str(node.get("startDate") or "")[:20]
        ed = str(node.get("endDate") or sd)[:20]
        out.append({
            "guid": f"{url}#{sd or node['name']}",
            "url": url,
            "titlu": strip_tags(str(node["name"]))[:220],
            "snippet": strip_tags(str(node.get("description") or f"{sd} {loc_name}"))[:320],
            "date_hint": f"{sd} {ed} {node['name']}",
            "locatie": strip_tags(str(loc_name))[:140],
        })
    if isinstance(node.get("@graph"), list):
        _collect_jsonld_events(node["@graph"], out, base_url)


def parse_html_links_and_jsonld(html_text: str, base_url: str) -> list[dict]:
    items = []
    seen = set()
    for m in re.finditer(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>([\s\S]*?)</script>', html_text, flags=re.I):
        try:
            obj = json.loads(m.group(1).strip())
            lds: list[dict] = []
            _collect_jsonld_events(obj, lds, base_url)
            for ev in lds:
                if ev["guid"] not in seen:
                    seen.add(ev["guid"])
                    items.append(ev)
        except Exception:
            pass

    base_host = urllib.parse.urlsplit(base_url).hostname or ""
    base_host = re.sub(r"^www\.", "", base_host)
    for m in re.finditer(r'<a\b[^>]*href=["\']([^"\'#]+)["\'][^>]*>([\s\S]*?)</a>', html_text, flags=re.I):
        if len(items) >= 40:
            break
        raw_href = m.group(1).strip()
        if raw_href.startswith(("mailto:", "tel:", "javascript:")):
            continue
        if re.search(r"\.(css|js|png|jpe?g|webp|svg|pdf|ico)(\?|$)", raw_href, flags=re.I):
            continue
        url = resolve_url(raw_href, base_url)
        if not url or url in seen:
            continue
        u_obj = urllib.parse.urlsplit(url)
        host = re.sub(r"^www\.", "", u_obj.hostname or "")
        is_bio_link = host in ("linktr.ee", "taplink.cc", "bento.me")
        if base_host and host != base_host and not is_bio_link:
            continue
        path_clean = u_obj.path.rstrip("/")
        if path_clean in ("", "/ro", "/en", "/events", "/evenimente"):
            continue
        titlu = strip_tags(m.group(2))[:220]
        if len(titlu) < 8 or re.match(r"^(citeste|detalii|vezi|mai mult|acasa|contact|login)", titlu, flags=re.I):
            continue
        after_ctx = strip_tags(html_text[m.start():m.start() + 500])[:300]
        seen.add(url)
        items.append({
            "guid": url,
            "url": url,
            "titlu": titlu,
            "snippet": after_ctx[:320],
            "date_hint": f"{titlu} {after_ctx}",
            "locatie": "",
        })
    return items


def match_item(item: dict, source: sqlite3.Row, events_by_id: dict, events_list: list) -> tuple[bool, str, str, int]:
    combined = strip_diacritics(f"{item['titlu']} {item['snippet']} {item['locatie']}")
    for bad in NOISE_TERMS:
        if bad in combined:
            return False, "", "", 0

    for evt_id, phrases in KNOWN_EVENT_PHRASES:
        for ph in phrases:
            if ph in combined:
                ev = events_by_id.get(evt_id)
                return True, (ev["id"] if ev else evt_id), (ev["titlu"] if ev else ""), 95

    if source["eveniment_id"] and source["eveniment_id"] in events_by_id:
        ev = events_by_id[source["eveniment_id"]]
        title_norm = strip_diacritics(item["titlu"])
        if any(s in title_norm for s in STATIC_SITE_SKIP_TERMS):
            return False, "", "", 0
        # Pe site-uri proprii (ex. ecolocal.md / wineofmoldova) cerem semnal de data sau noutate reala
        d_start, _, _ = extract_romanian_dates(item["date_hint"])
        if d_start or any(w in combined for w in ("editia", "program", "editie", "locatie noua", "sambata", "weekend", "bilete", "degustare")):
            ev_tokens = [t for t in strip_diacritics(ev["titlu"]).split() if len(t) >= 5]
            if any(t in combined for t in ev_tokens):
                return True, ev["id"], ev["titlu"], 80

    for ev in events_list:
        nt = strip_diacritics(ev["titlu"])
        if len(nt) >= 12 and nt in combined:
            return True, ev["id"], ev["titlu"], 85

    if source["tip"] in ("Agenda", "Website Oficial"):
        for skip in AGENDA_SKIP_TERMS + STATIC_SITE_SKIP_TERMS:
            if skip in combined:
                return False, "", "", 0
        strong = any(kw in combined for kw in TOURISM_RELEVANCE_TERMS)
        d_start, _, _ = extract_romanian_dates(item["date_hint"])
        if strong and d_start:
            return True, "", "", 70
        if strong and source["tip"] == "Agenda":
            return True, "", "", 60
        return False, "", "", 0

    hits = sum(1 for kw in TOURISM_RELEVANCE_TERMS if kw in combined)
    if hits >= 2 or (hits >= 1 and any(w in combined for w in ("festival", "targ", "crama", "vinuri", "usilor deschise", "degustare"))):
        return True, "", "", min(85, 50 + hits * 10)
    return False, "", "", 0


def run_local_crawl(compact: bool = False, force: bool = False, limit: int = 35) -> dict:
    now = utc_now()
    now_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    today = now.strftime("%Y-%m-%d")
    cur_month = str(now.month)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        if force:
            sources = conn.execute(
                "SELECT * FROM surse_monitorizate WHERE activ = 1 AND parser != 'social_manual' ORDER BY COALESCE(last_checked_at, '') ASC LIMIT ?",
                (limit,),
            ).fetchall()
        else:
            sources = conn.execute(
                "SELECT * FROM surse_monitorizate WHERE activ = 1 AND parser != 'social_manual' AND (next_check_at = '' OR next_check_at <= ?) ORDER BY COALESCE(next_check_at, '') ASC LIMIT ?",
                (now_iso, limit),
            ).fetchall()

        events_list = [dict(r) for r in conn.execute("SELECT id, slug, titlu, taguri, localitate FROM evenimente").fetchall()]
        events_by_id = {e["id"]: e for e in events_list}

        sources_checked = 0
        sources_not_modified = 0
        items_seen_skipped = 0
        items_new_scanned = 0
        matches_queued = 0
        errors = []
        new_candidates = []
        last_host_fetch: dict[str, float] = {}

        for src in sources:
            win = (src["luni_fereastra"] or "").strip()
            if win and not force:
                allowed = {x.strip() for x in win.split(",") if x.strip()}
                if cur_month not in allowed:
                    next_chk = (now + timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%SZ")
                    conn.execute(
                        "UPDATE surse_monitorizate SET next_check_at = ?, last_status = 'Out of season' WHERE id = ?",
                        (next_chk, src["id"]),
                    )
                    continue

            host = re.sub(r"^www\.", "", urllib.parse.urlsplit(src["url"]).hostname or src["id"])
            if host in last_host_fetch:
                elapsed = time.monotonic() - last_host_fetch[host]
                if elapsed < 1.2:
                    time.sleep(1.2 - elapsed)

            sources_checked += 1
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; ClubTuristicBot/3.0; +https://clubturistic.md)",
                "Accept": "text/html,application/rss+xml,application/xml;q=0.9,*/*;q=0.8",
            }
            if src["etag"]:
                headers["If-None-Match"] = src["etag"]
            if src["last_modified"]:
                headers["If-Modified-Since"] = src["last_modified"]

            req = urllib.request.Request(src["url"], headers=headers)
            interval_h = int(src["interval_ore"] or 24)
            next_ok = (now + timedelta(hours=interval_h)).strftime("%Y-%m-%dT%H:%M:%SZ")

            try:
                last_host_fetch[host] = time.monotonic()
                with urllib.request.urlopen(req, timeout=8) as resp:
                    status_code = resp.status
                    new_etag = resp.headers.get("ETag") or src["etag"] or ""
                    new_lm = resp.headers.get("Last-Modified") or src["last_modified"] or ""
                    body = resp.read(350000).decode("utf-8", errors="ignore")
            except urllib.error.HTTPError as e:
                if e.code == 304:
                    sources_not_modified += 1
                    conn.execute(
                        "UPDATE surse_monitorizate SET last_checked_at = ?, next_check_at = ?, fail_count = 0, last_status = '304 Not Modified', last_new_items = 0 WHERE id = ?",
                        (now_iso, next_ok, src["id"]),
                    )
                    continue
                fails = int(src["fail_count"] or 0) + 1
                backoff_h = [6, 24, 72][min(fails - 1, 2)]
                next_err = (now + timedelta(hours=backoff_h)).strftime("%Y-%m-%dT%H:%M:%SZ")
                st_txt = f"HTTP {e.code}"
                errors.append({"sursa": src["id"], "error": st_txt})
                conn.execute(
                    "UPDATE surse_monitorizate SET last_checked_at = ?, next_check_at = ?, fail_count = ?, last_status = ?, last_new_items = 0 WHERE id = ?",
                    (now_iso, next_err, fails, st_txt, src["id"]),
                )
                continue
            except Exception as e:
                fails = int(src["fail_count"] or 0) + 1
                backoff_h = [6, 24, 72][min(fails - 1, 2)]
                next_err = (now + timedelta(hours=backoff_h)).strftime("%Y-%m-%dT%H:%M:%SZ")
                st_txt = f"ERR: {str(e)[:45]}"
                errors.append({"sursa": src["id"], "error": st_txt})
                conn.execute(
                    "UPDATE surse_monitorizate SET last_checked_at = ?, next_check_at = ?, fail_count = ?, last_status = ?, last_new_items = 0 WHERE id = ?",
                    (now_iso, next_err, fails, st_txt, src["id"]),
                )
                continue

            if status_code == 304:
                sources_not_modified += 1
                conn.execute(
                    "UPDATE surse_monitorizate SET last_checked_at = ?, next_check_at = ?, fail_count = 0, last_status = '304 Not Modified', last_new_items = 0 WHERE id = ?",
                    (now_iso, next_ok, src["id"]),
                )
                continue

            parser_name = src["parser"]
            if parser_name == "rss":
                parsed = parse_rss_items(body, src["url"])
            elif parser_name == "fest_html":
                parsed = parse_fest_html_items(body, src["url"])
            elif parser_name == "telegram_html":
                parsed = parse_telegram_html(body, src["url"])
            else:
                parsed = parse_html_links_and_jsonld(body, src["url"])

            if not parsed:
                conn.execute(
                    "UPDATE surse_monitorizate SET etag = ?, last_modified = ?, last_checked_at = ?, next_check_at = ?, fail_count = 0, last_status = '200 OK (0 items)', last_new_items = 0 WHERE id = ?",
                    (new_etag, new_lm, now_iso, next_ok, src["id"]),
                )
                continue

            hashes = [(it, sha256_hex(f"{src['id']}|{it['guid'] or it['url']}")) for it in parsed]
            seen_set: set[str] = set()
            for i in range(0, len(hashes), 50):
                chunk_h = [h for _, h in hashes[i:i + 50]]
                qs = ",".join("?" for _ in chunk_h)
                for row in conn.execute(f"SELECT item_hash FROM surse_articole_vazute WHERE item_hash IN ({qs})", chunk_h):
                    seen_set.add(row[0])

            src_new = 0
            src_matches = 0
            for it, h in hashes:
                if h in seen_set:
                    items_seen_skipped += 1
                    continue
                seen_set.add(h)
                src_new += 1
                items_new_scanned += 1

                rel, evt_id, evt_title, score = match_item(it, src, events_by_id, events_list)
                d_start, d_end, d_text = extract_romanian_dates(it["date_hint"]) if rel else ("", "", "")
                is_stale_past = (not evt_id) and bool(d_start) and d_start < today
                should_queue = rel and not is_stale_past

                conn.execute(
                    "INSERT OR IGNORE INTO surse_articole_vazute (item_hash, sursa_id, url, titlu, matched) VALUES (?, ?, ?, ?, ?)",
                    (h, src["id"], it["url"][:400], it["titlu"][:220], 1 if should_queue else 0),
                )

                if should_queue:
                    fp_key = strip_diacritics(evt_id or it["titlu"])[:60]
                    fp = sha256_hex(f"{fp_key}|{d_start}", 24) if (d_start or evt_id) else ""
                    merged = None
                    if fp:
                        merged = conn.execute(
                            "SELECT id FROM actualizari_detectate WHERE status = 'De verificat' AND event_fingerprint = ?",
                            (fp,),
                        ).fetchone()
                    if merged:
                        conn.execute(
                            "UPDATE actualizari_detectate SET confirmari_count = confirmari_count + 1 WHERE id = ?",
                            (merged["id"],),
                        )
                    else:
                        dedupe_key = sha256_hex(f"{it['url']}|{d_start or it['titlu']}")
                        cur = conn.execute(
                            """
                            INSERT OR IGNORE INTO actualizari_detectate (
                                dedupe_key, sursa_id, sursa_nume, sursa_tip, eveniment_id, eveniment_titlu,
                                titlu_detectat, data_start_detectata, data_end_detectata, data_text_detectat,
                                locatie_detectata, descriere_snippet, url_sursa, scor_relevanta, event_fingerprint, status
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'De verificat')
                            """,
                            (
                                dedupe_key, src["id"], src["nume"], src["tip"], evt_id, evt_title,
                                it["titlu"][:220], d_start, d_end, d_text, it["locatie"][:140],
                                it["snippet"][:320], it["url"][:400], score, fp,
                            ),
                        )
                        if cur.rowcount > 0:
                            src_matches += 1
                            matches_queued += 1
                            if len(new_candidates) < 20:
                                new_candidates.append({
                                    "id": cur.lastrowid,
                                    "sursa": src["nume"],
                                    "tip": src["tip"],
                                    "eveniment_id": evt_id,
                                    "titlu": it["titlu"][:160],
                                    "data_start": d_start,
                                    "locatie": it["locatie"][:80],
                                    "url": it["url"][:250],
                                })

            conn.execute(
                """
                UPDATE surse_monitorizate SET
                    etag = ?, last_modified = ?, last_checked_at = ?, next_check_at = ?, fail_count = 0,
                    last_status = '200 OK', last_new_items = ?, total_matches = total_matches + ?
                WHERE id = ?
                """,
                (new_etag, new_lm, now_iso, next_ok, src_new, src_matches, src["id"]),
            )

        conn.execute(
            """
            INSERT INTO monitor_runs (
                trigger_type, sources_checked, sources_not_modified, items_seen_skipped,
                items_new_scanned, matches_queued, errors_json
            ) VALUES ('local_crawl', ?, ?, ?, ?, ?, ?)
            """,
            (sources_checked, sources_not_modified, items_seen_skipped, items_new_scanned, matches_queued, json.dumps(errors)),
        )
        conn.commit()

        due_queries = [
            dict(r)
            for r in conn.execute(
                """
                SELECT query_hash, nume, categorie, query_text, last_run_at
                FROM cautari_istoric
                WHERE activ = 1 AND (next_due_at = '' OR next_due_at <= ?)
                ORDER BY COALESCE(last_run_at, '') ASC
                LIMIT 2
                """,
                (now_iso,),
            ).fetchall()
        ]
        total_pending = conn.execute(
            "SELECT COUNT(*) FROM actualizari_detectate WHERE status = 'De verificat'"
        ).fetchone()[0]

        os.makedirs(os.path.dirname(CANDIDATES_PATH), exist_ok=True)
        with open(CANDIDATES_PATH, "w", encoding="utf-8", newline="\n") as f:
            json.dump({"ran_at": now_iso, "candidates": new_candidates}, f, ensure_ascii=False, indent=2)
        render_review_queue(conn)

        summary = {
            "sources_checked": sources_checked,
            "not_modified": sources_not_modified,
            "seen_skipped": items_seen_skipped,
            "new_scanned": items_new_scanned,
            "new_candidates": len(new_candidates),
            "matches_queued": matches_queued,
            "total_pending": total_pending,
            "due_web_queries": due_queries,
            "errors": errors,
        }
        if compact:
            print(
                f"SOURCES_CHECKED={sources_checked} NOT_MODIFIED={sources_not_modified} "
                f"SEEN_SKIPPED={items_seen_skipped} NEW_SCANNED={items_new_scanned} "
                f"NEW_CANDIDATES={len(new_candidates)} TOTAL_PENDING={total_pending}"
            )
            print("DUE_WEB_QUERIES=" + json.dumps(due_queries, ensure_ascii=False))
        else:
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        return summary
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Crawler local incremental ClubTuristic.md")
    parser.add_argument("--compact", action="store_true", help="Iesire compacta (economiseste tokeni)")
    parser.add_argument("--force", action="store_true", help="Ignora next_check_at / fereastra sezoniera")
    parser.add_argument("--limit", type=int, default=35, help="Numar maxim surse per rulare")
    args = parser.parse_args()
    run_local_crawl(compact=args.compact, force=args.force, limit=args.limit)


if __name__ == "__main__":
    main()
