"""
Inițializează și populează baza de date verificată `clubturistic.db` (SQLite + FTS5)
din `data/curated_catalog.py` și `data/media_manifest.json`.
Exportă și snapshot-uri curate: `baza_date_verificata.json` și `baza_date_verificata.csv`.
"""

import csv
import json
import os
import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from data.curated_catalog import EVENIMENTE, HRAMURI_NOTABILE, LOCATII
from search_utils import upsert_fts_entry

DB_PATH = os.path.join(BASE_DIR, "clubturistic.db")
MANIFEST_PATH = os.path.join(BASE_DIR, "data", "media_manifest.json")
EXPORT_JSON = os.path.join(BASE_DIR, "baza_date_verificata.json")
EXPORT_CSV = os.path.join(BASE_DIR, "baza_date_verificata.csv")


def load_manifest() -> dict:
    if not os.path.exists(MANIFEST_PATH):
        raise FileNotFoundError(
            f"Manifestul media lipsește ({MANIFEST_PATH}). Rulați mai întâi `python scripts/fetch_real_media.py`."
        )
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def resolve_media(manifest: dict, media_key: str) -> tuple[str, str]:
    entry = manifest.get(media_key)
    if not entry:
        raise KeyError(f"Cheia media `{media_key}` lipsește din media_manifest.json")
    disk_path = os.path.join(BASE_DIR, entry["path"].lstrip("/"))
    if not os.path.exists(disk_path):
        raise FileNotFoundError(f"Imaginea locală lipsește de pe disc: {disk_path}")
    return entry["path"], entry["credit"]


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DROP TABLE IF EXISTS search_fts;
        DROP TABLE IF EXISTS evenimente;
        DROP TABLE IF EXISTS locatii;
        DROP TABLE IF EXISTS hramuri_notabile;
        DROP TABLE IF EXISTS propuneri_comunitate;
        DROP TABLE IF EXISTS entitati;
        DROP TABLE IF EXISTS evenimente_calendar;

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
        CREATE INDEX idx_loc_regiune ON locatii(regiune);
        CREATE INDEX idx_loc_cat ON locatii(categorie);
        """
    )


def populate_database(conn: sqlite3.Connection, manifest: dict) -> dict:
    cur = conn.cursor()
    exported_evenimente = []
    exported_locatii = []
    exported_hramuri = []

    for e in EVENIMENTE:
        img_url, img_credit = resolve_media(manifest, e["media_key"])
        surse_json = json.dumps(e["surse_media"], ensure_ascii=False)
        cur.execute(
            """
            INSERT INTO evenimente (
                id, slug, titlu, tip, organizator, regiune, raion, localitate, locatie_exacta,
                lat, lng, distanta_chisinau_km, data_text, regula_recurenta, tip_recurenta,
                luna_principala, luni_active, sezon, ultima_editie_verificata, urmatoarea_data_estimata,
                status_data, pret_intrare, descriere_scurta, cum_a_fost_real, ce_gusti, taguri,
                link_oficial, surse_media_json, imagine_url, imagine_credit, este_recomandat
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                e["id"], e["slug"], e["titlu"], e["tip"], e["organizator"], e["regiune"],
                e["raion"], e["localitate"], e["locatie_exacta"], e["lat"], e["lng"],
                e["distanta_chisinau_km"], e["data_text"], e["regula_recurenta"], e["tip_recurenta"],
                e["luna_principala"], e["luni_active"], e["sezon"], e["ultima_editie_verificata"],
                e["urmatoarea_data_estimata"], e["status_data"], e["pret_intrare"],
                e["descriere_scurta"], e["cum_a_fost_real"], e["ce_gusti"], e["taguri"],
                e["link_oficial"], surse_json, img_url, img_credit, e["este_recomandat"],
            ),
        )
        upsert_fts_entry(
            conn,
            "eveniment",
            e["id"],
            e["slug"],
            e["titlu"],
            [
                e["tip"], e["organizator"], e["regiune"], e["raion"], e["localitate"],
                e["locatie_exacta"], e["data_text"], e["luni_active"], e["descriere_scurta"],
                e["cum_a_fost_real"], e["ce_gusti"],
            ],
            e["taguri"],
        )
        exported_evenimente.append({**e, "imagine_url": img_url, "imagine_credit": img_credit})

    for loc in LOCATII:
        img_url, img_credit = resolve_media(manifest, loc["media_key"])
        surse_json = json.dumps(loc["surse_media"], ensure_ascii=False)
        cur.execute(
            """
            INSERT INTO locatii (
                id, slug, titlu, categorie, regiune, raion, localitate, adresa,
                lat, lng, distanta_chisinau_km, program_vizita, rezervare_necesara, buget_orientativ,
                descriere_scurta, ce_merita_vazut, ce_gusti, taguri,
                link_oficial, surse_media_json, imagine_url, imagine_credit, este_recomandat
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                loc["id"], loc["slug"], loc["titlu"], loc["categorie"], loc["regiune"],
                loc["raion"], loc["localitate"], loc["adresa"], loc["lat"], loc["lng"],
                loc["distanta_chisinau_km"], loc["program_vizita"], loc["rezervare_necesara"],
                loc["buget_orientativ"], loc["descriere_scurta"], loc["ce_merita_vazut"],
                loc["ce_gusti"], loc["taguri"], loc["link_oficial"], surse_json,
                img_url, img_credit, loc["este_recomandat"],
            ),
        )
        upsert_fts_entry(
            conn,
            "locatie",
            loc["id"],
            loc["slug"],
            loc["titlu"],
            [
                loc["categorie"], loc["regiune"], loc["raion"], loc["localitate"],
                loc["adresa"], loc["descriere_scurta"], loc["ce_merita_vazut"], loc["ce_gusti"],
            ],
            loc["taguri"],
        )
        exported_locatii.append({**loc, "imagine_url": img_url, "imagine_credit": img_credit})

    for h in HRAMURI_NOTABILE:
        img_url, img_credit = resolve_media(manifest, h["media_key"])
        surse_json = json.dumps(h["surse_media"], ensure_ascii=False)
        cur.execute(
            """
            INSERT INTO hramuri_notabile (
                id, slug, titlu, regiune, raion, localitate, lat, lng,
                data_text, luna_principala, sezon, descriere, ce_se_intampla,
                imagine_url, imagine_credit, link_oficial, surse_media_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                h["id"], h["slug"], h["titlu"], h["regiune"], h["raion"], h["localitate"],
                h["lat"], h["lng"], h["data_text"], h["luna_principala"], h["sezon"],
                h["descriere"], h["ce_se_intampla"], img_url, img_credit,
                h["link_oficial"], surse_json,
            ),
        )
        upsert_fts_entry(
            conn,
            "hram",
            h["id"],
            h["slug"],
            h["titlu"],
            [h["regiune"], h["raion"], h["localitate"], h["data_text"], h["descriere"], h["ce_se_intampla"]],
            h["localitate"],
        )
        exported_hramuri.append({**h, "imagine_url": img_url, "imagine_credit": img_credit})

    conn.commit()
    return {
        "evenimente": exported_evenimente,
        "locatii": exported_locatii,
        "hramuri_notabile": exported_hramuri,
    }


def write_exports(snapshot: dict) -> None:
    with open(EXPORT_JSON, "w", encoding="utf-8") as fj:
        json.dump(snapshot, fj, ensure_ascii=False, indent=2)

    csv_fields = [
        "tip_record", "id", "slug", "titlu", "categorie_tip", "regiune", "raion",
        "localitate", "data_sau_program", "luna_principala", "sezon", "lat", "lng",
        "imagine_url", "link_oficial", "ce_gusti",
    ]
    with open(EXPORT_CSV, "w", encoding="utf-8-sig", newline="") as fc:
        writer = csv.DictWriter(fc, fieldnames=csv_fields)
        writer.writeheader()
        for e in snapshot["evenimente"]:
            writer.writerow({
                "tip_record": "Eveniment",
                "id": e["id"],
                "slug": e["slug"],
                "titlu": e["titlu"],
                "categorie_tip": e["tip"],
                "regiune": e["regiune"],
                "raion": e["raion"],
                "localitate": e["localitate"],
                "data_sau_program": e["data_text"],
                "luna_principala": e["luna_principala"],
                "sezon": e["sezon"],
                "lat": e["lat"],
                "lng": e["lng"],
                "imagine_url": e["imagine_url"],
                "link_oficial": e["link_oficial"],
                "ce_gusti": e["ce_gusti"],
            })
        for loc in snapshot["locatii"]:
            writer.writerow({
                "tip_record": "Locatie",
                "id": loc["id"],
                "slug": loc["slug"],
                "titlu": loc["titlu"],
                "categorie_tip": loc["categorie"],
                "regiune": loc["regiune"],
                "raion": loc["raion"],
                "localitate": loc["localitate"],
                "data_sau_program": loc["program_vizita"],
                "luna_principala": "Tot anul",
                "sezon": "Permanent",
                "lat": loc["lat"],
                "lng": loc["lng"],
                "imagine_url": loc["imagine_url"],
                "link_oficial": loc["link_oficial"],
                "ce_gusti": loc["ce_gusti"],
            })


def main():
    manifest = load_manifest()
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    try:
        create_schema(conn)
        snapshot = populate_database(conn, manifest)
        write_exports(snapshot)

        # Verificări stricte de integritate
        c = conn.cursor()
        evt_cnt = c.execute("SELECT COUNT(*) FROM evenimente").fetchone()[0]
        loc_cnt = c.execute("SELECT COUNT(*) FROM locatii").fetchone()[0]
        hrm_cnt = c.execute("SELECT COUNT(*) FROM hramuri_notabile").fetchone()[0]
        fts_cnt = c.execute("SELECT COUNT(*) FROM search_fts").fetchone()[0]
        assert evt_cnt == len(EVENIMENTE), f"Count mismatch evenimente: {evt_cnt}"
        assert loc_cnt == len(LOCATII), f"Count mismatch locatii: {loc_cnt}"
        assert hrm_cnt == len(HRAMURI_NOTABILE), f"Count mismatch hramuri: {hrm_cnt}"
        assert fts_cnt == evt_cnt + loc_cnt + hrm_cnt, f"FTS mismatch: {fts_cnt}"
        print(
            f"✅ Baza de date verificată creată cu succes: {DB_PATH}\n"
            f"   - Evenimente & Festivaluri: {evt_cnt}\n"
            f"   - Crame, Pensiuni & Obiective: {loc_cnt}\n"
            f"   - Hramuri Notabile (separate): {hrm_cnt}\n"
            f"   - Intrări indexate FTS5: {fts_cnt}\n"
            f"   - Export JSON: {EXPORT_JSON}\n"
            f"   - Export CSV: {EXPORT_CSV}"
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
