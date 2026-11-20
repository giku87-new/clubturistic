import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = r'c:\Users\geo\OneDrive\Documents\clubturistic.md'
JSON_PATH = os.path.join(BASE_DIR, 'baza_date_turism_evenimente_moldova.json')
INDEX_HTML = os.path.join(BASE_DIR, 'index.html')

with open(JSON_PATH, 'r', encoding='utf-8') as f:
    records = json.load(f)

json_data_str = json.dumps(records, ensure_ascii=False)

index_template = """<!DOCTYPE html>
<html lang="ro">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ClubTuristic.md - Evenimente, Recurență & Gastronomie Moldova</title>
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
  <style>
    html { scroll-behavior: smooth; font-family: system-ui, -apple-system, sans-serif; }
    .line-clamp-2 { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
    .line-clamp-3 { display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
  </style>
</head>
<body class="bg-stone-50 text-stone-900 min-h-screen flex flex-col">

  <!-- TOP BAR -->
  <header class="sticky top-0 z-50 bg-white/95 backdrop-blur border-b border-stone-200 shadow-sm">
    <div class="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
      <div class="flex items-center space-x-3">
        <span class="text-2xl">🍇</span>
        <div>
          <span class="text-xl font-bold tracking-tight text-red-900">ClubTuristic<span class="text-amber-600">.md</span></span>
          <span class="hidden sm:inline-block ml-2 text-xs bg-amber-100 text-amber-800 px-2 py-0.5 rounded-full font-medium">Turism, Recurență & Gastronomie</span>
        </div>
      </div>

      <nav class="hidden md:flex items-center space-x-6 text-sm font-medium text-stone-600">
        <a href="#destinatii" class="text-red-900 hover:text-red-700 font-semibold">Descoperă</a>
        <a href="#destinatii" onclick="setSearch('Kasîm')" class="hover:text-stone-900">Kasîm (Ceadîr-Lunga)</a>
        <a href="#destinatii" onclick="setCategoryFilter('Festival')" class="hover:text-stone-900">Festivaluri Gastronomice</a>
        <a href="#destinatii" onclick="setCategoryFilter('Cramă')" class="hover:text-stone-900">Crame & Vinuri</a>
        <a href="#destinatii" onclick="setCategoryFilter('Primărie')" class="hover:text-stone-900">Hramurile Satelor (897)</a>
      </nav>

      <div class="flex items-center space-x-3">
        <a href="/admin" class="bg-slate-900 hover:bg-slate-800 text-white text-xs sm:text-sm font-semibold px-4 py-2 rounded-lg shadow-sm transition flex items-center space-x-1.5">
          <span>⚡ Panou Admin DB</span>
        </a>
      </div>
    </div>
  </header>

  <!-- HERO SECTION -->
  <section class="relative bg-gradient-to-b from-stone-900 via-stone-800 to-stone-900 text-white py-12 px-4 overflow-hidden">
    <div class="max-w-5xl mx-auto text-center relative z-10">
      <div class="inline-flex items-center space-x-2 bg-white/10 backdrop-blur px-3 py-1 rounded-full text-xs text-amber-300 font-medium mb-3">
        <span>📅 Bază de date cu date exacte și formule de recurență calendaristică</span>
      </div>
      <h1 class="text-3xl sm:text-5xl font-extrabold tracking-tight mb-3">
        Când și unde mâncăm gustos în <span class="text-amber-400">Moldova</span>?
      </h1>
      <p class="text-stone-300 text-sm sm:text-base max-w-3xl mx-auto mb-6">
        Fiecare eveniment are acum data sau regula sa clară de recurență: <span class="text-amber-300 font-medium">„a 3-a duminică din lună”</span>, <span class="text-amber-300 font-medium">„primul weekend din octombrie”</span>, hramurile bisericești anuale sau degustări permanente.
      </p>

      <!-- SEARCH BAR -->
      <div class="bg-white p-2 rounded-2xl shadow-2xl max-w-4xl mx-auto flex flex-col md:flex-row gap-2 text-stone-800 mb-4">
        <div class="flex-1 flex items-center px-3 py-2 border-b md:border-b-0 md:border-r border-stone-200">
          <span class="text-stone-400 mr-2">🔍</span>
          <input id="searchInput" type="text" placeholder="Caută plăcinte, mămăligă, Ceadîr-Lunga, 8 noiembrie, duminică..." 
                 class="w-full bg-transparent text-sm focus:outline-none" oninput="filterCards()">
        </div>
        
        <!-- REGION SELECT -->
        <div class="flex items-center px-3 py-2 md:border-r border-stone-200 min-w-[140px]">
          <span class="text-stone-400 mr-2">📍</span>
          <select id="regionSelect" class="w-full bg-transparent text-xs sm:text-sm font-medium focus:outline-none cursor-pointer" onchange="filterCards()">
            <option value="Toate">Toată Moldova</option>
            <option value="Centru">Centru (Codri)</option>
            <option value="Nord">Nord (Bălți, Soroca)</option>
            <option value="Sud">Sud (Lunca Prutului)</option>
            <option value="UTA Găgăuzia">UTA Găgăuzia</option>
            <option value="Chișinău">Chișinău</option>
          </select>
        </div>

        <!-- SEASON SELECT -->
        <div class="flex items-center px-3 py-2 md:border-r border-stone-200 min-w-[140px]">
          <span class="text-stone-400 mr-2">🍂</span>
          <select id="seasonSelect" class="w-full bg-transparent text-xs sm:text-sm font-medium focus:outline-none cursor-pointer" onchange="filterCards()">
            <option value="Toate">Toate Anotimpurile</option>
            <option value="Toamnă">Toamnă (Hramuri & Vin)</option>
            <option value="Vară">Vară (Festivaluri aer liber)</option>
            <option value="Primăvară">Primăvară (Hederlez & Mămăligă)</option>
            <option value="Iarnă">Iarnă (Tradiții & Colinde)</option>
            <option value="Permanent">Permanent / Weekenduri</option>
          </select>
        </div>

        <!-- MONTH SELECT -->
        <div class="flex items-center px-3 py-2 min-w-[130px]">
          <span class="text-stone-400 mr-2">🗓️</span>
          <select id="monthSelect" class="w-full bg-transparent text-xs sm:text-sm font-medium focus:outline-none cursor-pointer" onchange="filterCards()">
            <option value="Toate">Toate Lunile</option>
            <option value="Mai">Mai</option>
            <option value="Iunie">Iunie</option>
            <option value="Iulie">Iulie</option>
            <option value="August">August</option>
            <option value="Septembrie">Septembrie</option>
            <option value="Octombrie">Octombrie</option>
            <option value="Noiembrie">Noiembrie</option>
            <option value="Ianuarie">Ianuarie</option>
            <option value="Februarie">Februarie</option>
            <option value="Martie">Martie</option>
            <option value="Tot anul">Tot anul</option>
          </select>
        </div>

        <button onclick="filterCards()" class="bg-amber-600 hover:bg-amber-500 text-white font-semibold text-sm px-6 py-2.5 rounded-xl transition shadow">
          Filtrează
        </button>
      </div>

      <!-- QUICK TIMING & FOOD TAGS -->
      <div class="flex flex-wrap justify-center gap-2 text-xs">
        <span class="text-stone-400 py-1">Filtre rapide recurență:</span>
        <button onclick="setRecurrenceFilter('relativa')" class="rec-pill bg-white/10 hover:bg-white/20 px-3 py-1 rounded-full text-amber-300 border border-amber-500/30 transition">🔄 Recurențe Relative (ex: a 3-a duminică)</button>
        <button onclick="setSearch('8 Noiembrie')" class="bg-white/10 hover:bg-white/20 px-3 py-1 rounded-full text-stone-200 transition">📅 #8 Noiembrie (Kasîm & Sf. Dumitru)</button>
        <button onclick="setSearch('14 Octombrie')" class="bg-white/10 hover:bg-white/20 px-3 py-1 rounded-full text-stone-200 transition">📅 #14 Octombrie (Hram Chișinău)</button>
        <button onclick="setSearch('Primul weekend din Octombrie')" class="bg-white/10 hover:bg-white/20 px-3 py-1 rounded-full text-stone-200 transition">🍷 #Ziua Vinului</button>
        <button onclick="setSearch('Plăcinte')" class="bg-white/10 hover:bg-white/20 px-3 py-1 rounded-full text-stone-200 transition">🥟 #Plăcinte</button>
        <button onclick="setSearch('Mămăligă')" class="bg-white/10 hover:bg-white/20 px-3 py-1 rounded-full text-stone-200 transition">🌽 #Mămăligă</button>
        <button onclick="setSearch('Zeamă')" class="bg-amber-500/20 hover:bg-amber-500/30 px-3 py-1 rounded-full text-amber-200 border border-amber-400/40 transition">🍲 #Zeamă & Zama</button>
        <button onclick="resetFilters()" class="bg-stone-700 hover:bg-stone-600 px-3 py-1 rounded-full text-stone-300 transition">✕ Resetează filtrele</button>
      </div>
    </div>
  </section>

  <!-- MAIN LISTING -->
  <main class="max-w-7xl mx-auto px-4 py-8 flex-1" id="destinatii">
    
    <!-- CONTROLS & CATEGORY PILLS -->
    <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-4 border-b border-stone-200 mb-6 gap-3">
      <div>
        <h2 class="text-xl font-bold text-stone-900">Evenimente, Destinații și Hramuri Locale</h2>
        <p class="text-xs text-stone-500" id="resultsCount">Se încarcă datele...</p>
      </div>

      <div class="flex flex-wrap gap-1.5 text-xs">
        <button onclick="setCategoryFilter('all')" class="cat-pill active px-3 py-1.5 rounded-lg bg-stone-900 text-white font-medium">Toate (""" + str(len(records)) + """)</button>
        <button onclick="setCategoryFilter('Festival')" class="cat-pill px-3 py-1.5 rounded-lg bg-white border border-stone-300 text-stone-700 hover:bg-stone-100 font-medium">Festivaluri Gastronomice</button>
        <button onclick="setCategoryFilter('Cramă')" class="cat-pill px-3 py-1.5 rounded-lg bg-white border border-stone-300 text-stone-700 hover:bg-stone-100 font-medium">Crame & Oenoturism</button>
        <button onclick="setCategoryFilter('Agroturistic')" class="cat-pill px-3 py-1.5 rounded-lg bg-white border border-stone-300 text-stone-700 hover:bg-stone-100 font-medium">Pensiuni & Meșteșuguri</button>
        <button onclick="setCategoryFilter('Primărie')" class="cat-pill px-3 py-1.5 rounded-lg bg-white border border-stone-300 text-stone-700 hover:bg-stone-100 font-medium">Primării & Hramuri</button>
      </div>
    </div>

    <!-- CARDS GRID -->
    <div id="cardsGrid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
      <!-- Populated dynamically via JS -->
    </div>

    <!-- PAGINATION -->
    <div class="mt-8 pt-4 border-t border-stone-200 flex items-center justify-between text-xs text-stone-500">
      <div id="pageInfo">Pagina 1</div>
      <div class="flex space-x-2">
        <button onclick="prevPublicPage()" class="px-3 py-1.5 bg-white border border-stone-300 hover:bg-stone-100 rounded-lg font-medium text-stone-700">← Înapoi</button>
        <button onclick="nextPublicPage()" class="px-3 py-1.5 bg-white border border-stone-300 hover:bg-stone-100 rounded-lg font-medium text-stone-700">Înainte →</button>
      </div>
    </div>

  </main>

  <!-- MODAL -->
  <div id="detailsModal" class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 hidden flex items-center justify-center p-4">
    <div class="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl relative max-h-[90vh] overflow-y-auto">
      <button onclick="closeModal()" class="absolute top-4 right-4 text-stone-400 hover:text-stone-700 text-xl font-bold">✕</button>
      <div id="modalContent"></div>
    </div>
  </div>

  <footer class="bg-stone-900 text-stone-400 py-6 px-4 text-center text-xs mt-auto">
    <div class="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
      <div>© 2026 <strong>ClubTuristic.md</strong> — Promovarea Turismului și Gastronomiei din Republica Moldova</div>
      <div class="space-x-4">
        <a href="/admin" class="text-amber-400 hover:underline">Panou de Administrare DB</a>
        <a href="/api/calendar" target="_blank" class="text-amber-300 hover:underline">Calendar JSON API</a>
        <a href="/baza_date_turism_evenimente_moldova.csv" class="hover:underline">Descarcă CSV Oficial</a>
      </div>
    </div>
  </footer>

  <script>
    let allRecords = """ + json_data_str + """;
    let filtered = [...allRecords];
    let page = 1;
    const perPage = 24;
    let activeCategory = 'all';
    let filterRelativeOnly = false;

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

    function filterCards() {
      const q = normalizeText(document.getElementById('searchInput').value.trim());
      const tokens = q ? q.split(/\\s+/).filter(t => t.length > 0) : [];
      const reg = document.getElementById('regionSelect').value;
      const sez = document.getElementById('seasonSelect').value;
      const luna = document.getElementById('monthSelect').value;

      filtered = allRecords.filter(r => {
        const fullText = normalizeText(
          (r.denumire || '') + ' ' + (r.localitate || '') + ' ' + (r.raion_municipiu || '') + ' ' + 
          (r.profil_turistic_gastronomic || '') + ' ' + (r.evenimente_tipice || '') + ' ' + 
          (r.conducator_responsabil || '') + ' ' + (r.data_eveniment || '') + ' ' + 
          (r.recurenta || '') + ' ' + (r.luna || '') + ' ' + (r.sezon || '')
        );
        const matchQ = tokens.length === 0 || tokens.every(tok => fullText.includes(tok));
        const matchReg = reg === 'Toate' || r.regiune === reg;
        const matchSez = sez === 'Toate' || r.sezon === sez;
        const matchLuna = luna === 'Toate' || r.luna === luna;
        const matchCat = activeCategory === 'all' || (r.categorie && r.categorie.includes(activeCategory));
        const matchRel = !filterRelativeOnly || (r.tip_recurenta && r.tip_recurenta.includes('relativ'));

        return matchQ && matchReg && matchSez && matchLuna && matchCat && matchRel;
      });

      page = 1;
      renderCards();
    }

    function setSearch(tag) {
      document.getElementById('searchInput').value = tag;
      filterCards();
    }

    function setRecurrenceFilter(type) {
      filterRelativeOnly = !filterRelativeOnly;
      const btn = document.querySelector('.rec-pill');
      if (filterRelativeOnly) {
        btn.classList.add('bg-amber-500', 'text-stone-900', 'font-bold');
        btn.classList.remove('bg-white/10', 'text-amber-300');
      } else {
        btn.classList.remove('bg-amber-500', 'text-stone-900', 'font-bold');
        btn.classList.add('bg-white/10', 'text-amber-300');
      }
      filterCards();
    }

    function resetFilters() {
      document.getElementById('searchInput').value = '';
      document.getElementById('regionSelect').value = 'Toate';
      document.getElementById('seasonSelect').value = 'Toate';
      document.getElementById('monthSelect').value = 'Toate';
      activeCategory = 'all';
      filterRelativeOnly = false;
      document.querySelectorAll('.cat-pill').forEach(btn => {
        btn.classList.remove('bg-stone-900', 'text-white');
        btn.classList.add('bg-white', 'text-stone-700');
      });
      const first = document.querySelector('.cat-pill');
      if (first) {
        first.classList.remove('bg-white', 'text-stone-700');
        first.classList.add('bg-stone-900', 'text-white');
      }
      const recBtn = document.querySelector('.rec-pill');
      if (recBtn) {
        recBtn.classList.remove('bg-amber-500', 'text-stone-900', 'font-bold');
        recBtn.classList.add('bg-white/10', 'text-amber-300');
      }
      filterCards();
    }

    function setCategoryFilter(cat) {
      activeCategory = cat;
      document.querySelectorAll('.cat-pill').forEach(btn => {
        btn.classList.remove('bg-stone-900', 'text-white');
        btn.classList.add('bg-white', 'text-stone-700');
      });
      if (event && event.target) {
        event.target.classList.remove('bg-white', 'text-stone-700');
        event.target.classList.add('bg-stone-900', 'text-white');
      }
      filterCards();
    }

    function renderCards() {
      const grid = document.getElementById('cardsGrid');
      grid.innerHTML = '';

      const total = filtered.length;
      document.getElementById('resultsCount').innerText = `Găsite ${total} destinații, hramuri și evenimente cu recurență`;

      const totalPages = Math.ceil(total / perPage) || 1;
      const start = (page - 1) * perPage;
      const currentCards = filtered.slice(start, start + perPage);

      currentCards.forEach(r => {
        const card = document.createElement('div');
        card.className = "bg-white rounded-2xl overflow-hidden border border-stone-200 shadow-sm hover:shadow-md transition flex flex-col justify-between";

        let badgeColor = "bg-stone-800";
        let icon = "🏛️";
        if (r.categorie.includes('Festival')) { badgeColor = "bg-rose-700"; icon = "🍲"; }
        else if (r.categorie.includes('Cramă')) { badgeColor = "bg-purple-800"; icon = "🍷"; }
        else if (r.categorie.includes('Agroturistic')) { badgeColor = "bg-emerald-800"; icon = "🏺"; }
        else if (r.categorie.includes('Consiliu')) { badgeColor = "bg-blue-800"; icon = "🏢"; }

        // Iconiță sezon
        let sezIcon = "🍂";
        if (r.sezon === 'Vară') sezIcon = "☀️";
        else if (r.sezon === 'Primăvară') sezIcon = "🌱";
        else if (r.sezon === 'Iarnă') sezIcon = "❄️";
        else if (r.sezon === 'Permanent') sezIcon = "🔄";

        card.innerHTML = `
          <div class="p-4">
            <div class="flex items-center justify-between gap-1 text-xs mb-2">
              <span class="inline-flex items-center space-x-1 text-[10px] font-semibold text-white px-2 py-0.5 rounded truncate max-w-[170px] ${badgeColor}">
                <span>${icon}</span>
                <span>${r.categorie.split('(')[0]}</span>
              </span>
              <span class="text-stone-500 font-medium text-[10px] whitespace-nowrap">${r.regiune}</span>
            </div>

            <h3 class="font-bold text-sm text-stone-900 line-clamp-2 mb-1.5" title="${r.denumire}">
              ${r.denumire}
            </h3>

            <!-- DATA / RECURENTA BADGE -->
            <div class="bg-amber-50 border border-amber-200/60 rounded-xl p-2 mb-2">
              <div class="flex items-center justify-between gap-1 text-[11px] font-bold text-amber-900 mb-0.5">
                <span class="flex items-center space-x-1 truncate max-w-[150px]">
                  <span>📅</span>
                  <span class="truncate">${r.data_eveniment || 'Data la cerere'}</span>
                </span>
                <span class="text-stone-600 font-semibold text-[10px] whitespace-nowrap">${sezIcon} ${r.luna || r.sezon}</span>
              </div>
              <div class="text-[10px] text-amber-800 leading-tight line-clamp-2">
                ${r.recurenta || 'Eveniment organizat anual'}
              </div>
            </div>

            <div class="text-xs text-stone-600 font-medium mb-1.5 flex items-center space-x-1">
              <span>📍</span>
              <span class="truncate">${r.localitate}, rl. ${r.raion_municipiu}</span>
            </div>

            <p class="text-xs text-stone-600 line-clamp-2 mb-1">
              ${r.evenimente_tipice || r.profil_turistic_gastronomic}
            </p>
          </div>

          <div class="px-4 py-2.5 bg-stone-50 border-t border-stone-100 flex items-center justify-between">
            <span class="text-[10px] text-stone-500 truncate max-w-[140px]">${r.conducator_responsabil || ''}</span>
            <button onclick="openModal('${r.id}')" class="text-xs font-semibold text-red-900 hover:text-red-700 whitespace-nowrap">
              Vezi Program →
            </button>
          </div>
        `;
        grid.appendChild(card);
      });

      document.getElementById('pageInfo').innerText = `Pagina ${page} din ${totalPages}`;
    }

    function prevPublicPage() {
      if (page > 1) { page--; renderCards(); }
    }
    function nextPublicPage() {
      if (page < Math.ceil(filtered.length / perPage)) { page++; renderCards(); }
    }

    function openModal(id) {
      const r = allRecords.find(item => item.id === id);
      if (!r) return;
      document.getElementById('modalContent').innerHTML = `
        <div class="flex items-center space-x-3 mb-3">
          <span class="text-3xl">🍇</span>
          <div>
            <span class="text-xs font-semibold text-amber-700 uppercase">${r.categorie}</span>
            <h3 class="text-base sm:text-lg font-bold text-stone-900 leading-snug">${r.denumire}</h3>
          </div>
        </div>

        <!-- TIMING BOX -->
        <div class="bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200 rounded-xl p-3.5 mb-3">
          <div class="flex items-center justify-between mb-1">
            <span class="text-xs font-bold text-amber-900 uppercase tracking-wider flex items-center space-x-1">
              <span>📅</span>
              <span>Când se petrece:</span>
            </span>
            <span class="text-xs font-bold text-amber-800 bg-white px-2 py-0.5 rounded-full border border-amber-200">
              ${r.sezon} • ${r.luna}
            </span>
          </div>
          <div class="text-sm font-bold text-stone-900 mb-1">${r.data_eveniment || '-'}</div>
          <p class="text-xs text-amber-950 font-medium"><strong>Regulă de recurență:</strong> ${r.recurenta || '-'}</p>
          <div class="text-[11px] text-stone-500 mt-1">Tip calendaristic: ${r.tip_recurenta || 'Dată fixă'}</div>
        </div>

        <div class="space-y-2 text-xs text-stone-700 mb-4">
          <p><strong>📍 Localitate & Raion:</strong> ${r.localitate}, ${r.raion_municipiu} (Regiunea ${r.regiune})</p>
          <p><strong>🏠 Adresă oficială:</strong> ${r.adresa_completa || '-'}</p>
          <p><strong>👤 Conducător / Responsabil:</strong> ${r.conducator_responsabil || '-'}</p>
          
          <div class="p-3 bg-stone-50 rounded-xl border border-stone-200 my-2">
            <p class="font-bold text-stone-900 mb-1">🎉 Evenimente & Specific Culinar:</p>
            <p class="text-stone-800">${r.evenimente_tipice}</p>
            <p class="text-stone-600 mt-1">${r.profil_turistic_gastronomic}</p>
          </div>

          <div class="bg-stone-100 p-2.5 rounded-lg space-y-1 font-mono text-[11px]">
            <div>Email: ${r.email_contact || '-'}</div>
            <div>Telefon: ${r.telefon || '-'}</div>
            <div>Web: <a href="${r.website_social}" target="_blank" class="text-red-900 underline">${r.website_social || '-'}</a></div>
            <div>IDNO: ${r.idno_cod_fiscal} | CUATM: ${r.cod_cuatm}</div>
          </div>
        </div>

        <div class="flex space-x-2">
          <a href="https://www.google.com/maps/search/${encodeURIComponent(r.localitate + ' ' + r.raion_municipiu + ' Moldova')}" target="_blank"
             class="flex-1 text-center bg-red-900 hover:bg-red-800 text-white font-semibold py-2 rounded-xl text-xs transition shadow-sm">
            Vezi pe Google Maps
          </a>
          <button onclick="closeModal()" class="px-4 bg-stone-200 hover:bg-stone-300 text-stone-800 font-semibold py-2 rounded-xl text-xs transition">
            Închide
          </button>
        </div>
      `;
      document.getElementById('detailsModal').classList.remove('hidden');
    }

    function closeModal() {
      document.getElementById('detailsModal').classList.add('hidden');
    }

    window.addEventListener('DOMContentLoaded', () => {
      renderCards();
    });
  </script>

</body>
</html>
"""

with open(INDEX_HTML, 'w', encoding='utf-8') as f:
    f.write(index_template)

print("Generated:", INDEX_HTML)
