/**
 * ClubTuristic.md Admin Studio v2
 * Autentificare Basic Auth stocată în sessionStorage și operațiuni CRUD live pe SQLite + FTS5.
 */

let admTab = "evenimente";
let admCache = [];
let monitorStatusFilter = "De verificat";
let lastMonitorBanner = "";
let searchTimeout = null;

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
  return (u.startsWith("http://") || u.startsWith("https://") || u.startsWith("/")) ? u : "#";
}

function getAuthHeader() {
  const token = sessionStorage.getItem("ct_admin_auth");
  return token ? { Authorization: `Basic ${token}` } : {};
}

async function handleAdminLogin(ev) {
  ev.preventDefault();
  const u = document.getElementById("loginUser").value.trim();
  const p = document.getElementById("loginPass").value;
  const errEl = document.getElementById("loginErr");

  const token = btoa(unescape(encodeURIComponent(`${u}:${p}`)));
  try {
    const res = await fetch("/api/admin/me", { headers: { Authorization: `Basic ${token}` } });
    if (!res.ok) {
      errEl.innerText = "Utilizator sau parolă incorectă.";
      errEl.classList.remove("hidden");
      return;
    }
    sessionStorage.setItem("ct_admin_auth", token);
    document.getElementById("loginGate").classList.add("hidden");
    loadAllCounts();
    loadAdminTab();
  } catch (e) {
    errEl.innerText = "Eroare de conexiune cu serverul.";
    errEl.classList.remove("hidden");
  }
}

function logoutAdmin() {
  sessionStorage.removeItem("ct_admin_auth");
  window.location.reload();
}

async function checkSessionOnLoad() {
  const token = sessionStorage.getItem("ct_admin_auth");
  if (!token) return;
  try {
    const res = await fetch("/api/admin/me", { headers: getAuthHeader() });
    if (res.ok) {
      document.getElementById("loginGate").classList.add("hidden");
      loadAllCounts();
      loadAdminTab();
    } else {
      sessionStorage.removeItem("ct_admin_auth");
    }
  } catch (e) {
    console.warn(e);
  }
}

async function loadAllCounts() {
  const res = await fetch("/api/stats");
  if (!res.ok) return;
  const s = await res.json();
  document.getElementById("admCnt-evt").innerText = s.evenimente;
  document.getElementById("admCnt-loc").innerText = s.locatii;
  document.getElementById("admCnt-prop").innerText = s.propuneri_in_asteptare;
  const monEl = document.getElementById("admCnt-mon");
  if (monEl) monEl.innerText = s.actualizari_de_verificat ?? 0;
}

function switchAdminTab(tab) {
  admTab = tab;
  document.querySelectorAll(".adm-tab").forEach((b) => {
    b.classList.remove("bg-amber-500", "text-slate-950");
    b.classList.add("bg-slate-800", "text-slate-300", "border", "border-slate-700");
  });
  const active = document.getElementById(`admTab-${tab}`);
  active.classList.remove("bg-slate-800", "text-slate-300", "border", "border-slate-700");
  active.classList.add("bg-amber-500", "text-slate-950");

  document.getElementById("addBtn").classList.toggle("hidden", tab === "propuneri" || tab === "monitor");
  const searchWrap = document.getElementById("searchWrap");
  if (searchWrap) searchWrap.classList.toggle("hidden", tab === "monitor");
  document.getElementById("tablePanel").classList.toggle("hidden", tab === "monitor");
  document.getElementById("monitorPanel").classList.toggle("hidden", tab !== "monitor");

  if (tab === "monitor") {
    loadMonitorTab();
  } else {
    loadAdminTab();
  }
}

async function loadAdminTab() {
  const q = document.getElementById("adminSearch").value.trim();
  const thead = document.getElementById("tableHead");
  const tbody = document.getElementById("tableBody");

  if (admTab === "evenimente") {
    const res = await fetch(`/api/evenimente?limit=300&q=${encodeURIComponent(q)}`);
    const data = await res.json();
    admCache = data.items || [];
    thead.innerHTML = `<tr>
      <th class="px-4 py-3">Foto &amp; Titlu</th>
      <th class="px-4 py-3">Tip</th>
      <th class="px-4 py-3">Locație</th>
      <th class="px-4 py-3">Când / Status</th>
      <th class="px-4 py-3 text-right">Acțiuni</th>
    </tr>`;
    tbody.innerHTML = admCache.map((r) => `
      <tr class="hover:bg-slate-800/50">
        <td class="px-4 py-3">
          <div class="flex items-center space-x-3">
            <img src="${escapeHtml(r.imagine_url)}" class="w-14 h-9 rounded object-cover bg-slate-800">
            <div>
              <div class="font-bold text-white">${escapeHtml(r.titlu)}</div>
              <div class="text-[10px] font-mono text-slate-400">/eveniment/${escapeHtml(r.slug)}</div>
            </div>
          </div>
        </td>
        <td class="px-4 py-3 text-amber-300 font-medium">${escapeHtml(r.tip)}</td>
        <td class="px-4 py-3 text-slate-300">${escapeHtml(r.localitate)}, ${escapeHtml(r.raion)}</td>
        <td class="px-4 py-3">
          <div class="text-white font-semibold">${escapeHtml(r.data_text)}</div>
          <div class="text-[10px] ${r.data_start ? "text-emerald-400" : "text-amber-400"}">
            ${escapeHtml(r.status_data)}${r.data_start ? ` (${escapeHtml(r.data_start)})` : ""}
          </div>
          ${r.facebook_url ? `<a href="${escapeHtml(safeUrl(r.facebook_url))}" target="_blank" rel="noopener noreferrer" class="text-[10px] text-sky-400 underline">FB ↗</a>` : ""}
        </td>
        <td class="px-4 py-3 text-right space-x-1.5 whitespace-nowrap">
          <a href="/eveniment/${encodeURIComponent(r.slug)}" target="_blank" class="px-2 py-1 bg-slate-800 hover:bg-slate-700 rounded text-slate-200">Vezi</a>
          <button onclick="openEditModal('${escapeHtml(r.id)}')" class="px-2 py-1 bg-amber-500/20 hover:bg-amber-500 text-amber-300 hover:text-slate-950 rounded font-semibold">Edit</button>
          <button onclick="deleteAdminItem('${escapeHtml(r.id)}')" class="px-2 py-1 bg-red-900/30 hover:bg-red-700 text-red-300 hover:text-white rounded">Del</button>
        </td>
      </tr>
    `).join("");
  } else if (admTab === "locatii") {
    const res = await fetch(`/api/locatii?limit=300&q=${encodeURIComponent(q)}`);
    const data = await res.json();
    admCache = data.items || [];
    thead.innerHTML = `<tr>
      <th class="px-4 py-3">Foto &amp; Locație</th>
      <th class="px-4 py-3">Categorie</th>
      <th class="px-4 py-3">Raion / Regiune</th>
      <th class="px-4 py-3">Program</th>
      <th class="px-4 py-3 text-right">Acțiuni</th>
    </tr>`;
    tbody.innerHTML = admCache.map((r) => `
      <tr class="hover:bg-slate-800/50">
        <td class="px-4 py-3">
          <div class="flex items-center space-x-3">
            <img src="${escapeHtml(r.imagine_url)}" class="w-14 h-9 rounded object-cover bg-slate-800">
            <div>
              <div class="font-bold text-white">${escapeHtml(r.titlu)}</div>
              <div class="text-[10px] font-mono text-slate-400">/locatie/${escapeHtml(r.slug)}</div>
            </div>
          </div>
        </td>
        <td class="px-4 py-3 text-emerald-300 font-medium">${escapeHtml(r.categorie)}</td>
        <td class="px-4 py-3 text-slate-300">${escapeHtml(r.localitate)}, ${escapeHtml(r.raion)}</td>
        <td class="px-4 py-3 text-slate-300">${escapeHtml(r.program_vizita)}</td>
        <td class="px-4 py-3 text-right space-x-1.5 whitespace-nowrap">
          <a href="/locatie/${encodeURIComponent(r.slug)}" target="_blank" class="px-2 py-1 bg-slate-800 hover:bg-slate-700 rounded text-slate-200">Vezi</a>
          <button onclick="openEditModal('${escapeHtml(r.id)}')" class="px-2 py-1 bg-amber-500/20 hover:bg-amber-500 text-amber-300 hover:text-slate-950 rounded font-semibold">Edit</button>
          <button onclick="deleteAdminItem('${escapeHtml(r.id)}')" class="px-2 py-1 bg-red-900/30 hover:bg-red-700 text-red-300 hover:text-white rounded">Del</button>
        </td>
      </tr>
    `).join("");
  } else {
    const res = await fetch("/api/admin/propuneri", { headers: getAuthHeader() });
    if (res.status === 401) return logoutAdmin();
    const data = await res.json();
    admCache = data.items || [];
    thead.innerHTML = `<tr>
      <th class="px-4 py-3">Titlu propus</th>
      <th class="px-4 py-3">Localitate / Dată</th>
      <th class="px-4 py-3">Link Sursă</th>
      <th class="px-4 py-3">Status</th>
      <th class="px-4 py-3 text-right">Acțiuni</th>
    </tr>`;
    tbody.innerHTML = admCache.length ? admCache.map((r) => `
      <tr class="hover:bg-slate-800/50">
        <td class="px-4 py-3">
          <div class="font-bold text-white">${escapeHtml(r.titlu)}</div>
          <div class="text-[11px] text-slate-400">${escapeHtml(r.tip_entitate)} — ${escapeHtml(r.descriere)}</div>
        </td>
        <td class="px-4 py-3 text-slate-300">
          <div>${escapeHtml(r.localitate)} ${r.raion ? `(${escapeHtml(r.raion)})` : ""}</div>
          <div class="text-[11px] text-amber-300">${escapeHtml(r.data_text)}</div>
        </td>
        <td class="px-4 py-3"><a href="${escapeHtml(r.link_sursa)}" target="_blank" rel="noopener noreferrer" class="text-sky-400 underline break-all">${escapeHtml(r.link_sursa)}</a></td>
        <td class="px-4 py-3 font-bold">${escapeHtml(r.status)}</td>
        <td class="px-4 py-3 text-right space-x-1 whitespace-nowrap">
          <button onclick="setPropStatus(${r.id}, 'Aprobat')" class="px-2 py-1 bg-emerald-700 hover:bg-emerald-600 text-white rounded">Aprobă</button>
          <button onclick="setPropStatus(${r.id}, 'Respins')" class="px-2 py-1 bg-slate-700 hover:bg-slate-600 text-white rounded">Respinge</button>
          <button onclick="deleteProposal(${r.id})" class="px-2 py-1 bg-red-900/40 hover:bg-red-700 text-red-300 hover:text-white rounded">Del</button>
        </td>
      </tr>
    `).join("") : `<tr><td colspan="5" class="px-4 py-8 text-center text-slate-400">Nu există propuneri comunitare încă.</td></tr>`;
  }
}

function fieldInput(name, label, value = "", full = false, isTextarea = false) {
  const span = full ? "sm:col-span-2" : "";
  if (isTextarea) {
    return `<div class="${span}">
      <label class="block text-slate-400 mb-1">${escapeHtml(label)}</label>
      <textarea id="fld_${name}" rows="3" class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-white">${escapeHtml(value)}</textarea>
    </div>`;
  }
  return `<div class="${span}">
    <label class="block text-slate-400 mb-1">${escapeHtml(label)}</label>
    <input id="fld_${name}" type="text" value="${escapeHtml(value)}" class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-white">
  </div>`;
}

function buildCrudFields(item = {}) {
  if (admTab === "evenimente") {
    return [
      fieldInput("titlu", "Titlu eveniment *", item.titlu || "", true),
      fieldInput("tip", "Tip (ex: Festival Gastronomic)", item.tip || "Festival Gastronomic"),
      fieldInput("organizator", "Organizator", item.organizator || ""),
      fieldInput("regiune", "Regiune (Chișinău / Centru / Nord / Sud / UTA Găgăuzia)", item.regiune || "Centru"),
      fieldInput("raion", "Raion / Municipiu", item.raion || "Chișinău"),
      fieldInput("localitate", "Localitate *", item.localitate || ""),
      fieldInput("locatie_exacta", "Locație exactă", item.locatie_exacta || ""),
      fieldInput("lat", "Latitudine GPS", item.lat ?? 47.0105),
      fieldInput("lng", "Longitudine GPS", item.lng ?? 28.8638),
      fieldInput("data_text", "Când se petrece (text)", item.data_text || ""),
      fieldInput("data_start", "Dată start exactă (YYYY-MM-DD)", item.data_start || ""),
      fieldInput("data_end", "Dată sfârșit exactă (YYYY-MM-DD)", item.data_end || ""),
      fieldInput("regula_recurenta", "Regulă de recurență", item.regula_recurenta || ""),
      fieldInput("luna_principala", "Lună principală", item.luna_principala || "Iunie"),
      fieldInput("luni_active", "Luni active (separate prin virgulă)", item.luni_active || "Iunie"),
      fieldInput("sezon", "Sezon (Primăvară / Vară / Toamnă / Iarnă / Permanent)", item.sezon || "Vară"),
      fieldInput("status_data", "Status (Confirmat / Estimat după tradiție / Săptămânal activ)", item.status_data || "Confirmat"),
      fieldInput("ultima_editie_verificata", "Ultima ediție verificată", item.ultima_editie_verificata || ""),
      fieldInput("urmatoarea_data_estimata", "Următoarea dată estimată (YYYY-MM-DD)", item.urmatoarea_data_estimata || "2027-06-15"),
      fieldInput("pret_intrare", "Preț intrare", item.pret_intrare || "Gratuit"),
      fieldInput("link_oficial", "Link oficial (https://...)", item.link_oficial || "https://moldova.travel/ro"),
      fieldInput("facebook_url", "Pagină Facebook oficială (https://facebook.com/...)", item.facebook_url || ""),
      fieldInput("instagram_url", "Instagram oficial (https://instagram.com/...)", item.instagram_url || ""),
      fieldInput("bilete_url", "Link Bilete / Înregistrare (iTicket / Sporter)", item.bilete_url || ""),
      fieldInput("sursa_confirmarii", "URL sursa confirmării datei", item.sursa_confirmarii || ""),
      fieldInput("imagine_url", "URL Imagine (/static/images/...)", item.imagine_url || "/static/images/chisinau.jpg"),
      fieldInput("taguri", "Tag-uri căutare", item.taguri || "", true),
      fieldInput("descriere_scurta", "Descriere scurtă", item.descriere_scurta || "", true, true),
      fieldInput("cum_a_fost_real", "Cum a fost în realitate (ediții trecute)", item.cum_a_fost_real || "", true, true),
      fieldInput("ce_gusti", "Ce guști", item.ce_gusti || "", true),
    ].join("");
  }
  return [
    fieldInput("titlu", "Titlu locație *", item.titlu || "", true),
    fieldInput("categorie", "Categorie (ex: Cramă & Resort Turistic)", item.categorie || "Pensiune & Gastronomie"),
    fieldInput("regiune", "Regiune", item.regiune || "Centru"),
    fieldInput("raion", "Raion", item.raion || "Orhei"),
    fieldInput("localitate", "Localitate", item.localitate || ""),
    fieldInput("adresa", "Adresă", item.adresa || ""),
    fieldInput("lat", "Latitudine GPS", item.lat ?? 47.0105),
    fieldInput("lng", "Longitudine GPS", item.lng ?? 28.8638),
    fieldInput("program_vizita", "Program vizită", item.program_vizita || "Cu programare"),
    fieldInput("rezervare_necesara", "Rezervare necesară", item.rezervare_necesara || "Recomandată"),
    fieldInput("buget_orientativ", "Buget orientativ", item.buget_orientativ || "300 - 700 MDL"),
    fieldInput("link_oficial", "Link oficial (https://...)", item.link_oficial || "https://moldova.travel/ro"),
    fieldInput("facebook_url", "Pagină Facebook oficială", item.facebook_url || ""),
    fieldInput("instagram_url", "Instagram oficial", item.instagram_url || ""),
    fieldInput("imagine_url", "URL Imagine (/static/images/...)", item.imagine_url || "/static/images/vineyard_moldova.jpg", true),
    fieldInput("taguri", "Tag-uri căutare", item.taguri || "", true),
    fieldInput("descriere_scurta", "Descriere scurtă", item.descriere_scurta || "", true, true),
    fieldInput("ce_merita_vazut", "Ce merită văzut aici", item.ce_merita_vazut || "", true, true),
    fieldInput("ce_gusti", "Ce guști", item.ce_gusti || "", true),
  ].join("");
}

function openCreateModal() {
  document.getElementById("fMode").value = "create";
  document.getElementById("fId").value = "";
  document.getElementById("crudTitle").innerText = admTab === "evenimente" ? "Adaugă Eveniment Verificat" : "Adaugă Locație Verificată";
  document.getElementById("crudFields").innerHTML = buildCrudFields({});
  document.getElementById("crudModal").classList.remove("hidden");
}

function openEditModal(id) {
  const item = admCache.find((x) => x.id === id);
  if (!item) return;
  document.getElementById("fMode").value = "edit";
  document.getElementById("fId").value = id;
  document.getElementById("crudTitle").innerText = `Editare: ${item.titlu}`;
  document.getElementById("crudFields").innerHTML = buildCrudFields(item);
  document.getElementById("crudModal").classList.remove("hidden");
}

function closeCrudModal() {
  document.getElementById("crudModal").classList.add("hidden");
}

async function saveCrudForm(ev) {
  ev.preventDefault();
  const mode = document.getElementById("fMode").value;
  const id = document.getElementById("fId").value;

  const inputs = document.querySelectorAll("#crudFields [id^='fld_']");
  const payload = {};
  inputs.forEach((el) => {
    const key = el.id.replace("fld_", "");
    payload[key] = (key === "lat" || key === "lng") ? (parseFloat(el.value) || 47.01) : el.value;
  });

  if (mode === "edit") {
    const existing = admCache.find((x) => x.id === id) || {};
    payload.surse_media = existing.surse_media || [];
    payload.slug = existing.slug;
    payload.imagine_credit = existing.imagine_credit || "Arhivă ClubTuristic.md";
    payload.este_recomandat = existing.este_recomandat || 0;
  }

  const baseApi = admTab === "evenimente" ? "/api/admin/evenimente" : "/api/admin/locatii";
  const url = mode === "create" ? baseApi : `${baseApi}/${encodeURIComponent(id)}`;
  const method = mode === "create" ? "POST" : "PUT";

  const res = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json", ...getAuthHeader() },
    body: JSON.stringify(payload),
  });
  if (res.status === 401) return logoutAdmin();
  if (!res.ok) {
    const err = await res.json();
    alert(`Eroare la salvare: ${JSON.stringify(err)}`);
    return;
  }
  closeCrudModal();
  await loadAllCounts();
  await loadAdminTab();
}

async function deleteAdminItem(id) {
  if (!confirm("Sigur doriți să ștergeți această înregistrare din SQLite?")) return;
  const baseApi = admTab === "evenimente" ? "/api/admin/evenimente" : "/api/admin/locatii";
  const res = await fetch(`${baseApi}/${encodeURIComponent(id)}`, {
    method: "DELETE",
    headers: getAuthHeader(),
  });
  if (res.status === 401) return logoutAdmin();
  await loadAllCounts();
  await loadAdminTab();
}

async function setPropStatus(pid, statusVal) {
  const res = await fetch(`/api/admin/propuneri/${pid}/status`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeader() },
    body: JSON.stringify({ status: statusVal }),
  });
  if (res.status === 401) return logoutAdmin();
  await loadAllCounts();
  await loadAdminTab();
}

async function deleteProposal(pid) {
  if (!confirm("Ștergeți propunerea?")) return;
  const res = await fetch(`/api/admin/propuneri/${pid}`, {
    method: "DELETE",
    headers: getAuthHeader(),
  });
  if (res.status === 401) return logoutAdmin();
  await loadAllCounts();
  await loadAdminTab();
}

// ============================================================================
// TAB MONITORIZARE INCREMENTALA & SURSE
// ============================================================================

function sourceTypeBadge(tip) {
  const t = (tip || "").toLowerCase();
  if (t === "agenda") return `<span class="px-2 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-800 text-[10px] font-bold">Agenda</span>`;
  if (t.includes("radio")) return `<span class="px-2 py-0.5 rounded bg-purple-950 text-purple-300 border border-purple-800 text-[10px] font-bold">${escapeHtml(tip)}</span>`;
  if (t === "stiri") return `<span class="px-2 py-0.5 rounded bg-sky-950 text-sky-300 border border-sky-800 text-[10px] font-bold">Știri RSS</span>`;
  if (t === "facebook") return `<span class="px-2 py-0.5 rounded bg-blue-950 text-blue-300 border border-blue-800 text-[10px] font-bold">Facebook</span>`;
  return `<span class="px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800 text-[10px] font-bold">${escapeHtml(tip || "Site Oficial")}</span>`;
}

async function loadMonitorTab() {
  const panel = document.getElementById("monitorPanel");
  if (!panel) return;
  panel.innerHTML = `<div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 text-xs text-slate-400">Se încarcă starea monitorizării și actualizările detectate...</div>`;

  const res = await fetch(`/api/admin/monitor/status?status=${encodeURIComponent(monitorStatusFilter)}`, {
    headers: getAuthHeader(),
  });
  if (res.status === 401) return logoutAdmin();
  if (!res.ok) {
    panel.innerHTML = `<div class="bg-red-950 border border-red-800 rounded-2xl p-4 text-xs text-red-200">Eroare la încărcarea datelor de monitorizare (HTTP ${res.status}).</div>`;
    return;
  }
  const data = await res.json();
  const c = data.counts || {};
  const lastRun = (data.runs || [])[0] || null;
  const monEl = document.getElementById("admCnt-mon");
  if (monEl) monEl.innerText = c.de_verificat ?? 0;

  const lastRunHtml = lastRun
    ? `Ultima rulare (<strong>${escapeHtml(lastRun.trigger_type)}</strong>, ${escapeHtml(lastRun.ran_at)}): <strong>${lastRun.sources_checked}</strong> surse verificate, <strong>${lastRun.sources_not_modified}</strong> neschimbate (304), <strong class="text-sky-300">${lastRun.items_seen_skipped}</strong> articole deja văzute sărite, <strong>${lastRun.items_new_scanned}</strong> noi scanate, <strong class="text-amber-300">${lastRun.matches_queued}</strong> potriviri noi.`
    : "Nicio scanare rulată încă din Worker (Cron activ la fiecare 6 ore).";

  const bannerHtml = lastMonitorBanner
    ? `<div id="monitorResultBanner" class="bg-emerald-950/70 border border-emerald-700 text-emerald-200 rounded-xl px-4 py-2.5 text-xs flex items-center justify-between">
         <span>${escapeHtml(lastMonitorBanner)}</span>
         <button onclick="lastMonitorBanner='';document.getElementById('monitorResultBanner')?.remove()" class="text-emerald-400 hover:text-white font-bold ml-3">✕</button>
       </div>`
    : "";

  const updates = data.updates || [];
  const updatesRows = updates.length
    ? updates.map((u) => `
      <tr class="hover:bg-slate-800/40 align-top">
        <td class="px-4 py-3 whitespace-nowrap">
          ${sourceTypeBadge(u.sursa_tip)}
          <div class="text-[11px] text-slate-300 mt-1 font-medium">${escapeHtml(u.sursa_nume)}</div>
        </td>
        <td class="px-4 py-3 max-w-[180px]">
          ${u.eveniment_id
            ? `<span class="inline-block px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 text-[10px] font-bold mb-1">Actualizare eveniment</span>
               <div class="text-[11px] font-semibold text-white">${escapeHtml(u.eveniment_titlu || u.eveniment_id)}</div>`
            : `<span class="inline-block px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 text-[10px] font-bold">🆕 Eveniment nou</span>`
          }
        </td>
        <td class="px-4 py-3 max-w-md">
          <div class="font-bold text-white text-xs">${escapeHtml(u.titlu_detectat)}</div>
          <div class="text-[11px] text-slate-400 mt-1 line-clamp-2">${escapeHtml(u.descriere_snippet)}</div>
          <a href="${escapeHtml(safeUrl(u.url_sursa))}" target="_blank" rel="noopener noreferrer" class="inline-block text-[11px] text-sky-400 underline mt-1">Deschide sursa ↗</a>
        </td>
        <td class="px-4 py-3 whitespace-nowrap">
          ${u.data_start_detectata
            ? `<div class="text-emerald-400 font-bold font-mono">${escapeHtml(u.data_start_detectata)}</div>
               <div class="text-[10px] text-slate-400">${escapeHtml(u.data_text_detectat)}</div>`
            : `<span class="text-[11px] text-amber-300">Fără dată ISO extrasă</span>`
          }
          ${u.locatie_detectata ? `<div class="text-[10px] text-slate-300 mt-0.5">📍 ${escapeHtml(u.locatie_detectata)}</div>` : ""}
        </td>
        <td class="px-4 py-3 text-right whitespace-nowrap space-x-1.5">
          ${u.status === "De verificat"
            ? `<button onclick="approveMonitorUpdate(${u.id})" class="px-2.5 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-bold">${u.eveniment_id ? "✓ Aprobă și actualizează" : "+ Importă eveniment"}</button>
               <button onclick="ignoreMonitorUpdate(${u.id})" class="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg">✕ Ignoră</button>`
            : `<span class="px-2 py-1 rounded text-[10px] font-bold ${u.status === "Aprobat" ? "bg-emerald-950 text-emerald-300" : "bg-slate-800 text-slate-400"}">${escapeHtml(u.status)}</span>`
          }
        </td>
      </tr>
    `).join("")
    : `<tr><td colspan="5" class="px-4 py-8 text-center text-slate-400">Nicio actualizare cu statusul „${escapeHtml(monitorStatusFilter)}”. Apasă „Scanează acum sursele noi” pentru o verificare live.</td></tr>`;

  const sources = data.sources || [];
  const sourceRows = sources.map((s) => `
    <tr class="hover:bg-slate-800/40">
      <td class="px-4 py-2.5">
        <div class="font-bold text-white">${escapeHtml(s.nume)}</div>
        <div class="text-[10px] text-slate-400 font-mono">${escapeHtml(s.parser)} • Regiune: ${escapeHtml(s.regiune_focus || "Moldova")}</div>
      </td>
      <td class="px-4 py-2.5">${sourceTypeBadge(s.tip)}</td>
      <td class="px-4 py-2.5 text-[11px]">
        <div class="${String(s.last_status || "").startsWith("ERR") || String(s.last_status || "").startsWith("HTTP 4") ? "text-red-400" : "text-emerald-400"} font-mono">${escapeHtml(s.last_status || "Neaccesat încă")}</div>
        <div class="text-[10px] text-slate-400">${escapeHtml(s.last_checked_at || "—")}</div>
      </td>
      <td class="px-4 py-2.5 text-[11px] text-slate-300">
        <strong>${s.last_new_items || 0}</strong> noi / <strong>${s.total_matches || 0}</strong> potriviri
      </td>
      <td class="px-4 py-2.5 text-right space-x-1.5 whitespace-nowrap">
        <a href="${escapeHtml(safeUrl(s.url))}" target="_blank" rel="noopener noreferrer" class="px-2 py-1 bg-slate-800 hover:bg-slate-700 rounded text-sky-300">Deschide ↗</a>
        ${s.parser !== "social_manual"
          ? `<button onclick="runMonitorScanNow('${escapeHtml(s.id)}', this)" class="px-2 py-1 bg-amber-500/20 hover:bg-amber-500 text-amber-300 hover:text-slate-950 rounded font-semibold">Scanează</button>`
          : ""
        }
        <button onclick="toggleMonitorSource('${escapeHtml(s.id)}')" class="px-2 py-1 rounded font-semibold ${s.activ ? "bg-emerald-900/50 text-emerald-300 hover:bg-emerald-800" : "bg-slate-800 text-slate-400 hover:bg-slate-700"}">${s.activ ? "Activă" : "Pauză"}</button>
        <button onclick="deleteMonitorSource('${escapeHtml(s.id)}')" class="px-2 py-1 bg-red-900/30 hover:bg-red-700 text-red-300 hover:text-white rounded">Del</button>
      </td>
    </tr>
  `).join("");

  panel.innerHTML = `
    <div class="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-3">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div class="flex flex-wrap gap-3 text-xs">
          <div class="bg-slate-800/80 border border-slate-700 rounded-xl px-3 py-2">
            <div class="text-[10px] uppercase text-slate-400">Surse active</div>
            <div class="text-base font-extrabold text-white">${c.surse_active ?? 0}</div>
          </div>
          <div class="bg-slate-800/80 border border-slate-700 rounded-xl px-3 py-2">
            <div class="text-[10px] uppercase text-slate-400">Articole văzute (skip auto)</div>
            <div class="text-base font-extrabold text-sky-400">${c.articole_vazute ?? 0}</div>
          </div>
          <div class="bg-slate-800/80 border border-slate-700 rounded-xl px-3 py-2">
            <div class="text-[10px] uppercase text-slate-400">De verificat</div>
            <div class="text-base font-extrabold text-amber-400">${c.de_verificat ?? 0}</div>
          </div>
        </div>

        <div class="flex flex-wrap items-center gap-2 text-xs">
          <select onchange="monitorStatusFilter=this.value;loadMonitorTab()" class="bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-white">
            ${["De verificat", "Toate", "Aprobat", "Ignorat"].map((st) => `<option value="${st}" ${monitorStatusFilter === st ? "selected" : ""}>${st}</option>`).join("")}
          </select>
          <button onclick="runMonitorScanNow('', this)" class="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold transition">
            ▶ Scanează acum sursele noi
          </button>
          <button onclick="document.getElementById('addSourceFormWrap').classList.toggle('hidden')" class="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-semibold">
            + Adaugă sursă
          </button>
        </div>
      </div>

      <div class="text-[11px] text-slate-400">${lastRunHtml} • Cron automat Worker: <code class="text-amber-300">0 */6 * * *</code></div>
      ${bannerHtml}

      <form id="addSourceFormWrap" onsubmit="submitNewMonitorSource(event)" class="hidden bg-slate-950 border border-slate-700 rounded-xl p-4 grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
        <div>
          <label class="block text-slate-400 mb-1">Nume sursă *</label>
          <input id="srcNewName" type="text" required placeholder="ex: Crama Mircești" class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-white">
        </div>
        <div>
          <label class="block text-slate-400 mb-1">Tip *</label>
          <select id="srcNewTip" class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-white">
            <option value="Website Oficial">Website Oficial</option>
            <option value="Agenda">Agenda</option>
            <option value="Stiri">Știri RSS</option>
            <option value="Radio">Radio</option>
            <option value="Facebook">Facebook (referință manuală)</option>
          </select>
        </div>
        <div>
          <label class="block text-slate-400 mb-1">Parser *</label>
          <select id="srcNewParser" class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-white">
            <option value="html_links">html_links (Site / JSON-LD)</option>
            <option value="rss">rss (Feed XML)</option>
            <option value="fest_html">fest_html</option>
            <option value="social_manual">social_manual (Facebook)</option>
          </select>
        </div>
        <div class="sm:col-span-2">
          <label class="block text-slate-400 mb-1">URL complet *</label>
          <input id="srcNewUrl" type="url" required placeholder="https://..." class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-white">
        </div>
        <div class="flex items-end space-x-2">
          <button type="submit" class="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-lg">Salvează sursa</button>
          <button type="button" onclick="document.getElementById('addSourceFormWrap').classList.add('hidden')" class="px-3 py-1.5 bg-slate-800 text-slate-300 rounded-lg">Anulează</button>
        </div>
      </form>
    </div>

    <div class="bg-slate-900 border border-slate-800 rounded-2xl overflow-x-auto shadow-lg">
      <div class="px-4 py-3 border-b border-slate-800 font-bold text-xs text-amber-300">
        1. Actualizări și evenimente detectate din surse (${updates.length})
      </div>
      <table class="w-full text-left text-xs">
        <thead class="bg-slate-800/80 text-slate-400 uppercase text-[11px]">
          <tr>
            <th class="px-4 py-2.5">Sursă</th>
            <th class="px-4 py-2.5">Potrivire</th>
            <th class="px-4 py-2.5">Anunț / Titlu detectat</th>
            <th class="px-4 py-2.5">Dată &amp; Locație extrase</th>
            <th class="px-4 py-2.5 text-right">Acțiuni</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-800">${updatesRows}</tbody>
      </table>
    </div>

    <div class="bg-slate-900 border border-slate-800 rounded-2xl overflow-x-auto shadow-lg">
      <div class="px-4 py-3 border-b border-slate-800 font-bold text-xs text-sky-300">
        2. Surse monitorizate: Agende, Știri RSS, Radio, Crame &amp; Pagini Facebook (${sources.length})
      </div>
      <table class="w-full text-left text-xs">
        <thead class="bg-slate-800/80 text-slate-400 uppercase text-[11px]">
          <tr>
            <th class="px-4 py-2.5">Sursă &amp; Parser</th>
            <th class="px-4 py-2.5">Tip</th>
            <th class="px-4 py-2.5">Ultimul răspuns HTTP</th>
            <th class="px-4 py-2.5">Istoric detectare</th>
            <th class="px-4 py-2.5 text-right">Control</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-800">${sourceRows}</tbody>
      </table>
    </div>
  `;
}

async function runMonitorScanNow(sursaId = "", btnEl = null) {
  if (btnEl) {
    btnEl.disabled = true;
    btnEl.dataset.origText = btnEl.innerText;
    btnEl.innerText = "Se scanează...";
  }
  try {
    const payload = sursaId ? { sursa_id: sursaId } : { limit: 12 };
    const res = await fetch("/api/admin/monitor/run", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getAuthHeader() },
      body: JSON.stringify(payload),
    });
    if (res.status === 401) return logoutAdmin();
    const out = await res.json();
    lastMonitorBanner = `Scanare finalizată: ${out.sources_checked} surse verificate, ${out.sources_not_modified} neschimbate (304), ${out.items_seen_skipped} articole deja văzute sărite, ${out.items_new_scanned} articole noi scanate, ${out.matches_queued} potriviri puse în coadă.`;
    await loadAllCounts();
    await loadMonitorTab();
  } finally {
    if (btnEl && btnEl.isConnected) {
      btnEl.disabled = false;
      btnEl.innerText = btnEl.dataset.origText || "▶ Scanează acum";
    }
  }
}

async function approveMonitorUpdate(updId) {
  const res = await fetch(`/api/admin/monitor/updates/${updId}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeader() },
    body: "{}",
  });
  if (res.status === 401) return logoutAdmin();
  if (!res.ok) {
    const err = await res.json();
    alert(`Eroare aprobare: ${JSON.stringify(err)}`);
    return;
  }
  const out = await res.json();
  lastMonitorBanner = out.action === "created"
    ? `Eveniment nou creat în DB: ${out.item?.titlu}`
    : `Eveniment actualizat în DB: ${out.item?.titlu}`;
  await loadAllCounts();
  await loadMonitorTab();
}

async function ignoreMonitorUpdate(updId) {
  const res = await fetch(`/api/admin/monitor/updates/${updId}/ignore`, {
    method: "POST",
    headers: getAuthHeader(),
  });
  if (res.status === 401) return logoutAdmin();
  await loadAllCounts();
  await loadMonitorTab();
}

async function submitNewMonitorSource(ev) {
  ev.preventDefault();
  const payload = {
    nume: document.getElementById("srcNewName").value.trim(),
    tip: document.getElementById("srcNewTip").value,
    parser: document.getElementById("srcNewParser").value,
    url: document.getElementById("srcNewUrl").value.trim(),
  };
  const res = await fetch("/api/admin/monitor/sources", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeader() },
    body: JSON.stringify(payload),
  });
  if (res.status === 401) return logoutAdmin();
  if (!res.ok) {
    alert(`Eroare la adăugarea sursei: HTTP ${res.status}`);
    return;
  }
  lastMonitorBanner = `Sursă nouă adăugată: ${payload.nume}`;
  await loadMonitorTab();
}

async function toggleMonitorSource(sid) {
  const res = await fetch(`/api/admin/monitor/sources/${encodeURIComponent(sid)}/toggle`, {
    method: "POST",
    headers: getAuthHeader(),
  });
  if (res.status === 401) return logoutAdmin();
  await loadMonitorTab();
}

async function deleteMonitorSource(sid) {
  if (!confirm(`Ștergeți sursa monitorizată ${sid}?`)) return;
  const res = await fetch(`/api/admin/monitor/sources/${encodeURIComponent(sid)}`, {
    method: "DELETE",
    headers: getAuthHeader(),
  });
  if (res.status === 401) return logoutAdmin();
  await loadMonitorTab();
}

window.addEventListener("DOMContentLoaded", () => {
  checkSessionOnLoad();
  document.getElementById("adminSearch").addEventListener("input", () => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(loadAdminTab, 200);
  });
});
