# Club Turistic Moldova (`clubturistic.md`)

Portal dedicat promovării turismului, festivalurilor și gastronomiei autentice din Republica Moldova.

---

## 📌 Ce conține acest depozit?

1. **Baza de Date Națională Turistică & Administrativă**:
   - [`baza_date_turism_evenimente_moldova.csv`](baza_date_turism_evenimente_moldova.csv): **999 de entități** organizate cu cap, compatibil 100% cu Excel (UTF-8 cu BOM), conținând:
     - Toate cele **897 de primării active (APL I)** din Republica Moldova;
     - Toate cele **34 de consilii raionale & municipale (APL II)**;
     - **36 de direcții și secții raionale de cultură și turism**;
     - Organizatorii festivalurilor mari culinare (Bostaniada, Festivalul Mămăligii, Festivalul Prunei, Festivalul Mărului, Festivalul Căpșunilor, IA MANIA, Gustar, DescOperă etc.);
     - Domeniile vinicole și cramele de top (Castel Mimi, Cricova, Mileștii Mici, Château Vartely, Purcari, Asconi, Et Cetera, Poiana, Kara Gani);
     - Pensiuni rurale de referință și meșteșugari (Butuceni, Văleni, Arta Rustică, Casa Olarului Vasilii Gonciari).
   - [`baza_date_turism_evenimente_moldova.json`](baza_date_turism_evenimente_moldova.json): Versiunea JSON structurată pentru aplicații web, API-uri și procesare de către agenți AI.

2. **Instrumente și Scripturi Utile (`scripts/`)**:
   - `interogheaza_turism.py`: Căutare rapidă flexibilă în linia de comandă (insensibilă la diacritice) după mâncăruri, festivaluri, regiuni sau raioane.
   - `genereaza_baza_date.py`: Script master care re-descarcă datele din Registrul de Stat deschis al Guvernului (`dataset.gov.md`), parsează clasificatorul CUATM și regenerează fișierele.
   - `export_json.py`: Utilitar de export rapid CSV -> JSON.

3. **Documentație și Arhitectură (`docs/`)**:
   - [`docs/DOCUMENTATIE_BAZA_DATE.md`](docs/DOCUMENTATIE_BAZA_DATE.md): Dicționar complet de date, explicația fiecărei coloane și a codurilor CUATM.
   - [`docs/ARHITECTURA_PORTAL_TURISM.md`](docs/ARHITECTURA_PORTAL_TURISM.md): Viziunea portalului, harta gastronomică interactivă și foaia de parcurs (roadmap).
   - [`AGENT_MEMORY.md`](AGENT_MEMORY.md): Memoria operațională detaliată pentru ca orice agent AI viitor să poată continua lucrul imediat.

---

## 🚀 Exemple Rapide de Utilizare

```bash
# Statistici generale despre date
python scripts/interogheaza_turism.py --stats

# Unde găsim evenimente cu plăcinte sau bucate tradiționale?
python scripts/interogheaza_turism.py --termen placinte

# Ce evenimente sau crame sunt în raionul Orhei?
python scripts/interogheaza_turism.py --raion Orhei

# Căutare evenimente gastronomice din Sudul Moldovei
python scripts/interogheaza_turism.py --regiune Sud --termen vin
```
