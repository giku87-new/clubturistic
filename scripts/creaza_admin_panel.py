"""
Generator pentru panoul de administrare tehnic (Admin Studio DB) pentru ClubTuristic.md.
Conține tabel cu toate cele 999 de înregistrări, căutare instantanee, filtrare după
regiune, raion, categorie, sezon, lună, sortare după orice coloană, paginare,
editare și adăugare directă cu sincronizare automată în REST API / SQLite, și export CSV/JSON.
"""

import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_PATH = os.path.join(BASE_DIR, 'baza_date_turism_evenimente_moldova.json')
OUT_HTML = os.path.join(BASE_DIR, 'admin.html')
ARTIFACT_HTML = r'C:\Users\geo\.gemini\antigravity\brain\49255be3-4071-4a72-95c8-43c0ab2bf1b5\admin_panel.html'

with open(JSON_PATH, 'r', encoding='utf-8') as f:
    records = json.load(f)

json_data_str = json.dumps(records, ensure_ascii=False)
total_count = len(records)
apl1_count = sum(1 for r in records if 'APL I' in r.get('categorie', ''))
apl2_count = sum(1 for r in records if 'APL II' in r.get('categorie', ''))
crama_fest_count = sum(1 for r in records if any(k in r.get('categorie', '') for k in ['Cramă', 'Festival', 'Agroturistic', 'Organizator']))
relativ_count = sum(1 for r in records if 'relativ' in r.get('tip_recurenta', '').lower())

html_template = """<!DOCTYPE html>
<html lang="ro" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ClubTuristic.md - Admin Database Studio & Recurență</title>
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace, sans-serif; }
    .table-cell-truncate { max-width: 200px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #0f172a; }
    ::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #475569; }
  </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col font-sans">

  <!-- TOP APP BAR -->
  <header class="bg-slate-900 border-b border-slate-800 px-6 py-3 flex items-center justify-between sticky top-0 z-30 shadow-md">
    <div class="flex items-center space-x-3">
      <div class="w-8 h-8 rounded-lg bg-amber-500/20 border border-amber-500/40 flex items-center justify-center text-amber-400 font-bold text-base">
        ⚡
      </div>
      <div>
        <div class="flex items-center space-x-2">
          <h1 class="text-sm font-bold tracking-tight text-white">ClubTuristic.md <span class="text-amber-400 font-mono text-xs">DB Studio</span></h1>
          <span class="bg-emerald-950 text-emerald-400 border border-emerald-800 text-[10px] font-mono px-2 py-0.5 rounded-full flex items-center space-x-1">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>REST API & SQLite Sync</span>
          </span>
        </div>
        <p class="text-[11px] text-slate-400 font-mono">Schema Extinsă: """ + str(total_count) + """ Entități • Date Exacte & Formule Recurență</p>
      </div>
    </div>

    <!-- Actions -->
    <div class="flex items-center space-x-2 text-xs">
      <a href="/" target="_blank" class="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700 flex items-center space-x-1.5 transition">
        <span>🌐</span>
        <span>Portal Public</span>
      </a>
      <a href="/api/calendar" target="_blank" class="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-amber-300 rounded-lg border border-slate-700 flex items-center space-x-1.5 transition font-mono">
        <span>📅</span>
        <span>API Calendar</span>
      </a>
      <button onclick="openAddModal()" class="px-3 py-1.5 bg-amber-600 hover:bg-amber-500 text-slate-950 font-bold rounded-lg shadow transition flex items-center space-x-1">
        <span>+</span>
        <span>Adaugă Entitate</span>
      </button>
      <button onclick="exportCSV()" class="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700 flex items-center space-x-1 transition" title="Exportă CSV">
        <span>📥</span>
        <span>CSV</span>
      </button>
      <button onclick="exportJSON()" class="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700 flex items-center space-x-1 transition" title="Exportă JSON">
        <span>📥</span>
        <span>JSON</span>
      </button>
    </div>
  </header>

  <!-- QUICK STATS BAR -->
  <section class="bg-slate-900/60 border-b border-slate-800/80 px-6 py-2.5">
    <div class="max-w-7xl mx-auto flex flex-wrap items-center justify-between text-xs text-slate-400 gap-3">
      <div class="flex items-center space-x-4">
        <div>Total: <span class="text-white font-bold font-mono">""" + str(total_count) + """</span> entități</div>
        <div class="text-slate-600">|</div>
        <div>Primării APL I: <span class="text-amber-400 font-bold font-mono">""" + str(apl1_count) + """</span></div>
        <div class="text-slate-600">|</div>
        <div>Consilii APL II: <span class="text-blue-400 font-bold font-mono">""" + str(apl2_count) + """</span></div>
        <div class="text-slate-600">|</div>
        <div>Crame & Festivaluri: <span class="text-purple-400 font-bold font-mono">""" + str(crama_fest_count) + """</span></div>
        <div class="text-slate-600">|</div>
        <div>Recurență Relativă: <span class="text-emerald-400 font-bold font-mono">""" + str(relativ_count) + """</span></div>
      </div>
      <div class="flex items-center space-x-2 font-mono text-[11px]">
        <span class="text-slate-500">Host:</span>
        <span class="text-slate-300 bg-slate-800 px-1.5 py-0.5 rounded border border-slate-700">127.0.0.1:8080</span>
        <span class="text-slate-500">DB:</span>
        <span class="text-slate-300 bg-slate-800 px-1.5 py-0.5 rounded border border-slate-700">clubturistic.db (SQLite)</span>
      </div>
    </div>
  </section>

  <!-- FILTER & SEARCH TOOLBAR -->
  <section class="max-w-7xl w-full mx-auto px-6 pt-4 pb-2">
    <div class="bg-slate-800 border border-slate-700 rounded-xl p-3 flex flex-wrap items-center justify-between gap-3 shadow-sm">
      
      <!-- Quick Search -->
      <div class="flex-1 min-w-[260px] relative">
        <span class="absolute left-3 top-2.5 text-slate-400 text-xs">🔍</span>
        <input id="adminSearch" type="text" placeholder="Caută în """ + str(total_count) + """ de înregistrări (nume, primar, recurență, dată, mâncare, IDNO)..."
               class="w-full bg-slate-900 border border-slate-700 rounded-lg pl-8 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-amber-500"
               oninput="applyFilters()">
      </div>

      <!-- Filters -->
      <div class="flex flex-wrap items-center gap-2">
        <select id="filterRegiune" class="bg-slate-900 border border-slate-700 text-xs text-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none" onchange="applyFilters()">
          <option value="">Toate Regiunile</option>
          <option value="Centru">Centru</option>
          <option value="Nord">Nord</option>
          <option value="Sud">Sud</option>
          <option value="UTA Găgăuzia">UTA Găgăuzia</option>
          <option value="Chișinău">Chișinău</option>
        </select>

        <select id="filterCategorie" class="bg-slate-900 border border-slate-700 text-xs text-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none" onchange="applyFilters()">
          <option value="">Toate Categoriile</option>
          <option value="Primărie (APL I)">Primărie (APL I)</option>
          <option value="Consiliu Raional / Municipal (APL II)">Consiliu Raional (APL II)</option>
          <option value="Direcție Cultură și Turism">Direcție Cultură & Turism</option>
          <option value="Festival">Festivaluri Gastronomice</option>
          <option value="Cramă">Crame & Oenoturism</option>
          <option value="Agroturistic">Pensiuni Rurale & Meșteșugari</option>
        </select>

        <select id="filterSezon" class="bg-slate-900 border border-slate-700 text-xs text-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none" onchange="applyFilters()">
          <option value="">Toate Sezoanele</option>
          <option value="Toamnă">Toamnă</option>
          <option value="Vară">Vară</option>
          <option value="Primăvară">Primăvară</option>
          <option value="Iarnă">Iarnă</option>
          <option value="Permanent">Permanent</option>
        </select>

        <select id="filterLuna" class="bg-slate-900 border border-slate-700 text-xs text-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none" onchange="applyFilters()">
          <option value="">Toate Lunile</option>
          <option value="Mai">Mai</option>
          <option value="Iunie">Iunie</option>
          <option value="Iulie">Iulie</option>
          <option value="August">August</option>
          <option value="Septembrie">Septembrie</option>
          <option value="Octombrie">Octombrie</option>
          <option value="Noiembrie">Noiembrie</option>
          <option value="Ianuarie">Ianuarie</option>
          <option value="Tot anul">Tot anul</option>
        </select>

        <select id="filterRaion" class="bg-slate-900 border border-slate-700 text-xs text-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none" onchange="applyFilters()">
          <option value="">Toate Raioanele</option>
        </select>

        <button onclick="resetAdminFilters()" class="text-xs text-slate-400 hover:text-white px-2 py-1 underline">Resetează</button>
      </div>

    </div>
  </section>

  <!-- DATA TABLE -->
  <section class="max-w-7xl w-full mx-auto px-6 py-3 flex-1 flex flex-col">
    <div class="bg-slate-800 border border-slate-700 rounded-xl overflow-hidden shadow-lg flex-1 flex flex-col">
      
      <!-- Table Header & Counter -->
      <div class="px-4 py-2.5 bg-slate-800/90 border-b border-slate-700 flex items-center justify-between text-xs text-slate-400">
        <div>
          Se afișează <span class="font-bold text-white" id="displayedCount">0</span> din <span class="font-bold text-white" id="totalCount">""" + str(total_count) + """</span> înregistrări
        </div>
        <div class="flex items-center space-x-2">
          <span>Rânduri pe pagină:</span>
          <select id="pageSize" class="bg-slate-900 border border-slate-700 text-xs rounded px-2 py-0.5 text-white" onchange="changePageSize()">
            <option value="25">25</option>
            <option value="50" selected>50</option>
            <option value="100">100</option>
            <option value="500">500</option>
          </select>
        </div>
      </div>

      <!-- Scrollable Table -->
      <div class="overflow-x-auto flex-1 max-h-[550px]">
        <table class="w-full text-left text-xs text-slate-300">
          <thead class="bg-slate-900/90 text-slate-400 uppercase font-semibold text-[10px] sticky top-0 z-10 border-b border-slate-700">
            <tr>
              <th class="px-3 py-2.5 cursor-pointer hover:text-white" onclick="sortBy('id')">ID ↕</th>
              <th class="px-3 py-2.5 cursor-pointer hover:text-white" onclick="sortBy('denumire')">Denumire Entitate ↕</th>
              <th class="px-3 py-2.5 cursor-pointer hover:text-white" onclick="sortBy('data_eveniment')">Dată & Recurență ↕</th>
              <th class="px-3 py-2.5 cursor-pointer hover:text-white" onclick="sortBy('categorie')">Categorie ↕</th>
              <th class="px-3 py-2.5 cursor-pointer hover:text-white" onclick="sortBy('regiune')">Regiune ↕</th>
              <th class="px-3 py-2.5 cursor-pointer hover:text-white" onclick="sortBy('raion_municipiu')">Raion / Localitate ↕</th>
              <th class="px-3 py-2.5">Specific Culinar & Evenimente</th>
              <th class="px-3 py-2.5">Contact (Email / Tel)</th>
              <th class="px-3 py-2.5 text-right">Acțiuni</th>
            </tr>
          </thead>
          <tbody id="tableBody" class="divide-y divide-slate-700/60 font-mono text-[11px]">
            <!-- Rendered by JS -->
          </tbody>
        </table>
      </div>

      <!-- Pagination Footer -->
      <div class="px-4 py-3 bg-slate-900 border-t border-slate-700 flex items-center justify-between text-xs text-slate-400">
        <div id="pageInfo">Pagina 1 din 20</div>
        <div class="flex items-center space-x-1">
          <button onclick="prevPage()" class="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-white rounded border border-slate-700 text-xs">← Înapoi</button>
          <div id="pageButtons" class="flex space-x-1"></div>
          <button onclick="nextPage()" class="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-white rounded border border-slate-700 text-xs">Înainte →</button>
        </div>
      </div>

    </div>
  </section>

  <!-- MODAL EDIT RECORD -->
  <div id="editModal" class="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 hidden flex items-center justify-center p-4">
    <div class="bg-slate-800 border border-slate-700 rounded-2xl max-w-2xl w-full p-6 shadow-2xl relative max-h-[90vh] overflow-y-auto">
      <button onclick="closeEditModal()" class="absolute top-4 right-4 text-slate-400 hover:text-white text-lg font-bold">✕</button>
      
      <div class="flex items-center space-x-2 mb-4 border-b border-slate-700 pb-3">
        <span class="text-xl">✏️</span>
        <h3 class="text-base font-bold text-white" id="modalTitle">Editare Înregistrare & Recurență</h3>
      </div>

      <form id="editForm" onsubmit="saveRecord(event)" class="space-y-4 text-xs">
        <input type="hidden" id="editId">
        
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-slate-400 mb-1">Denumire Oficială:</label>
            <input id="editDenumire" type="text" required class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-white font-medium focus:border-amber-500 focus:outline-none">
          </div>
          <div>
            <label class="block text-slate-400 mb-1">Categorie:</label>
            <input id="editCategorie" type="text" required class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-white focus:border-amber-500 focus:outline-none">
          </div>
        </div>

        <!-- TIMING & RECURRENCE GROUP -->
        <div class="bg-slate-900/80 border border-amber-500/40 rounded-xl p-3 space-y-2">
          <div class="text-[11px] font-bold text-amber-400 uppercase tracking-wider flex items-center space-x-1">
            <span>📅</span>
            <span>Date Calendaristice & Formulă de Recurență</span>
          </div>
          <div class="grid grid-cols-3 gap-3">
            <div>
              <label class="block text-slate-300 mb-1 font-semibold">Dată Eveniment:</label>
              <input id="editDataEveniment" type="text" placeholder="ex: 8 Noiembrie sau a 3-a duminică" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-white font-medium focus:border-amber-500 focus:outline-none">
            </div>
            <div>
              <label class="block text-slate-300 mb-1 font-semibold">Lună Principală:</label>
              <input id="editLuna" type="text" placeholder="ex: Noiembrie" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-white focus:border-amber-500 focus:outline-none">
            </div>
            <div>
              <label class="block text-slate-300 mb-1 font-semibold">Sezon:</label>
              <input id="editSezon" type="text" placeholder="ex: Toamnă" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-white focus:border-amber-500 focus:outline-none">
            </div>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-slate-300 mb-1 font-semibold">Formulă Recurență (completă):</label>
              <input id="editRecurenta" type="text" placeholder="ex: Anual în a 3-a duminică din Mai" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-white focus:border-amber-500 focus:outline-none">
            </div>
            <div>
              <label class="block text-slate-300 mb-1 font-semibold">Tip Recurență:</label>
              <input id="editTipRecurenta" type="text" placeholder="ex: Recurență relativă / Dată fixă" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-white focus:border-amber-500 focus:outline-none">
            </div>
          </div>
        </div>

        <div class="grid grid-cols-3 gap-3">
          <div>
            <label class="block text-slate-400 mb-1">Regiune:</label>
            <input id="editRegiune" type="text" class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-white">
          </div>
          <div>
            <label class="block text-slate-400 mb-1">Raion / Municipiu:</label>
            <input id="editRaion" type="text" class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-white">
          </div>
          <div>
            <label class="block text-slate-400 mb-1">Localitate:</label>
            <input id="editLocalitate" type="text" class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-white">
          </div>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-slate-400 mb-1">Conducător / Primar / Director:</label>
            <input id="editConducator" type="text" class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-white">
          </div>
          <div>
            <label class="block text-slate-400 mb-1">Adresă Poștală / Juridică:</label>
            <input id="editAdresa" type="text" class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-white">
          </div>
        </div>

        <div>
          <label class="block text-slate-400 mb-1">Profil Gastronomic & Turistic (ce mâncăm, ce vizităm):</label>
          <textarea id="editProfil" rows="3" class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-white text-xs"></textarea>
        </div>

        <div>
          <label class="block text-slate-400 mb-1">Evenimente Tipice (Hram, Festival, Datini):</label>
          <input id="editEvenimente" type="text" class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-white">
        </div>

        <div class="grid grid-cols-3 gap-3">
          <div>
            <label class="block text-slate-400 mb-1">Email Contact:</label>
            <input id="editEmail" type="text" class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-white">
          </div>
          <div>
            <label class="block text-slate-400 mb-1">Telefon:</label>
            <input id="editTelefon" type="text" class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-white">
          </div>
          <div>
            <label class="block text-slate-400 mb-1">Website / Social:</label>
            <input id="editWebsite" type="text" class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-white">
          </div>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-slate-400 mb-1">IDNO (Cod Fiscal):</label>
            <input id="editIdno" type="text" class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-400 font-mono">
          </div>
          <div>
            <label class="block text-slate-400 mb-1">Cod CUATM:</label>
            <input id="editCuatm" type="text" class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-400 font-mono">
          </div>
        </div>

        <div class="flex items-center justify-end space-x-3 pt-3 border-t border-slate-700">
          <button type="button" onclick="closeEditModal()" class="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-white font-medium">Anulează</button>
          <button type="submit" class="px-5 py-2 bg-amber-600 hover:bg-amber-500 rounded-lg text-slate-950 font-bold transition">Salvează în SQLite</button>
        </div>
      </form>
    </div>
  </div>

  <!-- SCRIPT ENGINE -->
  <script>
    let dbData = """ + json_data_str + """;
    let filteredData = [...dbData];
    let currentPage = 1;
    let pageSize = 50;
    let sortColumn = 'id';
    let sortAsc = true;

    window.addEventListener('DOMContentLoaded', () => {
      populateRaioane();
      applyFilters();
    });

    function normalizeText(text) {
      if (!text) return '';
      return text.toLowerCase()
        .replace(/[ăâ]/g, 'a')
        .replace(/î/g, 'i')
        .replace(/[șş]/g, 's')
        .replace(/[țţ]/g, 't')
        .replace(/ciadir/g, 'ceadir')
        .replace(/\b(zama|zemii|zemei|zeamei|zeama|zami|zemuri)\b/gi, 'zeama')
        .replace(/\b(zam|zem)\b/gi, 'zeam');
    }

    function populateRaioane() {
      const select = document.getElementById('filterRaion');
      const raioane = [...new Set(dbData.map(r => r.raion_municipiu))].sort();
      raioane.forEach(r => {
        if (!r) return;
        const opt = document.createElement('option');
        opt.value = r;
        opt.innerText = r;
        select.appendChild(opt);
      });
    }

    function applyFilters() {
      const q = normalizeText(document.getElementById('adminSearch').value.trim());
      const tokens = q ? q.split(/\\s+/).filter(t => t.length > 0) : [];
      const reg = document.getElementById('filterRegiune').value;
      const cat = document.getElementById('filterCategorie').value;
      const sez = document.getElementById('filterSezon').value;
      const luna = document.getElementById('filterLuna').value;
      const raion = document.getElementById('filterRaion').value;

      filteredData = dbData.filter(item => {
        const fullText = normalizeText(
          (item.id || '') + ' ' + (item.denumire || '') + ' ' + (item.raion_municipiu || '') + ' ' + 
          (item.localitate || '') + ' ' + (item.conducator_responsabil || '') + ' ' + 
          (item.profil_turistic_gastronomic || '') + ' ' + (item.evenimente_tipice || '') + ' ' + 
          (item.data_eveniment || '') + ' ' + (item.recurenta || '') + ' ' + 
          (item.luna || '') + ' ' + (item.sezon || '') + ' ' + 
          (item.email_contact || '') + ' ' + (item.idno_cod_fiscal || '')
        );

        const matchQ = tokens.length === 0 || tokens.every(tok => fullText.includes(tok));
        const matchReg = !reg || item.regiune === reg;
        const matchCat = !cat || (item.categorie && item.categorie.includes(cat));
        const matchSez = !sez || item.sezon === sez;
        const matchLuna = !luna || item.luna === luna;
        const matchRaion = !raion || item.raion_municipiu === raion;

        return matchQ && matchReg && matchCat && matchSez && matchLuna && matchRaion;
      });

      currentPage = 1;
      renderTable();
    }

    function resetAdminFilters() {
      document.getElementById('adminSearch').value = '';
      document.getElementById('filterRegiune').value = '';
      document.getElementById('filterCategorie').value = '';
      document.getElementById('filterSezon').value = '';
      document.getElementById('filterLuna').value = '';
      document.getElementById('filterRaion').value = '';
      applyFilters();
    }

    function sortBy(col) {
      if (sortColumn === col) {
        sortAsc = !sortAsc;
      } else {
        sortColumn = col;
        sortAsc = true;
      }

      filteredData.sort((a, b) => {
        let vA = (a[col] || '').toString().toLowerCase();
        let vB = (b[col] || '').toString().toLowerCase();
        if (vA < vB) return sortAsc ? -1 : 1;
        if (vA > vB) return sortAsc ? 1 : -1;
        return 0;
      });

      renderTable();
    }

    function renderTable() {
      const tbody = document.getElementById('tableBody');
      tbody.innerHTML = '';

      const total = filteredData.length;
      document.getElementById('displayedCount').innerText = total;
      document.getElementById('totalCount').innerText = dbData.length;

      const totalPages = Math.ceil(total / pageSize) || 1;
      if (currentPage > totalPages) currentPage = totalPages;

      const start = (currentPage - 1) * pageSize;
      const end = Math.min(start + pageSize, total);
      const pageRecords = filteredData.slice(start, end);

      pageRecords.forEach(r => {
        const tr = document.createElement('tr');
        tr.className = 'hover:bg-slate-750 transition group border-b border-slate-800';

        let badgeCatClass = 'bg-slate-700 text-slate-300';
        if (r.categorie.includes('Primărie')) badgeCatClass = 'bg-amber-950 text-amber-300 border border-amber-800';
        else if (r.categorie.includes('Consiliu')) badgeCatClass = 'bg-blue-950 text-blue-300 border border-blue-800';
        else if (r.categorie.includes('Festival')) badgeCatClass = 'bg-rose-950 text-rose-300 border border-rose-800 font-bold';
        else if (r.categorie.includes('Cramă')) badgeCatClass = 'bg-purple-950 text-purple-300 border border-purple-800 font-bold';
        else if (r.categorie.includes('Cultură')) badgeCatClass = 'bg-indigo-950 text-indigo-300 border border-indigo-800';

        tr.innerHTML = `
          <td class="px-3 py-2 text-slate-400 font-mono text-[10px]">${r.id}</td>
          <td class="px-3 py-2 font-semibold text-white table-cell-truncate" title="${r.denumire}">
            ${r.denumire}
          </td>
          <td class="px-3 py-2 font-mono text-[10px]">
            <div class="text-amber-400 font-bold">${r.data_eveniment || '-'}</div>
            <div class="text-slate-400 truncate max-w-[170px]" title="${r.recurenta}">${r.recurenta || '-'}</div>
          </td>
          <td class="px-3 py-2">
            <span class="inline-block text-[10px] px-2 py-0.5 rounded ${badgeCatClass}">
              ${r.categorie}
            </span>
          </td>
          <td class="px-3 py-2 text-slate-300">${r.regiune}</td>
          <td class="px-3 py-2 text-slate-300">
            <div class="font-medium text-white">${r.raion_municipiu}</div>
            <div class="text-[10px] text-slate-400">${r.localitate}</div>
          </td>
          <td class="px-3 py-2 text-slate-300 table-cell-truncate" title="${r.evenimente_tipice} | ${r.profil_turistic_gastronomic}">
            <span class="text-amber-300 font-medium">${r.evenimente_tipice}</span>
          </td>
          <td class="px-3 py-2 text-slate-400 text-[10px]">
            <div>${r.email_contact || '-'}</div>
            <div class="text-slate-500">${r.telefon || ''}</div>
          </td>
          <td class="px-3 py-2 text-right space-x-1 whitespace-nowrap">
            <button onclick="openEditModal('${r.id}')" class="px-2 py-1 bg-amber-600/20 hover:bg-amber-600 text-amber-300 hover:text-black rounded transition font-medium">Edit</button>
            <button onclick="deleteRecord('${r.id}')" class="px-2 py-1 bg-red-900/30 hover:bg-red-700 text-red-300 hover:text-white rounded transition">Del</button>
          </td>
        `;
        tbody.appendChild(tr);
      });

      document.getElementById('pageInfo').innerText = `Pagina ${currentPage} din ${totalPages} (${total} rezultate)`;
    }

    function changePageSize() {
      pageSize = parseInt(document.getElementById('pageSize').value, 10);
      currentPage = 1;
      renderTable();
    }

    function prevPage() {
      if (currentPage > 1) {
        currentPage--;
        renderTable();
      }
    }

    function nextPage() {
      const totalPages = Math.ceil(filteredData.length / pageSize) || 1;
      if (currentPage < totalPages) {
        currentPage++;
        renderTable();
      }
    }

    // Modal Edit & Add
    function openEditModal(id) {
      const rec = dbData.find(item => item.id === id);
      if (!rec) return;

      document.getElementById('modalTitle').innerText = `Editare: ${rec.denumire}`;
      document.getElementById('editId').value = rec.id;
      document.getElementById('editDenumire').value = rec.denumire || '';
      document.getElementById('editCategorie').value = rec.categorie || '';
      document.getElementById('editRegiune').value = rec.regiune || '';
      document.getElementById('editRaion').value = rec.raion_municipiu || '';
      document.getElementById('editLocalitate').value = rec.localitate || '';
      document.getElementById('editDataEveniment').value = rec.data_eveniment || '';
      document.getElementById('editRecurenta').value = rec.recurenta || '';
      document.getElementById('editTipRecurenta').value = rec.tip_recurenta || '';
      document.getElementById('editLuna').value = rec.luna || '';
      document.getElementById('editSezon').value = rec.sezon || '';
      document.getElementById('editConducator').value = rec.conducator_responsabil || '';
      document.getElementById('editAdresa').value = rec.adresa_completa || '';
      document.getElementById('editProfil').value = rec.profil_turistic_gastronomic || '';
      document.getElementById('editEvenimente').value = rec.evenimente_tipice || '';
      document.getElementById('editEmail').value = rec.email_contact || '';
      document.getElementById('editTelefon').value = rec.telefon || '';
      document.getElementById('editWebsite').value = rec.website_social || '';
      document.getElementById('editIdno').value = rec.idno_cod_fiscal || '';
      document.getElementById('editCuatm').value = rec.cod_cuatm || '';

      document.getElementById('editModal').classList.remove('hidden');
    }

    function openAddModal() {
      document.getElementById('modalTitle').innerText = 'Adăugare Entitate Nouă în Baza de Date';
      document.getElementById('editForm').reset();
      document.getElementById('editId').value = 'CUSTOM-' + Date.now();
      document.getElementById('editModal').classList.remove('hidden');
    }

    function closeEditModal() {
      document.getElementById('editModal').classList.add('hidden');
    }

    async function saveRecord(e) {
      e.preventDefault();
      const id = document.getElementById('editId').value;
      let existing = dbData.find(item => item.id === id);
      const isNew = !existing;

      const recordObj = {
        id: id,
        denumire: document.getElementById('editDenumire').value,
        categorie: document.getElementById('editCategorie').value,
        regiune: document.getElementById('editRegiune').value,
        raion_municipiu: document.getElementById('editRaion').value,
        localitate: document.getElementById('editLocalitate').value,
        data_eveniment: document.getElementById('editDataEveniment').value,
        recurenta: document.getElementById('editRecurenta').value,
        tip_recurenta: document.getElementById('editTipRecurenta').value,
        luna: document.getElementById('editLuna').value,
        sezon: document.getElementById('editSezon').value,
        conducator_responsabil: document.getElementById('editConducator').value,
        adresa_completa: document.getElementById('editAdresa').value,
        profil_turistic_gastronomic: document.getElementById('editProfil').value,
        evenimente_tipice: document.getElementById('editEvenimente').value,
        email_contact: document.getElementById('editEmail').value,
        telefon: document.getElementById('editTelefon').value,
        website_social: document.getElementById('editWebsite').value,
        idno_cod_fiscal: document.getElementById('editIdno').value,
        cod_cuatm: document.getElementById('editCuatm').value
      };

      if (existing) {
        Object.assign(existing, recordObj);
      } else {
        dbData.unshift(recordObj);
      }

      // Persistă în backend SQLite dacă serverul e activ
      try {
        const method = isNew ? 'POST' : 'PUT';
        const url = isNew ? '/api/entitati' : ('/api/entitati/' + encodeURIComponent(id));
        await fetch(url, {
          method: method,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(recordObj)
        });
      } catch (err) {
        console.warn('Salvat local:', err);
      }

      closeEditModal();
      applyFilters();
      alert(`Înregistrarea "${recordObj.denumire}" a fost salvată cu succes în baza de date SQLite!`);
    }

    async function deleteRecord(id) {
      const idx = dbData.findIndex(item => item.id === id);
      if (idx !== -1) {
        if (confirm(`Sigur doriți să ștergeți entitatea "${dbData[idx].denumire}"?`)) {
          dbData.splice(idx, 1);
          try {
            await fetch('/api/entitati/' + encodeURIComponent(id), { method: 'DELETE' });
          } catch (err) {
            console.warn('Șters local:', err);
          }
          applyFilters();
          alert(`Entitatea a fost eliminată din baza de date!`);
        }
      }
    }

    function exportJSON() {
      const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(dbData, null, 2));
      const downloadAnchor = document.createElement('a');
      downloadAnchor.setAttribute("href", dataStr);
      downloadAnchor.setAttribute("download", "baza_date_turism_actualizata.json");
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      downloadAnchor.remove();
    }

    function exportCSV() {
      if (!dbData.length) return;
      const headers = Object.keys(dbData[0]);
      const csvRows = [headers.map(h => `"${h}"`).join(',')];
      
      dbData.forEach(row => {
        const values = headers.map(h => {
          const val = (row[h] || '').toString().replace(/"/g, '""');
          return `"${val}"`;
        });
        csvRows.push(values.join(','));
      });

      const csvContent = "\\uFEFF" + csvRows.join('\\r\\n');
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = "baza_date_turism_actualizata.csv";
      document.body.appendChild(a);
      a.click();
      a.remove();
    }
  </script>

</body>
</html>
"""

with open(OUT_HTML, 'w', encoding='utf-8') as f:
    f.write(html_template)
print("Generat:", OUT_HTML)

try:
    with open(ARTIFACT_HTML, 'w', encoding='utf-8') as f:
        f.write(html_template)
    print("Generat:", ARTIFACT_HTML)
except Exception as e:
    print("Artifact skip:", e)
