/**
 * Utilitare de normalizare lingvistică și căutare FTS5 pentru Cloudflare D1.
 * Port 1:1 din `search_utils.py` pentru consistență completă cu backend-ul Python.
 */

const SYNONYM_GROUPS = [
  {
    triggers: new Set(["zeama", "zama", "zemii", "zemei", "zeamei", "zemuri", "zeam"]),
    prefixes: ["zeam"],
    tokens: ["zeama", "zama", "zemii", "zemei", "ciorba", "bors"],
  },
  {
    triggers: new Set(["cires", "cirese", "cireselor", "ciresar", "ciresii", "ciresi", "visine", "visina"]),
    prefixes: ["cires", "visin"],
    tokens: ["cires", "cirese", "cireselor", "ciresar", "ciresi", "visine"],
  },
  {
    triggers: new Set(["iamania"]),
    phrases: ["ia mania"],
    prefixes: [],
    tokens: ["iamania", "ia", "mania", "ie", "altita", "port", "popular"],
  },
  {
    triggers: new Set(["ie", "altita", "sezatoare", "sezatori"]),
    phrases: ["port popular", "portului popular", "camasa cu altita"],
    prefixes: [],
    tokens: ["ie", "altita", "port", "popular"],
  },
  {
    triggers: new Set(["placinta", "placinte", "placintelor", "varzari", "varzare", "invartita", "invartite", "gozleme", "geozleme"]),
    prefixes: ["placint", "varzar", "invartit"],
    tokens: ["placinta", "placinte", "placintelor", "varzari", "invartita"],
  },
  {
    triggers: new Set(["bostan", "bostani", "bostanului", "dovleac", "dovleci", "bostaniada"]),
    prefixes: ["bostan", "dovle"],
    tokens: ["bostan", "bostani", "dovleac", "dovleci"],
  },
  {
    triggers: new Set(["lavanda", "levantica", "lavender"]),
    prefixes: ["lavand", "levant", "lavender"],
    tokens: ["lavanda", "levantica", "lavender"],
  },
  {
    triggers: new Set(["patlagica", "patlagici", "rosii", "rosie", "tomate", "tomata"]),
    prefixes: ["patlagic", "tomat"],
    tokens: ["patlagica", "patlagici", "rosii", "tomate"],
  },
  {
    triggers: new Set(["mar", "mere", "marului", "merelor"]),
    prefixes: ["marul"],
    tokens: ["mar", "mere", "marului", "merelor"],
  },
  {
    triggers: new Set(["pruna", "prune", "prunei", "prunelor", "prunari"]),
    prefixes: ["prun"],
    tokens: ["pruna", "prune", "prunei", "prunelor"],
  },
  {
    triggers: new Set(["capsuni", "capsune", "capsunilor"]),
    prefixes: ["capsun"],
    tokens: ["capsuni", "capsune", "capsunilor"],
  },
  {
    triggers: new Set(["piersic", "piersici", "piersicului", "piersicilor"]),
    prefixes: ["piersic"],
    tokens: ["piersic", "piersici", "piersicului"],
  },
  {
    triggers: new Set(["cartof", "cartofi", "cartofului", "cartofilor"]),
    prefixes: ["cartof"],
    tokens: ["cartof", "cartofi", "cartofului"],
  },
  {
    triggers: new Set(["olar", "olari", "olarit", "olarului", "ceramica", "lut"]),
    prefixes: ["olar", "ceramic"],
    tokens: ["olar", "olari", "olarit", "olarului", "ceramica", "lut"],
  },
  {
    triggers: new Set(["covor", "covoare", "covorului", "scoarta", "scoarte"]),
    prefixes: ["covor", "scoart"],
    tokens: ["covor", "covoare", "scoarta"],
  },
  {
    triggers: new Set(["prosop", "stergar", "stergare", "iprosop"]),
    prefixes: ["prosop", "stergar"],
    tokens: ["prosop", "stergar"],
  },
  {
    triggers: new Set(["vin", "vinuri", "vinului", "vinarie", "vinarii", "crama", "crame", "degustare", "must", "tulburel", "spumant", "oenoturism"]),
    prefixes: ["vinar", "cram", "degust", "spumant"],
    tokens: ["vin", "vinuri", "vinului", "vinarie", "vinarii", "crama", "crame", "degustare", "spumant", "oenoturism"],
  },
  {
    triggers: new Set(["ceadir", "ciadir", "gagauzia", "gagauz", "gagauza", "gagauze", "gagauzesti", "kavurma", "shorpa", "surpa"]),
    prefixes: ["ceadir", "ciadir", "gagauz"],
    tokens: ["ceadir", "ciadir", "gagauzia", "gagauz", "kavurma", "shorpa", "surpa"],
  },
  {
    triggers: new Set(["targ", "targul", "targuri", "iarmaroc", "piata", "fermieri", "producatori", "artizanat", "mestesuguri", "mestesugari"]),
    prefixes: ["targ", "fermier", "producator", "artizan", "mestesug"],
    tokens: ["targ", "iarmaroc", "piata", "fermieri", "producatori", "artizanat", "mestesuguri"],
  },
  {
    triggers: new Set(["opera", "muzica", "concert", "jazz", "rock", "folk", "simfonic"]),
    prefixes: ["concert", "simfonic"],
    tokens: ["opera", "muzica", "concert", "festival"],
  },
  {
    triggers: new Set(["craciun", "revelion"]),
    prefixes: ["craciun"],
    tokens: ["craciun", "iarna", "revelion"],
  },
  {
    triggers: new Set(["miere", "apicole", "stupina", "albine"]),
    prefixes: ["apicol"],
    tokens: ["miere", "mierii", "apicole"],
  },
  {
    triggers: new Set(["desert", "deserturi", "prajituri", "dulce", "dulciuri", "patiserie", "ciocolata"]),
    prefixes: ["desert", "prajitur", "patiser"],
    tokens: ["desert", "deserturi", "prajituri", "dulce", "patiserie"],
  },
];

const SPACELESS_ALIASES = [
  ["ia mania", "iamania"],
  ["yard sale", "yardsale"],
  ["orheiul vechi", "orheiulvechi"],
  ["castel mimi", "castelmimi"],
  ["milestii mici", "milestiimici"],
  ["rusestii noi", "rusestiinoi"],
  ["dubasarii vechi", "dubasariivechi"],
  ["clisova noua", "clisovanoua"],
  ["ceadir lunga", "ceadirlunga ciadirlunga"],
  ["gagauz sofrasi", "gagauzsofrasi"],
  ["padurea domneasca", "padureadomneasca"],
  ["mai dulce", "maidulce"],
];

const QUERY_REWRITES = {
  iamania: "ia mania",
  ciadir: "ceadir",
  zama: "zeama",
  zemii: "zeama",
  zemei: "zeama",
  zeamei: "zeama",
  yardsale: "yard sale",
  ceadirlunga: "ceadir lunga",
  ciadirlunga: "ceadir lunga",
  castelmimi: "castel mimi",
  milestiimici: "milestii mici",
  orheiulvechi: "orheiul vechi",
  rusestiinoi: "rusestii noi",
  dubasariivechi: "dubasarii vechi",
  clisovanoua: "clisova noua",
  maidulce: "mai dulce",
};

const CHAR_MAP = {
  "ă": "a", "â": "a", "à": "a", "á": "a",
  "î": "i", "ï": "i", "í": "i",
  "ș": "s", "ş": "s", "ś": "s", "š": "s",
  "ț": "t", "ţ": "t",
  "ö": "o", "ó": "o", "ü": "u", "ú": "u",
  "é": "e", "è": "e", "ç": "c",
};

export function stripDiacritics(text) {
  if (!text) return "";
  let s = String(text).toLowerCase();
  for (const [src, dst] of Object.entries(CHAR_MAP)) {
    s = s.split(src).join(dst);
  }
  s = s.normalize("NFKD").replace(/[\u0300-\u036f]/g, "");
  return s.replace(/[^a-z0-9]+/g, " ").replace(/\s+/g, " ").trim();
}

export function expandSynonyms(normalizedText) {
  if (!normalizedText) return "";
  const wordsArr = normalizedText.split(" ");
  const words = new Set(wordsArr);
  const extras = [];

  for (const [phrase, alias] of SPACELESS_ALIASES) {
    if (normalizedText.includes(phrase)) {
      extras.push(alias);
    }
  }

  for (const grp of SYNONYM_GROUPS) {
    let matched = false;
    for (const t of grp.triggers) {
      if (words.has(t)) {
        matched = true;
        break;
      }
    }
    if (!matched && grp.phrases) {
      for (const ph of grp.phrases) {
        if (normalizedText.includes(ph)) {
          matched = true;
          break;
        }
      }
    }
    if (!matched && grp.prefixes && grp.prefixes.length > 0) {
      if (wordsArr.some((w) => grp.prefixes.some((p) => w.startsWith(p)))) {
        matched = true;
      }
    }
    if (matched) {
      extras.push(...grp.tokens);
    }
  }

  const seen = new Set();
  const uniqueExtras = [];
  for (const tok of extras) {
    for (const subtok of tok.split(" ")) {
      if (subtok && !seen.has(subtok)) {
        seen.add(subtok);
        uniqueExtras.push(subtok);
      }
    }
  }

  if (uniqueExtras.length === 0) return normalizedText;
  return `${normalizedText} ${uniqueExtras.join(" ")}`;
}

export function buildFtsText(...fields) {
  const joined = fields.filter(Boolean).map(String).join(" ");
  return expandSynonyms(stripDiacritics(joined));
}

export function buildFtsQuery(rawQ) {
  const norm = stripDiacritics(rawQ);
  if (!norm) return "";

  const expanded = [];
  for (const tok of norm.split(" ")) {
    const rewritten = QUERY_REWRITES[tok] || tok;
    expanded.push(...rewritten.split(" "));
  }

  const ftsParts = [];
  for (const tok of expanded) {
    if (tok.length >= 3) {
      ftsParts.push(`"${tok}"*`);
    } else if (tok.length >= 1) {
      ftsParts.push(`"${tok}"`);
    }
  }
  return ftsParts.join(" AND ");
}

export async function upsertFtsEntry(db, itemType, itemId, slug, titlu, contentFields, taguri) {
  await db
    .prepare("DELETE FROM search_fts WHERE item_type = ? AND item_id = ?")
    .bind(itemType, itemId)
    .run();
  await db
    .prepare(
      "INSERT INTO search_fts (item_type, item_id, slug, titlu_norm, content_norm, taguri_norm) VALUES (?, ?, ?, ?, ?, ?)"
    )
    .bind(
      itemType,
      itemId,
      slug,
      buildFtsText(titlu),
      buildFtsText(...contentFields),
      buildFtsText(taguri)
    )
    .run();
}

export async function deleteFtsEntry(db, itemType, itemId) {
  await db
    .prepare("DELETE FROM search_fts WHERE item_type = ? AND item_id = ?")
    .bind(itemType, itemId)
    .run();
}
