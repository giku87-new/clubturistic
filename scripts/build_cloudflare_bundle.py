"""
Generează artifactele pentru Cloudflare Workers + D1 + KV în directorul `cloudflare/`:
- `cloudflare/media_sources.js`: mapare filename -> { url, contentType } din media_manifest.json
- `cloudflare/schema.sql`: schema completă D1 + FTS5 + indecși
- `cloudflare/seed_data.json`: datele exacte exportate din `clubturistic.db` (evenimente, locatii, hramuri, FTS5)
- `cloudflare/cloudflare.config.ts`: configurație tipizată Cloudflare CLI (`cf`) cu binding-urile D1 și KV
"""

import json
import os
import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "clubturistic.db")
MANIFEST_PATH = os.path.join(BASE_DIR, "data", "media_manifest.json")
CF_DIR = os.path.join(BASE_DIR, "cloudflare")
STATIC_DIR = os.path.join(BASE_DIR, "static")

D1_ID = "785be804-a402-4bb0-ad6f-38ad632e45e7"
KV_ID = "36c56dede5934239a6853eb52f89195d"

os.makedirs(CF_DIR, exist_ok=True)


def guess_mime(filename: str) -> str:
    low = filename.lower()
    if low.endswith(".webp"):
        return "image/webp"
    if low.endswith(".png"):
        return "image/png"
    return "image/jpeg"


def build_media_sources() -> None:
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    sources = {}
    for _, meta in sorted(manifest.items()):
        filename = os.path.basename(meta["path"])
        sources[filename] = {
            "url": meta["source_url"],
            "contentType": guess_mime(filename),
        }

    out_path = os.path.join(CF_DIR, "media_sources.js")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("// Generat automat din data/media_manifest.json\n")
        f.write(f"export const MEDIA_SOURCES = {json.dumps(sources, ensure_ascii=False, indent=2)};\n")
    print(f"Generat {out_path} ({len(sources)} imagini)")


def build_schema_sql() -> None:
    sql = """DROP TABLE IF EXISTS cautari_istoric;
DROP TABLE IF EXISTS monitor_runs;
DROP TABLE IF EXISTS actualizari_detectate;
DROP TABLE IF EXISTS surse_articole_vazute;
DROP TABLE IF EXISTS surse_monitorizate;
DROP TABLE IF EXISTS search_fts;
DROP TABLE IF EXISTS evenimente;
DROP TABLE IF EXISTS locatii;
DROP TABLE IF EXISTS hramuri_notabile;
DROP TABLE IF EXISTS propuneri_comunitate;

CREATE TABLE evenimente (
    id TEXT PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    titlu TEXT NOT NULL,
    tip TEXT NOT NULL,
    organizator TEXT NOT NULL,
    regiune TEXT NOT NULL,
    raion TEXT NOT NULL,
    localitate TEXT NOT NULL,
    locatie_exacta TEXT NOT NULL,
    lat REAL NOT NULL,
    lng REAL NOT NULL,
    distanta_chisinau_km INTEGER DEFAULT 0,
    data_text TEXT NOT NULL,
    data_start TEXT DEFAULT '',
    data_end TEXT DEFAULT '',
    regula_recurenta TEXT NOT NULL,
    tip_recurenta TEXT NOT NULL,
    luna_principala TEXT NOT NULL,
    luni_active TEXT NOT NULL,
    sezon TEXT NOT NULL,
    ultima_editie_verificata TEXT NOT NULL,
    urmatoarea_data_estimata TEXT NOT NULL,
    status_data TEXT NOT NULL,
    pret_intrare TEXT NOT NULL,
    descriere_scurta TEXT NOT NULL,
    cum_a_fost_real TEXT NOT NULL,
    ce_gusti TEXT NOT NULL,
    taguri TEXT NOT NULL,
    link_oficial TEXT NOT NULL,
    facebook_url TEXT DEFAULT '',
    instagram_url TEXT DEFAULT '',
    bilete_url TEXT DEFAULT '',
    ultima_verificare_la TEXT DEFAULT '',
    sursa_confirmarii TEXT DEFAULT '',
    surse_media_json TEXT NOT NULL,
    imagine_url TEXT NOT NULL,
    imagine_credit TEXT NOT NULL,
    este_recomandat INTEGER DEFAULT 0,
    creat_la DATETIME DEFAULT CURRENT_TIMESTAMP,
    actualizat_la DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE locatii (
    id TEXT PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    titlu TEXT NOT NULL,
    categorie TEXT NOT NULL,
    regiune TEXT NOT NULL,
    raion TEXT NOT NULL,
    localitate TEXT NOT NULL,
    adresa TEXT NOT NULL,
    lat REAL NOT NULL,
    lng REAL NOT NULL,
    distanta_chisinau_km INTEGER DEFAULT 0,
    program_vizita TEXT NOT NULL,
    rezervare_necesara TEXT NOT NULL,
    buget_orientativ TEXT NOT NULL,
    descriere_scurta TEXT NOT NULL,
    ce_merita_vazut TEXT NOT NULL,
    ce_gusti TEXT NOT NULL,
    taguri TEXT NOT NULL,
    link_oficial TEXT NOT NULL,
    facebook_url TEXT DEFAULT '',
    instagram_url TEXT DEFAULT '',
    surse_media_json TEXT NOT NULL,
    imagine_url TEXT NOT NULL,
    imagine_credit TEXT NOT NULL,
    este_recomandat INTEGER DEFAULT 0,
    creat_la DATETIME DEFAULT CURRENT_TIMESTAMP,
    actualizat_la DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE hramuri_notabile (
    id TEXT PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    titlu TEXT NOT NULL,
    regiune TEXT NOT NULL,
    raion TEXT NOT NULL,
    localitate TEXT NOT NULL,
    lat REAL NOT NULL,
    lng REAL NOT NULL,
    data_text TEXT NOT NULL,
    luna_principala TEXT NOT NULL,
    sezon TEXT NOT NULL,
    descriere TEXT NOT NULL,
    ce_se_intampla TEXT NOT NULL,
    imagine_url TEXT NOT NULL,
    imagine_credit TEXT NOT NULL,
    link_oficial TEXT NOT NULL,
    surse_media_json TEXT NOT NULL
);

CREATE TABLE propuneri_comunitate (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tip_entitate TEXT NOT NULL,
    titlu TEXT NOT NULL,
    localitate TEXT NOT NULL,
    raion TEXT DEFAULT '',
    data_text TEXT DEFAULT '',
    descriere TEXT DEFAULT '',
    link_sursa TEXT NOT NULL,
    contact_expeditor TEXT DEFAULT '',
    status TEXT DEFAULT 'In asteptare',
    creat_la DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE surse_monitorizate (
    id TEXT PRIMARY KEY,
    nume TEXT NOT NULL,
    tip TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    parser TEXT NOT NULL,
    regiune_focus TEXT DEFAULT 'Moldova',
    eveniment_id TEXT DEFAULT '',
    activ INTEGER DEFAULT 1,
    interval_ore INTEGER DEFAULT 24,
    next_check_at TEXT DEFAULT '',
    luni_fereastra TEXT DEFAULT '',
    fail_count INTEGER DEFAULT 0,
    etag TEXT DEFAULT '',
    last_modified TEXT DEFAULT '',
    last_checked_at TEXT DEFAULT '',
    last_status TEXT DEFAULT '',
    last_new_items INTEGER DEFAULT 0,
    total_matches INTEGER DEFAULT 0,
    creat_la DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE surse_articole_vazute (
    item_hash TEXT PRIMARY KEY,
    sursa_id TEXT NOT NULL,
    url TEXT NOT NULL,
    titlu TEXT DEFAULT '',
    matched INTEGER DEFAULT 0,
    first_seen_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE actualizari_detectate (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dedupe_key TEXT UNIQUE NOT NULL,
    sursa_id TEXT NOT NULL,
    sursa_nume TEXT NOT NULL,
    sursa_tip TEXT NOT NULL,
    eveniment_id TEXT DEFAULT '',
    eveniment_titlu TEXT DEFAULT '',
    titlu_detectat TEXT NOT NULL,
    data_start_detectata TEXT DEFAULT '',
    data_end_detectata TEXT DEFAULT '',
    data_text_detectat TEXT DEFAULT '',
    locatie_detectata TEXT DEFAULT '',
    descriere_snippet TEXT DEFAULT '',
    url_sursa TEXT NOT NULL,
    scor_relevanta INTEGER DEFAULT 0,
    event_fingerprint TEXT DEFAULT '',
    confirmari_count INTEGER DEFAULT 1,
    status TEXT DEFAULT 'De verificat',
    detectat_la DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE cautari_istoric (
    query_hash TEXT PRIMARY KEY,
    nume TEXT NOT NULL,
    categorie TEXT NOT NULL,
    query_text TEXT NOT NULL,
    interval_zile INTEGER DEFAULT 7,
    last_run_at TEXT DEFAULT '',
    next_due_at TEXT DEFAULT '',
    last_result_count INTEGER DEFAULT 0,
    activ INTEGER DEFAULT 1
);

CREATE TABLE monitor_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trigger_type TEXT NOT NULL,
    sources_checked INTEGER DEFAULT 0,
    sources_not_modified INTEGER DEFAULT 0,
    items_seen_skipped INTEGER DEFAULT 0,
    items_new_scanned INTEGER DEFAULT 0,
    matches_queued INTEGER DEFAULT 0,
    errors_json TEXT DEFAULT '[]',
    ran_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE VIRTUAL TABLE search_fts USING fts5(
    item_type UNINDEXED,
    item_id UNINDEXED,
    slug UNINDEXED,
    titlu_norm,
    content_norm,
    taguri_norm,
    tokenize='unicode61'
);

CREATE INDEX idx_evt_regiune ON evenimente(regiune);
CREATE INDEX idx_evt_luna ON evenimente(luna_principala);
CREATE INDEX idx_evt_sezon ON evenimente(sezon);
CREATE INDEX idx_evt_tip ON evenimente(tip);
CREATE INDEX idx_evt_data_start ON evenimente(data_start);
CREATE INDEX idx_loc_regiune ON locatii(regiune);
CREATE INDEX idx_loc_cat ON locatii(categorie);
CREATE INDEX idx_vazute_sursa ON surse_articole_vazute(sursa_id);
CREATE INDEX idx_act_status ON actualizari_detectate(status);
"""
    out_path = os.path.join(CF_DIR, "schema.sql")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(sql)
    print(f"Generat {out_path}")


def build_seed_data() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        evenimente = [dict(r) for r in conn.execute("SELECT * FROM evenimente").fetchall()]
        locatii = [dict(r) for r in conn.execute("SELECT * FROM locatii").fetchall()]
        hramuri = [dict(r) for r in conn.execute("SELECT * FROM hramuri_notabile").fetchall()]
        search_fts = [dict(r) for r in conn.execute("SELECT * FROM search_fts").fetchall()]
        surse = [dict(r) for r in conn.execute("SELECT * FROM surse_monitorizate ORDER BY id").fetchall()]
    finally:
        conn.close()

    out_path = os.path.join(CF_DIR, "seed_data.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "evenimente": evenimente,
                "locatii": locatii,
                "hramuri_notabile": hramuri,
                "search_fts": search_fts,
                "surse_monitorizate": surse,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(
        f"Generat {out_path} (evt={len(evenimente)}, loc={len(locatii)}, "
        f"hram={len(hramuri)}, fts={len(search_fts)}, surse={len(surse)})"
    )


def build_cf_config() -> None:
    cfg = f"""export default {{
  name: "clubturistic",
  main: "worker.js",
  compatibilityDate: "2026-11-20",
  compatibilityFlags: ["nodejs_compat"],
  observability: {{
    enabled: true,
    logs: {{ enabled: true, headSamplingRate: 1 }},
    traces: {{ enabled: true, headSamplingRate: 0.01 }},
  }},
  bindings: {{
    DB: {{ type: "d1", id: "{D1_ID}" }},
    MEDIA_KV: {{ type: "kv_namespace", id: "{KV_ID}" }},
  }},
}};
"""
    out_path = os.path.join(CF_DIR, "cloudflare.config.ts")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(cfg)
    print(f"Generat {out_path}")


def check_static_files() -> None:
    required = ["index.html", "detail.html", "admin.html", "js/app.js", "js/admin.js"]
    for rel in required:
        p = os.path.join(STATIC_DIR, rel)
        if not os.path.exists(p):
            raise FileNotFoundError(f"Fișier static lipsă: {p}")
        print(f"  Static OK: {rel} ({os.path.getsize(p)} bytes)")


def build_static_sitemap() -> None:
    from datetime import datetime
    import html

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        ev_rows = conn.execute("SELECT slug, actualizat_la FROM evenimente ORDER BY slug").fetchall()
        loc_rows = conn.execute("SELECT slug, actualizat_la FROM locatii ORDER BY slug").fetchall()
    finally:
        conn.close()

    today = datetime.utcnow().strftime("%Y-%m-%d")
    base_url = "https://clubturistic.md"
    urls = [
        f"  <url><loc>{base_url}/</loc><lastmod>{today}</lastmod><changefreq>daily</changefreq><priority>1.0</priority></url>"
    ]
    for r in ev_rows:
        lm = (r["actualizat_la"] or today)[:10]
        loc_url = html.escape(f"{base_url}/eveniment/{r['slug']}")
        urls.append(
            f"  <url><loc>{loc_url}</loc><lastmod>{lm}</lastmod><changefreq>weekly</changefreq><priority>0.8</priority></url>"
        )
    for r in loc_rows:
        lm = (r["actualizat_la"] or today)[:10]
        loc_url = html.escape(f"{base_url}/locatie/{r['slug']}")
        urls.append(
            f"  <url><loc>{loc_url}</loc><lastmod>{lm}</lastmod><changefreq>monthly</changefreq><priority>0.8</priority></url>"
        )

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>\n"
    )
    out_path = os.path.join(STATIC_DIR, "sitemap.xml")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(xml)
    print(f"Generat {out_path} ({len(urls)} URL-uri)")


def main() -> None:
    build_media_sources()
    build_schema_sql()
    build_seed_data()
    build_cf_config()
    build_static_sitemap()
    check_static_files()


if __name__ == "__main__":
    main()
