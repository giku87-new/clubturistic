import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

gen_path = os.path.join(os.path.dirname(__file__), 'genereaza_baza_date.py')

with open(gen_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Add ORG-DUBASARI-PESTE-36 to SPECIAL_DATES
if "'ORG-DUBASARI-PESTE-36':" not in text:
    anchor = "'ORG-SIPOTENI-ZEAMA-34':"
    new_date = """    'ORG-DUBASARI-PESTE-36': ('Al 2-lea weekend din Iulie', 'Anual în al 2-lea weekend din Iulie (Festivalul Peștelui și al Zemei Pescărești la Nistru)', 'Recurență relativă', 'Iulie', 'Vară'),\n""" + anchor
    text = text.replace(anchor, new_date, 1)

# Add ORG-DUBASARI-PESTE-36 to special_entities
if "'ORG-DUBASARI-PESTE-36'" not in text:
    anchor_entity = """            'id': 'AGRO-HANUL-VASILE-35',"""
    new_entity = """            'id': 'ORG-DUBASARI-PESTE-36',
            'categorie': 'Organizator Festival Gastronomic',
            'denumire': 'Primăria Satului Dubăsarii Vechi - Festivalul Peștelui și al Zemei Pescărești',
            'regiune': 'Centru',
            'raion_municipiu': 'Criuleni',
            'localitate': 's. Dubăsarii Vechi',
            'adresa_completa': 'rl. Criuleni, s. Dubăsarii Vechi (pe malul Nistrului)',
            'conducator_responsabil': 'Primar Dubăsarii Vechi',
            'profil_turistic_gastronomic': 'Localitate amplasată pe malul Nistrului, renumită pentru tradiția zemei de pește la ceaun pescăresc cu mujdei de usturoi și ardei iute, pește prăjit pe tablă cu mămăligă și legume de luncă.',
            'evenimente_tipice': 'Festivalul Peștelui și al Zemei Pescărești (anual în al 2-lea weekend din Iulie), Hramul Satului (14 Octombrie), Concursuri culinare pescărești',
            'email_contact': 'primaria.dubasariivechi@apl.gov.md',
            'telefon': '+373 248 57 236',
            'website_social': 'https://criuleni.md',
            'idno_cod_fiscal': '1007601008123',
            'cod_cuatm': '3125'
        },
        {
            'id': 'AGRO-HANUL-VASILE-35',"""
    text = text.replace(anchor_entity, new_entity, 1)

# Mention zeamă in Château Vartely and Vatra
text = text.replace(
    "'profil_turistic_gastronomic': 'Complex vinicol și hotelier pe dealurile Orheiului; bucătărie fusion moldovenească la grătar, degustări ghidate de sommelieri, proiecții de lumini AR și căsuțe tradiționale.'",
    "'profil_turistic_gastronomic': 'Complex vinicol și hotelier pe dealurile Orheiului; renumit pentru bucătăria tradițională moldovenească (zeamă de pui de casă cu tăieței, plăcinte la cuptor, friptură) asociată cu vinuri de colecție.'"
)

text = text.replace(
    "'profil_turistic_gastronomic': 'Spațiu gigantic în aer liber special conceput pentru mega-evenimente, camping, festivaluri istorice, bucătărie la grătar, plăcinte boierești și meșteșuguri strămoșești.'",
    "'profil_turistic_gastronomic': 'Spațiu gigantic în aer liber pentru mega-evenimente culturale; zonă gastronomică cu bucate la ceaun pe lemne (zeamă de casă, friptură, mămăligă), plăcinte boierești și meșteșuguri strămoșești.'"
)

with open(gen_path, 'w', encoding='utf-8') as f:
    f.write(text)

print("Updated genereaza_baza_date.py with Dubasarii Vechi Zeama de Peste, Vartely and Vatra!")
