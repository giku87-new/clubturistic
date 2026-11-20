import csv
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

csv_path = r'c:\Users\geo\OneDrive\Documents\clubturistic.md\baza_date_turism_evenimente_moldova.csv'
json_path = r'c:\Users\geo\OneDrive\Documents\clubturistic.md\baza_date_turism_evenimente_moldova.json'

records = []
with open(csv_path, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        records.append(row)

with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(records, f, ensure_ascii=False, indent=2)

print(f"JSON export completed: {len(records)} items written to {json_path}")
