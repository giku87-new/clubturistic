"""
Utilitar CLI pentru interogarea și filtrarea bazei de date de turism și evenimente din Moldova.
Utilizabil atât de dezvoltatori umani, cât și de agenți AI pentru a găsi rapid primării, festivaluri,
crame și organizatori după regiune, raion, categorie sau cuvinte cheie gastronomice.

Suportă căutare flexibilă (cu sau fără diacritice, precum și căutare fonetică: ex. 'ciadir' va găsi 'ceadir').

Exemple de utilizare:
  python scripts/interogheaza_turism.py --stats
  python scripts/interogheaza_turism.py --termen ciadir
  python scripts/interogheaza_turism.py --termen "hram ceadir"
  python scripts/interogheaza_turism.py --termen placinte
  python scripts/interogheaza_turism.py --raion Orhei
"""

import argparse
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_PATH = os.path.join(BASE_DIR, 'baza_date_turism_evenimente_moldova.json')

def normalize(text):
    if not text:
        return ""
    text = text.lower()
    # Înlocuire diacritice
    trans = {
        'ă': 'a', 'â': 'a', 'î': 'i', 'ș': 's', 'ş': 's', 'ț': 't', 'ţ': 't',
        '-': ' ', '_': ' '
    }
    for k, v in trans.items():
        text = text.replace(k, v)
    # Înlocuiri fonetice populare (ex: ciadir -> ceadir)
    text = text.replace('ciadir', 'ceadir')
    return text

def load_data():
    if not os.path.exists(JSON_PATH):
        print(f"Eroare: Nu s-a găsit fișierul de date {JSON_PATH}. Rulați mai întâi genereaza_baza_date.py")
        sys.exit(1)
    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def print_stats(data):
    from collections import Counter
    print(f"\n=======================================================")
    print(f" TOTAL ÎNREGISTRĂRI ÎN BAZA DE DATE: {len(data)}")
    print(f"=======================================================")
    
    print("\n--- DISTRIBUȚIE PE CATEGORII ---")
    cats = Counter(r['categorie'] for r in data)
    for cat, cnt in cats.most_common():
        print(f"  • {cat:45}: {cnt}")

    print("\n--- DISTRIBUȚIE PE REGIUNI ---")
    regs = Counter(r['regiune'] for r in data)
    for reg, cnt in regs.most_common():
        print(f"  • {reg:25}: {cnt}")
    print()

def main():
    parser = argparse.ArgumentParser(description="Interogare Bază de Date Turism & Evenimente Moldova")
    parser.add_argument('--stats', action='store_true', help="Afișează sumar statistic detaliat")
    parser.add_argument('--regiune', type=str, help="Filtrează după regiune (ex: Centru, Nord, Sud, Chișinău, UTA Găgăuzia)")
    parser.add_argument('--raion', type=str, help="Filtrează după raion/municipiu (ex: Orhei, Cahul, Strășeni, Cimișlia)")
    parser.add_argument('--categorie', type=str, help="Filtrează după categorie (ex: Festival, Cramă, Primărie, Consiliu)")
    parser.add_argument('--termen', type=str, help="Căutare liberă în denumire, profil gastronomic și evenimente (ex: vin, mamaliga, placinte, ciadir, hram)")
    parser.add_argument('--limita', type=int, default=15, help="Număr maxim de rezultate afișate (default: 15)")
    parser.add_argument('--json-output', action='store_true', help="Returnează rezultatele în format JSON pur (ideal pentru alți agenți)")

    args = parser.parse_args()
    data = load_data()

    if args.stats:
        print_stats(data)
        return

    rezultate = data
    if args.regiune:
        reg_norm = normalize(args.regiune)
        rezultate = [r for r in rezultate if reg_norm in normalize(r['regiune'])]
    if args.raion:
        raion_norm = normalize(args.raion)
        rezultate = [r for r in rezultate if raion_norm in normalize(r['raion_municipiu'])]
    if args.categorie:
        cat_norm = normalize(args.categorie)
        rezultate = [r for r in rezultate if cat_norm in normalize(r['categorie'])]
    if args.termen:
        term_norm = normalize(args.termen)
        # Permite căutare pe cuvinte multiple
        cuvinte = term_norm.split()
        rezultate = [
            r for r in rezultate
            if all(
                c in normalize(r['denumire']) or
                c in normalize(r['profil_turistic_gastronomic']) or
                c in normalize(r['evenimente_tipice']) or
                c in normalize(r['localitate'])
                for c in cuvinte
            )
        ]

    if args.json_output:
        print(json.dumps(rezultate[:args.limita], ensure_ascii=False, indent=2))
        return

    print(f"\nGăsite {len(rezultate)} rezultate (se afișează primele {min(args.limita, len(rezultate))}):")
    print("-" * 80)
    for i, r in enumerate(rezultate[:args.limita], 1):
        print(f"[{i}] {r['denumire']} ({r['categorie']})")
        print(f"    Locație:     {r['localitate']}, {r['raion_municipiu']} (Regiunea {r['regiune']})")
        print(f"    Conducător:  {r['conducator_responsabil']}")
        print(f"    Specific:    {r['profil_turistic_gastronomic']}")
        print(f"    Evenimente:  {r['evenimente_tipice']}")
        if r['email_contact']:
            print(f"    Email:       {r['email_contact']}")
        if r['telefon']:
            print(f"    Telefon:     {r['telefon']}")
        if r['website_social']:
            print(f"    Web/Social:  {r['website_social']}")
        print("-" * 80)

if __name__ == '__main__':
    main()
