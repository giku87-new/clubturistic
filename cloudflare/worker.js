/**
 * Cloudflare Worker pentru ClubTuristic.md v2.0
 * Paritate completă cu backend-ul FastAPI:
 * - Static HTML/JS + imagini cache-uite în KV (MEDIA_KV) & Cache API
 * - Pagini SEO server-rendered cu OpenGraph (/eveniment/:slug, /locatie/:slug)
 * - Căutare full-text D1 FTS5 cu ranking BM25 & sinonime românești
 * - Export calendar RFC 5545 (.ics)
 * - Propuneri comunitare & Admin CRUD protejat prin timing-safe HTTP Basic Auth
 */

import {
  buildFtsQuery,
  deleteFtsEntry,
  stripDiacritics,
  upsertFtsEntry,
} from "./search_utils.js";
import { MEDIA_SOURCES } from "./media_sources.js";

const HTML_HEADERS = {
  "Content-Type": "text/html; charset=utf-8",
  "Cache-Control": "public, max-age=300",
};

function jsonResponse(data, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      ...extraHeaders,
    },
  });
}

function escapeHtmlAttr(val) {
  return String(val ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function serializeRow(row) {
  if (!row) return null;
  const out = { ...row };
  const rawSurse = out.surse_media_json || "[]";
  delete out.surse_media_json;
  try {
    out.surse_media = JSON.parse(rawSurse);
  } catch {
    out.surse_media = [];
  }
  return out;
}

function makeSlug(text, prefix = "item") {
  const norm = stripDiacritics(text);
  const slug = norm.replace(/\s+/g, "-").replace(/^-+|-+$/g, "");
  return slug || `${prefix}-${Math.floor(Date.now() / 1000)}`;
}

function guessContentType(filename) {
  const lower = filename.toLowerCase();
  if (lower.endsWith(".webp")) return "image/webp";
  if (lower.endsWith(".png")) return "image/png";
  return "image/jpeg";
}

function icsEscape(val) {
  return String(val ?? "")
    .replace(/\\/g, "\\\\")
    .replace(/\r\n/g, "\\n")
    .replace(/\n/g, "\\n")
    .replace(/,/g, "\\,")
    .replace(/;/g, "\\;");
}

async function timingSafeStrEqual(a, b) {
  const enc = new TextEncoder();
  const [hashA, hashB] = await Promise.all([
    crypto.subtle.digest("SHA-256", enc.encode(String(a ?? ""))),
    crypto.subtle.digest("SHA-256", enc.encode(String(b ?? ""))),
  ]);
  return crypto.subtle.timingSafeEqual(hashA, hashB);
}

async function requireAdmin(request, env) {
  const adminUser = env.ADMIN_USER;
  const adminPass = env.ADMIN_PASS;
  if (!adminUser || !adminPass) {
    return { ok: false, status: 500, error: "Secretele ADMIN_USER / ADMIN_PASS nu sunt configurate." };
  }

  const auth = request.headers.get("Authorization") || "";
  if (!auth.startsWith("Basic ")) {
    return { ok: false, status: 401 };
  }

  let decoded = "";
  try {
    const rawBin = atob(auth.slice(6).trim());
    const bytes = Uint8Array.from(rawBin, (c) => c.charCodeAt(0));
    decoded = new TextDecoder().decode(bytes);
  } catch {
    return { ok: false, status: 401 };
  }

  const colonIdx = decoded.indexOf(":");
  if (colonIdx === -1) {
    return { ok: false, status: 401 };
  }
  const reqUser = decoded.slice(0, colonIdx);
  const reqPass = decoded.slice(colonIdx + 1);

  const [uOk, pOk] = await Promise.all([
    timingSafeStrEqual(reqUser, adminUser),
    timingSafeStrEqual(reqPass, adminPass),
  ]);
  if (!uOk || !pOk) {
    return { ok: false, status: 401 };
  }
  return { ok: true, user: reqUser };
}

function unauthorizedResponse(status = 401, message = "Autentificare necesară pentru administrare.") {
  return jsonResponse(
    { detail: message },
    status,
    status === 401 ? { "WWW-Authenticate": 'Basic realm="ClubTuristic Admin"' } : {}
  );
}

async function cachePutSafe(cacheKey, response) {
  try {
    await caches.default.put(cacheKey, response);
  } catch {
    // Cache API poate fi ignorat fără erori pe rute workers.dev
  }
}

async function serveStaticFromKv(env, kvKey, contentType, cacheControl) {
  const text = await env.MEDIA_KV.get(kvKey, "text");
  if (text === null) {
    return new Response("Resursa statică nu a fost încărcată în KV.", { status: 404 });
  }
  return new Response(text, {
    status: 200,
    headers: {
      "Content-Type": contentType,
      "Cache-Control": cacheControl,
    },
  });
}

async function handleImageRequest(request, env, ctx, filename) {
  if (!/^[a-zA-Z0-9._-]+$/.test(filename)) {
    return new Response("Not Found", { status: 404 });
  }

  try {
    const cached = await caches.default.match(request);
    if (cached) return cached;
  } catch {
    // Continuăm din KV
  }

  const kvEntry = await env.MEDIA_KV.getWithMetadata(filename, "arrayBuffer");
  if (kvEntry && kvEntry.value) {
    const ct = kvEntry.metadata?.contentType || guessContentType(filename);
    const resp = new Response(kvEntry.value, {
      status: 200,
      headers: {
        "Content-Type": ct,
        "Cache-Control": "public, max-age=2592000, immutable",
      },
    });
    ctx.waitUntil(cachePutSafe(request, resp.clone()));
    return resp;
  }

  const src = MEDIA_SOURCES[filename];
  if (!src) {
    return new Response("Image Not Found", { status: 404 });
  }

  const upstream = await fetch(src.url, {
    headers: { "User-Agent": "ClubTuristicMD/2.0 (https://clubturistic.md; contact@clubturistic.md)" },
  });
  const ct = upstream.headers.get("Content-Type") || src.contentType || guessContentType(filename);
  if (!upstream.ok || !ct.startsWith("image/")) {
    return new Response("Upstream image unavailable", { status: 404 });
  }
  const buf = await upstream.arrayBuffer();
  if (buf.byteLength < 8000) {
    return new Response("Invalid upstream image", { status: 404 });
  }

  const resp = new Response(buf, {
    status: 200,
    headers: {
      "Content-Type": ct,
      "Cache-Control": "public, max-age=2592000, immutable",
    },
  });
  ctx.waitUntil(env.MEDIA_KV.put(filename, buf, { metadata: { contentType: ct } }));
  ctx.waitUntil(cachePutSafe(request, resp.clone()));
  return resp;
}

function buildJsonLd(itemType, item, desc, absImg, canonical, origin) {
  let ldObj;
  if (itemType === "eveniment") {
    const startDate = String(item.urmatoarea_data_estimata || "2027-06-01").slice(0, 10);
    const isFree = String(item.pret_intrare || "").toLowerCase().includes("gratuit");
    ldObj = {
      "@context": "https://schema.org",
      "@type": "Event",
      name: item.titlu,
      description: desc.slice(0, 300),
      startDate,
      endDate: startDate,
      eventAttendanceMode: "https://schema.org/OfflineEventAttendanceMode",
      eventStatus: "https://schema.org/EventScheduled",
      isAccessibleForFree: isFree,
      image: [absImg],
      url: canonical,
      location: {
        "@type": "Place",
        name: item.locatie_exacta || item.localitate || "Republica Moldova",
        address: {
          "@type": "PostalAddress",
          addressLocality: item.localitate || "",
          addressRegion: item.raion || item.regiune || "",
          addressCountry: "MD",
        },
        geo: {
          "@type": "GeoCoordinates",
          latitude: item.lat ?? 47.0105,
          longitude: item.lng ?? 28.8638,
        },
      },
      organizer: {
        "@type": "Organization",
        name: item.organizator || "ClubTuristic.md",
        url: item.link_oficial || origin,
      },
    };
  } else {
    ldObj = {
      "@context": "https://schema.org",
      "@type": "TouristAttraction",
      name: item.titlu,
      description: desc.slice(0, 300),
      image: [absImg],
      url: canonical,
      address: {
        "@type": "PostalAddress",
        streetAddress: item.adresa || "",
        addressLocality: item.localitate || "",
        addressRegion: item.raion || item.regiune || "",
        addressCountry: "MD",
      },
      geo: {
        "@type": "GeoCoordinates",
        latitude: item.lat ?? 47.0105,
        longitude: item.lng ?? 28.8638,
      },
    };
  }
  return JSON.stringify(ldObj).replace(/<\//g, "<\\/").replace(/<!--/g, "<\\!--");
}

async function renderDetailPage(env, requestUrl, itemType, row) {
  if (!row) {
    return new Response("Nu a fost găsit", { status: 404 });
  }
  const item = serializeRow(row);
  const tpl = await env.MEDIA_KV.get("__static__/detail.html", "text");
  if (!tpl) {
    return new Response("Șablon detail.html lipsă", { status: 500 });
  }

  const pageTitle = `${item.titlu} — ClubTuristic.md`;
  const desc = (item.descriere_scurta || item.cum_a_fost_real || item.ce_merita_vazut || "").slice(0, 220);
  const imgUrl = item.imagine_url || "/static/images/chisinau.jpg";
  const absImg = imgUrl.startsWith("http") ? imgUrl : new URL(imgUrl, requestUrl.origin).href;

  const payloadSafe = JSON.stringify({ item_type: itemType, item })
    .replace(/<\//g, "<\\/")
    .replace(/<!--/g, "<\\!--");
  const jsonLdSafe = buildJsonLd(itemType, item, desc, absImg, requestUrl.href, requestUrl.origin);

  const replacements = {
    __META_TITLE__: escapeHtmlAttr(pageTitle),
    __META_DESCRIPTION__: escapeHtmlAttr(desc),
    __OG_IMAGE__: escapeHtmlAttr(absImg),
    __OG_URL__: escapeHtmlAttr(requestUrl.href),
    __JSON_LD__: jsonLdSafe,
    __INITIAL_ITEM_JSON__: payloadSafe,
  };

  let rendered = tpl;
  for (const [marker, val] of Object.entries(replacements)) {
    rendered = rendered.split(marker).join(val);
  }
  return new Response(rendered, { status: 200, headers: HTML_HEADERS });
}

// ============================================================================
// PUBLIC API HANDLERS
// ============================================================================

async function handleGetEvenimente(env, sp) {
  const q = (sp.get("q") || "").trim();
  const tip = (sp.get("tip") || "").trim();
  const regiune = (sp.get("regiune") || "").trim();
  const sezon = (sp.get("sezon") || "").trim();
  const luna = (sp.get("luna") || "").trim();
  const gratuit = (sp.get("gratuit") || "").trim();
  const limit = Math.min(Math.max(parseInt(sp.get("limit") || "100", 10) || 100, 1), 500);
  const offset = Math.max(parseInt(sp.get("offset") || "0", 10) || 0, 0);

  const ftsExpr = q ? buildFtsQuery(q) : "";
  const usedFts = Boolean(ftsExpr);
  const args = [];

  let baseFrom = "FROM evenimente e";
  if (usedFts) {
    baseFrom += " JOIN search_fts f ON f.item_type = 'eveniment' AND f.item_id = e.id WHERE search_fts MATCH ?";
    args.push(ftsExpr);
  } else {
    baseFrom += " WHERE 1=1";
  }

  if (tip && tip !== "Toate") {
    baseFrom += " AND e.tip = ?";
    args.push(tip);
  }
  if (regiune && regiune !== "Toate") {
    baseFrom += " AND e.regiune = ?";
    args.push(regiune);
  }
  if (sezon && sezon !== "Toate") {
    baseFrom += " AND e.sezon = ?";
    args.push(sezon);
  }
  if (luna && luna !== "Toate") {
    baseFrom +=
      " AND (e.luna_principala = ? OR (',' || REPLACE(e.luni_active, ', ', ',') || ',') LIKE ? OR e.luni_active LIKE '%Tot anul%')";
    args.push(luna, `%,${luna},%`);
  }
  if (["1", "true", "True"].includes(gratuit)) {
    baseFrom += " AND LOWER(e.pret_intrare) LIKE '%gratuit%'";
  }

  const orderSql = usedFts
    ? " ORDER BY bm25(search_fts, 10.0, 2.0, 4.0) ASC, e.este_recomandat DESC"
    : " ORDER BY e.este_recomandat DESC, e.urmatoarea_data_estimata ASC";

  const totalRow = await env.DB.prepare(`SELECT COUNT(*) AS cnt ${baseFrom}`).bind(...args).first();
  const rowsRes = await env.DB.prepare(`SELECT e.* ${baseFrom}${orderSql} LIMIT ? OFFSET ?`)
    .bind(...args, limit, offset)
    .all();

  return jsonResponse({
    total: totalRow?.cnt || 0,
    items: (rowsRes.results || []).map(serializeRow),
  });
}

async function handleGetEventIcs(env, slug) {
  const row = await env.DB.prepare("SELECT * FROM evenimente WHERE slug = ?").bind(slug).first();
  if (!row) return jsonResponse({ detail: "Evenimentul nu a fost găsit" }, 404);

  const rawDate = String(row.urmatoarea_data_estimata || "2027-06-01").slice(0, 10);
  const parts = rawDate.split("-").map(Number);
  const dtStart =
    parts.length === 3 && !parts.some(Number.isNaN)
      ? new Date(Date.UTC(parts[0], parts[1] - 1, parts[2]))
      : new Date(Date.UTC(2027, 5, 1));
  const dtEnd = new Date(dtStart.getTime() + 86400000);

  const fmtDate = (d) =>
    `${d.getUTCFullYear()}${String(d.getUTCMonth() + 1).padStart(2, "0")}${String(d.getUTCDate()).padStart(2, "0")}`;
  const now = new Date();
  const dtstamp = `${fmtDate(now)}T${String(now.getUTCHours()).padStart(2, "0")}${String(now.getUTCMinutes()).padStart(2, "0")}${String(now.getUTCSeconds()).padStart(2, "0")}Z`;

  const lines = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//ClubTuristic.md//Calendar Evenimente Moldova//RO",
    "CALSCALE:GREGORIAN",
    "BEGIN:VEVENT",
    `UID:${row.id}@clubturistic.md`,
    `DTSTAMP:${dtstamp}`,
    `DTSTART;VALUE=DATE:${fmtDate(dtStart)}`,
    `DTEND;VALUE=DATE:${fmtDate(dtEnd)}`,
    `SUMMARY:${icsEscape(row.titlu)}`,
    `LOCATION:${icsEscape(`${row.locatie_exacta}, ${row.localitate}, Moldova`)}`,
    `DESCRIPTION:${icsEscape(`${row.descriere_scurta} | Recurență: ${row.regula_recurenta} | Detalii: ${row.link_oficial}`)}`,
    `URL:${row.link_oficial}`,
    "END:VEVENT",
    "END:VCALENDAR",
  ];

  return new Response(`${lines.join("\r\n")}\r\n`, {
    status: 200,
    headers: {
      "Content-Type": "text/calendar; charset=utf-8",
      "Content-Disposition": `attachment; filename="${slug}.ics"`,
    },
  });
}

async function handleGetLocatii(env, sp) {
  const q = (sp.get("q") || "").trim();
  const categorie = (sp.get("categorie") || "").trim();
  const regiune = (sp.get("regiune") || "").trim();
  const limit = Math.min(Math.max(parseInt(sp.get("limit") || "100", 10) || 100, 1), 500);
  const offset = Math.max(parseInt(sp.get("offset") || "0", 10) || 0, 0);

  const ftsExpr = q ? buildFtsQuery(q) : "";
  const usedFts = Boolean(ftsExpr);
  const args = [];

  let baseFrom = "FROM locatii l";
  if (usedFts) {
    baseFrom += " JOIN search_fts f ON f.item_type = 'locatie' AND f.item_id = l.id WHERE search_fts MATCH ?";
    args.push(ftsExpr);
  } else {
    baseFrom += " WHERE 1=1";
  }

  if (categorie && categorie !== "Toate") {
    baseFrom += " AND l.categorie = ?";
    args.push(categorie);
  }
  if (regiune && regiune !== "Toate") {
    baseFrom += " AND l.regiune = ?";
    args.push(regiune);
  }

  const orderSql = usedFts
    ? " ORDER BY bm25(search_fts, 10.0, 2.0, 4.0) ASC, l.este_recomandat DESC"
    : " ORDER BY l.este_recomandat DESC, l.distanta_chisinau_km ASC";

  const totalRow = await env.DB.prepare(`SELECT COUNT(*) AS cnt ${baseFrom}`).bind(...args).first();
  const rowsRes = await env.DB.prepare(`SELECT l.* ${baseFrom}${orderSql} LIMIT ? OFFSET ?`)
    .bind(...args, limit, offset)
    .all();

  return jsonResponse({
    total: totalRow?.cnt || 0,
    items: (rowsRes.results || []).map(serializeRow),
  });
}

async function handleGetHramuri(env, sp) {
  const q = (sp.get("q") || "").trim();
  const regiune = (sp.get("regiune") || "").trim();
  const luna = (sp.get("luna") || "").trim();

  const ftsExpr = q ? buildFtsQuery(q) : "";
  const args = [];
  let baseFrom = "FROM hramuri_notabile h";
  if (ftsExpr) {
    baseFrom += " JOIN search_fts f ON f.item_type = 'hram' AND f.item_id = h.id WHERE search_fts MATCH ?";
    args.push(ftsExpr);
  } else {
    baseFrom += " WHERE 1=1";
  }

  if (regiune && regiune !== "Toate") {
    baseFrom += " AND h.regiune = ?";
    args.push(regiune);
  }
  if (luna && luna !== "Toate") {
    baseFrom += " AND h.luna_principala = ?";
    args.push(luna);
  }

  const totalRow = await env.DB.prepare(`SELECT COUNT(*) AS cnt ${baseFrom}`).bind(...args).first();
  const rowsRes = await env.DB.prepare(`SELECT h.* ${baseFrom} ORDER BY h.titlu ASC`).bind(...args).all();

  return jsonResponse({
    total: totalRow?.cnt || 0,
    items: (rowsRes.results || []).map(serializeRow),
  });
}

async function handleGetStats(env) {
  const [ev, loc, hrm, prop, tips, regs, sezs, luns] = await Promise.all([
    env.DB.prepare("SELECT COUNT(*) AS c FROM evenimente").first(),
    env.DB.prepare("SELECT COUNT(*) AS c FROM locatii").first(),
    env.DB.prepare("SELECT COUNT(*) AS c FROM hramuri_notabile").first(),
    env.DB.prepare("SELECT COUNT(*) AS c FROM propuneri_comunitate WHERE status = 'In asteptare'").first(),
    env.DB.prepare("SELECT tip AS k, COUNT(*) AS c FROM evenimente GROUP BY tip").all(),
    env.DB.prepare("SELECT regiune AS k, COUNT(*) AS c FROM evenimente GROUP BY regiune").all(),
    env.DB.prepare("SELECT sezon AS k, COUNT(*) AS c FROM evenimente GROUP BY sezon").all(),
    env.DB.prepare("SELECT luna_principala AS k, COUNT(*) AS c FROM evenimente GROUP BY luna_principala").all(),
  ]);

  const toMap = (res) => Object.fromEntries((res.results || []).map((r) => [r.k, r.c]));
  return jsonResponse({
    evenimente: ev?.c || 0,
    locatii: loc?.c || 0,
    hramuri_notabile: hrm?.c || 0,
    propuneri_in_asteptare: prop?.c || 0,
    by_tip: toMap(tips),
    by_regiune: toMap(regs),
    by_sezon: toMap(sezs),
    by_luna: toMap(luns),
  });
}

async function handleCreatePropunere(request, env) {
  let body;
  try {
    body = await request.json();
  } catch {
    return jsonResponse({ detail: "JSON invalid" }, 400);
  }

  const titlu = String(body.titlu || "").trim();
  const localitate = String(body.localitate || "").trim();
  const linkSursa = String(body.link_sursa || "").trim();

  if (titlu.length < 3 || localitate.length < 2) {
    return jsonResponse({ detail: "Titlul (min. 3 caractere) și localitatea (min. 2 caractere) sunt obligatorii." }, 422);
  }
  if (!(linkSursa.startsWith("http://") || linkSursa.startsWith("https://"))) {
    return jsonResponse({ detail: "Link-ul sursă trebuie să înceapă cu http:// sau https://" }, 422);
  }

  const res = await env.DB.prepare(
    `INSERT INTO propuneri_comunitate (
      tip_entitate, titlu, localitate, raion, data_text, descriere, link_sursa, contact_expeditor
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)`
  )
    .bind(
      String(body.tip_entitate || "Eveniment / Festival").trim().slice(0, 80),
      titlu.slice(0, 180),
      localitate.slice(0, 120),
      String(body.raion || "").trim().slice(0, 80),
      String(body.data_text || "").trim().slice(0, 120),
      String(body.descriere || "").trim().slice(0, 1200),
      linkSursa.slice(0, 400),
      String(body.contact_expeditor || "").trim().slice(0, 120)
    )
    .run();

  return jsonResponse(
    {
      success: true,
      id: res.meta?.last_row_id || null,
      message: "Propunerea a fost trimisă spre verificare editorială.",
    },
    201
  );
}

// ============================================================================
// ADMIN CRUD HANDLERS (PROTECTED)
// ============================================================================

function normalizeEventPayload(body, existingSlug = null) {
  const titlu = String(body.titlu || "").trim();
  if (titlu.length < 2) throw new Error("Titlul evenimentului este obligatoriu.");
  const slug = String(body.slug || existingSlug || makeSlug(titlu, "evt")).trim();
  return {
    slug,
    titlu,
    tip: String(body.tip || "Festival Gastronomic"),
    organizator: String(body.organizator || "Organizator Local"),
    regiune: String(body.regiune || "Centru"),
    raion: String(body.raion || "Chișinău"),
    localitate: String(body.localitate || "mun. Chișinău"),
    locatie_exacta: String(body.locatie_exacta || ""),
    lat: Number.isFinite(Number(body.lat)) ? Number(body.lat) : 47.0105,
    lng: Number.isFinite(Number(body.lng)) ? Number(body.lng) : 28.8638,
    distanta_chisinau_km: parseInt(body.distanta_chisinau_km ?? 0, 10) || 0,
    data_text: String(body.data_text || "Anual (de confirmat)"),
    regula_recurenta: String(body.regula_recurenta || "Anual"),
    tip_recurenta: String(body.tip_recurenta || "Recurență relativă"),
    luna_principala: String(body.luna_principala || "Iunie"),
    luni_active: String(body.luni_active || body.luna_principala || "Iunie"),
    sezon: String(body.sezon || "Vară"),
    ultima_editie_verificata: String(body.ultima_editie_verificata || "Confirmat prin sursă publică"),
    urmatoarea_data_estimata: String(body.urmatoarea_data_estimata || "2027-06-15"),
    status_data: String(body.status_data || "Estimat după tradiție"),
    pret_intrare: String(body.pret_intrare || "Gratuit"),
    descriere_scurta: String(body.descriere_scurta || ""),
    cum_a_fost_real: String(body.cum_a_fost_real || ""),
    ce_gusti: String(body.ce_gusti || ""),
    taguri: String(body.taguri || ""),
    link_oficial: String(body.link_oficial || "https://moldova.travel/ro"),
    surse_media_json: JSON.stringify(Array.isArray(body.surse_media) ? body.surse_media : []),
    imagine_url: String(body.imagine_url || "/static/images/chisinau.jpg"),
    imagine_credit: String(body.imagine_credit || "Arhivă verificată ClubTuristic.md"),
    este_recomandat: parseInt(body.este_recomandat ?? 0, 10) || 0,
  };
}

function normalizeLocationPayload(body, existingSlug = null) {
  const titlu = String(body.titlu || "").trim();
  if (titlu.length < 2) throw new Error("Titlul locației este obligatoriu.");
  const slug = String(body.slug || existingSlug || makeSlug(titlu, "loc")).trim();
  return {
    slug,
    titlu,
    categorie: String(body.categorie || "Cramă & Resort Turistic"),
    regiune: String(body.regiune || "Centru"),
    raion: String(body.raion || "Chișinău"),
    localitate: String(body.localitate || ""),
    adresa: String(body.adresa || ""),
    lat: Number.isFinite(Number(body.lat)) ? Number(body.lat) : 47.0105,
    lng: Number.isFinite(Number(body.lng)) ? Number(body.lng) : 28.8638,
    distanta_chisinau_km: parseInt(body.distanta_chisinau_km ?? 0, 10) || 0,
    program_vizita: String(body.program_vizita || "Cu programare"),
    rezervare_necesara: String(body.rezervare_necesara || "Recomandată"),
    buget_orientativ: String(body.buget_orientativ || "300 - 700 MDL"),
    descriere_scurta: String(body.descriere_scurta || ""),
    ce_merita_vazut: String(body.ce_merita_vazut || ""),
    ce_gusti: String(body.ce_gusti || ""),
    taguri: String(body.taguri || ""),
    link_oficial: String(body.link_oficial || "https://moldova.travel/ro"),
    surse_media_json: JSON.stringify(Array.isArray(body.surse_media) ? body.surse_media : []),
    imagine_url: String(body.imagine_url || "/static/images/vineyard_moldova.jpg"),
    imagine_credit: String(body.imagine_credit || "Arhivă verificată ClubTuristic.md"),
    este_recomandat: parseInt(body.este_recomandat ?? 0, 10) || 0,
  };
}

async function indexEvent(db, id, d) {
  await upsertFtsEntry(
    db,
    "eveniment",
    id,
    d.slug,
    d.titlu,
    [
      d.tip, d.organizator, d.regiune, d.raion, d.localitate, d.locatie_exacta,
      d.data_text, d.luni_active, d.descriere_scurta, d.cum_a_fost_real, d.ce_gusti,
    ],
    d.taguri
  );
}

async function indexLocation(db, id, d) {
  await upsertFtsEntry(
    db,
    "locatie",
    id,
    d.slug,
    d.titlu,
    [
      d.categorie, d.regiune, d.raion, d.localitate, d.adresa,
      d.descriere_scurta, d.ce_merita_vazut, d.ce_gusti,
    ],
    d.taguri
  );
}

// ============================================================================
// MAIN FETCH ROUTER
// ============================================================================

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const { pathname, searchParams } = url;
    const method = request.method.toUpperCase();

    console.log(JSON.stringify({ message: "incoming_request", method, path: pathname }));

    try {
      // Static HTML, SEO & JS routes
      if (method === "GET" && (pathname === "/" || pathname === "/index.html")) {
        return serveStaticFromKv(env, "__static__/index.html", "text/html; charset=utf-8", "public, max-age=300");
      }
      if (method === "GET" && pathname === "/robots.txt") {
        const body = `User-agent: *\nAllow: /\nDisallow: /admin\nDisallow: /api/admin/\nSitemap: ${url.origin}/sitemap.xml\n`;
        return new Response(body, {
          status: 200,
          headers: { "Content-Type": "text/plain; charset=utf-8", "Cache-Control": "public, max-age=3600" },
        });
      }
      if (method === "GET" && (pathname === "/sitemap.xml" || pathname === "/static/sitemap.xml")) {
        const today = new Date().toISOString().slice(0, 10);
        const [evRes, locRes] = await Promise.all([
          env.DB.prepare("SELECT slug, actualizat_la FROM evenimente ORDER BY slug").all(),
          env.DB.prepare("SELECT slug, actualizat_la FROM locatii ORDER BY slug").all(),
        ]);
        const urls = [
          `  <url><loc>${escapeHtmlAttr(url.origin)}/</loc><lastmod>${today}</lastmod><changefreq>daily</changefreq><priority>1.0</priority></url>`,
        ];
        for (const r of evRes.results || []) {
          const lm = String(r.actualizat_la || today).slice(0, 10);
          urls.push(
            `  <url><loc>${escapeHtmlAttr(`${url.origin}/eveniment/${r.slug}`)}</loc><lastmod>${lm}</lastmod><changefreq>weekly</changefreq><priority>0.8</priority></url>`
          );
        }
        for (const r of locRes.results || []) {
          const lm = String(r.actualizat_la || today).slice(0, 10);
          urls.push(
            `  <url><loc>${escapeHtmlAttr(`${url.origin}/locatie/${r.slug}`)}</loc><lastmod>${lm}</lastmod><changefreq>monthly</changefreq><priority>0.8</priority></url>`
          );
        }
        const xml = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls.join("\n")}\n</urlset>\n`;
        return new Response(xml, {
          status: 200,
          headers: { "Content-Type": "application/xml; charset=utf-8", "Cache-Control": "public, max-age=3600" },
        });
      }
      if (method === "GET" && (pathname === "/admin" || pathname === "/admin.html")) {
        return serveStaticFromKv(env, "__static__/admin.html", "text/html; charset=utf-8", "no-store");
      }
      if (method === "GET" && pathname === "/static/js/app.js") {
        return serveStaticFromKv(env, "__static__/js/app.js", "application/javascript; charset=utf-8", "public, max-age=3600");
      }
      if (method === "GET" && pathname === "/static/js/admin.js") {
        return serveStaticFromKv(env, "__static__/js/admin.js", "application/javascript; charset=utf-8", "public, max-age=3600");
      }
      if (method === "GET" && pathname.startsWith("/static/images/")) {
        const filename = decodeURIComponent(pathname.slice("/static/images/".length));
        return handleImageRequest(request, env, ctx, filename);
      }
      if (method === "GET" && pathname === "/favicon.ico") {
        return handleImageRequest(request, env, ctx, "logo.png");
      }

      // Server-rendered SEO detail pages
      if (method === "GET" && pathname.startsWith("/eveniment/")) {
        const slug = decodeURIComponent(pathname.slice("/eveniment/".length));
        const row = await env.DB.prepare("SELECT * FROM evenimente WHERE slug = ?").bind(slug).first();
        return renderDetailPage(env, url, "eveniment", row);
      }
      if (method === "GET" && pathname.startsWith("/locatie/")) {
        const slug = decodeURIComponent(pathname.slice("/locatie/".length));
        const row = await env.DB.prepare("SELECT * FROM locatii WHERE slug = ?").bind(slug).first();
        return renderDetailPage(env, url, "locatie", row);
      }

      // Public JSON API
      if (method === "GET" && pathname === "/api/evenimente") {
        return handleGetEvenimente(env, searchParams);
      }
      if (method === "GET" && pathname.startsWith("/api/evenimente/") && pathname.endsWith("/ics")) {
        const slug = decodeURIComponent(pathname.slice("/api/evenimente/".length, -"/ics".length));
        return handleGetEventIcs(env, slug);
      }
      if (method === "GET" && pathname.startsWith("/api/evenimente/")) {
        const slug = decodeURIComponent(pathname.slice("/api/evenimente/".length));
        const row = await env.DB.prepare("SELECT * FROM evenimente WHERE slug = ?").bind(slug).first();
        return row ? jsonResponse(serializeRow(row)) : jsonResponse({ detail: "Evenimentul nu a fost găsit" }, 404);
      }
      if (method === "GET" && pathname === "/api/locatii") {
        return handleGetLocatii(env, searchParams);
      }
      if (method === "GET" && pathname.startsWith("/api/locatii/")) {
        const slug = decodeURIComponent(pathname.slice("/api/locatii/".length));
        const row = await env.DB.prepare("SELECT * FROM locatii WHERE slug = ?").bind(slug).first();
        return row ? jsonResponse(serializeRow(row)) : jsonResponse({ detail: "Locația nu a fost găsită" }, 404);
      }
      if (method === "GET" && pathname === "/api/hramuri") {
        return handleGetHramuri(env, searchParams);
      }
      if (method === "GET" && pathname === "/api/stats") {
        return handleGetStats(env);
      }
      if (method === "POST" && pathname === "/api/propuneri") {
        return handleCreatePropunere(request, env);
      }

      // Admin API (Protected)
      if (pathname.startsWith("/api/admin/")) {
        const authRes = await requireAdmin(request, env);
        if (!authRes.ok) {
          return unauthorizedResponse(authRes.status, authRes.error);
        }

        if (method === "GET" && pathname === "/api/admin/me") {
          return jsonResponse({ user: authRes.user, authenticated: true });
        }

        if (method === "POST" && pathname === "/api/admin/evenimente") {
          const body = await request.json();
          const d = normalizeEventPayload(body);
          const suffix = Math.floor(Date.now() / 1000) % 10000;
          const id = body.id || `evt-${d.slug}-${suffix}`;
          const existingSlug = await env.DB.prepare("SELECT 1 FROM evenimente WHERE slug = ?").bind(d.slug).first();
          if (existingSlug) d.slug = `${d.slug}-${suffix}`;

          await env.DB.prepare(
            `INSERT INTO evenimente (
              id, slug, titlu, tip, organizator, regiune, raion, localitate, locatie_exacta,
              lat, lng, distanta_chisinau_km, data_text, regula_recurenta, tip_recurenta,
              luna_principala, luni_active, sezon, ultima_editie_verificata, urmatoarea_data_estimata,
              status_data, pret_intrare, descriere_scurta, cum_a_fost_real, ce_gusti, taguri,
              link_oficial, surse_media_json, imagine_url, imagine_credit, este_recomandat
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
          )
            .bind(
              id, d.slug, d.titlu, d.tip, d.organizator, d.regiune, d.raion, d.localitate,
              d.locatie_exacta, d.lat, d.lng, d.distanta_chisinau_km, d.data_text, d.regula_recurenta,
              d.tip_recurenta, d.luna_principala, d.luni_active, d.sezon, d.ultima_editie_verificata,
              d.urmatoarea_data_estimata, d.status_data, d.pret_intrare, d.descriere_scurta,
              d.cum_a_fost_real, d.ce_gusti, d.taguri, d.link_oficial, d.surse_media_json,
              d.imagine_url, d.imagine_credit, d.este_recomandat
            )
            .run();
          await indexEvent(env.DB, id, d);
          const created = await env.DB.prepare("SELECT * FROM evenimente WHERE id = ?").bind(id).first();
          return jsonResponse({ success: true, item: serializeRow(created) }, 201);
        }

        if (method === "PUT" && pathname.startsWith("/api/admin/evenimente/")) {
          const itemId = decodeURIComponent(pathname.slice("/api/admin/evenimente/".length));
          const existing = await env.DB.prepare("SELECT slug FROM evenimente WHERE id = ?").bind(itemId).first();
          if (!existing) return jsonResponse({ detail: "Evenimentul nu există" }, 404);
          const body = await request.json();
          const d = normalizeEventPayload(body, existing.slug);
          await env.DB.prepare(
            `UPDATE evenimente SET
              slug = ?, titlu = ?, tip = ?, organizator = ?, regiune = ?, raion = ?,
              localitate = ?, locatie_exacta = ?, lat = ?, lng = ?, distanta_chisinau_km = ?,
              data_text = ?, regula_recurenta = ?, tip_recurenta = ?, luna_principala = ?,
              luni_active = ?, sezon = ?, ultima_editie_verificata = ?, urmatoarea_data_estimata = ?,
              status_data = ?, pret_intrare = ?, descriere_scurta = ?, cum_a_fost_real = ?,
              ce_gusti = ?, taguri = ?, link_oficial = ?, surse_media_json = ?,
              imagine_url = ?, imagine_credit = ?, este_recomandat = ?, actualizat_la = CURRENT_TIMESTAMP
            WHERE id = ?`
          )
            .bind(
              d.slug, d.titlu, d.tip, d.organizator, d.regiune, d.raion, d.localitate,
              d.locatie_exacta, d.lat, d.lng, d.distanta_chisinau_km, d.data_text, d.regula_recurenta,
              d.tip_recurenta, d.luna_principala, d.luni_active, d.sezon, d.ultima_editie_verificata,
              d.urmatoarea_data_estimata, d.status_data, d.pret_intrare, d.descriere_scurta,
              d.cum_a_fost_real, d.ce_gusti, d.taguri, d.link_oficial, d.surse_media_json,
              d.imagine_url, d.imagine_credit, d.este_recomandat, itemId
            )
            .run();
          await indexEvent(env.DB, itemId, d);
          const updated = await env.DB.prepare("SELECT * FROM evenimente WHERE id = ?").bind(itemId).first();
          return jsonResponse({ success: true, item: serializeRow(updated) });
        }

        if (method === "DELETE" && pathname.startsWith("/api/admin/evenimente/")) {
          const itemId = decodeURIComponent(pathname.slice("/api/admin/evenimente/".length));
          const del = await env.DB.prepare("DELETE FROM evenimente WHERE id = ?").bind(itemId).run();
          if ((del.meta?.changes || 0) === 0) return jsonResponse({ detail: "Evenimentul nu există" }, 404);
          await deleteFtsEntry(env.DB, "eveniment", itemId);
          return jsonResponse({ success: true, deleted: itemId });
        }

        if (method === "POST" && pathname === "/api/admin/locatii") {
          const body = await request.json();
          const d = normalizeLocationPayload(body);
          const suffix = Math.floor(Date.now() / 1000) % 10000;
          const id = body.id || `loc-${d.slug}-${suffix}`;
          const existingSlug = await env.DB.prepare("SELECT 1 FROM locatii WHERE slug = ?").bind(d.slug).first();
          if (existingSlug) d.slug = `${d.slug}-${suffix}`;

          await env.DB.prepare(
            `INSERT INTO locatii (
              id, slug, titlu, categorie, regiune, raion, localitate, adresa,
              lat, lng, distanta_chisinau_km, program_vizita, rezervare_necesara, buget_orientativ,
              descriere_scurta, ce_merita_vazut, ce_gusti, taguri, link_oficial,
              surse_media_json, imagine_url, imagine_credit, este_recomandat
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
          )
            .bind(
              id, d.slug, d.titlu, d.categorie, d.regiune, d.raion, d.localitate, d.adresa,
              d.lat, d.lng, d.distanta_chisinau_km, d.program_vizita, d.rezervare_necesara,
              d.buget_orientativ, d.descriere_scurta, d.ce_merita_vazut, d.ce_gusti, d.taguri,
              d.link_oficial, d.surse_media_json, d.imagine_url, d.imagine_credit, d.este_recomandat
            )
            .run();
          await indexLocation(env.DB, id, d);
          const created = await env.DB.prepare("SELECT * FROM locatii WHERE id = ?").bind(id).first();
          return jsonResponse({ success: true, item: serializeRow(created) }, 201);
        }

        if (method === "PUT" && pathname.startsWith("/api/admin/locatii/")) {
          const itemId = decodeURIComponent(pathname.slice("/api/admin/locatii/".length));
          const existing = await env.DB.prepare("SELECT slug FROM locatii WHERE id = ?").bind(itemId).first();
          if (!existing) return jsonResponse({ detail: "Locația nu există" }, 404);
          const body = await request.json();
          const d = normalizeLocationPayload(body, existing.slug);
          await env.DB.prepare(
            `UPDATE locatii SET
              slug = ?, titlu = ?, categorie = ?, regiune = ?, raion = ?, localitate = ?,
              adresa = ?, lat = ?, lng = ?, distanta_chisinau_km = ?, program_vizita = ?,
              rezervare_necesara = ?, buget_orientativ = ?, descriere_scurta = ?,
              ce_merita_vazut = ?, ce_gusti = ?, taguri = ?, link_oficial = ?,
              surse_media_json = ?, imagine_url = ?, imagine_credit = ?, este_recomandat = ?,
              actualizat_la = CURRENT_TIMESTAMP
            WHERE id = ?`
          )
            .bind(
              d.slug, d.titlu, d.categorie, d.regiune, d.raion, d.localitate, d.adresa,
              d.lat, d.lng, d.distanta_chisinau_km, d.program_vizita, d.rezervare_necesara,
              d.buget_orientativ, d.descriere_scurta, d.ce_merita_vazut, d.ce_gusti, d.taguri,
              d.link_oficial, d.surse_media_json, d.imagine_url, d.imagine_credit, d.este_recomandat, itemId
            )
            .run();
          await indexLocation(env.DB, itemId, d);
          const updated = await env.DB.prepare("SELECT * FROM locatii WHERE id = ?").bind(itemId).first();
          return jsonResponse({ success: true, item: serializeRow(updated) });
        }

        if (method === "DELETE" && pathname.startsWith("/api/admin/locatii/")) {
          const itemId = decodeURIComponent(pathname.slice("/api/admin/locatii/".length));
          const del = await env.DB.prepare("DELETE FROM locatii WHERE id = ?").bind(itemId).run();
          if ((del.meta?.changes || 0) === 0) return jsonResponse({ detail: "Locația nu există" }, 404);
          await deleteFtsEntry(env.DB, "locatie", itemId);
          return jsonResponse({ success: true, deleted: itemId });
        }

        if (method === "GET" && pathname === "/api/admin/propuneri") {
          const res = await env.DB.prepare("SELECT * FROM propuneri_comunitate ORDER BY id DESC").all();
          const items = res.results || [];
          return jsonResponse({ total: items.length, items });
        }

        if (method === "POST" && pathname.startsWith("/api/admin/propuneri/") && pathname.endsWith("/status")) {
          const pid = parseInt(pathname.slice("/api/admin/propuneri/".length, -"/status".length), 10);
          const body = await request.json();
          if (!["In asteptare", "Aprobat", "Respins"].includes(body.status)) {
            return jsonResponse({ detail: "Status invalid" }, 422);
          }
          const upd = await env.DB.prepare("UPDATE propuneri_comunitate SET status = ? WHERE id = ?").bind(body.status, pid).run();
          if ((upd.meta?.changes || 0) === 0) return jsonResponse({ detail: "Propunerea nu există" }, 404);
          return jsonResponse({ success: true, id: pid, status: body.status });
        }

        if (method === "DELETE" && pathname.startsWith("/api/admin/propuneri/")) {
          const pid = parseInt(pathname.slice("/api/admin/propuneri/".length), 10);
          const del = await env.DB.prepare("DELETE FROM propuneri_comunitate WHERE id = ?").bind(pid).run();
          if ((del.meta?.changes || 0) === 0) return jsonResponse({ detail: "Propunerea nu există" }, 404);
          return jsonResponse({ success: true, deleted: pid });
        }
      }

      return new Response("Not Found", { status: 404 });
    } catch (err) {
      console.error(JSON.stringify({ message: "request_failed", path: pathname, error: String(err) }));
      return jsonResponse({ detail: "Eroare internă de procesare." }, 500);
    }
  },
};
