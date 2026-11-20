---
name: turism-moldova
description: Expert skill for querying, updating, and building features for the Moldovan Tourism and Gastronomy Portal (clubturistic.md). Contains geographic knowledge, APL structure, and event calendars.
---

# Skill: Turism și Evenimente Gastronomice în Republica Moldova

Acest skill oferă oricărui agent AI cunoștințe complete despre geografia, administrația publică locală (APL), gastronomia tradițională și evenimentele turistice din Republica Moldova.

## Când se activează acest skill
- Când utilizatorul solicită informații despre primării, sate sau raioane din Moldova.
- Când se adaugă sau se interoghează festivaluri culinare (mămăligă, plăcinte, vin, fructe).
- Când se dezvoltă sau se îmbunătățește portalul `clubturistic.md`.

## Resurse Locale Disponibile în Workspace
1. `baza_date_turism_evenimente_moldova.csv` - 999 de înregistrări complete (primării, consilii raionale, festivaluri, crame, meșteșugari).
2. `baza_date_turism_evenimente_moldova.json` - Format JSON optimizat pentru API-uri și procesare directă.
3. `scripts/interogheaza_turism.py` - Utilitar CLI pentru căutări insensibile la diacritice:
   ```bash
   python scripts/interogheaza_turism.py --termen placinte
   python scripts/interogheaza_turism.py --raion Orhei
   python scripts/interogheaza_turism.py --stats
   ```
4. `scripts/genereaza_baza_date.py` - Scriptul master pentru regenerarea bazei de date din surse oficiale deschise.

## Regiuni și Specific Turistic
- **Centru** (Codrii, Orheiul Vechi, Cricova, Mileștii Mici, Călărași, Strășeni): Focus pe enoturism, agropensiuni, mănăstiri rupestre, festivaluri de operă și etnomuzică, ceramică tradițională (Hoginești).
- **Nord** (Soroca, Edineț, Briceni, Glodeni, Bălți): Cetatea Soroca, livezi de mere, Festivalul Cartofului (Corjeuți), stâncile Prutului ("Toltrele Prutului"), meșteșuguri populare.
- **Sud** (Cahul, Cimișlia, Ștefan Vodă, Leova, Cantemir): Lunca Prutului de Jos (UNESCO), podgoriile Purcari & Crocmaz, Festivalul Mămăligii (Selemet), ciorba de pește și cozonacii tradiționali (Văleni).
- **UTA Găgăuzia** (Comrat, Ceadîr-Lunga, Vulcănești): Specific etnogastronomic autentic: shorpa de berbec, kavurma, gozleme, Festivalul Hederlez și Gagauz Sarap Yortusu, crama Kara Gani.
- **Chișinău**: Evenimente naționale majore: Ziua Națională a Vinului (Piața Marii Adunări Naționale), Vernisajul Vinului, festivaluri urbane de street food.
