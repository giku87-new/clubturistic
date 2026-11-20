# Ghid Pas cu Pas de Deploy pentru ClubTuristic.md

Acest ghid explică modul în care poți publica site-ul pe internet în doar câteva minute, în funcție de tipul de găzduire pe care îl preferi.

---

## 🏆 Opțiunea 1: Cloud Modern Gratuit (Render.com) — *Cea mai simplă recomandare*
**Cost:** 0 Lei (Gratuit)  
**Timp necesar:** ~3 minute  
**Ce primești:** Link securizat HTTPS automat, domeniu propriu `clubturistic.md`, actualizare automată la fiecare modificare.

### Pași:
1. Încarcă proiectul pe un cont gratuit de **GitHub** (ex: `github.com/numele-tau/clubturistic`).
2. Intră pe [Render.com](https://render.com) și creează un cont gratuit (te poți loga direct cu GitHub).
3. Apasă pe **New +** ➔ **Web Service**.
4. Selectează depozitul tău `clubturistic`.
5. Completează doar aceste 2 câmpuri:
   - **Build Command:** `pip install -r requirements.txt` *(sau lasă liber)*
   - **Start Command:** `python server.py`
6. Apasă **Create Web Service**.
7. În 60 de secunde, site-ul tău este live pe o adresă de tipul `clubturistic.onrender.com`!
8. Din secțiunea **Custom Domains**, adaugi `clubturistic.md`.

---

## 🇲🇩 Opțiunea 2: Hosting Tradițional din Moldova sau cPanel (TopHost.md, AlexHost, Hostinger)
Dacă ai deja cumpărat un pachet clasic de găzduire cu **cPanel**:

### Pași:
1. Te autentifici în panoul **cPanel**.
2. Cauți secțiunea **Software** ➔ **Setup Python App**.
3. Apasă **Create Application**:
   - **Python version:** Selectează `3.10` sau `3.11` sau `3.12`.
   - **Application root:** `clubturistic`
   - **Application startup file:** `server.py`
4. Deschizi **File Manager** și încarci fișierele proiectului în folderul `clubturistic`.
5. Apasă pe **Restart** în Python App Manager. Site-ul este activ direct pe domeniul tău!

---

## 🐳 Opțiunea 3: Server VPS Propriu cu Docker (Hetzner, DigitalOcean)
Dacă ai un server virtual Linux (Ubuntu/Debian):

```bash
# 1. Clonează fișierele pe server
git clone https://github.com/numele-tau/clubturistic.git
cd clubturistic

# 2. Lansează containerul cu o singură comandă
docker compose up -d --build
```
Site-ul rulează automat pe portul 8080 în fundal și repornește singur dacă serverul este resetat.
