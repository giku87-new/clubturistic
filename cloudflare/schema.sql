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
