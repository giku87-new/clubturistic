/**
 * ClubTuristic.md Admin Studio v2
 * Autentificare Basic Auth stocată în sessionStorage și operațiuni CRUD live pe SQLite + FTS5.
 */

let admTab = "evenimente";
let admCache = [];
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

  document.getElementById("addBtn").classList.toggle("hidden", tab === "propuneri");
  loadAdminTab();
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
          <div class="text-[10px] text-emerald-400">${escapeHtml(r.status_data)}</div>
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
      fieldInput("regula_recurenta", "Regulă de recurență", item.regula_recurenta || ""),
      fieldInput("luna_principala", "Lună principală", item.luna_principala || "Iunie"),
      fieldInput("luni_active", "Luni active (separate prin virgulă)", item.luni_active || "Iunie"),
      fieldInput("sezon", "Sezon (Primăvară / Vară / Toamnă / Iarnă / Permanent)", item.sezon || "Vară"),
      fieldInput("status_data", "Status (Confirmat / Estimat după tradiție / Săptămânal activ)", item.status_data || "Confirmat"),
      fieldInput("ultima_editie_verificata", "Ultima ediție verificată", item.ultima_editie_verificata || ""),
      fieldInput("urmatoarea_data_estimata", "Următoarea dată (YYYY-MM-DD)", item.urmatoarea_data_estimata || "2027-06-15"),
      fieldInput("pret_intrare", "Preț intrare", item.pret_intrare || "Gratuit"),
      fieldInput("link_oficial", "Link oficial (https://...)", item.link_oficial || "https://moldova.travel/ro"),
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

window.addEventListener("DOMContentLoaded", () => {
  checkSessionOnLoad();
  document.getElementById("adminSearch").addEventListener("input", () => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(loadAdminTab, 200);
  });
});
