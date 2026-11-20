"""
Utilitar CLI pentru trierea cozii de monitorizare si aplicarea actualizarilor aprobate
exclusiv in baza locala `clubturistic.db` + regenerarea raportului `data/review_queue.md`.
"""

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
import re
import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from search_utils import strip_diacritics, upsert_fts_entry  # noqa: E402

DB_PATH = os.path.join(BASE_DIR, "clubturistic.db")
QUEUE_MD_PATH = os.path.join(BASE_DIR, "data", "review_queue.md")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def make_slug(text: str, prefix: str = "evt") -> str:
    norm = strip_diacritics(text)
    slug = re.sub(r"\s+", "-", norm).strip("-")
    return slug or f"{prefix}-{int(utc_now().timestamp())}"


def sha256_hex(val: str, length: int = 32) -> str:
    return hashlib.sha256((val or "").encode("utf-8")).hexdigest()[:length]


def render_review_queue(conn: sqlite3.Connection) -> str:
    os.makedirs(os.path.dirname(QUEUE_MD_PATH), exist_ok=True)
    pending = conn.execute(
        """
        SELECT * FROM actualizari_detectate
        WHERE status = 'De verificat'
        ORDER BY confirmari_count DESC, scor_relevanta DESC, id DESC
        LIMIT 80
        """
    ).fetchall()
    last_run = conn.execute("SELECT * FROM monitor_runs ORDER BY id DESC LIMIT 1").fetchone()
    seen_cnt = conn.execute("SELECT COUNT(*) FROM surse_articole_vazute").fetchone()[0]
    src_cnt = conn.execute("SELECT COUNT(*) FROM surse_monitorizate WHERE activ = 1").fetchone()[0]
    due_q = conn.execute(
        "SELECT query_hash, nume, categorie, next_due_at FROM cautari_istoric WHERE activ = 1 ORDER BY query_hash"
    ).fetchall()

    now_str = utc_now().strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Coadă de Verificare Evenimente — ClubTuristic.md",
        "",
        f"- **Actualizat:** {now_str}",
        f"- **Surse active:** {src_cnt} | **Articole memorate (skip automat):** {seen_cnt} | **Propuneri în așteptare:** {len(pending)}",
    ]
    if last_run:
        lines.append(
            f"- **Ultima rulare ({last_run['trigger_type']}):** "
            f"{last_run['sources_checked']} surse verificate, {last_run['sources_not_modified']} 304, "
            f"{last_run['items_seen_skipped']} sărite, {last_run['items_new_scanned']} noi scanate, "
            f"{last_run['matches_queued']} potriviri noi."
        )

    lines.extend(["", "## Propuneri noi / Actualizări de aprobat (`De verificat`)", ""])
    if not pending:
        lines.append("_Nicio propunere nouă în așteptare momentan._")
    else:
        lines.append("| ID | Tip | Sursă & Confirmări | Eveniment țintă | Titlu detectat | Dată | Sursă |")
        lines.append("|---:|---|---|---|---|---|---|")
        for r in pending:
            target = r["eveniment_titlu"] or r["eveniment_id"] or "🆕 Eveniment nou"
            title = (r["titlu_detectat"] or "").replace("|", "/").replace("\n", " ")[:75]
            dt = r["data_start_detectata"] or (r["data_text_detectat"] or "—")
            conf = f"{r['sursa_nume']} (×{r['confirmari_count']})"
            lines.append(
                f"| `{r['id']}` | {r['sursa_tip']} | {conf} | {target[:40]} | {title} | {dt} | [link]({r['url_sursa']}) |"
            )

        lines.extend(
            [
                "",
                "### Comenzi rapide de triere",
                "- Aprobă în `clubturistic.db`: `python scripts/apply_review_triage.py --approve <ID1,ID2>`",
                "- Respinge / ignoră zgomotul: `python scripts/apply_review_triage.py --ignore <ID1,ID2>`",
                "- Publică pe Cloudflare după verificare: `python scripts/publish_cloudflare.py`",
            ]
        )

    lines.extend(["", "## Căutări programate rare (`cautari_istoric`)", ""])
    for q in due_q:
        lines.append(
            f"- `{q['query_hash']}` ({q['categorie']}) — {q['nume']} | Următoarea rulare: `{q['next_due_at'] or 'Scadentă acum'}`"
        )

    content = "\n".join(lines) + "\n"
    with open(QUEUE_MD_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    return QUEUE_MD_PATH


def index_event_row(conn: sqlite3.Connection, row: dict) -> None:
    upsert_fts_entry(
        conn,
        "eveniment",
        row["id"],
        row["slug"],
        row["titlu"],
        [
            row["tip"], row["organizator"], row["regiune"], row["raion"], row["localitate"],
            row["locatie_exacta"], row["data_text"], row["luni_active"],
            row["descriere_scurta"], row["cum_a_fost_real"], row["ce_gusti"],
        ],
        row["taguri"],
    )


def approve_updates(conn: sqlite3.Connection, ids: list[int]) -> list[str]:
    today = utc_now().strftime("%Y-%m-%d")
    results = []
    for upd_id in ids:
        upd = conn.execute("SELECT * FROM actualizari_detectate WHERE id = ?", (upd_id,)).fetchone()
        if not upd:
            results.append(f"MISSING:{upd_id}")
            continue

        data_start = (upd["data_start_detectata"] or "").strip()[:20]
        data_end = (upd["data_end_detectata"] or data_start).strip()[:20]
        data_text = (upd["data_text_detectat"] or data_start or "De confirmat").strip()
        evt_id = (upd["eveniment_id"] or "").strip()

        if evt_id:
            ev = conn.execute("SELECT * FROM evenimente WHERE id = ?", (evt_id,)).fetchone()
            if not ev:
                results.append(f"TARGET_NOT_FOUND:{evt_id}")
                continue
            try:
                surse_arr = json.loads(ev["surse_media_json"] or "[]")
            except json.JSONDecodeError:
                surse_arr = []
            if not any(s.get("url") == upd["url_sursa"] for s in surse_arr):
                surse_arr.insert(0, {"titlu": upd["titlu_detectat"], "publicatie": upd["sursa_nume"], "url": upd["url_sursa"]})

            new_start = data_start or ev["data_start"] or ""
            new_end = data_end or ev["data_end"] or new_start
            new_next = new_start or ev["urmatoarea_data_estimata"]
            new_text = data_text if data_start else ev["data_text"]
            new_status = "Confirmat" if new_start else ev["status_data"]
            conn.execute(
                """
                UPDATE evenimente SET
                    data_start = ?, data_end = ?, urmatoarea_data_estimata = ?, data_text = ?,
                    status_data = ?, sursa_confirmarii = ?, ultima_verificare_la = ?,
                    surse_media_json = ?, actualizat_la = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (new_start, new_end, new_next, new_text, new_status, upd["url_sursa"], today, json.dumps(surse_arr, ensure_ascii=False), evt_id),
            )
            updated_row = dict(conn.execute("SELECT * FROM evenimente WHERE id = ?", (evt_id,)).fetchone())
            index_event_row(conn, updated_row)
            conn.execute("UPDATE actualizari_detectate SET status = 'Aprobat' WHERE id = ?", (upd_id,))
            results.append(f"UPDATED:{evt_id}")
        else:
            slug = make_slug(upd["titlu_detectat"], "evt")
            if conn.execute("SELECT 1 FROM evenimente WHERE slug = ?", (slug,)).fetchone():
                slug = f"{slug}-{upd_id}"
            new_id = f"evt-{slug}"[:64]
            loc = (upd["locatie_detectata"] or "mun. Chișinău").strip()
            status = "Confirmat" if data_start else "Estimat după tradiție"
            surse_json = json.dumps(
                [{"titlu": upd["titlu_detectat"], "publicatie": upd["sursa_nume"], "url": upd["url_sursa"]}],
                ensure_ascii=False,
            )
            conn.execute(
                """
                INSERT INTO evenimente (
                    id, slug, titlu, tip, organizator, regiune, raion, localitate, locatie_exacta,
                    lat, lng, distanta_chisinau_km, data_text, data_start, data_end, regula_recurenta,
                    tip_recurenta, luna_principala, luni_active, sezon, ultima_editie_verificata,
                    urmatoarea_data_estimata, status_data, pret_intrare, descriere_scurta,
                    cum_a_fost_real, ce_gusti, taguri, link_oficial, facebook_url, instagram_url,
                    bilete_url, ultima_verificare_la, sursa_confirmarii, surse_media_json,
                    imagine_url, imagine_credit, este_recomandat
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '', '', '', ?, ?, ?, ?, ?, 0)
                """,
                (
                    new_id, slug, upd["titlu_detectat"], "Festival Cultural & Muzică", upd["sursa_nume"],
                    "Chișinău", "Municipiul Chișinău", loc, loc, 47.0105, 28.8638, 0,
                    data_text, data_start, data_end, "Anual / Ediție anunțată",
                    "Dată confirmată" if data_start else "Recurență relativă",
                    "Noiembrie", "Noiembrie", "Toamnă",
                    f"Confirmat din {upd['sursa_nume']}", data_start or "2027-06-15", status,
                    "Vezi sursa oficială", upd["descriere_snippet"] or upd["titlu_detectat"],
                    upd["descriere_snippet"] or upd["titlu_detectat"], "",
                    strip_diacritics(upd["titlu_detectat"]), upd["url_sursa"],
                    today, upd["url_sursa"], surse_json, "/static/images/chisinau.jpg",
                    "Arhivă verificată ClubTuristic.md",
                ),
            )
            created_row = dict(conn.execute("SELECT * FROM evenimente WHERE id = ?", (new_id,)).fetchone())
            index_event_row(conn, created_row)
            conn.execute("UPDATE actualizari_detectate SET status = 'Aprobat' WHERE id = ?", (upd_id,))
            results.append(f"CREATED:{new_id}")
    return results


def parse_id_list(raw: str) -> list[int]:
    out = []
    for part in (raw or "").split(","):
        p = part.strip()
        if p.isdigit():
            out.append(int(p))
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Triere coada locala de evenimente ClubTuristic.md")
    parser.add_argument("--ignore", help="ID-uri separate prin virgula de marcat Ignorat")
    parser.add_argument("--approve", help="ID-uri separate prin virgula de aprobat in clubturistic.db")
    parser.add_argument("--add-finding", action="store_true", help="Adauga manual/AI o descoperire verificata")
    parser.add_argument("--sursa", default="Căutare Web Antigravity")
    parser.add_argument("--tip", default="Facebook")
    parser.add_argument("--titlu", default="")
    parser.add_argument("--url", default="")
    parser.add_argument("--data-start", default="")
    parser.add_argument("--data-end", default="")
    parser.add_argument("--data-text", default="")
    parser.add_argument("--locatie", default="")
    parser.add_argument("--eveniment-id", default="")
    parser.add_argument("--snippet", default="")
    parser.add_argument("--mark-query-done", help="query_hash din cautari_istoric de avansat")
    parser.add_argument("--results", type=int, default=0, help="Numar de rezultate noi gasite de cautare")
    parser.add_argument("--render", action="store_true", help="Regenereaza data/review_queue.md")
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        if args.ignore:
            ids = parse_id_list(args.ignore)
            if ids:
                q_marks = ",".join("?" for _ in ids)
                cur = conn.execute(f"UPDATE actualizari_detectate SET status = 'Ignorat' WHERE id IN ({q_marks})", ids)
                print(f"IGNORED={cur.rowcount}")

        if args.approve:
            ids = parse_id_list(args.approve)
            if ids:
                res = approve_updates(conn, ids)
                print("APPROVED=" + ",".join(res))

        if args.add_finding:
            if not args.titlu or not args.url:
                raise SystemExit("--titlu si --url sunt obligatorii pentru --add-finding")
            dedupe_key = sha256_hex(f"{args.url}|{args.data_start or args.titlu}")
            fp_base = strip_diacritics(args.eveniment_id or args.titlu)[:60]
            fp = sha256_hex(f"{fp_base}|{args.data_start}", 24) if (args.data_start or args.eveniment_id) else ""
            existing_fp = None
            if fp:
                existing_fp = conn.execute(
                    "SELECT id FROM actualizari_detectate WHERE status = 'De verificat' AND event_fingerprint = ?",
                    (fp,),
                ).fetchone()
            if existing_fp:
                conn.execute(
                    "UPDATE actualizari_detectate SET confirmari_count = confirmari_count + 1 WHERE id = ?",
                    (existing_fp["id"],),
                )
                print(f"MERGED_FINDING={existing_fp['id']}")
            else:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO actualizari_detectate (
                        dedupe_key, sursa_id, sursa_nume, sursa_tip, eveniment_id, eveniment_titlu,
                        titlu_detectat, data_start_detectata, data_end_detectata, data_text_detectat,
                        locatie_detectata, descriere_snippet, url_sursa, scor_relevanta, event_fingerprint, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'De verificat')
                    """,
                    (
                        dedupe_key, "web-search", args.sursa, args.tip, args.eveniment_id, "",
                        args.titlu[:220], args.data_start[:20], (args.data_end or args.data_start)[:20],
                        args.data_text or args.data_start, args.locatie[:140], args.snippet[:320],
                        args.url[:400], 90 if args.data_start else 70, fp,
                    ),
                )
                print(f"ADDED_FINDING={dedupe_key}")

        if args.mark_query_done:
            row = conn.execute(
                "SELECT interval_zile FROM cautari_istoric WHERE query_hash = ?",
                (args.mark_query_done,),
            ).fetchone()
            if row:
                now = utc_now()
                next_due = (now + timedelta(days=int(row["interval_zile"] or 7))).strftime("%Y-%m-%dT%H:%M:%SZ")
                conn.execute(
                    "UPDATE cautari_istoric SET last_run_at = ?, next_due_at = ?, last_result_count = ? WHERE query_hash = ?",
                    (now.strftime("%Y-%m-%dT%H:%M:%SZ"), next_due, args.results, args.mark_query_done),
                )
                print(f"QUERY_ADVANCED={args.mark_query_done} NEXT={next_due}")

        conn.commit()
        if args.render or args.ignore or args.approve or args.add_finding or args.mark_query_done:
            out_md = render_review_queue(conn)
            print(f"RENDERED={out_md}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
