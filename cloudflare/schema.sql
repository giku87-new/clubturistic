DROP TABLE IF EXISTS cautari_istoric;
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
