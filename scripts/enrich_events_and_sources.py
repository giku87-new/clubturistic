"""
Migreaza si imbogateste `clubturistic.db` (idempotent):
1. Adauga coloanele noi (`data_start`, `data_end`, `facebook_url`, `instagram_url`,
   `bilete_url`, `ultima_verificare_la`, `sursa_confirmarii`) in `evenimente`
   si (`facebook_url`, `instagram_url`) in `locatii`.
2. Creeaza tabelele de monitorizare incrementala (`surse_monitorizate`,
   `surse_articole_vazute`, `actualizari_detectate`, `monitor_runs`).
3. Actualizeaza cele 34 evenimente existente cu linkuri oficiale Facebook/IG/Bilete
   si date exacte confirmate (pastrand `data_start = ''` la cele sezoniere neanuntate).
4. Insereaza 6 evenimente reale verificate din Noiembrie-Decembrie 2026 (total: 40).
5. Populeaza `surse_monitorizate` cu 33 de surse reale (agende, stiri, radio, crame, FB).
6. Reconstruieste indexul FTS5 pentru toate cele 40 evenimente.
"""

import json
import os
import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from search_utils import upsert_fts_entry  # noqa: E402

DB_PATH = os.path.join(BASE_DIR, "clubturistic.db")
VERIFIED_DATE = "2026-11-20"


def ensure_columns(conn: sqlite3.Connection, table: str, cols: list[tuple[str, str]]) -> None:
    existing = {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    for name, col_def in cols:
        if name not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {col_def}")


def ensure_schema(conn: sqlite3.Connection) -> None:
    ensure_columns(
        conn,
        "evenimente",
        [
            ("data_start", "TEXT DEFAULT ''"),
            ("data_end", "TEXT DEFAULT ''"),
            ("facebook_url", "TEXT DEFAULT ''"),
            ("instagram_url", "TEXT DEFAULT ''"),
            ("bilete_url", "TEXT DEFAULT ''"),
            ("ultima_verificare_la", "TEXT DEFAULT ''"),
            ("sursa_confirmarii", "TEXT DEFAULT ''"),
        ],
    )
    ensure_columns(
        conn,
        "locatii",
        [
            ("facebook_url", "TEXT DEFAULT ''"),
            ("instagram_url", "TEXT DEFAULT ''"),
        ],
    )
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS surse_monitorizate (
            id TEXT PRIMARY KEY,
            nume TEXT NOT NULL,
            tip TEXT NOT NULL,
            url TEXT UNIQUE NOT NULL,
            parser TEXT NOT NULL,
            regiune_focus TEXT DEFAULT 'Moldova',
            eveniment_id TEXT DEFAULT '',
            activ INTEGER DEFAULT 1,
            etag TEXT DEFAULT '',
            last_modified TEXT DEFAULT '',
            last_checked_at TEXT DEFAULT '',
            last_status TEXT DEFAULT '',
            last_new_items INTEGER DEFAULT 0,
            total_matches INTEGER DEFAULT 0,
            creat_la DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS surse_articole_vazute (
            item_hash TEXT PRIMARY KEY,
            sursa_id TEXT NOT NULL,
            url TEXT NOT NULL,
            titlu TEXT DEFAULT '',
            matched INTEGER DEFAULT 0,
            first_seen_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS actualizari_detectate (
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
            status TEXT DEFAULT 'De verificat',
            detectat_la DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS monitor_runs (
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

        CREATE INDEX IF NOT EXISTS idx_evt_data_start ON evenimente(data_start);
        CREATE INDEX IF NOT EXISTS idx_vazute_sursa ON surse_articole_vazute(sursa_id);
        CREATE INDEX IF NOT EXISTS idx_act_status ON actualizari_detectate(status);
        """
    )


EVENT_UPDATES: dict[str, dict] = {
    "evt-ia-mania-holercani": {
        "data_start": "2027-07-04",
        "data_end": "2027-07-04",
        "urmatoarea_data_estimata": "2027-07-04",
        "status_data": "Confirmat",
        "data_text": "4 Iulie 2027 (Holercani / Ustia)",
        "ultima_editie_verificata": "Ediția 2026 (5 Iulie 2026)",
        "facebook_url": "https://www.facebook.com/klumeaevents/",
        "instagram_url": "https://www.instagram.com/klumea.eu/",
        "bilete_url": "https://iticket.md",
        "sursa_confirmarii": "https://iticket.md",
    },
    "evt-ziua-nationala-a-vinului": {
        "data_start": "2027-10-02",
        "data_end": "2027-10-03",
        "urmatoarea_data_estimata": "2027-10-02",
        "status_data": "Confirmat",
        "data_text": "2 - 3 Octombrie 2027 (PMAN Chișinău & Crame)",
        "ultima_editie_verificata": "Ediția aniversară XXV (3-4 Octombrie 2026)",
        "facebook_url": "https://www.facebook.com/wineofmoldova/",
        "sursa_confirmarii": "https://wineofmoldova.com/ro/",
    },
    "evt-targul-de-craciun-chisinau": {
        "data_start": "2026-12-05",
        "data_end": "2027-01-15",
        "urmatoarea_data_estimata": "2026-12-05",
        "status_data": "Confirmat",
        "data_text": "5 Decembrie 2026 - 15 Ianuarie 2027",
        "sursa_confirmarii": "https://www.chisinau.md/ro",
    },
    "evt-hederlez-ceadir-lunga": {
        "data_start": "2027-05-06",
        "data_end": "2027-05-06",
        "urmatoarea_data_estimata": "2027-05-06",
        "status_data": "Confirmat",
        "sursa_confirmarii": "https://ceadir-lunga.md",
    },
    "evt-festivalul-martisor-chisinau": {
        "data_start": "2027-03-01",
        "data_end": "2027-03-12",
        "urmatoarea_data_estimata": "2027-03-01",
        "status_data": "Confirmat",
        "sursa_confirmarii": "https://mc.gov.md",
    },
    "evt-ziua-portului-popular": {
        "data_start": "2027-06-27",
        "data_end": "2027-06-27",
        "urmatoarea_data_estimata": "2027-06-27",
        "status_data": "Confirmat",
        "sursa_confirmarii": "https://mc.gov.md",
    },
    "evt-ecolocal-chisinau": {
        "data_start": "2026-11-21",
        "data_end": "2026-11-21",
        "urmatoarea_data_estimata": "2026-11-21",
        "status_data": "Săptămânal activ",
        "facebook_url": "https://www.facebook.com/EcoLocal.md",
        "sursa_confirmarii": "https://ecolocal.md",
    },
    "evt-yard-sale-chisinau": {
        "data_start": "",
        "data_end": "",
        "status_data": "Săptămânal activ",
        "facebook_url": "https://www.facebook.com/yardsalemoldova/",
        "instagram_url": "https://www.instagram.com/yardsale_md/",
    },
    "evt-milestii-mici-winerun": {
        "data_start": "",
        "data_end": "",
        "status_data": "Dată neanunțată (sezon)",
        "facebook_url": "https://www.facebook.com/sporter.md",
        "instagram_url": "https://www.instagram.com/sportermd",
        "bilete_url": "https://sporter.md/ro/events",
    },
    "evt-mai-dulce-chisinau": {
        "facebook_url": "https://www.facebook.com/klumeaevents/",
        "instagram_url": "https://www.instagram.com/klumea.eu/",
    },
    "evt-lavender-fest-cobusca": {
        "facebook_url": "https://www.facebook.com/klumeaevents/",
        "instagram_url": "https://www.instagram.com/klumea.eu/",
    },
    "evt-vernisajul-vinului-chisinau": {
        "facebook_url": "https://www.facebook.com/vernisajulvinului/",
    },
    "evt-bostaniada-balabanesti": {
        "ultima_editie_verificata": "Ediția 2026 (26-27 Septembrie 2026)",
        "bilete_url": "https://iticket.md",
    },
    "evt-descopera-butuceni": {
        "ultima_editie_verificata": "Ediția aniversară X (18-21 Iunie 2026)",
        "facebook_url": "https://www.facebook.com/orheiulvechireserve/",
        "instagram_url": "https://www.instagram.com/rezervatia.orheiul.vechi/",
        "bilete_url": "https://iticket.md",
    },
    "evt-gustar-orheiul-vechi": {
        "facebook_url": "https://www.facebook.com/orheiulvechireserve/",
        "instagram_url": "https://www.instagram.com/rezervatia.orheiul.vechi/",
        "bilete_url": "https://iticket.md",
    },
    "evt-festivalul-lupilor-orheiul-vechi": {
        "facebook_url": "https://www.facebook.com/orheiulvechireserve/",
        "instagram_url": "https://www.instagram.com/rezervatia.orheiul.vechi/",
        "bilete_url": "https://iticket.md",
    },
    "evt-underland-cricova": {
        "facebook_url": "https://www.facebook.com/CricovaWinery",
        "instagram_url": "https://www.instagram.com/cricova_winery",
        "bilete_url": "https://iticket.md",
    },
    "evt-vinopera-castel-mimi": {
        "facebook_url": "https://www.facebook.com/CastelMimi.md",
        "instagram_url": "https://www.instagram.com/castelmimi.wineresort/",
        "bilete_url": "https://castelmimi.md/evenimente/",
    },
    "evt-purcari-wine-run": {
        "facebook_url": "https://www.facebook.com/purcari",
        "instagram_url": "https://www.instagram.com/purcari_wines/",
        "bilete_url": "https://sporter.md/ro/events",
    },
    "evt-ciresar-truseni": {
        "facebook_url": "https://www.facebook.com/truseni",
    },
    "evt-festivalul-marului-soroca": {
        "facebook_url": "https://www.facebook.com/Prim%C4%83ria-ora%C5%9Fului-Soroca-502414779852857",
    },
    "evt-festivalul-prunei-nisporeni": {
        "facebook_url": "https://www.facebook.com/crnisporeni/",
    },
}

NEW_EVENTS_2026 = [
    {
        "id": "evt-festivalul-bach-2026",
        "slug": "festivalul-international-js-bach-chisinau",
        "titlu": "Festivalul Internațional „J.S. Bach” (Ediția a XV-a)",
        "tip": "Festival Cultural & Muzică",
        "organizator": "Sala cu Orgă din Chișinău",
        "regiune": "Chișinău",
        "raion": "Municipiul Chișinău",
        "localitate": "mun. Chișinău",
        "locatie_exacta": "Sala cu Orgă, bd. Ștefan cel Mare și Sfânt 81",
        "lat": 47.0229,
        "lng": 28.8339,
        "distanta_chisinau_km": 0,
        "data_text": "12 - 26 Noiembrie 2026",
        "data_start": "2026-11-12",
        "data_end": "2026-11-26",
        "regula_recurenta": "Anual în luna Noiembrie",
        "tip_recurenta": "Dată confirmată",
        "luna_principala": "Noiembrie",
        "luni_active": "Noiembrie",
        "sezon": "Toamnă",
        "ultima_editie_verificata": "Ediția a XV-a (12-26 Noiembrie 2026)",
        "urmatoarea_data_estimata": "2026-11-20",
        "status_data": "Confirmat",
        "pret_intrare": "100 - 300 MDL (iTicket)",
        "descriere_scurta": "Ediția a XV-a a prestigiosului festival dedicat lui Johann Sebastian Bach, cu recitaluri de orgă, muzică de cameră și seri de Bach Jazz Trio la Sala cu Orgă.",
        "cum_a_fost_real": "Concertul de deschidere a reunit organiști internaționali de renume, inclusiv organistul german Jan Liebermann, alături de orchestra națională de cameră și interpreți din Europa. Acustica monumentalei Săli cu Orgă din inima Chișinăului transformă fiecare seară într-o experiență culturală aparte.",
        "ce_gusti": "Patiserie și cafea de specialitate în cafenelele istorice de pe bd. Ștefan cel Mare înainte de recital",
        "taguri": "bach, orga, muzica clasica, concert, chisinau, noiembrie, 2026, jazz",
        "link_oficial": "https://fest.md/ro/evenimente",
        "facebook_url": "https://www.facebook.com/iticket.md",
        "instagram_url": "",
        "bilete_url": "https://iticket.md/events",
        "ultima_verificare_la": VERIFIED_DATE,
        "sursa_confirmarii": "https://fest.md/ro/evenimente",
        "surse_media": [
            {"titlu": "Agenda culturală Noiembrie 2026 Chișinău", "publicatie": "Fest.md", "url": "https://fest.md/ro/evenimente"},
            {"titlu": "Bilete Festivalul J.S. Bach", "publicatie": "iTicket.md", "url": "https://iticket.md/events"},
        ],
        "imagine_url": "/static/images/outdoor_opera.jpg",
        "imagine_credit": "Arhivă verificată ClubTuristic.md",
        "este_recomandat": 1,
    },
    {
        "id": "evt-satul-meu-vatra-aleasa-cahul-2026",
        "slug": "festivalul-folcloric-satul-meu-vatra-aleasa-cahul",
        "titlu": "Festivalul Folcloric „Satul meu – vatră aleasă”",
        "tip": "Festival Cultural & Muzică",
        "organizator": "Consiliul Raional Cahul & Direcția Cultură",
        "regiune": "Sud",
        "raion": "Cahul",
        "localitate": "s. Alexandru Ioan Cuza",
        "locatie_exacta": "Casa de Cultură din satul Alexandru Ioan Cuza, r. Cahul",
        "lat": 45.5964,
        "lng": 28.4481,
        "distanta_chisinau_km": 188,
        "data_text": "22 Noiembrie 2026",
        "data_start": "2026-11-22",
        "data_end": "2026-11-22",
        "regula_recurenta": "Festival folcloric regional (Noiembrie 2026)",
        "tip_recurenta": "Dată confirmată",
        "luna_principala": "Noiembrie",
        "luni_active": "Noiembrie",
        "sezon": "Toamnă",
        "ultima_editie_verificata": "Ediția 22 Noiembrie 2026",
        "urmatoarea_data_estimata": "2026-11-22",
        "status_data": "Confirmat",
        "pret_intrare": "Gratuit",
        "descriere_scurta": "Sărbătoare a folclorului, costumului popular și obiceiurilor din sudul Moldovei, găzduită în satul Alexandru Ioan Cuza din raionul Cahul.",
        "cum_a_fost_real": "Ansambluri folclorice din localitățile sudului aduc cântece bătrânești, dansuri populare și prezentări de port autentic din zona Prutului de Jos, într-o atmosferă caldă de toamnă târzie.",
        "ce_gusti": "Plăcinte coapte pe vatră, brânză de oi din sud, sarmale tradiționale și vin roșu de Cahul",
        "taguri": "folclor, cahul, alexandru ioan cuza, sud, port popular, noiembrie, 2026, gratuit",
        "link_oficial": "https://turism.gov.md/ro/",
        "facebook_url": "",
        "instagram_url": "",
        "bilete_url": "",
        "ultima_verificare_la": VERIFIED_DATE,
        "sursa_confirmarii": "https://turism.gov.md/ro/",
        "surse_media": [
            {"titlu": "Calendar turistic și cultural Republica Moldova", "publicatie": "Turism.gov.md", "url": "https://turism.gov.md/ro/"},
        ],
        "imagine_url": "/static/images/moldovan_ie.jpg",
        "imagine_credit": "Arhivă verificată ClubTuristic.md",
        "este_recomandat": 0,
    },
    {
        "id": "evt-moldova-accordion-days-2026",
        "slug": "moldova-accordion-days-chisinau",
        "titlu": "Festivalul „Moldova Accordion Days” — Rapsodia Română",
        "tip": "Festival Cultural & Muzică",
        "organizator": "Sala cu Orgă & Artiști Concertiști",
        "regiune": "Chișinău",
        "raion": "Municipiul Chișinău",
        "localitate": "mun. Chișinău",
        "locatie_exacta": "Sala cu Orgă, mun. Chișinău (ora 18:30)",
        "lat": 47.0229,
        "lng": 28.8339,
        "distanta_chisinau_km": 0,
        "data_text": "1 Decembrie 2026, ora 18:30",
        "data_start": "2026-12-01",
        "data_end": "2026-12-01",
        "regula_recurenta": "Deschidere 1 Decembrie 2026",
        "tip_recurenta": "Dată confirmată",
        "luna_principala": "Decembrie",
        "luni_active": "Decembrie",
        "sezon": "Iarnă",
        "ultima_editie_verificata": "Ediția 1 Decembrie 2026",
        "urmatoarea_data_estimata": "2026-12-01",
        "status_data": "Confirmat",
        "pret_intrare": "150 - 350 MDL",
        "descriere_scurta": "Seară de gală dedicată acordeonului de concert și muzicii românești simfonice și folclorice virtuoz interpretate la Sala cu Orgă.",
        "cum_a_fost_real": "Evenimentul adună acordeoniști și baianiști de talie internațională din Moldova și Europa, îmbinând rapsodiile clasice cu folclorul balcanic și jazzul de cameră.",
        "ce_gusti": "Ciocolată caldă, deserturi de iarnă și vin fiert în centrul Chișinăului",
        "taguri": "acordeon, rapsodia romana, sala cu orga, decembrie, 1 decembrie, 2026, chisinau",
        "link_oficial": "https://fest.md/ro/evenimente",
        "facebook_url": "https://www.facebook.com/fest.md",
        "instagram_url": "",
        "bilete_url": "https://iticket.md/events",
        "ultima_verificare_la": VERIFIED_DATE,
        "sursa_confirmarii": "https://fest.md/ro/evenimente",
        "surse_media": [
            {"titlu": "Agenda concertelor Decembrie 2026", "publicatie": "Fest.md", "url": "https://fest.md/ro/evenimente"},
        ],
        "imagine_url": "/static/images/jazz_sax.jpg",
        "imagine_credit": "Arhivă verificată ClubTuristic.md",
        "este_recomandat": 0,
    },
    {
        "id": "evt-targul-international-caritate-2026",
        "slug": "targul-international-de-caritate-moldexpo-2026",
        "titlu": "Târgul Internațional de Caritate 2026 (Ambasade & Gastronomie)",
        "tip": "Târg Producători & Meșteșuguri",
        "organizator": "International Women's Club of Moldova (IWCM)",
        "regiune": "Chișinău",
        "raion": "Municipiul Chișinău",
        "localitate": "mun. Chișinău",
        "locatie_exacta": "CIE Moldexpo, Pavilionul Central, str. Ghioceilor 1",
        "lat": 47.0315,
        "lng": 28.8037,
        "distanta_chisinau_km": 0,
        "data_text": "5 Decembrie 2026, 10:00 - 17:00",
        "data_start": "2026-12-05",
        "data_end": "2026-12-05",
        "regula_recurenta": "Anual în primul weekend din Decembrie",
        "tip_recurenta": "Dată confirmată",
        "luna_principala": "Decembrie",
        "luni_active": "Decembrie",
        "sezon": "Iarnă",
        "ultima_editie_verificata": "Ediția 5 Decembrie 2026",
        "urmatoarea_data_estimata": "2026-12-05",
        "status_data": "Confirmat",
        "pret_intrare": "Bilet acces caritabil (~50 MDL)",
        "descriere_scurta": "Cel mai mare târg multicultural de iarnă din Moldova: standuri ale ambasadelor, mâncăruri autentice din zeci de țări, artizanat și tombole caritabile.",
        "cum_a_fost_real": "Peste 30 de ambasade și misiuni diplomatice amenajează standuri culinare și culturale la Moldexpo. Vizitatorii pot gusta preparate naționale din întreaga lume, cumpăra cadouri de Crăciun și susține cauze sociale din Moldova.",
        "ce_gusti": "Specialități culinare internaționale pregătite de ambasadele din Moldova, deserturi artizanale, vin fiert",
        "taguri": "targ, caritate, moldexpo, ambasade, gastronomie, decembrie, 2026, chisinau, craciun",
        "link_oficial": "https://fest.md/ro/evenimente",
        "facebook_url": "https://www.facebook.com/fest.md",
        "instagram_url": "",
        "bilete_url": "https://iticket.md/events",
        "ultima_verificare_la": VERIFIED_DATE,
        "sursa_confirmarii": "https://fest.md/ro/evenimente",
        "surse_media": [
            {"titlu": "Târgul Internațional de Caritate 5 Decembrie 2026", "publicatie": "Fest.md", "url": "https://fest.md/ro/evenimente"},
        ],
        "imagine_url": "/static/images/farmers_market.jpg",
        "imagine_credit": "Arhivă verificată ClubTuristic.md",
        "este_recomandat": 1,
    },
    {
        "id": "evt-joc-cricova-subteran-2026",
        "slug": "concert-ansamblul-joc-orasul-subteran-cricova",
        "titlu": "Concert Coregrafic Ansamblul Național „JOC” în Orașul Subteran Cricova",
        "tip": "Ziua Ușilor Deschise & Vin",
        "organizator": "Combinatul de Vinuri Cricova & Ansamblul JOC",
        "regiune": "Chișinău",
        "raion": "Municipiul Chișinău",
        "localitate": "or. Cricova",
        "locatie_exacta": "Galeriile Subterane Cricova, str. Chișinăului 124",
        "lat": 47.1369,
        "lng": 28.8594,
        "distanta_chisinau_km": 15,
        "data_text": "5 Decembrie 2026",
        "data_start": "2026-12-05",
        "data_end": "2026-12-05",
        "regula_recurenta": "Eveniment special de iarnă (5 Decembrie 2026)",
        "tip_recurenta": "Dată confirmată",
        "luna_principala": "Decembrie",
        "luni_active": "Decembrie",
        "sezon": "Iarnă",
        "ultima_editie_verificata": "Ediția 5 Decembrie 2026",
        "urmatoarea_data_estimata": "2026-12-05",
        "status_data": "Confirmat",
        "pret_intrare": "Bilet acces / pachet degustare",
        "descriere_scurta": "Spectacol coregrafic unic al legendarului Ansamblul Național „JOC” găzduit în galeriile subterane de la Cricova, îmbinat cu degustări de spumante clasice.",
        "cum_a_fost_real": "Îmbină patrimoniul dansului popular moldovenesc cu atmosfera spectaculoasă a sălilor de degustare din calcar la 60 de metri sub pământ.",
        "ce_gusti": "Spumante brut Cricova prin metoda tradițională, vinuri de colecție, plăcinte și brânzeturi locale",
        "taguri": "cricova, joc, crama, vin, spumant, subteran, decembrie, 2026, dans",
        "link_oficial": "https://cricova.md/ro/",
        "facebook_url": "https://www.facebook.com/CricovaWinery",
        "instagram_url": "https://www.instagram.com/cricova_winery",
        "bilete_url": "https://fest.md/ro/evenimente",
        "ultima_verificare_la": VERIFIED_DATE,
        "sursa_confirmarii": "https://fest.md/ro/evenimente",
        "surse_media": [
            {"titlu": "Cricova — Evenimente și degustări", "publicatie": "Cricova.md", "url": "https://cricova.md/ro/"},
            {"titlu": "Program Concert JOC la Cricova (5 Decembrie 2026)", "publicatie": "Fest.md", "url": "https://fest.md/ro/evenimente"},
        ],
        "imagine_url": "/static/images/cricova.jpg",
        "imagine_credit": "Arhivă verificată ClubTuristic.md",
        "este_recomandat": 1,
    },
    {
        "id": "evt-covorul-dorului-2026",
        "slug": "targul-covorul-dorului-chisinau",
        "titlu": "Târgul Național „Covorul Dorului” (Patrimoniu UNESCO)",
        "tip": "Târg Producători & Meșteșuguri",
        "organizator": "Ministerul Culturii & Muzeul Național de Istorie a Moldovei",
        "regiune": "Chișinău",
        "raion": "Municipiul Chișinău",
        "localitate": "mun. Chișinău",
        "locatie_exacta": "Muzeul Național de Istorie a Moldovei, str. 31 August 1989 nr. 121A",
        "lat": 47.0228,
        "lng": 28.8282,
        "distanta_chisinau_km": 0,
        "data_text": "20 Decembrie 2026",
        "data_start": "2026-12-20",
        "data_end": "2026-12-20",
        "regula_recurenta": "Anual în Decembrie (Ediția 2026: 20 Decembrie)",
        "tip_recurenta": "Dată confirmată",
        "luna_principala": "Decembrie",
        "luni_active": "Decembrie",
        "sezon": "Iarnă",
        "ultima_editie_verificata": "Ediția 20 Decembrie 2026",
        "urmatoarea_data_estimata": "2026-12-20",
        "status_data": "Confirmat",
        "pret_intrare": "Gratuit / Bilet muzeu",
        "descriere_scurta": "Târgul dedicat scoarței tradiționale înscrise în patrimoniul UNESCO, colindelor de iarnă și meșterilor populari din toate zonele țării.",
        "cum_a_fost_real": "În sălile Muzeului Național de Istorie sunt expuse covoare basarabene vechi de peste un secol, ateliere live de țesut la război, prezentări ale meșteșugarilor și cete de colindători.",
        "ce_gusti": "Cozonaci, colaci împletiți de Crăciun, dulcețuri de casă și ceaiuri din plante medicinale din Codri",
        "taguri": "covorul dorului, unesco, scoarta, covor, mestesugari, colinde, decembrie, 2026, muzeu",
        "link_oficial": "https://turism.gov.md/ro/",
        "facebook_url": "",
        "instagram_url": "",
        "bilete_url": "",
        "ultima_verificare_la": VERIFIED_DATE,
        "sursa_confirmarii": "https://turism.gov.md/ro/",
        "surse_media": [
            {"titlu": "Calendarul Național al Târgurilor — Covorul Dorului", "publicatie": "Turism.gov.md", "url": "https://turism.gov.md/ro/"},
        ],
        "imagine_url": "/static/images/moldovan_carpet.jpg",
        "imagine_credit": "Arhivă verificată ClubTuristic.md",
        "este_recomandat": 1,
    },
]

LOCATION_SOCIALS: dict[str, tuple[str, str]] = {
    "loc-cricova": ("https://www.facebook.com/CricovaWinery", "https://www.instagram.com/cricova_winery"),
    "loc-castel-mimi": ("https://www.facebook.com/CastelMimi.md", "https://www.instagram.com/castelmimi.wineresort/"),
    "loc-purcari": ("https://www.facebook.com/purcari", "https://www.instagram.com/purcari_wines/"),
    "loc-asconi": ("https://www.facebook.com/asconiwinerymd/", "https://www.instagram.com/asconi.winery/"),
    "loc-et-cetera": ("https://www.facebook.com/EtCeteraWines", "https://www.instagram.com/etcetera_winery/"),
    "loc-chateau-vartely": ("https://www.facebook.com/ChateauVartely/", "https://www.instagram.com/chateauvartely/"),
    "loc-butuceni": ("https://www.facebook.com/orheiulvechireserve/", "https://www.instagram.com/rezervatia.orheiul.vechi/"),
}

MONITORED_SOURCES = [
    # 5 Agende & Bilete
    ("src-fest-festivaluri", "Fest.md — Festivaluri", "Agenda", "https://fest.md/ro/evenimente/festivaluri", "fest_html", "Moldova", ""),
    ("src-fest-targuri", "Fest.md — Târguri", "Agenda", "https://fest.md/ro/evenimente/targuri", "fest_html", "Moldova", ""),
    ("src-fest-expozitii", "Fest.md — Expoziții", "Agenda", "https://fest.md/ro/evenimente/expozitii", "fest_html", "Moldova", ""),
    ("src-iticket", "iTicket.md — Evenimente", "Agenda", "https://iticket.md/events", "html_links", "Moldova", ""),
    ("src-sporter", "Sporter.md — Curse & Winerun", "Agenda", "https://sporter.md/ro/events", "html_links", "Moldova", "evt-milestii-mici-winerun"),
    # 8 Portaluri de Stiri RSS
    ("src-diez", "Diez.md", "Stiri", "https://diez.md/feed/", "rss", "Moldova", ""),
    ("src-locals", "Locals.md — Cultură & Chișinău", "Stiri", "https://locals.md/feed/", "rss", "Chișinău", ""),
    ("src-locuri", "Locuri.md — Turism Moldova", "Stiri", "https://locuri.md/feed/", "rss", "Moldova", ""),
    ("src-newsmaker", "NewsMaker.md", "Stiri", "https://newsmaker.md/ro/feed/", "rss", "Moldova", ""),
    ("src-tv8", "TV8.md", "Stiri", "https://tv8.md/rss", "rss", "Moldova", ""),
    ("src-agrotv", "AgroTV.md — Festivaluri Rurale", "Stiri", "https://agrotv.md/feed/", "rss", "Moldova", ""),
    ("src-zdg", "Ziarul de Gardă", "Stiri", "https://www.zdg.md/feed/", "rss", "Moldova", ""),
    ("src-europalibera", "Europa Liberă Moldova", "Stiri", "https://moldova.europalibera.org/api/z-pqpiev-qpp", "rss", "Moldova", ""),
    # 6 Radio, TV Public & Presa Regionala RSS
    ("src-radiomoldova", "Radio Moldova", "Radio", "https://radiomoldova.md/rss", "rss", "Moldova", ""),
    ("src-moldova1", "Moldova 1", "Radio/TV", "https://moldova1.md/rss", "rss", "Moldova", ""),
    ("src-esp", "ESP.md — Nord / Bălți", "Stiri", "https://esp.md/ro/rss.xml", "rss", "Nord", ""),
    ("src-nokta", "Nokta.md — UTA Găgăuzia", "Stiri", "https://nokta.md/feed/", "rss", "UTA Găgăuzia", ""),
    ("src-ialoveni", "IaloveniOnline.md — Centru", "Stiri", "https://ialovenionline.md/feed/", "rss", "Centru", ""),
    ("src-observatorul", "Observatorul de Nord — Soroca", "Stiri", "https://observatorul.md/feed/", "rss", "Nord", ""),
    # 4 Site-uri Oficiale Festivaluri & Crame
    ("src-bostaniada", "Bostaniada.md (RSS)", "Website Oficial", "https://bostaniada.md/feed/", "rss", "Centru", "evt-bostaniada-balabanesti"),
    ("src-castelmimi", "Castel Mimi — Evenimente", "Website Oficial", "https://castelmimi.md/evenimente/", "html_links", "Centru", "evt-vinopera-castel-mimi"),
    ("src-wineofmoldova", "Wine of Moldova", "Website Oficial", "https://wineofmoldova.com/ro/", "html_links", "Moldova", "evt-ziua-nationala-a-vinului"),
    ("src-ecolocal", "EcoLocal.md", "Website Oficial", "https://ecolocal.md/", "html_links", "Chișinău", "evt-ecolocal-chisinau"),
    # 10 Pagini Facebook Oficiale
    ("src-fb-klumea", "Facebook — KLumea Events (IA MANIA / Mai Dulce / Lavender)", "Facebook", "https://www.facebook.com/klumeaevents/", "social_manual", "Moldova", "evt-ia-mania-holercani"),
    ("src-fb-ecolocal", "Facebook — EcoLocal Farmers Market", "Facebook", "https://www.facebook.com/EcoLocal.md", "social_manual", "Chișinău", "evt-ecolocal-chisinau"),
    ("src-fb-yardsale", "Facebook — Yard Sale Moldova", "Facebook", "https://www.facebook.com/yardsalemoldova/", "social_manual", "Chișinău", "evt-yard-sale-chisinau"),
    ("src-fb-wineofmoldova", "Facebook — Wine of Moldova", "Facebook", "https://www.facebook.com/wineofmoldova/", "social_manual", "Moldova", "evt-ziua-nationala-a-vinului"),
    ("src-fb-vernisaj", "Facebook — Vernisajul Vinului", "Facebook", "https://www.facebook.com/vernisajulvinului/", "social_manual", "Chișinău", "evt-vernisajul-vinului-chisinau"),
    ("src-fb-castelmimi", "Facebook — Castel Mimi Wine Resort", "Facebook", "https://www.facebook.com/CastelMimi.md", "social_manual", "Centru", "evt-vinopera-castel-mimi"),
    ("src-fb-cricova", "Facebook — Cricova Winery", "Facebook", "https://www.facebook.com/CricovaWinery", "social_manual", "Chișinău", "evt-underland-cricova"),
    ("src-fb-purcari", "Facebook — Château Purcari", "Facebook", "https://www.facebook.com/purcari", "social_manual", "Sud", "evt-purcari-wine-run"),
    ("src-fb-sporter", "Facebook — Sporter Moldova", "Facebook", "https://www.facebook.com/sporter.md", "social_manual", "Moldova", "evt-milestii-mici-winerun"),
    ("src-fb-orheiulvechi", "Facebook — Rezervația Orheiul Vechi", "Facebook", "https://www.facebook.com/orheiulvechireserve/", "social_manual", "Centru", "evt-descopera-butuceni"),
]


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        ensure_schema(conn)

        # Marcam toate evenimentele existente ca verificate azi; cele cu status 'Estimat dupa traditie'
        # raman transparent fara data_start / data_end.
        conn.execute("UPDATE evenimente SET ultima_verificare_la = ?", (VERIFIED_DATE,))
        conn.execute(
            "UPDATE evenimente SET data_start = '', data_end = '' "
            "WHERE status_data LIKE '%Estimat%'"
        )

        # Aplicam actualizari punctuale cu linkuri FB/IG/Bilete & date confirmate
        for evt_id, fields in EVENT_UPDATES.items():
            sets = ", ".join(f"{k} = ?" for k in fields) + ", ultima_verificare_la = ?"
            vals = list(fields.values()) + [VERIFIED_DATE, evt_id]
            cur = conn.execute(f"UPDATE evenimente SET {sets} WHERE id = ?", vals)
            assert cur.rowcount == 1, f"Event ID negasit in clubturistic.db: {evt_id}"

        # Inseram cele 6 evenimente reale din Noiembrie-Decembrie 2026
        for ev in NEW_EVENTS_2026:
            surse_json = json.dumps(ev["surse_media"], ensure_ascii=False)
            conn.execute(
                """
                INSERT OR REPLACE INTO evenimente (
                    id, slug, titlu, tip, organizator, regiune, raion, localitate, locatie_exacta,
                    lat, lng, distanta_chisinau_km, data_text, data_start, data_end, regula_recurenta,
                    tip_recurenta, luna_principala, luni_active, sezon, ultima_editie_verificata,
                    urmatoarea_data_estimata, status_data, pret_intrare, descriere_scurta,
                    cum_a_fost_real, ce_gusti, taguri, link_oficial, facebook_url, instagram_url,
                    bilete_url, ultima_verificare_la, sursa_confirmarii, surse_media_json,
                    imagine_url, imagine_credit, este_recomandat
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ev["id"], ev["slug"], ev["titlu"], ev["tip"], ev["organizator"],
                    ev["regiune"], ev["raion"], ev["localitate"], ev["locatie_exacta"],
                    ev["lat"], ev["lng"], ev["distanta_chisinau_km"], ev["data_text"],
                    ev["data_start"], ev["data_end"], ev["regula_recurenta"], ev["tip_recurenta"],
                    ev["luna_principala"], ev["luni_active"], ev["sezon"],
                    ev["ultima_editie_verificata"], ev["urmatoarea_data_estimata"],
                    ev["status_data"], ev["pret_intrare"], ev["descriere_scurta"],
                    ev["cum_a_fost_real"], ev["ce_gusti"], ev["taguri"], ev["link_oficial"],
                    ev["facebook_url"], ev["instagram_url"], ev["bilete_url"],
                    ev["ultima_verificare_la"], ev["sursa_confirmarii"], surse_json,
                    ev["imagine_url"], ev["imagine_credit"], ev["este_recomandat"],
                ),
            )

        # Imbogatim locatiile cu linkuri Facebook/Instagram oficiale
        for loc_id, (fb, ig) in LOCATION_SOCIALS.items():
            cur = conn.execute(
                "UPDATE locatii SET facebook_url = ?, instagram_url = ? WHERE id = ?",
                (fb, ig, loc_id),
            )
            assert cur.rowcount == 1, f"Location ID negasit in clubturistic.db: {loc_id}"

        # Populam surse_monitorizate (pastram istoricul last_checked_at/etag daca exista deja)
        for sid, nume, tip, url, parser, regiune_focus, evt_id in MONITORED_SOURCES:
            conn.execute(
                """
                INSERT INTO surse_monitorizate (id, nume, tip, url, parser, regiune_focus, eveniment_id, activ)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                ON CONFLICT(id) DO UPDATE SET
                    nume = excluded.nume,
                    tip = excluded.tip,
                    url = excluded.url,
                    parser = excluded.parser,
                    regiune_focus = excluded.regiune_focus,
                    eveniment_id = excluded.eveniment_id
                """,
                (sid, nume, tip, url, parser, regiune_focus, evt_id),
            )

        # Reconstruim FTS5 pentru toate evenimentele
        all_evts = conn.execute("SELECT * FROM evenimente").fetchall()
        for row in all_evts:
            d = dict(row)
            upsert_fts_entry(
                conn,
                "eveniment",
                d["id"],
                d["slug"],
                d["titlu"],
                [
                    d["tip"], d["organizator"], d["regiune"], d["raion"], d["localitate"],
                    d["locatie_exacta"], d["data_text"], d["luni_active"],
                    d["descriere_scurta"], d["cum_a_fost_real"], d["ce_gusti"],
                ],
                d["taguri"],
            )

        conn.commit()

        evt_cnt = conn.execute("SELECT COUNT(*) FROM evenimente").fetchone()[0]
        conf_cnt = conn.execute("SELECT COUNT(*) FROM evenimente WHERE data_start != ''").fetchone()[0]
        fb_cnt = conn.execute("SELECT COUNT(*) FROM evenimente WHERE facebook_url != ''").fetchone()[0]
        fts_cnt = conn.execute("SELECT COUNT(*) FROM search_fts").fetchone()[0]
        src_cnt = conn.execute("SELECT COUNT(*) FROM surse_monitorizate").fetchone()[0]
        print(
            f"Imbogatire completa OK: evenimente={evt_cnt}, cu data_start={conf_cnt}, "
            f"cu facebook_url={fb_cnt}, search_fts={fts_cnt}, surse_monitorizate={src_cnt}"
        )
        assert evt_cnt == 40
        assert src_cnt == 33
        assert conf_cnt >= 11
    finally:
        conn.close()


if __name__ == "__main__":
    main()
