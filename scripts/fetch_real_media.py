"""
Descarcă și verifică imagini reale (cu atribuire corectă) pentru toate cele
38 de chei media din `data/curated_catalog.py`.
Salvează fișierele în `static/images/` și generează `data/media_manifest.json`.
Nu salvează niciodată pagini HTML de eroare sau imagini invalide.
"""

import json
import os
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from data.curated_catalog import EVENIMENTE, HRAMURI_NOTABILE, LOCATII

IMAGES_DIR = os.path.join(BASE_DIR, "static", "images")
MANIFEST_PATH = os.path.join(BASE_DIR, "data", "media_manifest.json")
os.makedirs(IMAGES_DIR, exist_ok=True)

USER_AGENT = "ClubTuristicMD/2.0 (https://clubturistic.md; contact@clubturistic.md)"

# Surse curate, verificate manual (site-uri oficiale + Wikimedia Commons exact File:)
CURATED_MEDIA_SOURCES = {
    "castel_mimi": {
        "direct": [
            ("https://castelmimi.md/wp-content/uploads/2023/05/castel-mimi-cover.webp", "Castel Mimi Wine Resort (site oficial)"),
        ],
        "commons": ["File:Castel Mimi 2.jpg"],
    },
    "cricova": {
        "direct": [
            ("https://cricova.md/wp-content/uploads/2026/03/c2c2b11dc0a7ae1f1f524d48ab82775e-1-1024x640.jpg", "Combinatul de Vinuri Cricova (site oficial)"),
        ],
        "commons": ["File:Cricova State Winery (38108339585).jpg", "File:Cricova-wagon-museum.jpg"],
    },
    "vartely": {
        "direct": [
            ("https://vartely.md/wp-content/uploads/2017/01/fb.jpg", "Château Vartely Winery & Resort (site oficial)"),
        ],
        "commons": ["File:Moldova Competitiveness Project, USAID Moldova (48121769796).jpg"],
    },
    "yard_sale": {
        "direct": [
            ("https://yardsale.md/assets/yardsale-market-2026-11-14-15.webp", "Yard Sale Chișinău (site oficial)"),
        ],
        "commons": ["File:2023 USDA Farmers Market (20230714-USDA-AMS-RDC-35).jpg"],
    },
    "butuceni": {"commons": ["File:Butuceni, Moldova - panoramio.jpg", "File:Cetățuia „Orheiul Vechi”.jpg"]},
    "capriana": {"commons": ["File:Monasterio de Căpriana, Căpriana, Moldavia, 2023-11-02, DD 38.jpg"]},
    "cherries": {"commons": ["File:Cherry Stella444.jpg", "File:Sweet-cherry bloom 2020 G2.jpg"]},
    "varzari_placinta": {"commons": ["File:Plăcinta Frățească.jpg", "File:Placinta.jpg"]},
    "chicken_soup": {"commons": ["File:Chicken Noodle Soup.jpg", "File:Chicken noodle soup (cropped).jpg"]},
    "chisinau": {"commons": ["File:Arcul de Triumf Chisinau.jpg", "File:Chisinau Stefan cel Mare park fountain.jpg"]},
    "christmas_market": {"commons": ["File:Cours Mirabeau Nuit Décembre.jpg"]},
    "farmers_market": {"commons": ["File:2023 USDA Farmers Market (20230714-USDA-AMS-RDC-35).jpg", "File:Cambridge Farmers' Market- Front.jpg"]},
    "gagauzia": {"commons": ["File:Comrat,market-area.jpg", "File:MD.GE.Ceadîr-Lunga - râpele de la Ceadîr-Lunga - apr 2018 - 01.jpg"]},
    "gagauz_sofrasi": {"commons": ["File:MD.GE.Ceadîr-Lunga - râpele de la Ceadîr-Lunga - apr 2018 - 01.jpg", "File:Comrat,market-area.jpg"]},
    "horses_race": {"commons": ["File:Race Horse On Gallops (8236293870).jpg"]},
    "jazz_sax": {"commons": ["File:Brede Sørum Jazz på Jølst 2026 (223648).jpg"]},
    "lacul_beleu": {"commons": ["File:Lacul Beleu priveliște.jpg"]},
    "lavender": {"commons": ["File:Lavandula angustifolia (16).jpg", "File:Lavender field in Misato Town, Akita 20180624e.jpg"]},
    "milestii_mici": {"commons": ["File:Caves Milestii Mici Moldavie.jpg"]},
    "moldovan_carpet": {"commons": ["File:Moldovan carpet.jpg", "File:Moldovan carpet (1985). (27854644994).jpg"]},
    "moldovan_ie": {"commons": ["File:Blouse MET 23.123.1.jpg", "File:Ie (Iasi, Moldova, end of XIX cent.).jpg"]},
    "nistru": {"commons": ["File:Cruise ship on the Dniester River.jpg"]},
    "outdoor_opera": {"commons": ["File:HCM Opera House outdoor performance.jpg", "File:Jay Pritzker Pavilion, Millennium Park, Chicago, Illinois (28507852437).jpg"]},
    "padurea_domneasca": {"commons": ["File:Padurea Domneasca Glodeni (1).jpg"]},
    "apples": {"commons": ["File:Apples in basket 2018 G1.jpg", "File:Apples in a basket.jpg"]},
    "peaches": {"commons": ["File:Peaches at Applecrest Farm Orchards - 20107074158.jpg", "File:Autumn Red peaches.jpg"]},
    "plums": {"commons": ["File:Plums.jpg"]},
    "potatoes": {"commons": ["File:Big and fresh potatoes 01.jpg"]},
    "pottery": {"commons": ["File:Grncarija iz Zlakuse 01.jpg", "File:Potter shaping clay on a traditional manual potter’s wheel in India 01.jpg"]},
    "pumpkin_fest": {"commons": ["File:2024 The Elegant Farmer Autumn Harvest Fest 01 (Pumpkin Patch).jpg", "File:Keene pumpkin festival 1.jpg"]},
    "purcari": {"commons": ["File:Purcari.jpg", "File:AIRM - Crama din Purcari - martie 2014 - 777328332291922.jpg"]},
    "rock_folk_fest": {"commons": ["File:Calgary Folk Festival 2023 main stage at night.jpg"]},
    "soroca": {"commons": ["File:Fuerte de Soroca, Soroca, Moldavia, 2023-11-01, DD 06.jpg"]},
    "strawberries_honey": {"commons": ["File:Collection of strawberry (Unsplash).jpg", "File:Bowl of fresh strawberries on a tray.jpg"]},
    "sweets_pastry": {"commons": ["File:Dessert for Chef's table, Mainz.jpg"]},
    "tomatoes": {"commons": ["File:Red Tomatoes at a Farmers Market.jpg", "File:Tomatoes in basket 2022 G1.jpg"]},
    "vineyard_moldova": {"commons": ["File:Moldova Competitiveness Project, USAID Moldova (48121769796).jpg", "File:Denbies vineyard and Box Hill in Autumn.jpg"]},
    "wine_cellar": {"commons": ["File:Port tasting (8907536314).jpg", "File:Porto Calém Cellar Age-Old Casks and Tasting Experience (55243068528).jpg"]},
}

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE


def detect_image_ext(data: bytes) -> str | None:
    if len(data) < 8000:
        return None
    if data[:3] == b"\xff\xd8\xff":
        return "jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def download_bytes(url: str, retries: int = 3) -> bytes | None:
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=15, context=SSL_CTX) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                wait = 1.5 * (attempt + 1)
                print(f"  [throttle {e.code}] retry in {wait:.1f}s for {url[:70]}...")
                time.sleep(wait)
            else:
                print(f"  [HTTP {e.code}] {url[:80]}")
                return None
        except Exception as e:
            print(f"  [ERR {type(e).__name__}] {url[:80]} -> {e}")
            time.sleep(0.5)
    return None


def clean_html_meta(val: str) -> str:
    txt = re.sub(r"<[^>]+>", "", val or "").strip()
    return re.sub(r"\s+", " ", txt)[:120]


def resolve_commons_metadata(file_titles: list[str]) -> dict[str, dict]:
    """Interoghează API-ul Wikimedia Commons în loturi pentru URL-uri directe și atribuire."""
    result = {}
    batch_size = 20
    for i in range(0, len(file_titles), batch_size):
        chunk = file_titles[i : i + batch_size]
        url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(
            {
                "action": "query",
                "titles": "|".join(chunk),
                "prop": "imageinfo",
                "iiprop": "url|extmetadata|mime|size",
                "iiurlwidth": "960",
                "format": "json",
            }
        )
        raw = download_bytes(url)
        if not raw:
            continue
        data = json.loads(raw.decode("utf-8"))
        # Normalizări titluri
        norm_map = {n["from"]: n["to"] for n in data.get("query", {}).get("normalized", [])}
        pages = data.get("query", {}).get("pages", {})
        by_title = {}
        for p in pages.values():
            t = p.get("title")
            if not t or "imageinfo" not in p:
                continue
            ii = p["imageinfo"][0]
            extm = ii.get("extmetadata", {})
            artist = clean_html_meta(extm.get("Artist", {}).get("value", ""))
            lic = clean_html_meta(extm.get("LicenseShortName", {}).get("value", "CC / Public Domain"))
            credit = f"Wikimedia Commons ({lic})"
            if artist and len(artist) < 60:
                credit = f"{artist} • {lic} (Wikimedia Commons)"
            by_title[t] = {
                "url": ii.get("thumburl") or ii.get("url"),
                "orig_url": ii.get("url"),
                "credit": credit,
            }
        for orig_title in chunk:
            canonical = norm_map.get(orig_title, orig_title)
            if canonical in by_title:
                result[orig_title] = by_title[canonical]
        time.sleep(0.3)
    return result


def main():
    required_keys = sorted(set(x["media_key"] for x in EVENIMENTE + LOCATII + HRAMURI_NOTABILE))
    missing_from_map = [k for k in required_keys if k not in CURATED_MEDIA_SOURCES]
    if missing_from_map:
        raise RuntimeError(f"Chei media lipsă din CURATED_MEDIA_SOURCES: {missing_from_map}")

    # Preluăm manifestul existent dacă avem deja fișiere valide pe disc
    existing_manifest = {}
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            existing_manifest = json.load(f)

    all_commons_titles = []
    for k in required_keys:
        all_commons_titles.extend(CURATED_MEDIA_SOURCES[k].get("commons", []))
    all_commons_titles = sorted(set(all_commons_titles))

    print(f"Rezolvăm metadatele pentru {len(all_commons_titles)} fișiere Wikimedia Commons...")
    commons_meta = resolve_commons_metadata(all_commons_titles)

    manifest = {}
    for key in required_keys:
        # Dacă deja există pe disc și e valid, nu mai descărcăm inutil
        prev = existing_manifest.get(key)
        if prev:
            prev_disk = os.path.join(BASE_DIR, prev["path"].lstrip("/"))
            if os.path.exists(prev_disk):
                with open(prev_disk, "rb") as pf:
                    if detect_image_ext(pf.read()):
                        manifest[key] = prev
                        continue

        spec = CURATED_MEDIA_SOURCES[key]
        candidates = []
        for durl, dcredit in spec.get("direct", []):
            candidates.append((durl, dcredit))
        for ctitle in spec.get("commons", []):
            if ctitle in commons_meta:
                meta = commons_meta[ctitle]
                candidates.append((meta["url"], meta["credit"]))
                if meta.get("orig_url") and meta["orig_url"] != meta["url"]:
                    candidates.append((meta["orig_url"], meta["credit"]))

        saved = False
        for cand_url, cand_credit in candidates:
            if not cand_url:
                continue
            print(f"[{key}] Descărcare: {cand_url[:80]}...")
            raw = download_bytes(cand_url)
            if not raw:
                continue
            ext = detect_image_ext(raw)
            if not ext:
                print(f"  [INVALID] Nu este imagine validă (>= 8KB JPEG/PNG/WEBP)")
                continue
            # Curățăm eventuale fișiere vechi cu altă extensie
            for old_ext in ("jpg", "jpeg", "png", "webp"):
                old_p = os.path.join(IMAGES_DIR, f"{key}.{old_ext}")
                if os.path.exists(old_p):
                    os.remove(old_p)
            out_file = os.path.join(IMAGES_DIR, f"{key}.{ext}")
            with open(out_file, "wb") as out:
                out.write(raw)
            manifest[key] = {
                "path": f"/static/images/{key}.{ext}",
                "credit": cand_credit,
                "source_url": cand_url,
                "size_bytes": len(raw),
            }
            print(f"  [OK] {key}.{ext} ({len(raw) // 1024} KB)")
            saved = True
            time.sleep(0.35)
            break

        if not saved:
            raise RuntimeError(f"Nu s-a putut descărca nicio imagine validă pentru {key}!")

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Succes! {len(manifest)}/{len(required_keys)} imagini reale descărcate și validate în {IMAGES_DIR}.")


if __name__ == "__main__":
    main()
