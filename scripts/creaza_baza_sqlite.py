"""
Script de inițializare a bazei de date SQL relaționale (SQLite) pentru ClubTuristic.md.
Creează schema relațională completă, tabelele cu constrângeri și indecși,
și importă cele 999 de entități din fișierul JSON îmbogățit cu date de calendar și recurență.

Fișierul generat: clubturistic.db (poate fi deschis în DBeaver, SQLiteStudio, VS Code sau conectat la backend).
"""

import sqlite3
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_PATH = os.path.join(BASE_DIR, 'baza_date_turism_evenimente_moldova.json')
DB_PATH = os.path.join(BASE_DIR, 'clubturistic.db')

def init_db():
    print(f"Inițializare bază de date SQLite: {DB_PATH}")
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Activează cheile străine
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. Tabelul de Regiuni
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS regiuni (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nume VARCHAR(50) UNIQUE NOT NULL,
        descriere TEXT
    );
    """)

    # 2. Tabelul de Categorii
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS categorii (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nume VARCHAR(100) UNIQUE NOT NULL,
        tip_organizare VARCHAR(50),
        prioritate_afisare INTEGER DEFAULT 10
    );
    """)

    # 3. Tabelul Principal: Entități (Primării, Consilii, Festivaluri, Crame, Pensiuni)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS entitati (
        id VARCHAR(50) PRIMARY KEY,
        categorie VARCHAR(100) NOT NULL,
        denumire VARCHAR(255) NOT NULL,
        regiune VARCHAR(50) NOT NULL,
        raion_municipiu VARCHAR(100) NOT NULL,
        localitate VARCHAR(100) NOT NULL,
        adresa_completa TEXT,
        conducator_responsabil VARCHAR(150),
        profil_turistic_gastronomic TEXT,
        evenimente_tipice TEXT,
        data_eveniment VARCHAR(150),
        recurenta VARCHAR(255),
        tip_recurenta VARCHAR(100),
        luna VARCHAR(50),
        sezon VARCHAR(50),
        email_contact VARCHAR(150),
        telefon VARCHAR(50),
        website_social TEXT,
        idno_cod_fiscal VARCHAR(20),
        cod_cuatm VARCHAR(10),
        latitudine REAL,
        longitudine REAL,
        rating_mediu REAL DEFAULT 5.0,
        imagine_principala TEXT,
        status_verificare VARCHAR(20) DEFAULT 'Verificat',
        data_creare DATETIME DEFAULT CURRENT_TIMESTAMP,
        data_actualizare DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 4. Tabelul de Evenimente Programate în Calendar
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS evenimente_calendar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entitate_id VARCHAR(50) NOT NULL,
        titlu_eveniment VARCHAR(255) NOT NULL,
        data_start DATE,
        data_sfarsit DATE,
        perioada_anuala VARCHAR(100),
        recurenta VARCHAR(255),
        tip_recurenta VARCHAR(100),
        luna VARCHAR(50),
        sezon VARCHAR(50),
        specific_gastronomic TEXT,
        pret_intrare VARCHAR(50) DEFAULT 'Gratuit',
        locatie_gps VARCHAR(100),
        link_promovare TEXT,
        status_aprobare VARCHAR(20) DEFAULT 'Aprobat',
        FOREIGN KEY (entitate_id) REFERENCES entitati(id) ON DELETE CASCADE
    );
    """)

    # 5. Tabelul de Audit / Jurnal Modificări Admin
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS jurnal_modificari (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entitate_id VARCHAR(50) NOT NULL,
        camp_modificat VARCHAR(50) NOT NULL,
        valoare_veche TEXT,
        valoare_noua TEXT,
        modificat_de VARCHAR(50) DEFAULT 'Admin',
        data_modificare DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Indecși pentru căutare și filtrare ultra-rapidă
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_entitati_regiune ON entitati(regiune);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_entitati_raion ON entitati(raion_municipiu);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_entitati_categorie ON entitati(categorie);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_entitati_cuatm ON entitati(cod_cuatm);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_entitati_idno ON entitati(idno_cod_fiscal);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_entitati_luna ON entitati(luna);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_entitati_sezon ON entitati(sezon);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_entitati_tip_recurenta ON entitati(tip_recurenta);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cal_data_start ON evenimente_calendar(data_start);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cal_luna ON evenimente_calendar(luna);")

    # Ingestie date din JSON
    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        records = json.load(f)

    print(f"Importare {len(records)} entități cu date de recurență...")
    
    insert_sql = """
    INSERT INTO entitati (
        id, categorie, denumire, regiune, raion_municipiu, localitate,
        adresa_completa, conducator_responsabil, profil_turistic_gastronomic,
        evenimente_tipice, data_eveniment, recurenta, tip_recurenta, luna, sezon,
        email_contact, telefon, website_social, idno_cod_fiscal, cod_cuatm
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    for r in records:
        cursor.execute(insert_sql, (
            r['id'],
            r['categorie'],
            r['denumire'],
            r['regiune'],
            r['raion_municipiu'],
            r['localitate'],
            r['adresa_completa'],
            r['conducator_responsabil'],
            r['profil_turistic_gastronomic'],
            r['evenimente_tipice'],
            r.get('data_eveniment', ''),
            r.get('recurenta', ''),
            r.get('tip_recurenta', ''),
            r.get('luna', ''),
            r.get('sezon', ''),
            r['email_contact'],
            r['telefon'],
            r['website_social'],
            r['idno_cod_fiscal'],
            r['cod_cuatm']
        ))

    # Populare automată categorii și regiuni unice
    cursor.execute("""
    INSERT OR IGNORE INTO regiuni (nume)
    SELECT DISTINCT regiune FROM entitati;
    """)

    cursor.execute("""
    INSERT OR IGNORE INTO categorii (nume)
    SELECT DISTINCT categorie FROM entitati;
    """)

    # Populare evenimente cheie în calendar (edițiile 2027)
    evenimente_cheie = [
        ('ORG-ONVV-03', 'Ziua Națională a Vinului (Wine of Moldova)', '2027-10-02', '2027-10-03', 'Primul weekend din Octombrie', 'Anual în primul weekend din Octombrie', 'Recurență relativă', 'Octombrie', 'Toamnă', 'Degustări de vinuri de la peste 90 de vinării, frigărui, plăcinte moldovenești, mămăligă cu friptură', 'Gratuit (Degustări cu Carnet)', 'Piața Marii Adunări Naționale, Chișinău', 'https://wineofmoldova.com'),
        ('ORG-BOSTANIADA-07', 'Festivalul Etno-Gastronomic Bostaniada', '2027-09-25', '2027-09-26', 'Ultimul weekend din Septembrie', 'Anual în ultimul weekend din Septembrie', 'Recurență relativă', 'Septembrie', 'Toamnă', 'Plăcinte cu bostan la cuptor, cremă de dovleac, expoziții de bostani uriași, bucate la ceaun', '70 MDL', 'Agropensiunea Bostaniada, Bălăbănești, Criuleni', 'https://bostaniada.md'),
        ('ORG-DESCOPERA-10', 'DescOperă - Festivalul de Muzică Clasică în aer liber', '2027-06-18', '2027-06-20', 'Al 3-lea weekend din Iunie', 'Anual în al 3-lea weekend din Iunie', 'Recurență relativă', 'Iunie', 'Vară', 'Operă simfonică sub stâncile Butuceniului, degustări de vinuri albe și rosé, plăcinte boierești', '300 - 500 MDL', 'Amfiteatrul Natural Butuceni, Orheiul Vechi', 'https://facebook.com/DescOperaButuceni'),
        ('ORG-GUSTAR-09', 'Gustar Music & Food Festival', '2027-08-20', '2027-08-22', 'Al 3-lea weekend din August', 'Anual în al 3-lea weekend din August', 'Recurență relativă', 'August', 'Vară', 'Aleea Gastronomică Tradițională, plăcinte rumenite, frigărui, vinuri de casă și muzică world', '250 MDL', 'Rezervația Cultural-Naturală Orheiul Vechi', 'https://gustar.md'),
        ('ORG-MAMALIGA-08', 'Festivalul Național al Mămăligii', '2027-05-16', '2027-05-16', 'A 3-a duminică din Mai', 'Anual în a 3-a duminică din Mai', 'Recurență relativă', 'Mai', 'Primăvară', 'Mămăligă gigantică răsturnată la ceaun, friptură de porc/iepure, tocăniță de ciuperci, brânză de oi', 'Gratuit', 's. Selemet, rl. Cimișlia', 'https://facebook.com/festivalulmamaligii'),
        ('APL1-1007601008007', 'Hramul Orașului Ceadîr-Lunga / Sărbătoarea Tradițională Kasîm', '2027-11-08', '2027-11-08', '8 Noiembrie', 'Anual pe 8 Noiembrie (Kasîm de Sf. Dumitru)', 'Dată fixă anuală', 'Noiembrie', 'Toamnă', 'Kavurma fierbinte de berbecuț la ceaun, plăcinte gőzleme calde, bulgur tradițional, vin roșu găgăuz', 'Gratuit', 'Piața Centrală & Hipodromul AT-ProLin, Ceadîr-Lunga', 'https://ceadir-lunga.md'),
        ('ORG-GAGAUZ-HEDERLEZ-19', 'Sărbătoarea Națională Primăvăratică Hederlez', '2027-05-06', '2027-05-06', '6 Mai', 'Anual pe 6 Mai', 'Dată fixă anuală', 'Mai', 'Primăvară', 'Curse de cai de rasă orlov, bulgur cu carne de miel, brânză de burduf, dansuri găgăuze', 'Gratuit', 'Hipodromul AT-ProLin, Ceadîr-Lunga', 'https://ugagauzia.md'),
        ('APL1-1007601009484', 'Hramul Municipiului Chișinău', '2027-10-14', '2027-10-14', '14 Octombrie', 'Anual pe 14 Octombrie (Acoperământul Maicii Domnului)', 'Dată fixă anuală', 'Octombrie', 'Toamnă', 'Curți gastronomice pe bulevardul Ștefan cel Mare, plăcinte moldovenești, mici, vin din toate raioanele', 'Gratuit', 'bd. Ștefan cel Mare și Sfânt, Chișinău', 'https://chisinau.md'),
        ('APL1-1007601008007', 'Hramul Municipiului Orhei', '2027-11-08', '2027-11-08', '8 Noiembrie', 'Anual pe 8 Noiembrie (Sf. Dumitru)', 'Dată fixă anuală', 'Noiembrie', 'Toamnă', 'Mămăligă cu brânză și smântână, plăcinte boierești, sarmale la cuptor, spectacole folclorice', 'Gratuit', 'Piața Vasile Lupu, mun. Orhei', 'https://orhei.md'),
        ('ORG-SOROCA-MERE-13', 'Festivalul Național al Mărului', '2027-09-26', '2027-09-26', 'Ultima duminică din Septembrie', 'Anual în ultima duminică din Septembrie', 'Recurență relativă', 'Septembrie', 'Toamnă', 'Expoziție pomicolă de soiuri de mere de pe malul Nistrului, plăcinte cu mere și scorțișoară, cidru', 'Gratuit', 'Cetatea Soroca & Piața Libertății, mun. Soroca', 'https://soroca.org.md'),
        ('ORG-NISPORENI-PRUNE-12', 'Festivalul Național al Prunei', '2027-09-19', '2027-09-19', 'A 3-a duminică din Septembrie', 'Anual în a 3-a duminică din Septembrie', 'Recurență relativă', 'Septembrie', 'Toamnă', 'Magiun proaspăt fiert la ceaun, prune uscate umplute cu nuci, plăcinte cu prune, țuică', 'Gratuit', 'Piața Ștefan cel Mare, or. Nisporeni', 'https://nisporeni.md'),
        ('ORG-VORNICENI-SARMA-31', 'Festivalul Sarmalei și al Pitei de Casă', '2027-10-10', '2027-10-10', 'A 2-a duminică din Octombrie', 'Anual în a 2-a duminică din Octombrie', 'Recurență relativă', 'Octombrie', 'Toamnă', 'Sarmale în foi de viță și varză acră, pită de casă coaptă pe vatră, plăcinte cu varză și brânză', 'Gratuit', 's. Vorniceni, rl. Strășeni', 'https://straseni.md'),
        ('ORG-SADOVA-CAPSUNI-14', 'Festivalul Căpșunilor și Mierii', '2027-06-06', '2027-06-06', 'Prima duminică din Iunie', 'Anual în prima duminică din Iunie', 'Recurență relativă', 'Iunie', 'Vară', 'Căpșuni proaspete din Codri, miere de salcâm curată, tarte de casă cu căpșuni, vin spumant', 'Gratuit', 's. Sadova, rl. Călărași', 'https://calarasi.md'),
        ('ORG-TUDORA-PIERSICI-15', 'Festivalul Piersicului - Hai la piersici la Tudora', '2027-07-25', '2027-07-25', 'Ultima duminică din Iulie', 'Anual în ultima duminică din Iulie', 'Recurență relativă', 'Iulie', 'Vară', 'Piersici aromate de pe malul Nistrului, compoturi, dulcețuri, ciorbă de pește nistreană la ceaun', 'Gratuit', 's. Tudora, rl. Ștefan Vodă', 'https://facebook.com/FestivalulPiersiculuiTudora'),
        ('ORG-VALENI-COZONACI-16', 'Festivalul Național Hai la Cozonaci', '2027-05-09', '2027-05-09', 'A 2-a duminică după Paște', 'Anual în a 2-a duminică după Paștele Ortodox', 'Recurență relativă', 'Mai', 'Primăvară', 'Cozonaci rumeniți la cuptor pe lemne, plăcinte poale-n brâu, dulceți de nuci verzi din Lunca Prutului', 'Gratuit', 'Rezervația Biosferei UNESCO Prutul de Jos, s. Văleni, rl. Cahul', 'https://valeni.md'),
        ('ORG-CLISOVA-COVOR-17', 'Festivalul Național Frumos Covor Basarabean', '2027-06-20', '2027-06-20', 'A 3-a duminică din Iunie', 'Anual în a 3-a duminică din Iunie', 'Recurență relativă', 'Iunie', 'Vară', 'Bucate coapte la cuptorul strămoșesc, învârtite cu brânză de oi, ateliere de țesut la război', 'Gratuit', 'Complexul Arta Rustică, s. Clișova Nouă, rl. Orhei', 'https://artarustica.md'),
        ('ORG-HOGINESTI-OLARIT-18', 'Târgul Internațional al Olarilor La Vatra Olarului', '2027-07-18', '2027-07-18', 'A 3-a duminică din Iulie', 'Anual în a 3-a duminică din Iulie', 'Recurență relativă', 'Iulie', 'Vară', 'Ghiveci și fasole fierte lent în oale arse de lut, plăcinte moldovenești, modelat lut la roată', 'Gratuit', 'Casa Olarului Vasilii Gonciari, s. Hoginești, rl. Călărași', 'https://casaolarului.md'),
        ('ORG-CORJEUTI-CARTOFI-32', 'Festivalul Cartofului din Corjeuți', '2027-09-12', '2027-09-12', 'A 2-a duminică din Septembrie', 'Anual în a 2-a duminică din Septembrie', 'Recurență relativă', 'Septembrie', 'Toamnă', 'Peste 30 de feluri de mâncare din cartofi, plăcinte cu cartofi, clătite și friptură de casă', 'Gratuit', 's. Corjeuți, rl. Briceni', 'https://briceni.md'),
        ('WIN-CASTEL-MIMI-20', 'Rosé Day la Castel Mimi', '2027-06-12', '2027-06-12', 'A 2-a sâmbătă din Iunie', 'Anual în a 2-a sâmbătă din Iunie', 'Recurență relativă', 'Iunie', 'Vară', 'Vinuri rosé premiate internațional, bucătărie gourmet la grătar pe lemne, muzică live la piscină', '350 MDL', 'Castel Mimi Wine Resort, s. Bulboaca, rl. Anenii Noi', 'https://castelmimi.md'),
        ('WIN-CRICOVA-21', 'Underland Wine & Music Festival', '2027-02-20', '2027-02-20', 'A 3-a sâmbătă din Februarie', 'Anual în a 3-a sâmbătă din Februarie', 'Recurență relativă', 'Februarie', 'Iarnă', 'Degustări subterane de vin spumant și vinuri roșii în galeriile de piatră, gustări tradiționale', '350 MDL', 'Combinatul Cricova, or. Cricova', 'https://cricova.md'),
        ('ORG-SIPOTENI-ZEAMA-34', 'Festivalul Național al Zemii (ediția a XI-a)', '2027-08-08', '2027-08-08', 'A 2-a duminică din August', 'Anual în a 2-a duminică din August', 'Recurență relativă', 'August', 'Vară', 'Zeamă fierbinte de găină cu tăieței frământați manual și borș acru preparată la peste 30 de ceaune, plăcinte călărășene, vin de casă', 'Gratuit', 'Poiana „La Sălcii”, com. Sipoteni, rl. Călărași', 'https://facebook.com/FestivalulZemiiSipoteni'),
        ('ORG-DUBASARI-PESTE-36', 'Festivalul Peștelui și al Zemei Pescărești la Nistru', '2027-07-11', '2027-07-11', 'Al 2-lea weekend din Iulie', 'Anual în al 2-lea weekend din Iulie', 'Recurență relativă', 'Iulie', 'Vară', 'Zeamă pescărească de pește la ceaun cu ardei iute și mujdei de usturoi, pește prăjit la tablă cu mămăligă', 'Gratuit', 's. Dubăsarii Vechi (malul Nistrului), rl. Criuleni', 'https://criuleni.md')
    ]

    cal_insert_sql = """
    INSERT INTO evenimente_calendar (
        entitate_id, titlu_eveniment, data_start, data_sfarsit,
        perioada_anuala, recurenta, tip_recurenta, luna, sezon,
        specific_gastronomic, pret_intrare, link_promovare
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    for ev in evenimente_cheie:
        cursor.execute(cal_insert_sql, (
            ev[0], ev[1], ev[2], ev[3], ev[4], ev[5], ev[6], ev[7], ev[8], ev[9], ev[10], ev[12]
        ))

    conn.commit()

    # Verificare
    cursor.execute("SELECT COUNT(*) FROM entitati;")
    count_entitati = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM categorii;")
    count_categorii = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM regiuni;")
    count_regiuni = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM evenimente_calendar;")
    count_cal = cursor.fetchone()[0]

    print("\n✅ Baza de date relațională SQLite a fost creată cu succes!")
    print(f"   - Total Entități importate: {count_entitati}")
    print(f"   - Evenimente programate în Calendar: {count_cal}")
    print(f"   - Total Categorii clasificate: {count_categorii}")
    print(f"   - Total Regiuni mapate: {count_regiuni}")
    print(f"   - Dimensiune fișier: {os.path.getsize(DB_PATH) / 1024:.1f} KB")

    conn.close()

if __name__ == '__main__':
    init_db()
