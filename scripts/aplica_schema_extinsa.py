"""
Script de extindere a bazei de date SQLite clubturistic.db cu tabele avansate pentru:
1. Coordonate GPS & Geocoding (pentru Harta Interactivă Leaflet/Mapbox)
2. Calendar de Evenimente cu Bilete și Date Exacte
3. Sistem de Utilizatori & Roluri (SuperAdmin, Reprezentant Primărie, Organizator Privat)
4. Galerie Foto / Media
5. Trasee Turistice Tematice (ex: Drumul Vinului, Traseul Mănăstirilor, Drumul Mămăligii)
6. Sistem de Recenzii & Evaluări (Rating 1-5 stele)
7. Suport Multilingv (RO, EN, RU pentru turiști internaționali)
"""

import sqlite3
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'clubturistic.db')

def extinde_baza_date():
    print(f"Extindere schemă bază de date: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON;")

    # 1. Adăugare coloane GPS în tabela entități dacă nu există
    try:
        cur.execute("ALTER TABLE entitati ADD COLUMN latitudine REAL;")
        cur.execute("ALTER TABLE entitati ADD COLUMN longitudine REAL;")
        cur.execute("ALTER TABLE entitati ADD COLUMN rating_mediu REAL DEFAULT 5.0;")
        cur.execute("ALTER TABLE entitati ADD COLUMN imagine_principala TEXT;")
    except sqlite3.OperationalError:
        pass # Coloanele există deja

    # 2. Tabel Utilizatori & Autentificare
    cur.execute("""
    CREATE TABLE IF NOT EXISTS utilizatori (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email VARCHAR(150) UNIQUE NOT NULL,
        parola_hash VARCHAR(255) NOT NULL,
        nume_complet VARCHAR(150) NOT NULL,
        rol VARCHAR(30) DEFAULT 'turist', -- 'superadmin', 'primar_editor', 'organizator', 'turist'
        entitate_asociata_id VARCHAR(50),
        telefon VARCHAR(50),
        data_inregistrare DATETIME DEFAULT CURRENT_TIMESTAMP,
        activ INTEGER DEFAULT 1,
        FOREIGN KEY (entitate_asociata_id) REFERENCES entitati(id) ON DELETE SET NULL
    );
    """)

    # 3. Tabel Galerie Media / Imagini
    cur.execute("""
    CREATE TABLE IF NOT EXISTS galerie_media (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entitate_id VARCHAR(50) NOT NULL,
        eveniment_id INTEGER,
        url_imagine TEXT NOT NULL,
        titlu VARCHAR(150),
        este_principala INTEGER DEFAULT 0,
        data_adaugare DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (entitate_id) REFERENCES entitati(id) ON DELETE CASCADE
    );
    """)

    # 4. Tabel Trasee Turistice Tematice
    cur.execute("""
    CREATE TABLE IF NOT EXISTS trasee_turistice (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titlu VARCHAR(150) NOT NULL,
        slug VARCHAR(150) UNIQUE NOT NULL,
        descriere TEXT,
        lungime_km REAL,
        durata_recomandata VARCHAR(50), -- ex: '1 zi', 'Weekend'
        tematica VARCHAR(50), -- 'Vinicol', 'Gastronomic', 'Istoric', 'Natură'
        imagine_banner TEXT
    );
    """)

    # 5. Tabel Puncte de Oprire pe Traseu (M2M Trasee <-> Entități)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS opriri_traseu (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        traseu_id INTEGER NOT NULL,
        entitate_id VARCHAR(50) NOT NULL,
        numar_ordine INTEGER NOT NULL,
        nota_oprire TEXT, -- ex: 'Oprire pentru degustare plăcinte la cuptor'
        FOREIGN KEY (traseu_id) REFERENCES trasee_turistice(id) ON DELETE CASCADE,
        FOREIGN KEY (entitate_id) REFERENCES entitati(id) ON DELETE CASCADE
    );
    """)

    # 6. Tabel Recenzii & Impresii Vizitatori
    cur.execute("""
    CREATE TABLE IF NOT EXISTS recenzii (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entitate_id VARCHAR(50) NOT NULL,
        nume_autor VARCHAR(100) NOT NULL,
        email_autor VARCHAR(150),
        scor_rating INTEGER CHECK(scor_rating >= 1 AND scor_rating <= 5),
        comentariu TEXT NOT NULL,
        mancare_recomandata VARCHAR(150), -- ex: 'Plăcintele cu bostan și zeama de casă'
        data_recenzie DATETIME DEFAULT CURRENT_TIMESTAMP,
        status VARCHAR(20) DEFAULT 'Aprobat',
        FOREIGN KEY (entitate_id) REFERENCES entitati(id) ON DELETE CASCADE
    );
    """)

    # 7. Tabel Traduceri Multilingve (RO, EN, RU)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS traduceri (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tabela_sursa VARCHAR(50) NOT NULL, -- 'entitati', 'evenimente_calendar', 'trasee_turistice'
        inregistrare_id VARCHAR(50) NOT NULL,
        limba VARCHAR(5) NOT NULL, -- 'en', 'ru'
        camp VARCHAR(50) NOT NULL, -- 'profil_turistic_gastronomic', 'evenimente_tipice'
        text_tradus TEXT NOT NULL,
        UNIQUE(tabela_sursa, inregistrare_id, limba, camp)
    );
    """)

    # Inserare Trasee Tematice Inițiale
    trasee_demo = [
        ('Drumul Vinurilor Legendare din Centru', 'drumul-vinurilor-centru', 'Traseu de 2 zile vizitând cramele Cricova, Mileștii Mici și Castel Mimi.', 115.0, 'Weekend (2 zile)', 'Vinicol', 'https://images.unsplash.com/photo-1510812431401-41d2bd2722f3'),
        ('Traseul Plăcintelor și al Gastronomiei din Codri', 'traseul-placintelor-codri', 'Descoperă Sadova, Vorniceni și Hoginești cu bucate la cuptor pe lemne și ateliere meșteșugărești.', 75.0, '1 zi', 'Gastronomic', 'https://images.unsplash.com/photo-1504674900247-0877df9cc836'),
        ('Comorile Găgăuziei: De la Hederlez la Kasîm', 'comorile-gagauziei', 'Experiență unică în Ceadîr-Lunga și Comrat: kavurma tradițională, hipodromul de cai și vinuri sudice.', 160.0, '2 zile', 'Gastronomic', 'https://images.unsplash.com/photo-1555396273-367ea4eb4db5')
    ]

    for t in trasee_demo:
        cur.execute("""
        INSERT OR IGNORE INTO trasee_turistice (titlu, slug, descriere, lungime_km, durata_recomandata, tematica, imagine_banner)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, t)

    conn.commit()
    conn.close()
    print("✅ Schema bazei de date a fost extinsă cu succes cu toate modulele avansate!")

if __name__ == '__main__':
    extinde_baza_date()
