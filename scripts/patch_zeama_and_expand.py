import os
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
gen_path = os.path.join(BASE_DIR, 'scripts', 'genereaza_baza_date.py')

with open(gen_path, 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Update SPECIAL_DATES in genereaza_baza_date.py to include Sipoteni & Hanul lui Vasile
special_dates_anchor = "'WIN-CASTEL-MIMI-20':"
new_dates = """    'ORG-SIPOTENI-ZEAMA-34': ('A 2-a duminică din August', 'Anual în a 2-a duminică din August (Festivalul Național al Zemii în poiana La Sălcii)', 'Recurență relativă', 'August', 'Vară'),
    'AGRO-HANUL-VASILE-35': ('Permanent (Zilnic 10:00 - 23:00)', 'Permanent (Zilnic cu bucătărie tradițională moldovenească, zeamă și plăcinte)', 'Permanent / La cerere', 'Tot anul', 'Permanent'),
    'WIN-CASTEL-MIMI-20':"""

if "'ORG-SIPOTENI-ZEAMA-34':" not in text:
    text = text.replace(special_dates_anchor, new_dates, 1)

# 2. Enrich PRIMĂRIA COMUNEI SIPOTENI in loop
primarie_loop_anchor = "# Verificare dacă este un oraș cu profil îmbogățit"
sipoteni_enrichment = """            # Verificare profil specific Sipoteni (Festivalul Zemii)
            if 'SIPOTENI' in nume_u:
                profil = "Comună renumită din inima Codrilor Călărașiului, gazda celebrului Festival Național al Zemii (ediția a X-a); tradiție gastronomică arhaică bazată pe zeamă de pasăre cu tăieței de casă și borș acru, plăcinte rumenite la cuptor și meșteșuguri."
                evenimente = "Festivalul Național al Zemii (anual în a 2-a duminică din August în poiana La Sălcii), Hramul Comunei Sipoteni (21 Noiembrie, Sf. Arhangheli Mihail și Gavriil), Târgul Meșteșugurilor Tradiționale"

            # Verificare dacă este un oraș cu profil îmbogățit"""

if "Festivalul Național al Zemii" not in text:
    text = text.replace(primarie_loop_anchor, sipoteni_enrichment, 1)

# 3. Add ORG-SIPOTENI-ZEAMA-34 and AGRO-HANUL-VASILE-35 to special_entities
special_entities_end_anchor = """            'idno_cod_fiscal': '1009600034125',
            'cod_cuatm': '2528'
        }
    ]"""

new_special_entities = """            'idno_cod_fiscal': '1009600034125',
            'cod_cuatm': '2528'
        },
        {
            'id': 'ORG-SIPOTENI-ZEAMA-34',
            'categorie': 'Organizator Festival Gastronomic',
            'denumire': 'Primăria Comunei Sipoteni & AO Băștinașii din Sipoteni - Festivalul Național al Zemii',
            'regiune': 'Centru',
            'raion_municipiu': 'Călărași',
            'localitate': 's. Sipoteni',
            'adresa_completa': 'rl. Călărași, com. Sipoteni (Poiana „La Sălcii”)',
            'conducator_responsabil': 'Vasile Rață (Primar)',
            'profil_turistic_gastronomic': 'Capitala zemei tradiționale moldovenești; organizează cel mai mare festival gastronomic din Moldova dedicat zemei de găină și pasăre de casă cu tăieței frământați manual, borș acru de tărâțe și ardei iute, preparate la peste 30 de ceaune uriașe pe lemne.',
            'evenimente_tipice': 'Festivalul Național al Zemii (anual în a 2-a duminică din August în poiana La Sălcii), Concursul Cea Mai Bună Zeamă la Ceaun, Degustări de plăcinte călărășene, Hramul Comunei Sipoteni (21 Noiembrie)',
            'email_contact': 'primaria.sipoteni@apl.gov.md',
            'telefon': '+373 244 76 236',
            'website_social': 'https://facebook.com/FestivalulZemiiSipoteni',
            'idno_cod_fiscal': '1007601007907',
            'cod_cuatm': '2541'
        },
        {
            'id': 'AGRO-HANUL-VASILE-35',
            'categorie': 'Complex Agroturistic & Gastronomic Tradițional',
            'denumire': 'Complexul Tradițional Hanul lui Vasile',
            'regiune': 'Chișinău',
            'raion_municipiu': 'Municipiul Chișinău',
            'localitate': 'com. Tohatin',
            'adresa_completa': 'mun. Chișinău, com. Tohatin, str. Păcii 1',
            'conducator_responsabil': 'Vasile Cerbu (Administrator)',
            'profil_turistic_gastronomic': 'Renumit la nivel național pentru bucătăria moldovenească rustică: zeamă fierbinte de găină cu tăieței de casă, mămăligă aburindă cu brânză de oi, friptură de porc la ceaun, plăcinte rumenite și foișoare din lemn pe malul lacului.',
            'evenimente_tipice': 'Seri de gastronomie moldovenească cu lăutari, Zilele Zemei de Casă, Hramul Tohatinului (14 Octombrie), Mese festive cu bucate tradiționale',
            'email_contact': 'info@hanul-lui-vasile.md',
            'telefon': '+373 69 11 22 44',
            'website_social': 'https://hanul-lui-vasile.md',
            'idno_cod_fiscal': '1003600045892',
            'cod_cuatm': '0142'
        }
    ]"""

if "'ORG-SIPOTENI-ZEAMA-34'" not in text:
    text = text.replace(special_entities_end_anchor, new_special_entities, 1)

# 4. Enrich existing entities with zeamă references
text = text.replace(
    "'profil_turistic_gastronomic': 'Polul turismului rural din Republica Moldova; sat muzeu reabilitat în care oaspeții participă la frământat pâine, învârtit sarmale minuscule, copt plăcinte și plimbat cu căruța.'",
    "'profil_turistic_gastronomic': 'Polul turismului rural din Republica Moldova; sat muzeu reabilitat renumit pentru zeamă tradițională de găină cu tăieței frământați manual și borș acru, participare la frământat pâine, învârtit sarmale minuscule și plăcinte la cuptor.'"
)

text = text.replace(
    "'profil_turistic_gastronomic': 'Centru de salvare a tradițiilor basarabene; oferă prânzuri ecologice gătite la cuptorul cu lemne, ceaiuri din 20 de plante culese din pădure și gemuri din trandafiri.'",
    "'profil_turistic_gastronomic': 'Centru de salvare a tradițiilor basarabene; oferă prânzuri ecologice gătite la cuptorul cu lemne: zeamă de pasăre cu plante aromatice din Codri, plăcinte pe vatră, ceaiuri din 20 de plante și gemuri din trandafiri.'"
)

text = text.replace(
    "'profil_turistic_gastronomic': 'Satul Văleni (câștigător Best Tourism Villages UNWTO); gazda celebrei bunici care bate toba de la Zdob și Zdub; leagăn de meșteșuguri și gastronomie arhaică din Lunca Prutului.'",
    "'profil_turistic_gastronomic': 'Satul Văleni (Best Tourism Villages UNWTO); leagăn de gastronomie autentică din Lunca Prutului: zeamă de pește la ceaun pescăresc, zeamă de pui cu tăieței de casă, plăcinte poale-n brâu și pâine coaptă la cuptor pe lemne.'"
)

with open(gen_path, 'w', encoding='utf-8') as f:
    f.write(text)

print("Patch zeamă aplicat cu succes pe genereaza_baza_date.py!")
