# AGENT_MEMORY.md - Memoria Operațională a Proiectului "Club Turistic Moldova"

> **IMPORTANT PENTRU AGENȚI AI**: Acest fișier servește drept punct de pornire și memorie persistentă pentru orice agent AI care lucrează în acest depozit (`c:\Users\geo\OneDrive\Documents\clubturistic.md`). Citiți acest fișier înainte de a efectua modificări sau de a continua dezvoltarea portalului.

---

## 1. Misiunea Proiectului
Construirea portalului web **Club Turistic Moldova** (`clubturistic.md`) dedicat promovării turismului experiențial din Republica Moldova, cu accent deosebit pe:
- **Evenimente locale, festivaluri și hramuri**: Evenimente la care oamenii vin să viziteze locuri deosebite, să asculte muzică autentică și să descopere tradiții.
- **Calendar de Recurență Exactă**: Fiecare eveniment include data exactă sau formula de recurență calendaristică (ex: *„a 3-a duminică din Mai”*, *„primul weekend din Octombrie”*, hramurile ecleziastice anuale, sau programe permanente).
- **Turism Gastronomic & Oenologic**: Locuri unde se mănâncă gustos, autentic și deosebit (bucătărie tradițională la cuptor de lut, plăcinte, sarmale, mămăligă, zeamă de casă, deserturi specifice, bucătărie etnică găgăuză/bulgară) și crame de renume mondial.
- **Rețeaua Națională de Contacte**: Conectarea directă cu toate cele **897 de primării**, **34 de consilii raionale/municipale**, direcțiile de cultură și organizatorii privați/asociațiile de profil.

---

## 2. Structura Depozitului și Fișiere Cheie

```
clubturistic.md/
├── baza_date_turism_evenimente_moldova.csv    # Fișierul principal (UTF-8 cu BOM, 999 entități, 20 coloane)
├── baza_date_turism_evenimente_moldova.json   # Versiunea JSON structurată pentru API-uri & agenți
├── clubturistic.db                            # Bază de date relațională SQLite (11 tabele extinse)
├── server.py                                  # Server HTTP & REST API (GET, POST, PUT, DELETE pe port 8080)
├── index.html                                 # Interfața publică a portalului turistic (cu filtre temporale)
├── admin.html                                 # Panoul Web de Administrare a Bazei de Date (cu editare recurență)
├── Dockerfile & docker-compose.yml            # Containerizare pentru lansare pe orice server/VPS
├── AGENT_MEMORY.md                            # Prezentul fișier de memorie și context operațional
├── README.md                                  # Prezentare generală a depozitului
├── data_source/
│   └── noiembrie_2026.xlsx                    # Registrul de Stat oficial ASP / dataset.gov.md
├── docs/
│   ├── DOCUMENTATIE_BAZA_DATE.md              # Dicționar de date, taxonomii și coduri CUATM
│   ├── ARHITECTURA_PORTAL_TURISM.md           # Plan de arhitectură, componente și roadmap portal
│   ├── ARHITECTURA_EXTINSA.md                 # Arhitectura scalabilă și posibilitățile de extindere
│   └── GHID_DEPLOY.md                         # Ghid detaliat de deploy (Render, cPanel, VPS/Docker)
├── scripts/
│   ├── creaza_baza_sqlite.py                  # Inițializator SQLite din JSON (populează entități & calendar)
│   ├── aplica_schema_extinsa.py               # Extindere schemă (trasee, opriri, recenzii, traduceri)
│   ├── genereaza_baza_date.py                 # Scriptul master de extracție, clasificare și îmbogățire
│   ├── build_dynamic_portal.py                # Generator frontend index.html cu suport pentru recurență
│   ├── creaza_admin_panel.py                  # Generator panou admin.html cu sincronizare SQLite
│   ├── export_json.py                         # Exportator CSV -> JSON
│   └── interogheaza_turism.py                 # Utilitar CLI de căutare flexibilă (fără/cu diacritice)
└── .agent/
    └── skills/
        └── turism-moldova/
            └── SKILL.md                       # Skill Antigravity cu reguli de domeniu și asistență
```

---

## 3. Schema Bazei de Date (20 de Câmpuri)

Fiecare înregistrare din CSV, JSON și SQLite conține 20 de câmpuri standardizate:

| Câmp | Tip | Descriere | Exemplu |
|---|---|---|---|
| `id` | String | Identificator unic formatat | `APL1-1007601000285`, `ORG-BOSTANIADA-07`, `WIN-CASTEL-MIMI-20` |
| `categorie` | String | Taxonomie entitate | `Primărie (APL I)`, `Consiliu Raional / Municipal (APL II)`, `Organizator Festival Gastronomic` |
| `denumire` | String | Numele complet oficial | `PRIMĂRIA MUNICIPIULUI CEADÎR-LUNGA`, `Castel Mimi Wine Resort` |
| `regiune` | String | Regiunea istorică/geografică | `Centru`, `Nord`, `Sud`, `Chișinău`, `UTA Găgăuzia`, `Transnistria` |
| `raion_municipiu` | String | Raionul sau municipiul | `Orhei`, `Cahul`, `Strășeni`, `Călărași`, `Soroca`, `UTA Găgăuzia` |
| `localitate` | String | Localitatea reședință | `mun. Ceadîr-Lunga`, `s. Butuceni`, `mun. Chișinău` |
| `adresa_completa` | String | Adresa poștală sau juridică | `UTA Găgăuzia, mun. Ceadîr-Lunga, str. Lenin 91` |
| `conducator_responsabil` | String | Nume conducător / persoană contact | `Primar / Președinte raion / Director` |
| `profil_turistic_gastronomic` | String | Profil culinar și atractivitate | Plăcinte, kavurma, gozleme, vinuri, mămăligă, sarmale la cuptor |
| `evenimente_tipice` | String | Evenimente majore organizate | `Hramul Satului, Festivalul Mămăligii, Degustări de vin` |
| `data_eveniment` | String | Data sau reperul temporal | `8 Noiembrie`, `14 Octombrie`, `A 3-a duminică din Mai` |
| `recurenta` | String | Formula exactă de recurență | `Anual în a 3-a duminică din Mai (Festivalul Național al Mămăligii)` |
| `tip_recurenta` | String | Tipul tiparului temporal | `Recurență relativă`, `Dată fixă anuală`, `Permanent / La cerere` |
| `luna` | String | Luna principală | `Noiembrie`, `Octombrie`, `Mai`, `August`, `Septembrie`, `Tot anul` |
| `sezon` | String | Anotimpul propice | `Toamnă`, `Vară`, `Primăvară`, `Iarnă`, `Permanent` |
| `email_contact` | String | Email instituțional sau oficial | `primaria.ceadirlunga@apl.gov.md` |
| `telefon` | String | Telefon secretariat/evenimente | `+373 291 22 509` |
| `website_social` | String | Website oficial / Pagina Facebook | `https://ceadir-lunga.md` |
| `idno_cod_fiscal` | String | Codul fiscal unic (13 cifre) | `1007601008007` |
| `cod_cuatm` | String | Codul statistic teritorial (4 cifre) | `9602` |

---

## 4. Tipare de Recurență Implementate

1. **Recurență Relativă**:
   - `A 3-a duminică din Mai`: Festivalul Național al Mămăligii (Selemet), Festivalul Mai Dulce (Chișinău).
   - `Primul weekend din Octombrie`: Ziua Națională a Vinului (Wine of Moldova) la Chișinău & etape raionale.
   - `Ultimul weekend din Septembrie`: Festivalul Etno-Gastronomic Bostaniada (Criuleni).
   - `A 3-a duminică din Septembrie`: Festivalul Național al Prunei (Nisporeni).
   - `Ultima duminică din Septembrie`: Festivalul Național al Mărului (Soroca).
   - `Al 3-lea weekend din Iunie`: Festivalul de Muzică Clasică DescOperă Butuceni (Orheiul Vechi).
   - `Al 3-lea weekend din August`: Gustar Music & Food Festival.
   - `A 2-a duminică din Octombrie`: Festivalul Sarmalei și al Pitei de Casă (Vorniceni).
   - `Prima duminică din Iunie`: Festivalul Căpșunilor și Mierii (Sadova).
   - `A 3-a duminică din Iulie`: Târgul Internațional al Olarilor La Vatra Olarului (Hoginești).
   - `A 2-a duminică după Paște`: Festivalul Hai la Cozonaci (Văleni).
   - `Prima duminică din Noiembrie`: Gagauz Sarap Yortusu (Festivalul Vinului Găgăuz la Comrat).

2. **Hramuri Creștin-Ortodoxe (Date Fixe Anuale)**:
   - `8 Noiembrie`: Hramul Orașului Ceadîr-Lunga (Sărbătoarea Tradițională Kasîm de Sf. Dumitru), Orhei etc.
   - `14 Octombrie`: Hramul Municipiului Chișinău (Acoperământul Maicii Domnului), Rezina, Briceni etc.
   - `21 Noiembrie`: Hramul Municipiului Cahul (Sf. Arhangheli Mihail și Gavriil), Hîncești etc.
   - `28 August`: Hramul Municipiului Soroca (Adormirea Maicii Domnului / Uspenia), Ungheni etc.
   - `22 Mai`: Hramul Municipiului Bălți (Sf. Nicolae de Vară), Criuleni, Fălești etc.
   - `6 Mai`: Sărbătoarea Hederlez (Ceadîr-Lunga), Taraclia (Sf. Gheorghe).

3. **Permanent / La Cerere**:
   - Marile crame (Cricova, Mileștii Mici, Castel Mimi, Purcari, Château Vartely, Asconi, Et Cetera, Poiana, Kara Gani) deschise pe tot parcursul anului.

---

## 5. Ghid de Servicii Web & API

Serverul local `server.py` rulează pe portul `8080`:
- **Portal Public**: `http://localhost:8080/`
- **Panou Admin**: `http://localhost:8080/admin`
- **REST API Entități**: `http://localhost:8080/api/entitati` (suportă parametri `q`, `regiune`, `categorie`, `raion`, `luna`, `sezon`, `tip_recurenta`, `limit`, `offset`)
- **REST API Calendar**: `http://localhost:8080/api/calendar` (returnează evenimentele programate cu reguli de recurență)
- **REST API Stats**: `http://localhost:8080/api/stats` (statistici în timp real pe categorii, regiuni, sezoane și luni)

## GitHub / Deploy & Monitorizare v4 (Backend Local Incremental)
- **Repo:** https://github.com/giku87-new/clubturistic (user `giku87-new`). Autentificare salvată în Windows Credential Manager (`git`) — NU cere din nou tokenul și NU scrie tokenuri sau parole în fișiere.
- **Cloudflare LIVE (Worker Pasiv, fără Cron Triggers):** https://clubturistic.clubturistic.workers.dev (Admin: `/admin`). Cont `ro.gfrunza@gmail.com`, D1 `clubturistic-db`, KV `clubturistic-media`, subdomain `clubturistic`, Worker `clubturistic`. `CLOUDFLARE_API_TOKEN` și `CLOUDFLARE_ACCOUNT_ID` sunt salvate în variabilele de mediu de utilizator Windows (NU le scrie niciodată în repo). Site-ul public NU face scraping/căutări în cloud; servește strict portalul, API-ul și `/admin`.
- **Schema v4 (`cloudflare/schema.sql` & `clubturistic.db`):**
  - `evenimente` (40 evenimente): include `data_start`, `data_end`, `facebook_url`, `instagram_url`, `bilete_url`, `ultima_verificare_la`, `sursa_confirmarii`.
  - `locatii` (18 locații): include `facebook_url`, `instagram_url`.
  - `hramuri_notabile` (7 hramuri) & `search_fts` (65 intrări FTS5).
  - Tabele de monitorizare locală: `surse_monitorizate` (39 surse: 29 feeduri/agende/Telegram/site-uri HTTP automate cu 0 tokeni AI + 10 pagini Facebook oficiale acoperite prin interogări web programate), `surse_articole_vazute` (registru SHA-256 cu deduplicare incrementală), `cautari_istoric` (6 interogări rare, max 2/zi, recurență 7–14 zile), `actualizari_detectate` (coadă locală de verificare), `monitor_runs` (istoric rulări).
- **Backend Local Incremental (`scripts/`):**
  - Deduplicare incrementală prin `ETag` / `If-Modified-Since`, `next_check_at`, fereastră sezonieră (`luni_fereastra`) și registru SHA-256 `surse_articole_vazute`.
  - `scripts/crawl_local.py`: colectare HTTP locală (0 tokeni AI) + export `data/review_queue.md` și `data/new_candidates.json`.
  - `scripts/apply_review_triage.py`: triere coadă locală (`--ignore`, `--approve`, `--add-finding`, `--mark-query-done`).
  - `scripts/publish_cloudflare.py`: deploy controlat pe Cloudflare Workers/D1/KV exclusiv după verificarea și aprobarea utilizatorului.
- **Automatizare Antigravity (`ClubTuristic Daily Event Monitor`):** Rulează zilnic la `09:00 Europe/Chisinau`, mod economic (fast-exit când `NEW_CANDIDATES=0` și `DUE_WEB_QUERIES=[]`), fără auto-deploy.
- **REGULĂ PENTRU AGENȚI VIITORI:** Nu repetați căutări pe surse/articole deja aflate în `surse_articole_vazute` sau `cautari_istoric` (`next_due_at`), nu mutați crawlingul în Cloudflare Worker și nu faceți deploy pe Cloudflare fără acordul explicit al utilizatorului.
