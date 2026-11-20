"""
Utilitare de normalizare lingvistică și căutare FTS5 pentru ClubTuristic.md.
Elimină diacriticele românești, curăță caracterele speciale FTS5 și extinde
sinonimele/formele flexionare populare din Republica Moldova la indexare.
"""

import re
import unicodedata

# Grupuri de sinonime și forme flexionare/dialectale românești & găgăuze
SYNONYM_GROUPS = [
    {
        "triggers": {"zeama", "zama", "zemii", "zemei", "zeamei", "zemuri", "zeam"},
        "prefixes": ("zeam",),
        "tokens": ["zeama", "zama", "zemii", "zemei", "ciorba", "bors"],
    },
    {
        "triggers": {"cires", "cirese", "cireselor", "ciresar", "ciresii", "ciresi", "visine", "visina"},
        "prefixes": ("cires", "visin"),
        "tokens": ["cires", "cirese", "cireselor", "ciresar", "ciresi", "visine"],
    },
    {
        "triggers": {"iamania"},
        "phrases": ("ia mania",),
        "prefixes": (),
        "tokens": ["iamania", "ia", "mania", "ie", "altita", "port", "popular"],
    },
    {
        "triggers": {"ie", "altita", "sezatoare", "sezatori"},
        "phrases": ("port popular", "portului popular", "camasa cu altita"),
        "prefixes": (),
        "tokens": ["ie", "altita", "port", "popular"],
    },
    {
        "triggers": {"placinta", "placinte", "placintelor", "varzari", "varzare", "invartita", "invartite", "gozleme", "geozleme"},
        "prefixes": ("placint", "varzar", "invartit"),
        "tokens": ["placinta", "placinte", "placintelor", "varzari", "invartita"],
    },
    {
        "triggers": {"bostan", "bostani", "bostanului", "dovleac", "dovleci", "bostaniada"},
        "prefixes": ("bostan", "dovle"),
        "tokens": ["bostan", "bostani", "dovleac", "dovleci"],
    },
    {
        "triggers": {"lavanda", "levantica", "lavender"},
        "prefixes": ("lavand", "levant", "lavender"),
        "tokens": ["lavanda", "levantica", "lavender"],
    },
    {
        "triggers": {"patlagica", "patlagici", "rosii", "rosie", "tomate", "tomata"},
        "prefixes": ("patlagic", "tomat"),
        "tokens": ["patlagica", "patlagici", "rosii", "tomate"],
    },
    {
        "triggers": {"mar", "mere", "marului", "merelor"},
        "prefixes": ("marul",),
        "tokens": ["mar", "mere", "marului", "merelor"],
    },
    {
        "triggers": {"pruna", "prune", "prunei", "prunelor", "prunari"},
        "prefixes": ("prun",),
        "tokens": ["pruna", "prune", "prunei", "prunelor"],
    },
    {
        "triggers": {"capsuni", "capsune", "capsunilor"},
        "prefixes": ("capsun",),
        "tokens": ["capsuni", "capsune", "capsunilor"],
    },
    {
        "triggers": {"piersic", "piersici", "piersicului", "piersicilor"},
        "prefixes": ("piersic",),
        "tokens": ["piersic", "piersici", "piersicului"],
    },
    {
        "triggers": {"cartof", "cartofi", "cartofului", "cartofilor"},
        "prefixes": ("cartof",),
        "tokens": ["cartof", "cartofi", "cartofului"],
    },
    {
        "triggers": {"olar", "olari", "olarit", "olarului", "ceramica", "lut"},
        "prefixes": ("olar", "ceramic"),
        "tokens": ["olar", "olari", "olarit", "olarului", "ceramica", "lut"],
    },
    {
        "triggers": {"covor", "covoare", "covorului", "scoarta", "scoarte"},
        "prefixes": ("covor", "scoart"),
        "tokens": ["covor", "covoare", "scoarta"],
    },
    {
        "triggers": {"prosop", "stergar", "stergare", "iprosop"},
        "prefixes": ("prosop", "stergar"),
        "tokens": ["prosop", "stergar"],
    },
    {
        "triggers": {"vin", "vinuri", "vinului", "vinarie", "vinarii", "crama", "crame", "degustare", "must", "tulburel", "spumant", "oenoturism"},
        "prefixes": ("vinar", "cram", "degust", "spumant"),
        "tokens": ["vin", "vinuri", "vinului", "vinarie", "vinarii", "crama", "crame", "degustare", "spumant", "oenoturism"],
    },
    {
        "triggers": {"ceadir", "ciadir", "gagauzia", "gagauz", "gagauza", "gagauze", "gagauzesti", "kavurma", "shorpa", "surpa"},
        "prefixes": ("ceadir", "ciadir", "gagauz"),
        "tokens": ["ceadir", "ciadir", "gagauzia", "gagauz", "kavurma", "shorpa", "surpa"],
    },
    {
        "triggers": {"targ", "targul", "targuri", "iarmaroc", "piata", "fermieri", "producatori", "artizanat", "mestesuguri", "mestesugari"},
        "prefixes": ("targ", "fermier", "producator", "artizan", "mestesug"),
        "tokens": ["targ", "iarmaroc", "piata", "fermieri", "producatori", "artizanat", "mestesuguri"],
    },
    {
        "triggers": {"opera", "muzica", "concert", "jazz", "rock", "folk", "simfonic"},
        "prefixes": ("concert", "simfonic"),
        "tokens": ["opera", "muzica", "concert", "festival"],
    },
    {
        "triggers": {"craciun", "revelion"},
        "prefixes": ("craciun",),
        "tokens": ["craciun", "iarna", "revelion"],
    },
    {
        "triggers": {"miere", "apicole", "stupina", "albine"},
        "prefixes": ("apicol",),
        "tokens": ["miere", "mierii", "apicole"],
    },
    {
        "triggers": {"desert", "deserturi", "prajituri", "dulce", "dulciuri", "patiserie", "ciocolata"},
        "prefixes": ("desert", "prajitur", "patiser"),
        "tokens": ["desert", "deserturi", "prajituri", "dulce", "patiserie"],
    },
]

# Expresii celebre cautate frecvent legate (fără spațiu) sau în variante fonetice
SPACELESS_ALIASES = [
    ("ia mania", "iamania"),
    ("yard sale", "yardsale"),
    ("orheiul vechi", "orheiulvechi"),
    ("castel mimi", "castelmimi"),
    ("milestii mici", "milestiimici"),
    ("rusestii noi", "rusestiinoi"),
    ("dubasarii vechi", "dubasariivechi"),
    ("clisova noua", "clisovanoua"),
    ("ceadir lunga", "ceadirlunga ciadirlunga"),
    ("gagauz sofrasi", "gagauzsofrasi"),
    ("padurea domneasca", "padureadomneasca"),
    ("mai dulce", "maidulce"),
]

QUERY_REWRITES = {
    "iamania": "ia mania",
    "ciadir": "ceadir",
    "zama": "zeama",
    "zemii": "zeama",
    "zemei": "zeama",
    "zeamei": "zeama",
    "yardsale": "yard sale",
    "ceadirlunga": "ceadir lunga",
    "ciadirlunga": "ceadir lunga",
    "castelmimi": "castel mimi",
    "milestiimici": "milestii mici",
    "orheiulvechi": "orheiul vechi",
    "rusestiinoi": "rusestii noi",
    "dubasariivechi": "dubasarii vechi",
    "clisovanoua": "clisova noua",
    "maidulce": "mai dulce",
}


def strip_diacritics(text: str) -> str:
    """Normalizează textul românesc: lowercase, fără diacritice și fără punctuație."""
    if not text:
        return ""
    s = text.lower()
    replacements = {
        "ă": "a", "â": "a", "à": "a", "á": "a",
        "î": "i", "ï": "i", "í": "i",
        "ș": "s", "ş": "s", "ś": "s", "š": "s",
        "ț": "t", "ţ": "t",
        "ö": "o", "ó": "o", "ü": "u", "ú": "u",
        "é": "e", "è": "e", "ç": "c",
    }
    for src, dst in replacements.items():
        s = s.replace(src, dst)
    # Fallback Unicode decomposition pentru alte accente
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def expand_synonyms(normalized_text: str) -> str:
    """Extinde sinonimele și formele flexionare pentru indexare FTS5."""
    if not normalized_text:
        return ""
    words = set(normalized_text.split())
    extras = []

    for phrase, alias in SPACELESS_ALIASES:
        if phrase in normalized_text:
            extras.append(alias)

    for grp in SYNONYM_GROUPS:
        matched = False
        if words & grp.get("triggers", set()):
            matched = True
        if not matched:
            for ph in grp.get("phrases", ()):
                if ph in normalized_text:
                    matched = True
                    break
        if not matched:
            prefs = grp.get("prefixes", ())
            if prefs and any(w.startswith(prefs) for w in words):
                matched = True
        if matched:
            extras.extend(grp["tokens"])

    # Eliminăm duplicatele păstrând ordinea
    seen = set()
    unique_extras = []
    for tok in extras:
        for subtok in tok.split():
            if subtok not in seen:
                seen.add(subtok)
                unique_extras.append(subtok)

    if not unique_extras:
        return normalized_text
    return normalized_text + " " + " ".join(unique_extras)


def build_fts_text(*fields) -> str:
    """Construiește textul normalizat + sinonime pentru o coloană FTS5."""
    joined = " ".join(str(f) for f in fields if f)
    norm = strip_diacritics(joined)
    return expand_synonyms(norm)


def build_fts_query(raw_q: str) -> str:
    """
    Construiește o expresie FTS5 sigură (imună la erori de sintaxă pe semne de punctuație).
    Returnează șir gol dacă interogarea nu conține tokeni alfanumerici.
    """
    norm = strip_diacritics(raw_q)
    if not norm:
        return ""

    raw_tokens = norm.split()
    expanded_tokens = []
    for tok in raw_tokens:
        rewritten = QUERY_REWRITES.get(tok, tok)
        expanded_tokens.extend(rewritten.split())

    fts_parts = []
    for tok in expanded_tokens:
        if len(tok) >= 3:
            # În FTS5, "tok"* efectuează căutare pe prefix și evită cuvintele rezervate (and/or/not)
            fts_parts.append(f'"{tok}"*')
        elif len(tok) >= 1:
            fts_parts.append(f'"{tok}"')

    return " AND ".join(fts_parts)


def upsert_fts_entry(conn, item_type: str, item_id: str, slug: str, titlu: str, content_fields: list, taguri: str) -> None:
    """Actualizează sau inserează intrarea normalizată în indexul FTS5."""
    conn.execute(
        "DELETE FROM search_fts WHERE item_type = ? AND item_id = ?",
        (item_type, item_id),
    )
    conn.execute(
        """
        INSERT INTO search_fts (item_type, item_id, slug, titlu_norm, content_norm, taguri_norm)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            item_type,
            item_id,
            slug,
            build_fts_text(titlu),
            build_fts_text(*content_fields),
            build_fts_text(taguri),
        ),
    )


def delete_fts_entry(conn, item_type: str, item_id: str) -> None:
    """Elimină o intrare din indexul FTS5."""
    conn.execute(
        "DELETE FROM search_fts WHERE item_type = ? AND item_id = ?",
        (item_type, item_id),
    )

