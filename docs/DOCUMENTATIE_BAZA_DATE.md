# Documentația Tehnică a Bazei de Date: Turism, Gastronomie, Recurență & APL Moldova

Fișierul principal: [`baza_date_turism_evenimente_moldova.csv`](file:///c:/Users/geo/OneDrive/Documents/clubturistic.md/baza_date_turism_evenimente_moldova.csv)  
Versiunea JSON: [`baza_date_turism_evenimente_moldova.json`](file:///c:/Users/geo/OneDrive/Documents/clubturistic.md/baza_date_turism_evenimente_moldova.json)  
Baza de date SQLite: [`clubturistic.db`](file:///c:/Users/geo/OneDrive/Documents/clubturistic.md/clubturistic.db)

---

## 1. Originea și Calitatea Datelor

Baza de date reunește date din trei mari categorii de surse oficiale și din teren:
1. **Registrul de Stat al Unităților de Drept din Republica Moldova**:
   - Gestionat de **Agenția Servicii Publice (ASP)** și publicat pe portalul de date deschise [dataset.gov.md](https://dataset.gov.md).
   - Setul de date oficial extras: `Date din Registrul de stat al unităţilor de drept privind organele centrale de specialitate ale administraţiei publice şi autorităţilor publice locale (noiembrie 2026)`.
   - Conține toate cele **897 de primării active** și autoritățile raionale din țară, cu IDNO și CUATM.
2. **Nomenclatorul Clasificatorului Unităților Administrativ-Teritoriale din Moldova (CUATM)**:
   - Utilizat pentru maparea automată precisă pe cele 32 de raioane, 3 municipii (Chișinău, Bălți, Bender) și UTA Găgăuzia, precum și pe macro-regiunile economice și turistice (Nord, Centru, Sud, Chișinău, Găgăuzia).
3. **Calendarul Recurențelor, Festivalurilor și Tradițiilor Etnogastronomice**:
   - Colectat din registrele ANTRIM ([moldova.travel](https://moldova.travel)), Oficiul Național al Turismului, Oficiul Național al Viei și Vinului (ONVV), organizatorii de festivaluri și agropensiunile premiate internațional (ex: Văleni - UNWTO Best Tourism Village).
   - Conține **formule exacte de recurență** (ex: *„A 3-a duminică din Mai”*, *„Primul weekend din Octombrie”*, *„Ultimul weekend din Septembrie”*) și **hramurile ecleziastice anuale** ale tuturor localităților din țară.

---

## 2. Dicționar de Date (Coloane)

Baza de date conține **20 de coloane structurate**:

| Nr. | Nume Coloană | Tip | Obligatoriu | Descriere & Valoare |
|---|---|---|---|---|
| 1 | `id` | String | DA | Cod unic curat. Prefixat: `APL1-` (primării), `APL2-` (consilii raionale), `DIR-CUL-` (direcții cultură), `ORG-` (asociații/festivaluri), `WIN-` (crame), `RESORT-` / `PENS-` (complexe rurale). |
| 2 | `categorie` | String | DA | Categoria organizațională (ex: `Primărie (APL I)`, `Consiliu Raional / Municipal (APL II)`, `Organizator Festival Gastronomic`, `Cramă / Complex Oenoturistic`). |
| 3 | `denumire` | String | DA | Numele complet oficial al entității juridice. |
| 4 | `regiune` | String | DA | Regiunea turistică/geografică: `Centru`, `Nord`, `Sud`, `Chișinău`, `UTA Găgăuzia`, `Transnistria`. |
| 5 | `raion_municipiu` | String | DA | Raionul sau municipiul de apartenență (ex: `Orhei`, `Cahul`, `Nisporeni`, `Strășeni`). |
| 6 | `localitate` | String | DA | Satul, comuna sau orașul unde își are sediul entitatea. |
| 7 | `adresa_completa` | String | DA | Adresa poștală sau juridică detaliată. |
| 8 | `conducator_responsabil` | String | DA | Conducătorul entității (Primar, Președinte de raion, Director general, Oenolog, Fondator). |
| 9 | `profil_turistic_gastronomic` | String | DA | Sinteză a potențialului turistic și gastronomic: specific culinar (ex: plăcinte, sarmale, bostan, căpșuni, vinuri, fripturi), dotări și atractivitate pentru călători. |
| 10 | `evenimente_tipice` | String | DA | Evenimentele majore organizate de regulă (festivaluri gastronomice renumite, Hramul Satului, Ziua Vinului, ateliere culinare). |
| 11 | `data_eveniment` | String | DA | Data calendaristică sau reperul temporal: `8 Noiembrie`, `14 Octombrie`, `A 3-a duminică din Mai`, `Primul weekend din Octombrie`, `Permanent`. |
| 12 | `recurenta` | String | DA | Formula completă de recurență: ex: `Anual în a 3-a duminică din Mai (Festivalul Mămăligii)`, `Anual pe 8 Noiembrie (Sărbătoarea Kasîm de Sf. Dumitru)`, `Anual în primul weekend din Octombrie`. |
| 13 | `tip_recurenta` | String | DA | Tipul tiparului temporal: `Recurență relativă` (ziua/weekendul N dintr-o lună), `Dată fixă anuală` (Hramuri creștine), `Recurență mixtă`, `Permanent / La cerere`, `Săptămânal / Weekend`. |
| 14 | `luna` | String | DA | Luna principală a evenimentului: `Ianuarie` - `Decembrie` sau `Tot anul`. |
| 15 | `sezon` | String | DA | Anotimpul propice pentru vizitare: `Primăvară`, `Vară`, `Toamnă`, `Iarnă`, `Permanent`. |
| 16 | `email_contact` | String | OPȚIONAL | Email oficial sau instituțional (@apl.gov.md, @raion.md, domenii proprii). |
| 17 | `telefon` | String | OPȚIONAL | Număr de telefon pentru contact, rezervări sau informații despre evenimente. |
| 18 | `website_social` | String | OPȚIONAL | Link către site-ul oficial, pagina de Facebook a festivalului sau portalul administrativ. |
| 19 | `idno_cod_fiscal` | String | DA | Codul fiscal unic de 13 cifre din Registrul de Stat al Republicii Moldova. |
| 20 | `cod_cuatm` | String | DA | Codul statistic teritorial conform Biroului Național de Statistică al RM. |

---

## 3. Tipare de Recurență în Republica Moldova

Baza de date reflectă fidel modul în care se planifică turismul și viața comunitară în Moldova:

1. **Recurență Relativă (Formule pe bază de duminici / weekenduri)**:
   - *„A 3-a duminică din Mai”*: Festivalul Național al Mămăligii (Selemet, Cimișlia), Mai Dulce (Chișinău).
   - *„Primul weekend din Octombrie”*: Ziua Națională a Vinului (Wine of Moldova) la Chișinău și etapele din raioane.
   - *„Ultimul weekend din Septembrie”*: Festivalul Etno-Gastronomic Bostaniada (Bălăbănești, Criuleni).
   - *„A 3-a duminică din Septembrie”*: Festivalul Național al Prunei (Nisporeni).
   - *„Ultima duminică din Septembrie”*: Festivalul Național al Mărului (Soroca).
   - *„Al 3-lea weekend din Iunie”*: DescOperă (Festivalul de Operă în amfiteatrul Butuceni, Orheiul Vechi).
   - *„Al 3-lea weekend din August”*: Gustar Music & Food Festival.
   - *„Prima duminică din Iunie”*: Festivalul Căpșunilor și Mierii (Sadova, Călărași).
   - *„A 2-a duminică din Octombrie”*: Festivalul Sarmalei și al Pitei de Casă (Vorniceni, Strășeni).
   - *„A 3-a duminică din Iulie”*: Târgul Internațional al Olarilor La Vatra Olarului (Hoginești, Călărași).
   - *„A 2-a duminică după Paște”*: Festivalul Hai la Cozonaci (Văleni, Lunca Prutului).
   - *„Prima duminică din Noiembrie”*: Gagauz Sarap Yortusu (Festivalul Vinului Găgăuz la Comrat).

2. **Hramuri Creștin-Ortodoxe (Date Fixe Anuale)**:
   - *8 Noiembrie*: Hramul Orașului Ceadîr-Lunga (Sărbătoarea Tradițională Kasîm de Sf. Dumitru), Orhei, Anenii Noi, Edineț, Dondușeni, Sîngerei etc.
   - *14 Octombrie*: Hramul Municipiului Chișinău (Acoperământul Maicii Domnului), Rezina, Briceni, Florești, Călărași, Vulcănești etc.
   - *21 Noiembrie*: Hramul Orașului Cahul (Sf. Arhangheli Mihail și Gavriil), Hîncești, Telenești, Glodeni etc.
   - *28 August*: Hramul Municipiului Soroca (Adormirea Maicii Domnului / Uspenia), Ungheni, Cimișlia, Drochia etc.
   - *22 Mai*: Hramul Municipiului Bălți (Sf. Nicolae de Vară), Criuleni, Fălești, Basarabeasca, Ștefan Vodă, Șoldănești etc.
   - *6 Mai*: Sărbătoarea Hederlez (Ceadîr-Lunga la hipodromul de cai), Taraclia (Sf. Gheorghe).
   - *27 Octombrie*: Hramul Strășeni și Ialoveni (Sf. Cuvioasa Parascheva).
   - *20 Ianuarie*: Hramul Comrat (Sf. Ioan Botezătorul).

3. **Permanent / La cerere**:
   - Cramele majore (Cricova, Mileștii Mici, Castel Mimi, Purcari, Château Vartely, Asconi, Et Cetera, Poiana, Kara Gani) deschise zilnic și în weekend cu circuite de vizitare și restaurante gastronomice.

---

## 4. REST API & Endpoint-uri Web

Serverul local [`server.py`](file:///c:/Users/geo/OneDrive/Documents/clubturistic.md/server.py) expune:
- **`GET /`**: Portalul public interactiv cu căutare, filtrare pe sezoane/luni/recurență și paginare.
- **`GET /admin`**: Panoul tehnic Admin DB Studio cu CRUD live și export CSV/JSON.
- **`GET /api/entitati`**: Căutare și filtrare avansată:
  - Parametri suportați: `q` (termen căutare), `regiune`, `categorie`, `raion`, `luna`, `sezon`, `tip_recurenta`, `limit`, `offset`.
- **`GET /api/calendar`**: Calendar structurat JSON cu evenimentele programate, datele start/sfârșit și regulile de recurență.
- **`GET /api/stats`**: Statistici agregate în timp real pe categorii, regiuni, anotimpuri și luni.
- **`POST /api/entitati`**: Adăugare entitate nouă direct în SQLite `clubturistic.db`.
- **`PUT /api/entitati/<id>`**: Actualizare entitate în SQLite.
- **`DELETE /api/entitati/<id>`**: Ștergere entitate din SQLite.

---

## 5. Codurile Teritoriale CUATM pe Raioane

- `01xx`: Municipiul Chișinău
- `03xx`: Municipiul Bălți
- `05xx`: Municipiul Bender (Tighina)
- `10xx`: Raionul Anenii Noi
- `12xx`: Raionul Basarabeasca
- `14xx`: Raionul Briceni
- `17xx`: Raionul Cahul
- `21xx`: Raionul Cantemir
- `25xx`: Raionul Călărași
- `27xx`: Raionul Căușeni
- `29xx`: Raionul Cimișlia
- `31xx`: Raionul Criuleni
- `34xx`: Raionul Dondușeni
- `36xx`: Raionul Drochia
- `38xx`: Raionul Dubăsari
- `41xx`: Raionul Edineț
- `43xx`: Raionul Fălești
- `45xx`: Raionul Florești
- `48xx`: Raionul Glodeni
- `53xx`: Raionul Hîncești
- `55xx`: Raionul Ialoveni
- `57xx`: Raionul Leova
- `60xx`: Raionul Nisporeni
- `62xx`: Raionul Ocnița
- `64xx`: Raionul Orhei
- `67xx`: Raionul Rezina
- `71xx`: Raionul Rîșcani
- `74xx`: Raionul Sîngerei
- `78xx`: Raionul Soroca
- `80xx`: Raionul Strășeni
- `83xx`: Raionul Șoldănești
- `85xx`: Raionul Ștefan Vodă
- `87xx`: Raionul Taraclia
- `89xx`: Raionul Telenești
- `92xx`: Raionul Ungheni
- `96xx`: Unitatea Teritorial-Autonomă Găgăuzia
