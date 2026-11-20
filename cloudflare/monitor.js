/**
 * Motor de monitorizare incrementala (stateful) pentru ClubTuristic.md.
 * - Scaneaza agende de evenimente (Fest.md, iTicket, Sporter), portaluri de stiri RSS,
 *   Radio Moldova / Moldova 1 si site-uri oficiale de crame & festivaluri.
 * - Foloseste HTTP conditional (ETag / Last-Modified) + tabela `surse_articole_vazute`
 *   ca sa NU repete niciodata cautarea pe articole sau anunturi deja procesate.
 * - Pune potrivirile noi in `actualizari_detectate` (status: 'De verificat') pentru
 *   aprobare cu 1 clic in `/admin`.
 */

import { stripDiacritics } from "./search_utils.js";

const RO_MONTHS = {
  ianuarie: 1, ian: 1,
  februarie: 2, feb: 2,
  martie: 3, mar: 3,
  aprilie: 4, apr: 4,
  mai: 5,
  iunie: 6, iun: 6,
  iulie: 7, iul: 7,
  august: 8, aug: 8,
  septembrie: 9, sep: 9, sept: 9,
  octombrie: 10, oct: 10,
  noiembrie: 11, noi: 11, nov: 11,
  decembrie: 12, dec: 12,
};

const KNOWN_EVENT_PHRASES = [
  ["evt-ia-mania-holercani", ["ia mania", "iamania"]],
  ["evt-bostaniada-balabanesti", ["bostaniada"]],
  ["evt-descopera-butuceni", ["descopera butuceni", "festivalul descopera"]],
  ["evt-gustar-orheiul-vechi", ["gustar music", "festivalul gustar"]],
  ["evt-festivalul-lupilor-orheiul-vechi", ["festivalul lupilor", "lupii lui calancea"]],
  ["evt-underland-cricova", ["underland"]],
  ["evt-vernisajul-vinului-chisinau", ["vernisajul vinului"]],
  ["evt-ziua-nationala-a-vinului", ["ziua nationala a vinului", "ziua vinului"]],
  ["evt-mai-dulce-chisinau", ["mai dulce"]],
  ["evt-lavender-fest-cobusca", ["lavender fest"]],
  ["evt-ciresar-truseni", ["festivalul ciresar", "ciresar truseni"]],
  ["evt-cireselor-varzarilor-rusestii-noi", ["rusestii noi", "varzarilor"]],
  ["evt-festivalul-zemii-sipoteni", ["festivalul zemii", "zemii sipoteni"]],
  ["evt-festivalul-marului-soroca", ["festivalul marului", "festivalul national al marului"]],
  ["evt-festivalul-prunei-nisporeni", ["festivalul prunei", "festivalul national al prunei"]],
  ["evt-capsunilor-mierii-sadova", ["capsunilor", "sadova"]],
  ["evt-hai-la-piersici-tudora", ["hai la piersici", "tudora"]],
  ["evt-iprosop-selemet", ["iprosop"]],
  ["evt-frumos-covor-basarabean-clisova", ["frumos covor basarabean", "clisova"]],
  ["evt-vatra-olarului-hoginesti", ["vatra olarului", "hoginesti"]],
  ["evt-festivalul-patlagica-dubasarii-vechi", ["patlagica"]],
  ["evt-festivalul-cartofului-corjeuti", ["festivalul cartofului", "corjeuti"]],
  ["evt-hederlez-ceadir-lunga", ["hederlez"]],
  ["evt-gagauz-sarap-yortusu-comrat", ["sarap yortusu", "vinului gagauz"]],
  ["evt-vinopera-castel-mimi", ["vinopera", "rose day castel mimi"]],
  ["evt-milestii-mici-winerun", ["milestii mici winerun", "winerun"]],
  ["evt-purcari-wine-run", ["purcari wine run", "nocturne night run purcari"]],
  ["evt-ecolocal-chisinau", ["ecolocal"]],
  ["evt-yard-sale-chisinau", ["yard sale", "yardsale"]],
  ["evt-ziua-portului-popular", ["ziua portului popular", "ziua nationala a portului"]],
  ["evt-festivalul-padurilor-condrita", ["festivalul padurilor"]],
  ["evt-festivalul-martisor-chisinau", ["festivalul martisor", "martisor"]],
  ["evt-ethno-jazz-chisinau", ["ethno jazz"]],
  ["evt-targul-de-craciun-chisinau", ["targul de craciun chisinau", "oraselul sarbatorilor"]],
  ["evt-festivalul-bach-2026", ["festivalul j s bach", "festivalul international bach"]],
  ["evt-satul-meu-vatra-aleasa-cahul-2026", ["satul meu vatra aleasa"]],
  ["evt-moldova-accordion-days-2026", ["accordion days", "rapsodia romana"]],
  ["evt-targul-international-caritate-2026", ["targul international de caritate"]],
  ["evt-joc-cricova-subteran-2026", ["ansamblul joc cricova", "joc in orasul subteran"]],
  ["evt-covorul-dorului-2026", ["covorul dorului"]],
];

const TOURISM_RELEVANCE_TERMS = [
  "festival", "targ", "crama", "vin ", "vinuri", "degustare", "usilor deschise",
  "hram", "folclor", "traditional", "placinte", "zeama", "mamaliga", "bostan",
  "lavanda", "cires", "craciun", "turism", "orheiul vechi", "butuceni",
  "cricova", "castel mimi", "purcari", "milestii mici", "moldexpo",
  "concert simfonic", "expozitie", "mestesugar", "olarii", "vinicol", "maraton",
];

const NOISE_TERMS = [
  "accident", "politie", "incendiu", "dosar penal", "retinut", "coruptie",
  "procuratura", "salmonella", "decedat", "tragedie", "perchezitii",
  "contrabanda", "arest", "inculpat", "sentinta", "omor",
];

const AGENDA_SKIP_TERMS = [
  "cinema", "imax", "bilete film", "avatar", "desene animate",
  "cursa taxi", "reducere black friday", "cursuri online",
  "filmul", " 2d", " 3d", "friday party", "friday night", "dj set",
  "karaoke", "stand-up", "standup", "teatrul", "improvizatie",
  "vixen", "house culture",
];

export function decodeHtmlEntities(str) {
  if (!str) return "";
  return String(str)
    .replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, "$1")
    .replace(/&amp;/gi, "&")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">")
    .replace(/&quot;/gi, '"')
    .replace(/&#39;|&apos;/gi, "'")
    .replace(/&nbsp;/gi, " ")
    .replace(/&#(\d+);/g, (_, n) => {
      const code = parseInt(n, 10);
      return code > 0 && code < 0x10ffff ? String.fromCodePoint(code) : "";
    })
    .replace(/&#x([0-9a-f]+);/gi, (_, h) => {
      const code = parseInt(h, 16);
      return code > 0 && code < 0x10ffff ? String.fromCodePoint(code) : "";
    });
}

function stripTags(html) {
  return decodeHtmlEntities(String(html || ""))
    .replace(/<script[\s\S]*?<\/script>/gi, " ")
    .replace(/<style[\s\S]*?<\/style>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function resolveUrl(href, baseUrl) {
  try {
    const u = new URL(href, baseUrl);
    u.hash = "";
    return u.href;
  } catch {
    return "";
  }
}

async function sha256Hex(input, len = 32) {
  const bytes = new TextEncoder().encode(String(input || ""));
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("")
    .slice(0, len);
}

function pad2(n) {
  return String(n).padStart(2, "0");
}

function validYmd(y, m, d) {
  if (y < 2025 || y > 2030 || m < 1 || m > 12 || d < 1 || d > 31) return "";
  return `${y}-${pad2(m)}-${pad2(d)}`;
}

export function extractRomanianDates(text, fallbackYear = new Date().getUTCFullYear()) {
  if (!text) return { dataStart: "", dataEnd: "", dataText: "" };
  const raw = String(text);
  const norm = stripDiacritics(raw);

  // 1. ISO date (YYYY-MM-DD)
  const isoMatch = raw.match(/\b(202[5-9])-(\d{2})-(\d{2})\b/);
  if (isoMatch) {
    const start = validYmd(Number(isoMatch[1]), Number(isoMatch[2]), Number(isoMatch[3]));
    if (start) return { dataStart: start, dataEnd: start, dataText: isoMatch[0] };
  }

  // 2. Dotted date (DD.MM.YYYY)
  const dotMatch = raw.match(/\b(\d{1,2})\.(\d{1,2})\.(202[5-9])\b/);
  if (dotMatch) {
    const start = validYmd(Number(dotMatch[3]), Number(dotMatch[2]), Number(dotMatch[1]));
    if (start) return { dataStart: start, dataEnd: start, dataText: dotMatch[0] };
  }

  // 3. Range same month: e.g. "18 21 iunie 2026" / "2 si 3 octombrie 2027"
  const monthNamesPat = Object.keys(RO_MONTHS).join("|");
  const rangeSameMonth = new RegExp(
    `\\b(\\d{1,2})\\s*(?:si\\s+)?(\\d{1,2})\\s+(${monthNamesPat})(?:\\s+(202[5-9]))?\\b`,
    "i"
  );
  const rsm = norm.match(rangeSameMonth);
  if (rsm) {
    const d1 = Number(rsm[1]);
    const d2 = Number(rsm[2]);
    const m = RO_MONTHS[rsm[3]];
    const y = Number(rsm[4] || fallbackYear);
    const start = validYmd(y, m, d1);
    const end = validYmd(y, m, d2);
    if (start) {
      return {
        dataStart: start,
        dataEnd: end || start,
        dataText: `${d1}-${d2} ${rsm[3]} ${y}`,
      };
    }
  }

  // 4. Single date with Romanian month name: e.g. "20 noiembrie 2026" or "5 dec"
  const singleRo = new RegExp(
    `\\b(\\d{1,2})\\s+(${monthNamesPat})(?:\\s+(202[5-9]))?\\b`,
    "i"
  );
  const sm = norm.match(singleRo);
  if (sm) {
    const d = Number(sm[1]);
    const m = RO_MONTHS[sm[2]];
    const explicitYear = sm[3] ? Number(sm[3]) : null;
    let y = explicitYear || fallbackYear;
    if (!explicitYear) {
      const now = new Date();
      const curM = now.getUTCMonth() + 1;
      // Daca luna detectata a trecut deja cu >1 luna fata de luna curenta, probabil e pentru anul viitor
      if (m + 1 < curM) y = fallbackYear + 1;
    }
    const start = validYmd(y, m, d);
    if (start) {
      return { dataStart: start, dataEnd: start, dataText: `${d} ${sm[2]} ${y}` };
    }
  }

  return { dataStart: "", dataEnd: "", dataText: "" };
}

export function parseRssItems(xmlText, baseUrl) {
  const items = [];
  const blockRe = /<(item|entry)\b[^>]*>([\s\S]*?)<\/\1>/gi;
  let m;
  while ((m = blockRe.exec(xmlText)) !== null && items.length < 40) {
    const block = m[2];
    const tagVal = (tag) => {
      const r = new RegExp(`<${tag}\\b[^>]*>([\\s\\S]*?)<\\/${tag}>`, "i").exec(block);
      return r ? stripTags(r[1]) : "";
    };
    let link = tagVal("link");
    if (!link) {
      const atomHref = /<link\b[^>]*href=["']([^"']+)["']/i.exec(block);
      if (atomHref) link = atomHref[1];
    }
    const url = resolveUrl(link, baseUrl);
    if (!url) continue;
    const guid = tagVal("guid") || tagVal("id") || url;
    const titlu = tagVal("title");
    if (!titlu) continue;
    const desc = tagVal("description") || tagVal("content:encoded") || tagVal("summary") || "";
    const pubDate = tagVal("pubDate") || tagVal("updated") || tagVal("published") || "";
    items.push({
      guid,
      url,
      titlu: titlu.slice(0, 220),
      snippet: desc.slice(0, 320),
      dateHint: `${titlu} ${desc} ${pubDate}`,
      locatie: "",
    });
  }
  return items;
}

export function parseFestHtmlItems(html, baseUrl) {
  const items = [];
  const blocks = html.split(/<div[^>]*class=["'][^"']*block-item/i);
  for (let i = 1; i < blocks.length && items.length < 45; i++) {
    const chunk = blocks[i].slice(0, 3500);
    const titleMatch = /<a[^>]*class=["'][^"']*\btitle\b[^"']*["'][^>]*href=["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/i.exec(chunk);
    if (!titleMatch) continue;
    const rawHref = titleMatch[1].trim();
    const parts = rawHref.split("/").filter(Boolean);
    // Excludem linkuri de categorie (/ro/evenimente/targuri), pastram evenimente individuale
    if (parts.length < 4) continue;
    const lowHref = rawHref.toLowerCase();
    if (["/filme/", "/cluburi/", "/teatre/", "/stand-up/", "/cursuri/", "/traininguri/"].some((p) => lowHref.includes(p))) {
      continue;
    }

    const url = resolveUrl(rawHref, baseUrl || "https://fest.md");
    const titlu = stripTags(titleMatch[2]).slice(0, 220);
    if (!url || titlu.length < 4) continue;

    const calMatch = /icon-calendar[\s\S]*?<span[^>]*>([\s\S]*?)<\/span>/i.exec(chunk);
    const dateRaw = calMatch ? stripTags(calMatch[1]) : "";
    const pinMatch = /icon-pinpoint[\s\S]*?<a[^>]*>([\s\S]*?)<\/a>/i.exec(chunk);
    const locRaw = pinMatch ? stripTags(pinMatch[1]).slice(0, 140) : "";

    items.push({
      guid: url,
      url,
      titlu,
      snippet: [dateRaw, locRaw].filter(Boolean).join(" • ").slice(0, 320),
      dateHint: `${dateRaw} ${titlu}`,
      locatie: locRaw,
    });
  }
  return items;
}

function collectJsonLdEvents(node, out, baseUrl) {
  if (!node || typeof node !== "object") return;
  if (Array.isArray(node)) {
    for (const item of node) collectJsonLdEvents(item, out, baseUrl);
    return;
  }
  const tp = node["@type"];
  const isEvent = Array.isArray(tp)
    ? tp.some((t) => String(t).toLowerCase().includes("event"))
    : String(tp || "").toLowerCase().includes("event");
  if (isEvent && node.name) {
    const url = resolveUrl(node.url || "", baseUrl) || baseUrl;
    const locName =
      typeof node.location === "string"
        ? node.location
        : node.location?.name || node.location?.address?.addressLocality || "";
    const startDate = String(node.startDate || "").slice(0, 20);
    const endDate = String(node.endDate || startDate).slice(0, 20);
    out.push({
      guid: `${url}#${startDate || node.name}`,
      url,
      titlu: stripTags(node.name).slice(0, 220),
      snippet: stripTags(node.description || `${startDate} ${locName}`).slice(0, 320),
      dateHint: `${startDate} ${endDate} ${node.name}`,
      locatie: stripTags(locName).slice(0, 140),
    });
  }
  if (Array.isArray(node["@graph"])) {
    collectJsonLdEvents(node["@graph"], out, baseUrl);
  }
}

export function parseHtmlLinksAndJsonLd(html, baseUrl) {
  const items = [];
  const seenUrls = new Set();

  // 1. Structuri JSON-LD @type Event
  const ldRe = /<script[^>]*type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi;
  let m;
  while ((m = ldRe.exec(html)) !== null) {
    try {
      const parsed = JSON.parse(m[1].trim());
      const ldEvents = [];
      collectJsonLdEvents(parsed, ldEvents, baseUrl);
      for (const ev of ldEvents) {
        if (!seenUrls.has(ev.guid)) {
          seenUrls.add(ev.guid);
          items.push(ev);
        }
      }
    } catch {
      // JSON-LD invalid ignorat
    }
  }

  // 2. Linkuri relevante catre pagini de evenimente/stiri de pe acelasi domeniu
  let baseHost = "";
  try {
    baseHost = new URL(baseUrl).hostname.replace(/^www\./, "");
  } catch {
    baseHost = "";
  }
  const linkRe = /<a\b[^>]*href=["']([^"'#]+)["'][^>]*>([\s\S]*?)<\/a>/gi;
  while ((m = linkRe.exec(html)) !== null && items.length < 40) {
    const rawHref = m[1].trim();
    if (/^(mailto:|tel:|javascript:)/i.test(rawHref)) continue;
    if (/\.(css|js|png|jpe?g|webp|svg|pdf|ico)(\?|$)/i.test(rawHref)) continue;
    const url = resolveUrl(rawHref, baseUrl);
    if (!url || seenUrls.has(url)) continue;

    let uObj;
    try {
      uObj = new URL(url);
    } catch {
      continue;
    }
    const host = uObj.hostname.replace(/^www\./, "");
    if (baseHost && host !== baseHost) continue;
    const pathClean = uObj.pathname.replace(/\/+$/, "");
    if (!pathClean || pathClean === "/ro" || pathClean === "/en" || pathClean === "/events" || pathClean === "/evenimente") {
      continue;
    }
    const titlu = stripTags(m[2]).slice(0, 220);
    if (titlu.length < 8 || /^(citeste|detalii|vezi|mai mult|acasa|contact|login)/i.test(titlu)) continue;

    const afterCtx = stripTags(html.slice(m.index, m.index + 500)).slice(0, 300);
    seenUrls.add(url);
    items.push({
      guid: url,
      url,
      titlu,
      snippet: afterCtx.slice(0, 320),
      dateHint: `${titlu} ${afterCtx}`,
      locatie: "",
    });
  }
  return items;
}

function matchItemToEvents(item, source, eventsById, eventsList) {
  const combinedNorm = stripDiacritics(`${item.titlu} ${item.snippet} ${item.locatie}`);

  // Respingem stirile care sunt zgomot ne-turistic (accidente, politie, etc.)
  for (const bad of NOISE_TERMS) {
    if (combinedNorm.includes(bad)) {
      return { relevant: false, eventId: "", eventTitle: "", score: 0 };
    }
  }

  // 1. Potrivire explicita cu unul din cele 40+ evenimente din baza de date
  for (const [evtId, phrases] of KNOWN_EVENT_PHRASES) {
    for (const ph of phrases) {
      if (combinedNorm.includes(ph)) {
        const ev = eventsById.get(evtId);
        return {
          relevant: true,
          eventId: ev ? ev.id : evtId,
          eventTitle: ev ? ev.titlu : "",
          score: 95,
        };
      }
    }
  }

  // 2. Daca sursa este legata implicit de un eveniment si are un anunt nou cu data sau relevant
  if (source.eveniment_id && eventsById.has(source.eveniment_id)) {
    const ev = eventsById.get(source.eveniment_id);
    const evTokens = stripDiacritics(ev.titlu)
      .split(" ")
      .filter((t) => t.length >= 5);
    if (evTokens.some((t) => combinedNorm.includes(t))) {
      return {
        relevant: true,
        eventId: ev.id,
        eventTitle: ev.titlu,
        score: 80,
      };
    }
  }

  // 3. Potrivire dinamica pentru evenimente adaugate ulterior din Admin
  for (const ev of eventsList) {
    const normTitle = stripDiacritics(ev.titlu);
    if (normTitle.length >= 12 && combinedNorm.includes(normTitle)) {
      return { relevant: true, eventId: ev.id, eventTitle: ev.titlu, score: 85 };
    }
  }

  // 4. Descoperire evenimente noi din Agende & Site-uri Oficiale
  if (source.tip === "Agenda" || source.tip === "Website Oficial") {
    for (const skip of AGENDA_SKIP_TERMS) {
      if (combinedNorm.includes(skip)) {
        return { relevant: false, eventId: "", eventTitle: "", score: 0 };
      }
    }
    const isStrongCulture = TOURISM_RELEVANCE_TERMS.some((kw) => combinedNorm.includes(kw));
    const parsedDate = extractRomanianDates(item.dateHint);
    if (isStrongCulture || parsedDate.dataStart) {
      return {
        relevant: true,
        eventId: "",
        eventTitle: "",
        score: isStrongCulture ? 65 : 45,
      };
    }
    return { relevant: false, eventId: "", eventTitle: "", score: 0 };
  }

  // 5. Stiri / Radio / Radio-TV: doar articole care mentioneaza explicit turism/festivaluri/crame/targuri
  let hits = 0;
  for (const kw of TOURISM_RELEVANCE_TERMS) {
    if (combinedNorm.includes(kw)) hits++;
  }
  if (hits >= 1) {
    return { relevant: true, eventId: "", eventTitle: "", score: Math.min(85, 50 + hits * 10) };
  }
  return { relevant: false, eventId: "", eventTitle: "", score: 0 };
}

async function fetchSeenHashes(db, hashes) {
  const existing = new Set();
  const chunkSize = 35;
  for (let i = 0; i < hashes.length; i += chunkSize) {
    const chunk = hashes.slice(i, i + chunkSize);
    if (!chunk.length) continue;
    const placeholders = chunk.map(() => "?").join(", ");
    const res = await db
      .prepare(`SELECT item_hash FROM surse_articole_vazute WHERE item_hash IN (${placeholders})`)
      .bind(...chunk)
      .all();
    for (const r of res.results || []) {
      existing.add(r.item_hash);
    }
  }
  return existing;
}

export async function runMonitorScan(env, triggerType = "cron", options = {}) {
  const limit = Math.min(Math.max(parseInt(options.limit || "12", 10) || 12, 1), 16);
  const sursaIdFilter = String(options.sursa_id || "").trim();
  const nowIso = new Date().toISOString();
  const today = nowIso.slice(0, 10);

  let sources = [];
  if (sursaIdFilter) {
    const sourcesRes = await env.DB.prepare(
      "SELECT * FROM surse_monitorizate WHERE id = ? AND parser != 'social_manual'"
    )
      .bind(sursaIdFilter)
      .all();
    sources = sourcesRes.results || [];
  } else {
    const sourcesRes = await env.DB.prepare(
      "SELECT * FROM surse_monitorizate WHERE activ = 1 AND parser != 'social_manual' ORDER BY COALESCE(last_checked_at, '') ASC LIMIT 25"
    ).all();
    const seenHosts = new Set();
    for (const candidate of sourcesRes.results || []) {
      let host = candidate.id;
      try {
        host = new URL(candidate.url).hostname.replace(/^www\./, "");
      } catch {
        host = candidate.id;
      }
      if (seenHosts.has(host)) continue;
      seenHosts.add(host);
      sources.push(candidate);
      if (sources.length >= limit) break;
    }
  }

  const evRes = await env.DB.prepare(
    "SELECT id, slug, titlu, taguri, localitate FROM evenimente"
  ).all();
  const eventsList = evRes.results || [];
  const eventsById = new Map(eventsList.map((e) => [e.id, e]));

  let sourcesChecked = 0;
  let sourcesNotModified = 0;
  let itemsSeenSkipped = 0;
  let itemsNewScanned = 0;
  let matchesQueued = 0;
  const errors = [];
  const sourceDetails = [];

  for (const src of sources) {
    sourcesChecked++;
    try {
      const reqHeaders = {
        "User-Agent": "Mozilla/5.0 (compatible; ClubTuristicBot/2.0; +https://clubturistic.md)",
        Accept: "text/html,application/rss+xml,application/xml;q=0.9,*/*;q=0.8",
      };
      if (src.etag) reqHeaders["If-None-Match"] = src.etag;
      if (src.last_modified) reqHeaders["If-Modified-Since"] = src.last_modified;

      const resp = await fetch(src.url, {
        headers: reqHeaders,
        signal: AbortSignal.timeout(6500),
      });

      if (resp.status === 304) {
        sourcesNotModified++;
        await env.DB.prepare(
          "UPDATE surse_monitorizate SET last_checked_at = ?, last_status = '304 Not Modified', last_new_items = 0 WHERE id = ?"
        )
          .bind(nowIso, src.id)
          .run();
        sourceDetails.push({ id: src.id, status: "304", skipped: 0, new: 0, matches: 0 });
        continue;
      }

      if (!resp.ok) {
        const st = `HTTP ${resp.status}`;
        await env.DB.prepare(
          "UPDATE surse_monitorizate SET last_checked_at = ?, last_status = ?, last_new_items = 0 WHERE id = ?"
        )
          .bind(nowIso, st, src.id)
          .run();
        errors.push({ sursa: src.id, error: st });
        sourceDetails.push({ id: src.id, status: st, skipped: 0, new: 0, matches: 0 });
        continue;
      }

      const newEtag = resp.headers.get("etag") || src.etag || "";
      const newLastMod = resp.headers.get("last-modified") || src.last_modified || "";
      const bodyText = (await resp.text()).slice(0, 350000);

      let parsedItems = [];
      if (src.parser === "rss") {
        parsedItems = parseRssItems(bodyText, src.url);
      } else if (src.parser === "fest_html") {
        parsedItems = parseFestHtmlItems(bodyText, src.url);
      } else {
        parsedItems = parseHtmlLinksAndJsonLd(bodyText, src.url);
      }

      if (parsedItems.length === 0) {
        await env.DB.prepare(
          "UPDATE surse_monitorizate SET etag = ?, last_modified = ?, last_checked_at = ?, last_status = '200 OK (0 items)', last_new_items = 0 WHERE id = ?"
        )
          .bind(newEtag, newLastMod, nowIso, src.id)
          .run();
        sourceDetails.push({ id: src.id, status: "200 OK (0)", skipped: 0, new: 0, matches: 0 });
        continue;
      }

      // Calculam hash-urile si sarim instant articolele deja vazute
      const withHashes = await Promise.all(
        parsedItems.map(async (it) => ({
          item: it,
          hash: await sha256Hex(`${src.id}|${it.guid || it.url}`),
        }))
      );
      const seenSet = await fetchSeenHashes(
        env.DB,
        withHashes.map((x) => x.hash)
      );

      let srcSkipped = 0;
      let srcNew = 0;
      let srcMatches = 0;
      const seenStmts = [];
      const updateStmts = [];

      for (const { item, hash } of withHashes) {
        if (seenSet.has(hash)) {
          srcSkipped++;
          itemsSeenSkipped++;
          continue;
        }
        seenSet.add(hash);
        srcNew++;
        itemsNewScanned++;

        const m = matchItemToEvents(item, src, eventsById, eventsList);
        const dt = m.relevant ? extractRomanianDates(item.dateHint) : { dataStart: "", dataEnd: "", dataText: "" };
        const isStalePast = !m.eventId && Boolean(dt.dataStart) && dt.dataStart < today;
        const shouldQueue = m.relevant && !isStalePast;

        seenStmts.push(
          env.DB.prepare(
            "INSERT OR IGNORE INTO surse_articole_vazute (item_hash, sursa_id, url, titlu, matched) VALUES (?, ?, ?, ?, ?)"
          ).bind(hash, src.id, item.url.slice(0, 400), item.titlu.slice(0, 220), shouldQueue ? 1 : 0)
        );

        if (shouldQueue) {
          const dedupeKey = await sha256Hex(`${item.url}|${dt.dataStart || item.titlu}`);
          srcMatches++;
          matchesQueued++;
          updateStmts.push(
            env.DB.prepare(
              `INSERT OR IGNORE INTO actualizari_detectate (
                dedupe_key, sursa_id, sursa_nume, sursa_tip, eveniment_id, eveniment_titlu,
                titlu_detectat, data_start_detectata, data_end_detectata, data_text_detectat,
                locatie_detectata, descriere_snippet, url_sursa, scor_relevanta, status
              ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'De verificat')`
            ).bind(
              dedupeKey,
              src.id,
              src.nume,
              src.tip,
              m.eventId,
              m.eventTitle,
              item.titlu.slice(0, 220),
              dt.dataStart,
              dt.dataEnd,
              dt.dataText,
              item.locatie || "",
              item.snippet || "",
              item.url.slice(0, 400),
              m.score
            )
          );
        }
      }

      const allStmts = [...seenStmts, ...updateStmts];
      for (let i = 0; i < allStmts.length; i += 40) {
        await env.DB.batch(allStmts.slice(i, i + 40));
      }

      await env.DB.prepare(
        `UPDATE surse_monitorizate SET
          etag = ?, last_modified = ?, last_checked_at = ?, last_status = '200 OK',
          last_new_items = ?, total_matches = total_matches + ?
        WHERE id = ?`
      )
        .bind(newEtag, newLastMod, nowIso, srcNew, srcMatches, src.id)
        .run();

      sourceDetails.push({
        id: src.id,
        status: "200 OK",
        skipped: srcSkipped,
        new: srcNew,
        matches: srcMatches,
      });
    } catch (err) {
      const msg = String(err?.message || err).slice(0, 120);
      errors.push({ sursa: src.id, error: msg });
      await env.DB.prepare(
        "UPDATE surse_monitorizate SET last_checked_at = ?, last_status = ?, last_new_items = 0 WHERE id = ?"
      )
        .bind(nowIso, `ERR: ${msg.slice(0, 50)}`, src.id)
        .run();
      sourceDetails.push({ id: src.id, status: `ERR`, skipped: 0, new: 0, matches: 0 });
    }
  }

  await env.DB.prepare(
    `INSERT INTO monitor_runs (
      trigger_type, sources_checked, sources_not_modified, items_seen_skipped,
      items_new_scanned, matches_queued, errors_json
    ) VALUES (?, ?, ?, ?, ?, ?, ?)`
  )
    .bind(
      triggerType,
      sourcesChecked,
      sourcesNotModified,
      itemsSeenSkipped,
      itemsNewScanned,
      matchesQueued,
      JSON.stringify(errors)
    )
    .run();

  return {
    success: true,
    trigger_type: triggerType,
    ran_at: nowIso,
    sources_checked: sourcesChecked,
    sources_not_modified: sourcesNotModified,
    items_seen_skipped: itemsSeenSkipped,
    items_new_scanned: itemsNewScanned,
    matches_queued: matchesQueued,
    errors,
    sources: sourceDetails,
  };
}
