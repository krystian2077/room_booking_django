# 🏢 RoomBooker - System Zarządzania Rezerwacjami Sal

<div align="center">

**Zbudowano z ❤️ używając Django**

![Django](https://img.shields.io/badge/Django-6.0.2-092E20?style=for-the-badge&logo=django&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.13+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

**Nowoczesna aplikacja webowa do rezerwacji sal konferencyjnych**  
**z powiadomieniami i rozbudowanym dashboardem analitycznym**

</div>

---

## 🚀 Dostęp do aplikacji

<div align="center">

### 🌐 [Aplikacja Live](https://roombooker-app-m03e.onrender.com)

### 🔐 [Panel Admina](https://roombooker-app-m03e.onrender.com/admin/)
**Username:** `krystian`  
**Password:** `admin`

</div>

---

## ✨ Najważniejsze (TL;DR)

- 📅 **Rezerwacje sal** z walidacją konfliktów terminów i czytelnymi statusami
- 🔔 **Powiadomienia**: potwierdzenie utworzenia rezerwacji + przypomnienie **1h przed startem**
- 📊 **Dashboard**: wykresy (Chart.js), heatmapa obłożenia i statystyki w czasie rzeczywistym
- 🎛️ **Panel administracyjny** (Jazzmin, dark theme) do szybkiego zarządzania danymi
- 🏢 **Sale i wyposażenie**: pojemność, wyposażenie, oznaczenie sal premium
- 📄 **Raporty**: eksport danych do PDF/Excel

---

## 🧭 Spis treści

- [✨ Najważniejsze (TL;DR)](#-najważniejsze-tldr)
- [⭐ Funkcje](#-funkcje)
- [🎯 Technologie](#-technologie)
- [🧪 Dane demo](#-dane-demo)
- [🚀 Szybki start (lokalnie)](#-szybki-start-lokalnie)
- [🗺️ Krotki przewodnik po aplikacji](#-krotki-przewodnik-po-aplikacji)
- [📊 Struktura projektu](#-struktura-projektu)
- [🧩 Architektura (w skrocie)](#-architektura-w-skrocie)
- [🧭 Roadmap (kolejne ulepszenia)](#-roadmap-kolejne-ulepszenia)
- [📄 Licencja](#-licencja)
- [👤 Autor](#-autor)

---

## ⭐ Funkcje

### 📅 Rezerwacje
- Tworzenie i edycja rezerwacji z datą, godziną, salą i liczbą uczestników
- Walidacja konfliktów (blokada nakładających się terminów)
- Statusy rezerwacji (np. otwarta/potwierdzona/anulowana/zakończona)
- Widoki „ostatnie” i „najbliższe” rezerwacje
- Filtrowanie po sali, statusie, dacie i użytkowniku

### 🔔 System powiadomień
- Powiadomienie od razu po utworzeniu nowej rezerwacji
- Przypomnienia 1h przed rozpoczęciem rezerwacji
- Lista powiadomień w aplikacji + oznaczanie jako przeczytane
- Integracja logiki zdarzeń poprzez Django Signals

### 🏢 Sale i wyposażenie
- Zarządzanie salami: nazwa, opis, pojemność, zdjęcie
- Oznaczenie sal premium (wyróżnienie w UI)
- Zarządzanie wyposażeniem i przypisywanie do sal

### 📊 Dashboard i analityka
- Statystyki w czasie rzeczywistym (np. liczba rezerwacji/sal/użytkowników)
- Wykresy i trendy wykorzystania sal
- Heatmapa obłożenia (dzień × godzina)
- Zestawienia top sal i top użytkowników

### 🎛️ Panel admina (Jazzmin)
- Profesjonalny wygląd (dark theme) i wygodny workflow
- Wyszukiwanie, filtrowanie i szybka edycja danych
- Dodawanie/edycja rezerwacji, sal, wyposażenia i powiadomień

### 📄 Raporty
- Eksport wybranych danych do PDF
- Eksport danych do Excel

---

## 🎯 Technologie

**Backend:** Django 6.0.2, Django ORM, Django Signals  
**Baza:** PostgreSQL (prod), SQLite (dev)  
**Frontend:** HTML/CSS, JavaScript (ES6+), Chart.js, Flatpickr  
**Admin:** Django Jazzmin  
**Runtime:** Gunicorn + WhiteNoise

---

## 🧪 Dane demo

Repozytorium zawiera plik `db_backup.json` z przykładowymi danymi (użytkownicy, sale, rezerwacje, powiadomienia). Dzięki temu możesz szybko uruchomić projekt lokalnie i od razu pokazać pełne możliwości.

**Domyślne konto do admina (na demo live):**
- Username: `krystian`
- Password: `admin`

---

## 🚀 Szybki start (lokalnie)

### Wymagania
- Python 3.13+
- Git

### Instalacja

```bash
git clone https://github.com/krystian2077/room_booking_django.git
cd room_booking_django

python -m venv .venv
.venv\Scripts\activate  # Windows

pip install -r requirements.txt

# Minimalny .env (DEV)
echo SECRET_KEY=dev-secret-key > .env
echo DEBUG=True >> .env
echo ALLOWED_HOSTS=localhost,127.0.0.1 >> .env

python manage.py migrate
python manage.py loaddata db_backup.json

python manage.py runserver
```

**Aplikacja:** http://127.0.0.1:8000  
**Admin:** http://127.0.0.1:8000/admin/

---

## 🗺️ Krotki przewodnik po aplikacji

Jeśli pokazujesz projekt mentorowi, to te miejsca najlepiej „sprzedają” aplikację:

1. **Dashboard** – statystyki, wykresy (Chart.js) i heatmapa obłożenia
2. **Najbliższe rezerwacje** – szybki podgląd nadchodzących wydarzeń
3. **Powiadomienia** – potwierdzenie utworzenia rezerwacji i przypomnienie 1h przed
4. **Panel admina** – szybkie zarządzanie salami, rezerwacjami i wyposażeniem

---

## 📊 Struktura projektu

```
room_booking_django/
├── bookings/              # Główna aplikacja
│   ├── models.py         # Room, Booking, Notification, Equipment
│   ├── views.py          # Widoki + dashboard
│   ├── signals.py        # Powiadomienia i automatyzacje
│   ├── admin.py          # Konfiguracja panelu admina
│   └── templates/        # Szablony HTML
├── room_booking_django/   # Konfiguracja projektu
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── static/               # CSS/JS
├── build.sh              # Skrypt build/deploy
├── db_backup.json        # Dane demonstracyjne
└── manage.py
```

---

## 🧩 Architektura (w skrocie)

- **Django Templates** jako warstwa UI + dynamiczne komponenty JS (powiadomienia, wykresy)
- **Logika biznesowa** w `bookings/views.py` + walidacje na poziomie modelu/formularzy
- **Automatyzacje** w `bookings/signals.py` (powiadomienia o zdarzeniach)
- **Dane**: Django ORM + PostgreSQL/SQLite

---

## 🧭 Roadmap (kolejne ulepszenia)

- ⏱️ Harmonogram zadań (Celery/Redis) dla precyzyjnych przypomnień i kolejek email
- 👥 Uczestnicy jako lista użytkowników + zaproszenia (RSVP)
- 🧾 Audyt zmian rezerwacji (kto i kiedy zmienił) + timeline w panelu admina
- 🔎 Pełnotekstowe wyszukiwanie (PostgreSQL) po tytułach/opisach

---

## 📄 Licencja

MIT License – Copyright (c) 2026

---

## 👤 Autor

**Krystian Potaczek**

- GitHub: [@krystian2077](https://github.com/krystian2077)
- Email: krystian.potaczek07@gmail.com
