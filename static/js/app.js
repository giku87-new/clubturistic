/**
 * Logica dinamică pentru ClubTuristic.md (Portal Public).
 * Încarcă datele exclusiv din SQLite prin API REST, suportă căutare FTS5,
 * hartă interactivă Leaflet și previzualizare sigură fără XSS.
 */

let activeTab = "evenimente";
let searchTimer = null;
let leafletMap = null;
let mapMarkersLayer = null;

function escapeHtml(val) {
  if (val === null || val === undefined) return "";
  return String(val)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function safeUrl(url) {
  if (!url) return "#";
  const u = String(url).trim();
  if (u.startsWith("http://") || u.startsWith("https://") || u.startsWith("/")) {
    return u;
  }
  return "#";
}

function statusBadgeHtml(statusText, dataStart = "") {
  const s = (statusText || "").toLowerCase();
  if (s.includes("saptamanal") || s.includes("săptămânal")) {
    return `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-teal-100 text-teal-800 border border-teal-200">🔄 Săptămânal activ</span>`;
  }
  if (dataStart && s.includes("confirmat")) {
    return `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">✓ Dată exactă confirmată</span>`;
  }
  if (s.includes("confirmat")) {
    return `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">✓ Confirmat</span>`;
  }
  return `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-200">🗓️ Dată neanunțată (sezon)</span>`;
}

async function fetchStats() {
  try {
    const res = await fetch("/api/stats");
    if (!res.ok) return;
    const stats = await res.json();
    document.getElementById("cnt-evenimente").innerText = stats.evenimente;
    document.getElementById("cnt-locatii").innerText = stats.locatii;
    document.getElementById("cnt-hramuri").innerText = stats.hramuri_notabile;
  } catch (e) {
    console.warn("Eroare stats:", e);
  }
}

function updateTypeFilterOptions() {
  const sel = document.getElementById("typeFilter");
  const seasonSel = document.getElementById("seasonFilter");
  const freeWrap = document.getElementById("freeOnlyWrap");
  const confWrap = document.getElementById("confirmedOnlyWrap");

  if (activeTab === "evenimente") {
    sel.classList.remove("hidden");
    seasonSel.classList.remove("hidden");
    freeWrap.classList.remove("hidden");
    if (confWrap) confWrap.classList.remove("hidden");
    sel.innerHTML = `
      <option value="Toate">Toate tipurile de evenimente</option>
      <option value="Festival Gastronomic">🍲 Festival Gastronomic</option>
      <option value="Festival Cultural & Muzică">🎵 Festival Cultural &amp; Muzică</option>
      <option value="Târg Producători & Meșteșuguri">🧺 Târg Producători &amp; Meșteșuguri</option>
      <option value="Ziua Ușilor Deschise & Vin">🍷 Ziua Ușilor Deschise &amp; Vin</option>
      <option value="Sport & Vin">🏃 Sport &amp; Vin</option>
      <option value="Târg Sezonier">🎄 Târg Sezonier</option>
    `;
  } else if (activeTab === "locatii") {
    sel.classList.remove("hidden");
    seasonSel.classList.add("hidden");
    freeWrap.classList.add("hidden");
    if (confWrap) confWrap.classList.add("hidden");
    sel.innerHTML = `
      <option value="Toate">Toate categoriile de locuri</option>
      <option value="Cramă & Resort Turistic">🍷 Cramă &amp; Resort Turistic</option>
      <option value="Pensiune & Gastronomie">🏡 Pensiune &amp; Gastronomie</option>
      <option value="Meșteșuguri & Obiective">🏺 Meșteșuguri &amp; Obiective</option>
      <option value="Natură & Patrimoniu">🌿 Natură &amp; Patrimoniu</option>
    `;
  } else {
    sel.classList.add("hidden");
    seasonSel.classList.add("hidden");
    freeWrap.classList.add("hidden");
    if (confWrap) confWrap.classList.add("hidden");
  }
}

function switchTab(tabName) {
  activeTab = tabName;
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.classList.remove("bg-rose-900", "text-white", "shadow-sm");
    btn.classList.add("bg-white", "border", "border-stone-300", "text-stone-700");
  });
  const activeBtn = document.getElementById(`tab-${tabName}`);
  if (activeBtn) {
    activeBtn.classList.remove("bg-white", "border", "border-stone-300", "text-stone-700");
    activeBtn.classList.add("bg-rose-900", "text-white", "shadow-sm");
  }

  document.getElementById("hramuriNotice").classList.toggle("hidden", tabName !== "hramuri");
  document.getElementById("mapSection").classList.toggle("hidden", tabName !== "harta");
  document.getElementById("cardsGrid").classList.toggle("hidden", tabName === "harta");
  document.getElementById("filtersRow").classList.toggle("hidden", tabName === "harta");

  updateTypeFilterOptions();
  if (tabName === "harta") {
    loadInteractiveMap();
  } else {
    loadCurrentTab();
  }
}

function setQuickSearch(term) {
  document.getElementById("searchInput").value = term;
  if (activeTab === "harta") {
    switchTab("evenimente");
  } else {
    loadCurrentTab();
  }
}

function applyCurrentSearch() {
  if (activeTab === "harta") {
    loadInteractiveMap();
  } else {
    loadCurrentTab();
  }
}

function resetAllFilters() {
  document.getElementById("searchInput").value = "";
  document.getElementById("regionSelect").value = "Toate";
  document.getElementById("monthSelect").value = "Toate";
  document.getElementById("typeFilter").value = "Toate";
  document.getElementById("seasonFilter").value = "Toate";
  document.getElementById("freeOnlyCheck").checked = false;
  const confCheck = document.getElementById("confirmedOnlyCheck");
  if (confCheck) confCheck.checked = false;
  applyCurrentSearch();
}

function getCommonFilterParams() {
  const confCheck = document.getElementById("confirmedOnlyCheck");
  return {
    q: document.getElementById("searchInput").value.trim(),
    regiune: document.getElementById("regionSelect").value,
    luna: document.getElementById("monthSelect").value,
    tip: document.getElementById("typeFilter").value,
    sezon: document.getElementById("seasonFilter").value,
    gratuit: document.getElementById("freeOnlyCheck").checked ? "1" : "",
    doar_confirmate: confCheck && confCheck.checked ? "1" : "",
  };
}

async function loadCurrentTab() {
  const f = getCommonFilterParams();
  const grid = document.getElementById("cardsGrid");
  const emptyEl = document.getElementById("emptyState");
  const summaryEl = document.getElementById("resultsSummary");

  let endpoint = "/api/evenimente";
  const params = new URLSearchParams();
  if (f.q) params.set("q", f.q);
  if (f.regiune !== "Toate") params.set("regiune", f.regiune);

  if (activeTab === "evenimente") {
    if (f.tip !== "Toate") params.set("tip", f.tip);
    if (f.sezon !== "Toate") params.set("sezon", f.sezon);
    if (f.luna !== "Toate") params.set("luna", f.luna);
    if (f.gratuit) params.set("gratuit", "1");
    if (f.doar_confirmate) params.set("doar_confirmate", "1");
  } else if (activeTab === "locatii") {
    endpoint = "/api/locatii";
    if (f.tip !== "Toate") params.set("categorie", f.tip);
  } else if (activeTab === "hramuri") {
    endpoint = "/api/hramuri";
    if (f.luna !== "Toate") params.set("luna", f.luna);
  }

  try {
    const res = await fetch(`${endpoint}?${params.toString()}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const items = data.items || [];

    summaryEl.innerText = `Afișate ${items.length} rezultate verificate`;
    if (items.length === 0) {
      grid.innerHTML = "";
      emptyEl.classList.remove("hidden");
      return;
    }

    emptyEl.classList.add("hidden");
    if (activeTab === "evenimente") {
      grid.innerHTML = items.map(renderEventCard).join("");
    } else if (activeTab === "locatii") {
      grid.innerHTML = items.map(renderLocationCard).join("");
    } else {
      grid.innerHTML = items.map(renderHramCard).join("");
    }
  } catch (err) {
    console.error(err);
    summaryEl.innerText = "Eroare la încărcarea datelor.";
  }
}

function renderEventCard(e) {
  const slugSafe = encodeURIComponent(e.slug);
  const imgSafe = safeUrl(e.imagine_url);
  const recomBadge = e.este_recomandat
    ? `<span class="bg-amber-400 text-stone-950 px-2 py-0.5 rounded-md text-[10px] font-extrabold shadow-xs">⭐ Recomandat</span>`
    : "";

  return `
    <article class="bg-white rounded-2xl border border-stone-200 overflow-hidden shadow-xs hover:shadow-lg transition flex flex-col justify-between group">
      <div>
        <a href="/eveniment/${slugSafe}" class="block relative aspect-video bg-stone-200 overflow-hidden">
          <img src="${escapeHtml(imgSafe)}" alt="${escapeHtml(e.titlu)}" loading="lazy"
               class="w-full h-full object-cover group-hover:scale-105 transition duration-300">
          <div class="absolute top-2.5 left-2.5 flex flex-wrap gap-1.5">
            <span class="bg-stone-950/80 backdrop-blur text-white px-2.5 py-0.5 rounded-md text-[10px] font-bold">
              ${escapeHtml(e.tip)}
            </span>
          </div>
          <div class="absolute top-2.5 right-2.5 flex gap-1.5">
            ${recomBadge}
            <span class="bg-emerald-700/90 text-white px-2 py-0.5 rounded-md text-[10px] font-bold">✓ Verificat</span>
          </div>
        </a>

        <div class="p-4">
          <div class="flex items-center justify-between gap-2 mb-2">
            ${statusBadgeHtml(e.status_data, e.data_start)}
            <span class="text-[11px] font-semibold text-stone-500">${escapeHtml(e.luna_principala)} • ${escapeHtml(e.sezon)}</span>
          </div>

          <a href="/eveniment/${slugSafe}" class="block">
            <h3 class="font-extrabold text-base text-stone-900 group-hover:text-rose-800 transition line-clamp-2 mb-2">
              ${escapeHtml(e.titlu)}
            </h3>
          </a>

          <div class="bg-amber-50/80 border border-amber-200/70 rounded-xl px-3 py-2 text-xs text-amber-950 mb-3">
            <div class="font-bold">📅 ${escapeHtml(e.data_text)}</div>
            <div class="text-[11px] text-amber-800 mt-0.5 line-clamp-1">${escapeHtml(e.ultima_editie_verificata)}</div>
          </div>

          <div class="flex flex-wrap items-center justify-between gap-1 text-xs text-stone-600 font-medium mb-2">
            <span>📍 ${escapeHtml(e.localitate)}, ${escapeHtml(e.raion)}</span>
            <span class="text-[11px] text-stone-500">${e.distanta_chisinau_km === 0 ? "În Chișinău" : `${escapeHtml(e.distanta_chisinau_km)} km de Chișinău`}</span>
          </div>

          <p class="text-xs text-stone-600 line-clamp-2 mb-2.5">${escapeHtml(e.descriere_scurta)}</p>

          ${e.ce_gusti ? `<div class="text-[11px] text-stone-700 bg-stone-100 rounded-lg px-2.5 py-1.5 line-clamp-2 mb-2"><span class="font-bold">🍽️ Ce guști:</span> ${escapeHtml(e.ce_gusti)}</div>` : ""}

          ${(e.facebook_url || e.bilete_url) ? `
          <div class="flex flex-wrap gap-1.5 mt-1">
            ${e.facebook_url ? `<a href="${escapeHtml(safeUrl(e.facebook_url))}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-bold bg-sky-50 text-sky-800 border border-sky-200 hover:bg-sky-100 transition">Facebook ↗</a>` : ""}
            ${e.bilete_url ? `<a href="${escapeHtml(safeUrl(e.bilete_url))}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-bold bg-rose-50 text-rose-800 border border-rose-200 hover:bg-rose-100 transition">🎟️ Bilete ↗</a>` : ""}
          </div>
          ` : ""}
        </div>
      </div>

      <div class="px-4 py-3 bg-stone-50 border-t border-stone-100 flex items-center justify-between text-xs">
        <span class="font-semibold text-stone-700 truncate max-w-[160px]" title="${escapeHtml(e.pret_intrare)}">🎟️ ${escapeHtml(e.pret_intrare)}</span>
        <div class="flex items-center space-x-2">
          <button onclick="openQuickPreview('eveniment', '${escapeHtml(e.slug)}')" class="text-stone-500 hover:text-stone-900 font-semibold px-2 py-1 rounded-lg hover:bg-stone-200/60 transition">
            Previzualizare
          </button>
          <a href="/eveniment/${slugSafe}" class="font-bold text-rose-800 hover:text-rose-600 whitespace-nowrap">
            Detalii →
          </a>
        </div>
      </div>
    </article>
  `;
}

function renderLocationCard(loc) {
  const slugSafe = encodeURIComponent(loc.slug);
  const imgSafe = safeUrl(loc.imagine_url);

  return `
    <article class="bg-white rounded-2xl border border-stone-200 overflow-hidden shadow-xs hover:shadow-lg transition flex flex-col justify-between group">
      <div>
        <a href="/locatie/${slugSafe}" class="block relative aspect-video bg-stone-200 overflow-hidden">
          <img src="${escapeHtml(imgSafe)}" alt="${escapeHtml(loc.titlu)}" loading="lazy"
               class="w-full h-full object-cover group-hover:scale-105 transition duration-300">
          <div class="absolute top-2.5 left-2.5">
            <span class="bg-emerald-900/85 backdrop-blur text-white px-2.5 py-0.5 rounded-md text-[10px] font-bold">
              ${escapeHtml(loc.categorie)}
            </span>
          </div>
          <div class="absolute top-2.5 right-2.5">
            <span class="bg-stone-900/80 text-amber-300 px-2 py-0.5 rounded-md text-[10px] font-bold">
              ${escapeHtml(loc.regiune)}
            </span>
          </div>
        </a>

        <div class="p-4">
          <a href="/locatie/${slugSafe}" class="block">
            <h3 class="font-extrabold text-base text-stone-900 group-hover:text-emerald-800 transition line-clamp-2 mb-2">
              ${escapeHtml(loc.titlu)}
            </h3>
          </a>

          <div class="text-xs text-stone-600 font-medium mb-2 flex items-center justify-between">
            <span>📍 ${escapeHtml(loc.localitate)}, ${escapeHtml(loc.raion)}</span>
            <span class="text-[11px] text-stone-500">${escapeHtml(loc.distanta_chisinau_km)} km de Chișinău</span>
          </div>

          <div class="bg-emerald-50/70 border border-emerald-200/70 rounded-xl px-3 py-2 text-[11px] text-emerald-950 mb-3">
            <div><strong>🕒 Orar:</strong> ${escapeHtml(loc.program_vizita)}</div>
            <div><strong>📞 Rezervare:</strong> ${escapeHtml(loc.rezervare_necesara)}</div>
          </div>

          <p class="text-xs text-stone-600 line-clamp-2 mb-2.5">${escapeHtml(loc.descriere_scurta)}</p>
          ${loc.ce_gusti ? `<div class="text-[11px] text-stone-700 bg-stone-100 rounded-lg px-2.5 py-1.5 line-clamp-2"><span class="font-bold">🍽️ Recomandat:</span> ${escapeHtml(loc.ce_gusti)}</div>` : ""}
        </div>
      </div>

      <div class="px-4 py-3 bg-stone-50 border-t border-stone-100 flex items-center justify-between text-xs">
        <span class="font-semibold text-stone-700 truncate max-w-[155px]">💰 ${escapeHtml(loc.buget_orientativ)}</span>
        <div class="flex items-center space-x-2">
          <button onclick="openQuickPreview('locatie', '${escapeHtml(loc.slug)}')" class="text-stone-500 hover:text-stone-900 font-semibold px-2 py-1 rounded-lg hover:bg-stone-200/60 transition">
            Previzualizare
          </button>
          <a href="/locatie/${slugSafe}" class="font-bold text-emerald-800 hover:text-emerald-600 whitespace-nowrap">
            Detalii →
          </a>
        </div>
      </div>
    </article>
  `;
}

function renderHramCard(h) {
  const imgSafe = safeUrl(h.imagine_url);
  const linkSafe = safeUrl(h.link_oficial);
  const surseHtml = (h.surse_media || [])
    .map(
      (s) =>
        `<a href="${escapeHtml(safeUrl(s.url))}" target="_blank" rel="noopener noreferrer" class="underline text-rose-800 hover:text-rose-600">${escapeHtml(s.publicatie)}</a>`
    )
    .join(" • ");

  return `
    <article class="bg-white rounded-2xl border border-stone-200 overflow-hidden shadow-xs flex flex-col justify-between">
      <div>
        <div class="relative aspect-video bg-stone-200 overflow-hidden">
          <img src="${escapeHtml(imgSafe)}" alt="${escapeHtml(h.titlu)}" loading="lazy" class="w-full h-full object-cover">
          <span class="absolute top-2.5 left-2.5 bg-stone-900/80 text-amber-200 px-2.5 py-0.5 rounded-md text-[10px] font-bold">
            Hram Urban Verificat
          </span>
          <span class="absolute top-2.5 right-2.5 bg-white/90 text-stone-800 px-2 py-0.5 rounded-md text-[10px] font-bold">
            ${escapeHtml(h.regiune)}
          </span>
        </div>

        <div class="p-4">
          <div class="text-xs font-bold text-amber-800 mb-1">📅 ${escapeHtml(h.data_text)}</div>
          <h3 class="font-extrabold text-base text-stone-900 mb-2">${escapeHtml(h.titlu)}</h3>
          <p class="text-xs text-stone-600 mb-2">${escapeHtml(h.descriere)}</p>
          <div class="text-[11px] bg-stone-100 rounded-xl p-2.5 text-stone-700">
            <strong>Ce se întâmplă:</strong> ${escapeHtml(h.ce_se_intampla)}
          </div>
        </div>
      </div>

      <div class="px-4 py-3 bg-stone-50 border-t border-stone-100 flex items-center justify-between text-[11px]">
        <div class="truncate max-w-[200px]">Surse: ${surseHtml || "Oficial"}</div>
        <a href="${escapeHtml(linkSafe)}" target="_blank" rel="noopener noreferrer" class="font-bold text-rose-800 hover:underline">
          Site oficial ↗
        </a>
      </div>
    </article>
  `;
}

async function openQuickPreview(kind, slug) {
  const endpoint = kind === "eveniment" ? `/api/evenimente/${encodeURIComponent(slug)}` : `/api/locatii/${encodeURIComponent(slug)}`;
  try {
    const res = await fetch(endpoint);
    if (!res.ok) return;
    const item = await res.json();
    const detailPath = kind === "eveniment" ? `/eveniment/${encodeURIComponent(item.slug)}` : `/locatie/${encodeURIComponent(item.slug)}`;
    const bodyText = kind === "eveniment" ? item.cum_a_fost_real : item.ce_merita_vazut;

    const surseList = (item.surse_media || [])
      .map(
        (s) =>
          `<li><a href="${escapeHtml(safeUrl(s.url))}" target="_blank" rel="noopener noreferrer" class="text-rose-800 hover:underline font-medium">🔗 ${escapeHtml(s.titlu)} (${escapeHtml(s.publicatie)})</a></li>`
      )
      .join("");

    document.getElementById("previewContent").innerHTML = `
      <div class="aspect-video bg-stone-200 overflow-hidden rounded-t-2xl relative">
        <img src="${escapeHtml(safeUrl(item.imagine_url))}" alt="${escapeHtml(item.titlu)}" class="w-full h-full object-cover">
        <div class="absolute bottom-2 left-3 bg-black/65 text-white text-[10px] px-2 py-0.5 rounded">
          Foto: ${escapeHtml(item.imagine_credit)}
        </div>
      </div>
      <div class="p-6 space-y-4">
        <div>
          <span class="text-xs font-bold uppercase tracking-wide text-rose-800">${escapeHtml(item.tip || item.categorie)}</span>
          <h3 class="text-xl font-extrabold text-stone-900 mt-0.5">${escapeHtml(item.titlu)}</h3>
          <div class="text-xs text-stone-500 mt-1">📍 ${escapeHtml(item.localitate)}, ${escapeHtml(item.raion)} (${escapeHtml(item.regiune)})</div>
        </div>

        <div class="bg-amber-50 border border-amber-200 rounded-xl p-3 text-xs space-y-1">
          <div><strong>📅 Când:</strong> ${escapeHtml(item.data_text || item.program_vizita)}</div>
          ${item.regula_recurenta ? `<div><strong>🔄 Recurență:</strong> ${escapeHtml(item.regula_recurenta)}</div>` : ""}
          ${item.ultima_editie_verificata ? `<div><strong>📰 Ultima ediție verificată:</strong> ${escapeHtml(item.ultima_editie_verificata)}</div>` : ""}
          <div><strong>🎟️ Acces / Buget:</strong> ${escapeHtml(item.pret_intrare || item.buget_orientativ)}</div>
        </div>

        <div class="text-xs text-stone-700 leading-relaxed space-y-2">
          <h4 class="font-bold text-stone-900 text-sm">${kind === "eveniment" ? "Cum a fost în realitate la edițiile anterioare:" : "Ce merită văzut și făcut aici:"}</h4>
          <p>${escapeHtml(bodyText)}</p>
        </div>

        ${item.ce_gusti ? `<div class="bg-stone-100 rounded-xl p-3 text-xs text-stone-800"><strong>🍽️ Ce guști aici:</strong> ${escapeHtml(item.ce_gusti)}</div>` : ""}

        <div class="text-xs">
          <h4 class="font-bold text-stone-900 mb-1.5">Surse Media &amp; Linkuri Oficiale:</h4>
          <ul class="space-y-1">${surseList}</ul>
        </div>

        <div class="pt-2 flex flex-wrap gap-2">
          <a href="${escapeHtml(detailPath)}" class="flex-1 text-center bg-rose-800 hover:bg-rose-700 text-white font-bold py-2.5 px-4 rounded-xl text-xs transition">
            Deschide Pagina Completă →
          </a>
          ${item.facebook_url ? `<a href="${escapeHtml(safeUrl(item.facebook_url))}" target="_blank" rel="noopener noreferrer" class="bg-sky-100 hover:bg-sky-200 text-sky-900 font-bold py-2.5 px-4 rounded-xl text-xs transition">📘 Facebook ↗</a>` : ""}
          ${item.bilete_url ? `<a href="${escapeHtml(safeUrl(item.bilete_url))}" target="_blank" rel="noopener noreferrer" class="bg-rose-100 hover:bg-rose-200 text-rose-900 font-bold py-2.5 px-4 rounded-xl text-xs transition">🎟️ Bilete ↗</a>` : ""}
          ${kind === "eveniment" ? `<a href="/api/evenimente/${encodeURIComponent(item.slug)}/ics" class="bg-amber-100 hover:bg-amber-200 text-amber-950 font-bold py-2.5 px-4 rounded-xl text-xs transition">📅 Calendar (.ics)</a>` : ""}
          <a href="https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${item.lat},${item.lng}`)}" target="_blank" rel="noopener noreferrer"
             class="bg-stone-200 hover:bg-stone-300 text-stone-800 font-bold py-2.5 px-4 rounded-xl text-xs transition">
            Google Maps ↗
          </a>
        </div>
      </div>
    `;
    document.getElementById("previewModal").classList.remove("hidden");
  } catch (e) {
    console.error(e);
  }
}

function closePreviewModal() {
  document.getElementById("previewModal").classList.add("hidden");
}

async function loadInteractiveMap() {
  if (!leafletMap) {
    leafletMap = L.map("moldovaMap").setView([47.15, 28.65], 8);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18,
      attribution: "&copy; OpenStreetMap contributors",
    }).addTo(leafletMap);
    mapMarkersLayer = L.layerGroup().addTo(leafletMap);
  }
  setTimeout(() => leafletMap.invalidateSize(), 120);

  const f = getCommonFilterParams();
  const params = new URLSearchParams();
  if (f.q) params.set("q", f.q);
  if (f.regiune !== "Toate") params.set("regiune", f.regiune);
  if (f.luna !== "Toate") params.set("luna", f.luna);

  const [evRes, locRes] = await Promise.all([
    fetch(`/api/evenimente?${params.toString()}`),
    fetch(`/api/locatii?${new URLSearchParams({ q: f.q, regiune: f.regiune !== "Toate" ? f.regiune : "" }).toString()}`),
  ]);
  const evData = await evRes.json();
  const locData = await locRes.json();

  mapMarkersLayer.clearLayers();
  let countPins = 0;

  (evData.items || []).forEach((e) => {
    if (!e.lat || !e.lng) return;
    countPins += 1;
    const marker = L.circleMarker([e.lat, e.lng], {
      radius: 8,
      color: "#881337",
      fillColor: "#be123c",
      fillOpacity: 0.9,
      weight: 2,
    });
    marker.bindPopup(`
      <div style="width:210px;font-family:sans-serif">
        <img src="${escapeHtml(safeUrl(e.imagine_url))}" style="width:100%;height:105px;object-fit:cover;border-radius:8px;margin-bottom:6px">
        <div style="font-size:10px;font-weight:700;color:#9f1239">${escapeHtml(e.tip)}</div>
        <div style="font-size:13px;font-weight:800;margin:2px 0">${escapeHtml(e.titlu)}</div>
        <div style="font-size:11px;color:#57534e;margin-bottom:6px">📅 ${escapeHtml(e.data_text)}</div>
        <a href="/eveniment/${encodeURIComponent(e.slug)}" style="font-size:11px;font-weight:700;color:#9f1239">Deschide detalii →</a>
      </div>
    `);
    marker.addTo(mapMarkersLayer);
  });

  (locData.items || []).forEach((loc) => {
    if (!loc.lat || !loc.lng) return;
    countPins += 1;
    const marker = L.circleMarker([loc.lat, loc.lng], {
      radius: 8,
      color: "#064e3b",
      fillColor: "#047857",
      fillOpacity: 0.9,
      weight: 2,
    });
    marker.bindPopup(`
      <div style="width:210px;font-family:sans-serif">
        <img src="${escapeHtml(safeUrl(loc.imagine_url))}" style="width:100%;height:105px;object-fit:cover;border-radius:8px;margin-bottom:6px">
        <div style="font-size:10px;font-weight:700;color:#065f46">${escapeHtml(loc.categorie)}</div>
        <div style="font-size:13px;font-weight:800;margin:2px 0">${escapeHtml(loc.titlu)}</div>
        <div style="font-size:11px;color:#57534e;margin-bottom:6px">📍 ${escapeHtml(loc.localitate)} • ${escapeHtml(loc.program_vizita)}</div>
        <a href="/locatie/${encodeURIComponent(loc.slug)}" style="font-size:11px;font-weight:700;color:#065f46">Deschide detalii →</a>
      </div>
    `);
    marker.addTo(mapMarkersLayer);
  });

  document.getElementById("resultsSummary").innerText = `${countPins} puncte verificate pe harta Moldovei`;
}

function openProposeModal() {
  document.getElementById("propFeedback").classList.add("hidden");
  document.getElementById("proposeModal").classList.remove("hidden");
}

function closeProposeModal() {
  document.getElementById("proposeModal").classList.add("hidden");
}

async function submitProposal(ev) {
  ev.preventDefault();
  const fb = document.getElementById("propFeedback");
  const payload = {
    tip_entitate: document.getElementById("propTip").value,
    titlu: document.getElementById("propTitlu").value,
    localitate: document.getElementById("propLocalitate").value,
    raion: document.getElementById("propRaion").value,
    data_text: document.getElementById("propData").value,
    link_sursa: document.getElementById("propLink").value,
    descriere: document.getElementById("propDesc").value,
    contact_expeditor: document.getElementById("propContact").value,
  };

  try {
    const res = await fetch("/api/propuneri", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const out = await res.json();
    if (!res.ok) {
      throw new Error(out.detail ? JSON.stringify(out.detail) : "Eroare la trimitere.");
    }
    fb.className = "p-2.5 rounded-xl text-xs font-semibold bg-emerald-100 text-emerald-900";
    fb.innerText = "✓ Mulțumim! Propunerea a fost înregistrată pentru verificare editorială.";
    fb.classList.remove("hidden");
    document.getElementById("proposeForm").reset();
  } catch (err) {
    fb.className = "p-2.5 rounded-xl text-xs font-semibold bg-red-100 text-red-900";
    fb.innerText = `Eroare: ${err.message}`;
    fb.classList.remove("hidden");
  }
}

window.addEventListener("DOMContentLoaded", () => {
  fetchStats();
  updateTypeFilterOptions();
  loadCurrentTab();

  document.getElementById("searchInput").addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(applyCurrentSearch, 220);
  });
  ["regionSelect", "monthSelect", "typeFilter", "seasonFilter", "freeOnlyCheck", "confirmedOnlyCheck"].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.addEventListener("change", applyCurrentSearch);
  });
});
