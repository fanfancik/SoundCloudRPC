<p align="center">
  <img src="assets/icon.png" width="96" alt="SoundCloudRPC logo">
</p>

<h1 align="center">SoundCloudRPC</h1>

<p align="center">
  <img src="https://img.shields.io/badge/version-1.1.0-red">
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey">
  <img src="https://img.shields.io/badge/python-3.9%2B-blue">
</p>

<p align="center">
  Показывай друзьям в Discord, что сейчас играет в SoundCloud.<br>
  Show your friends on Discord what's currently playing on SoundCloud.
</p>

---

## 🇷🇺 Русский

Небольшая программа для Windows, Linux и macOS, которая ловит текущий трек прямо из открытой вкладки SoundCloud в браузере и отправляет его в статус Discord — с обложкой, названием, исполнителем и полосой прогресса.

### Возможности

- 🎵 Статус «Слушает SoundCloud» с живой обложкой и прогрессом трека
- ▶️⏸️ Индикатор play/pause
- 🔗 Кнопка «Открыть в SoundCloud» прямо в статусе
- 🧵 Работает в фоне через трей, без окна консоли
- 🚀 Опциональная автозагрузка вместе с системой
- 📦 Сама ставит недостающие зависимости при первом запуске

### Установка

1. Скачай `SoundCloudRPC.exe` из этого репозитория.
2. Установи Google Chrome, если ещё не установлен (рекомендуется — 
   с другими Chromium-браузерами не тестировалось).
3. Просто запусти `SoundCloudRPC.exe`. Всё остальное (Chrome с debug-портом, 
   зависимости и т.д.) программа настроит сама при первом запуске.
4. Открой soundcloud.com в открывшемся окне Chrome и включи любой трек.
5. Приложение свернётся в трей — оттуда доступны настройки и лог.

### Что нового в этой версии

- Мастер настроек в трее (пункт «Настройки») — теперь открывается меню 
  с диагностикой и починкой, разбором проблем с обложками и выбором 
  цвета иконки play/pause.
- Исправлена пауза: раньше при паузе трека время в статусе могло 
  показывать случайные числа — теперь показывается точная позиция, 
  на которой остановлен трек.
- Вместо стандартной ноты 🎵 в статусе теперь можно выбрать свою иконку 
  play/pause (в том числе классические красные).
- Повышена надёжность определения обложки трека.

### ⚠️ О текущем состоянии проекта

Проект в активной разработке для личного использования, выложен в первую очередь для себя и знакомых. SoundCloud время от времени меняет вёрстку своего плеера, из-за чего часть функций (например, обложка) может временно ломаться — раньше такое уже случалось и почти всегда чинится. Если что-то не работает — открой Issue, буду рад разобраться.

---

## 🇬🇧 English

A small Windows / Linux / macOS app that grabs whatever's currently playing in an open SoundCloud browser tab and turns it into a Discord Rich Presence status — with cover art, title, artist and a live progress bar.

### Features

- 🎵 "Listening to SoundCloud" status with live artwork and progress
- ▶️⏸️ Play/pause indicator
- 🔗 "Open in SoundCloud" button right in the status card
- 🧵 Runs quietly from the system tray, no console window
- 🚀 Optional launch on startup
- 📦 Installs missing dependencies on first run automatically

### Installation

1. Install [Python 3.9+](https://www.python.org/downloads/) and [Google Chrome](https://www.google.com/chrome/).
2. Download this repo.
3. Run `run.bat` (Windows) — everything else is handled automatically.

For Linux/macOS: `./start_chrome_debug.sh`, then `python3 main.py`.

### ⚠️ Current state

This is an actively developed personal project, shared mainly for myself and friends. SoundCloud occasionally tweaks its player markup, which can temporarily break things like artwork detection — it's happened before and usually gets fixed quickly. If something's broken, feel free to open an Issue.

---

## 🖱 Tray menu / Меню в трее

- **Show App** — открыть лог / open log file
- **Настройки / Settings** — открыть config.json
- **Restart** — перезапустить / restart
- **Автозагрузка / Autostart** — вкл/выкл
- **GitHub** — открыть репозиторий
- **Quit** — закрыть

## 🔒 Приватность / Privacy

Скрипт не собирает и никуда не отправляет никакие данные — работает только с твоим локальным Chrome и Discord.
The script doesn't collect or send any data anywhere — it only talks to your local Chrome and Discord.

## 📄 License

All Rights Reserved — see [LICENSE](LICENSE).
