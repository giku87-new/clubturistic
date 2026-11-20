import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

gen_path = os.path.join(os.path.dirname(__file__), 'genereaza_baza_date.py')

with open(gen_path, 'r', encoding='utf-8') as f:
    text = f.read()

target = """            'cod_cuatm': '0142'
        }
    ]"""

replacement = """            'cod_cuatm': '0142'
        },
        {
            'id': 'ORG-DUBASARI-PESTE-36',
            'categorie': 'Organizator Festival Gastronomic',
            'denumire': 'Primăria Satului Dubăsarii Vechi - Festivalul Peștelui și al Zemei Pescărești',
            'regiune': 'Centru',
            'raion_municipiu': 'Criuleni',
            'localitate': 's. Dubăsarii Vechi',
            'adresa_completa': 'rl. Criuleni, s. Dubăsarii Vechi (pe malul Nistrului)',
            'conducator_responsabil': 'Primar Dubăsarii Vechi',
            'profil_turistic_gastronomic': 'Localitate amplasată pe malul Nistrului; renumită pentru tradiția zemei de pește la ceaun pescăresc cu mujdei de usturoi și ardei iute, pește prăjit pe tablă cu mămăligă și legume din lunca Nistrului.',
            'evenimente_tipice': 'Festivalul Peștelui și al Zemei Pescărești (anual în al 2-lea weekend din Iulie), Hramul Satului (14 Octombrie), Concursuri culinare pescărești la ceaun',
            'email_contact': 'primaria.dubasariivechi@apl.gov.md',
            'telefon': '+373 248 57 236',
            'website_social': 'https://criuleni.md',
            'idno_cod_fiscal': '1007601008123',
            'cod_cuatm': '3125'
        }
    ]"""

assert target in text, "Target not found!"
text = text.replace(target, replacement, 1)

with open(gen_path, 'w', encoding='utf-8') as f:
    f.write(text)

print("Added ORG-DUBASARI-PESTE-36 to genereaza_baza_date.py successfully!")
