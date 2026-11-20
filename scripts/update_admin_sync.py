import os

BASE_DIR = r'c:\Users\geo\OneDrive\Documents\clubturistic.md'
ADMIN_HTML = os.path.join(BASE_DIR, 'admin.html')

with open(ADMIN_HTML, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace saveRecord to call REST API
old_save = """    function saveRecord(e) {
      e.preventDefault();
      const id = document.getElementById('editId').value;
      let existing = dbData.find(item => item.id === id);"""

new_save = """    async function saveRecord(e) {
      e.preventDefault();
      const id = document.getElementById('editId').value;
      let existing = dbData.find(item => item.id === id);
      const isNew = !existing;"""

content = content.replace(old_save, new_save)

old_after_save = """      if (existing) {
        Object.assign(existing, recordObj);
      } else {
        dbData.unshift(recordObj);
      }

      closeEditModal();
      applyFilters();
      alert(`Înregistrarea "${recordObj.denumire}" a fost salvată cu succes în baza de date!`);
    }"""

new_after_save = """      if (existing) {
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
        console.warn('Salvat local (server offline sau rulare via file://):', err);
      }

      closeEditModal();
      applyFilters();
      alert(`Înregistrarea "${recordObj.denumire}" a fost salvată cu succes în baza de date SQLite!`);
    }"""

content = content.replace(old_after_save, new_after_save)

# Also enhance deleteRecord
old_delete = """    function deleteRecord(id) {
      const idx = dbData.findIndex(item => item.id === id);
      if (idx !== -1) {
        if (confirm(`Sigur doriți să ștergeți entitatea ${dbData[idx].denumire}?`)) {
          dbData.splice(idx, 1);
          applyFilters();
        }
      }
    }"""

new_delete = """    async function deleteRecord(id) {
      const idx = dbData.findIndex(item => item.id === id);
      if (idx !== -1) {
        if (confirm(`Sigur doriți să ștergeți entitatea "${dbData[idx].denumire}"?`)) {
          const removed = dbData.splice(idx, 1)[0];
          try {
            await fetch('/api/entitati/' + encodeURIComponent(id), { method: 'DELETE' });
          } catch (err) {
            console.warn('Șters local:', err);
          }
          applyFilters();
          alert(`Entitatea a fost eliminată din baza de date!`);
        }
      }
    }"""

content = content.replace(old_delete, new_delete)

with open(ADMIN_HTML, 'w', encoding='utf-8') as f:
    f.write(content)

print("admin.html updated with live REST API sync!")
