"""
Genereaza payload-urile UTF-8 (fara BOM) pentru deploy pe Cloudflare D1 si KV:
- `cloudflare/seed.sql` din `cloudflare/seed_data.json` (fara BEGIN/COMMIT)
- `cloudflare/kv_static.json` (HTML/JS statice + logo.png)
- `cloudflare/kv_images_1.json`, ... (restul imaginilor in batch-uri de 10)

Ruleaza si un dry-run local in sqlite3 (:memory:) cu `cloudflare/schema.sql`.
"""

import base64
import json
import os
import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CF_DIR = os.path.join(BASE_DIR, "cloudflare")
STATIC_DIR = os.path.join(BASE_DIR, "static")
IMAGES_DIR = os.path.join(STATIC_DIR, "images")
SEED_JSON_PATH = os.path.join(CF_DIR, "seed_data.json")
SCHEMA_SQL_PATH = os.path.join(CF_DIR, "schema.sql")
SEED_SQL_PATH = os.path.join(CF_DIR, "seed.sql")


def guess_mime(filename: str) -> str:
    low = filename.lower()
    if low.endswith(".webp"):
        return "image/webp"
    if low.endswith(".png"):
        return "image/png"
    return "image/jpeg"


def sql_literal(val) -> str:
    if val is None:
        return "NULL"
    if isinstance(val, bool):
        return "1" if val else "0"
    if isinstance(val, (int, float)):
        return str(val)
    text = str(val).replace("'", "''")
    return f"'{text}'"


def build_insert_statements(table: str, rows: list[dict], columns: list[str] | None = None) -> list[str]:
    stmts = []
    for row in rows:
        cols = columns if columns is not None else list(row.keys())
        col_sql = ", ".join(cols)
        val_sql = ", ".join(sql_literal(row.get(c)) for c in cols)
        stmts.append(f"INSERT INTO {table} ({col_sql}) VALUES ({val_sql});")
    return stmts


def generate_seed_sql(seed_data: dict) -> str:
    lines = [
        "DELETE FROM search_fts;",
        "DELETE FROM evenimente;",
        "DELETE FROM locatii;",
        "DELETE FROM hramuri_notabile;",
        "DELETE FROM surse_monitorizate;",
    ]
    lines.extend(build_insert_statements("evenimente", seed_data.get("evenimente", [])))
    lines.extend(build_insert_statements("locatii", seed_data.get("locatii", [])))
    lines.extend(build_insert_statements("hramuri_notabile", seed_data.get("hramuri_notabile", [])))
    lines.extend(build_insert_statements("surse_monitorizate", seed_data.get("surse_monitorizate", [])))
    lines.extend(
        build_insert_statements(
            "search_fts",
            seed_data.get("search_fts", []),
            columns=["item_type", "item_id", "slug", "titlu_norm", "content_norm", "taguri_norm"],
        )
    )
    sql_text = "\n".join(lines) + "\n"
    with open(SEED_SQL_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write(sql_text)
    print(
        f"Generat {SEED_SQL_PATH} ("
        f"evt={len(seed_data.get('evenimente', []))}, "
        f"loc={len(seed_data.get('locatii', []))}, "
        f"hram={len(seed_data.get('hramuri_notabile', []))}, "
        f"surse={len(seed_data.get('surse_monitorizate', []))}, "
        f"fts={len(seed_data.get('search_fts', []))})"
    )
    return sql_text


def dry_run_sqlite(sql_text: str) -> None:
    with open(SCHEMA_SQL_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    conn = sqlite3.connect(":memory:")
    try:
        conn.executescript(schema_sql)
        conn.executescript(sql_text)
        counts = tuple(
            conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            for t in ("evenimente", "locatii", "hramuri_notabile", "search_fts", "surse_monitorizate")
        )
        assert counts == (40, 18, 7, 65, 39), f"Unexpected dry-run counts: {counts}"
        confirmed_cnt = conn.execute(
            "SELECT COUNT(*) FROM evenimente WHERE data_start != ''"
        ).fetchone()[0]
        assert confirmed_cnt >= 11, f"Expected >= 11 events with data_start, got {confirmed_cnt}"
        zeama_hits = conn.execute(
            "SELECT COUNT(*) FROM search_fts WHERE search_fts MATCH 'zeama'"
        ).fetchone()[0]
        assert zeama_hits >= 1, f"Expected >= 1 FTS match for 'zeama', got {zeama_hits}"
        print(f"Dry-run SQLite OK: counts={counts}, data_start={confirmed_cnt}, fts('zeama')={zeama_hits}")
    finally:
        conn.close()


def read_utf8(rel_path: str) -> str:
    full_path = os.path.join(STATIC_DIR, rel_path)
    with open(full_path, "r", encoding="utf-8") as f:
        return f.read()


def read_b64(full_path: str) -> str:
    with open(full_path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def generate_kv_payloads() -> None:
    # Curatam vechile fisiere kv_*.json ca sa nu ramana batch-uri orfane
    for name in os.listdir(CF_DIR):
        if name.startswith("kv_") and name.endswith(".json"):
            os.remove(os.path.join(CF_DIR, name))

    static_entries = [
        {"key": "__static__/index.html", "value": read_utf8("index.html")},
        {"key": "__static__/detail.html", "value": read_utf8("detail.html")},
        {"key": "__static__/admin.html", "value": read_utf8("admin.html")},
        {"key": "__static__/js/app.js", "value": read_utf8(os.path.join("js", "app.js"))},
        {"key": "__static__/js/admin.js", "value": read_utf8(os.path.join("js", "admin.js"))},
    ]

    logo_path = os.path.join(IMAGES_DIR, "logo.png")
    if not os.path.exists(logo_path):
        raise FileNotFoundError(f"Lipseste imaginea logo.png: {logo_path}")
    static_entries.append(
        {
            "key": "logo.png",
            "value": read_b64(logo_path),
            "base64": True,
            "metadata": {"contentType": "image/png"},
        }
    )

    kv_static_path = os.path.join(CF_DIR, "kv_static.json")
    with open(kv_static_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(static_entries, f, ensure_ascii=False)
    print(f"Generat {kv_static_path} ({len(static_entries)} chei)")

    other_images = sorted(
        f
        for f in os.listdir(IMAGES_DIR)
        if f != "logo.png" and os.path.isfile(os.path.join(IMAGES_DIR, f))
    )
    batch_size = 10
    for idx in range(0, len(other_images), batch_size):
        batch_num = (idx // batch_size) + 1
        chunk = other_images[idx : idx + batch_size]
        entries = [
            {
                "key": fname,
                "value": read_b64(os.path.join(IMAGES_DIR, fname)),
                "base64": True,
                "metadata": {"contentType": guess_mime(fname)},
            }
            for fname in chunk
        ]
        batch_path = os.path.join(CF_DIR, f"kv_images_{batch_num}.json")
        with open(batch_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(entries, f, ensure_ascii=False)
        print(f"Generat {batch_path} ({len(entries)} imagini)")


def main() -> None:
    with open(SEED_JSON_PATH, "r", encoding="utf-8") as f:
        seed_data = json.load(f)
    sql_text = generate_seed_sql(seed_data)
    dry_run_sqlite(sql_text)
    generate_kv_payloads()


if __name__ == "__main__":
    main()
