"""
main.py

SoundCloud -> Discord Rich Presence, с иконкой в трее.

Запускается через pythonw (без консоли вообще) — поэтому логи пишутся
в файл soundcloud_rpc.log, а не только на экран. Пункт "Show App (лог)"
в трее открывает этот файл.
Если нужно увидеть работу вживую — запусти debug_console.bat
(там используется обычный python.exe с видимым окном).
"""

import importlib
import os
import subprocess
import sys
import time

APP_TAG = "[SoundCloudRPC]"
APP_VERSION = "1.2.0"

if getattr(sys, "frozen", False):
    # Запущено как собранный .exe (PyInstaller) — берём папку самого exe,
    # а не временную папку распаковки, чтобы config.json и лог лежали рядом.
    SCRIPT_DIR = os.path.dirname(sys.executable)
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

LOG_PATH = os.path.join(SCRIPT_DIR, "soundcloud_rpc.log")


def _write_log_file(msg: str):
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    except Exception:
        pass


def _plain_log(msg: str):
    try:
        print(f"{APP_TAG} -> {msg}")
    except Exception:
        pass
    _write_log_file(msg)


def ensure_dependencies():
    """Проверяет, что все нужные библиотеки установлены, и ставит недостающие."""
    checks = {
        "pypresence": "pypresence>=4.7.0",
        "websocket": "websocket-client>=1.7.0",
        "colorama": "colorama>=0.4.6",
        "pystray": "pystray>=0.19.5",
        "PIL": "Pillow>=10.0.0",
    }
    to_install = []
    for module_name, pip_spec in checks.items():
        try:
            importlib.import_module(module_name)
        except ImportError:
            to_install.append(pip_spec)

    if not to_install:
        return

    _plain_log(f"Устанавливаю недостающие библиотеки: {', '.join(to_install)}")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", *to_install])
    except subprocess.CalledProcessError as e:
        _plain_log(f"Не удалось установить библиотеки автоматически: {e}")
        _plain_log("Попробуй вручную: pip install -r requirements.txt")
        sys.exit(1)
    _plain_log("Библиотеки установлены.")


ensure_dependencies()

import json
import platform
import re
import threading
import webbrowser

from pypresence import Presence
from pypresence import exceptions as pypresence_exceptions
from pypresence.types import ActivityType

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    import colorama
    from colorama import Fore, Style

    colorama.init()
    COLOR_MAP = {
        "red": Fore.RED, "green": Fore.GREEN, "yellow": Fore.YELLOW,
        "blue": Fore.BLUE, "magenta": Fore.MAGENTA, "cyan": Fore.CYAN,
        "white": Fore.WHITE,
    }
    GREEN = Fore.GREEN
    YELLOW = Fore.YELLOW
    RESET = Style.RESET_ALL
    TRAY_COLORS_AVAILABLE = True
except ImportError:
    COLOR_MAP = {}
    GREEN = YELLOW = RESET = ""
    TRAY_COLORS_AVAILABLE = False

from soundcloud import SoundCloudMonitor, default_chrome_binary_path

CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")
SETTINGS_MENU_BAT = os.path.join(SCRIPT_DIR, "settings_menu.bat")

DEFAULT_CONFIG = {
    "discord_client_id": "1520997345171476621",
    "chrome_binary_path": "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "debug_profile_path": "./chrome_debug_profile",
    "debug_port": 9222,
    "soundcloud_url": "https://soundcloud.com",
    "update_interval": 5,
    "tray_enabled": True,
    "small_icons_enabled": True,
    "play_icon_asset": "https://raw.githubusercontent.com/fanfancik/SoundCloudRPC/main/assets/play_icon.png",
    "pause_icon_asset": "https://raw.githubusercontent.com/fanfancik/SoundCloudRPC/main/assets/pause_icon.png",
    "badge_repo_base": "https://raw.githubusercontent.com/fanfancik/SoundCloudRPC/main/assets/badges",
    "accent_color": "classic",
    "github_url": "",
    "console_color": "red",
}


def load_config() -> dict:
    """Если config.json нет рядом с exe (например, скачали только exe с
    GitHub, без остальных файлов репозитория) — создаём его сами со
    значениями по умолчанию, чтобы программа не падала с
    FileNotFoundError, а сразу запускалась."""
    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
        _plain_log(f"config.json не найден — создал новый со значениями по умолчанию: {CONFIG_PATH}")
        return dict(DEFAULT_CONFIG)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    # если конфиг старый и в нём чего-то не хватает — дополняем дефолтами,
    # не трогая то, что пользователь уже сам поменял
    changed = False
    for key, value in DEFAULT_CONFIG.items():
        if key not in cfg:
            cfg[key] = value
            changed = True
    if changed:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    return cfg


try:
    _early_config = load_config()
except Exception:
    _early_config = {}

_tag_color = COLOR_MAP.get(_early_config.get("console_color", "red"), COLOR_MAP.get("red", ""))
APP_TAG_COLORED = f"{_tag_color}[SoundCloudRPC]{RESET}"

IS_WINDOWS = platform.system() == "Windows"
FORCE_CONSOLE = "--console" in sys.argv

STATUS_MESSAGES = {
    "no_target": "Вкладка SoundCloud не найдена. Открой soundcloud.com в "
                 "Chrome, запущенном через start_chrome_debug.",
    "ws_failed": "Не удалось подключиться к вкладке Chrome.",
    "eval_failed": "Не удалось прочитать данные со страницы SoundCloud.",
    "widget_not_found": "Плеер SoundCloud ещё не появился на странице — нажми Play хотя бы раз.",
    "title_missing": "Плеер найден, но не удалось определить название трека.",
    "exception": "Непредвиденная ошибка при чтении страницы SoundCloud.",
}


def log(msg: str):
    try:
        print(f"{APP_TAG_COLORED} -> {msg}")
    except Exception:
        pass
    clean = re.sub(r"\x1b\[[0-9;]*m", "", msg)
    _write_log_file(clean)


def truncate(text, limit: int = 128) -> str:
    if not text:
        return ""
    text = text.strip()
    if len(text) > limit:
        text = text[: limit - 1] + "…"
    return text


def format_time(seconds) -> str:
    seconds = int(seconds or 0)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


# ---------- автозагрузка (Windows) ----------

def _startup_bat_path():
    startup_dir = os.path.join(
        os.environ.get("APPDATA", ""), "Microsoft", "Windows",
        "Start Menu", "Programs", "Startup",
    )
    return os.path.join(startup_dir, "SoundCloudRPC.bat")


def is_autostart_enabled() -> bool:
    return IS_WINDOWS and os.path.exists(_startup_bat_path())


def set_autostart(enabled: bool):
    if not IS_WINDOWS:
        log(f"{YELLOW}Автозагрузка пока поддерживается только на Windows.{RESET}")
        return
    path = _startup_bat_path()
    if enabled:
        run_bat = os.path.join(SCRIPT_DIR, "run.bat")
        with open(path, "w", encoding="utf-8") as f:
            f.write(f'@echo off\r\ncd /d "{SCRIPT_DIR}"\r\nstart "" "{run_bat}"\r\n')
        log(f"{GREEN}Добавлено в автозагрузку.{RESET}")
    else:
        if os.path.exists(path):
            os.remove(path)
        log(f"{GREEN}Убрано из автозагрузки.{RESET}")


# ---------- Discord ----------

def connect_to_discord(client_id: str) -> Presence:
    rpc = Presence(client_id)
    attempt = 0
    while True:
        try:
            rpc.connect()
            return rpc
        except pypresence_exceptions.DiscordNotFound:
            attempt += 1
            if attempt == 1:
                log(f"{YELLOW}Discord не запущен. Открой Discord — жду...{RESET}")
            time.sleep(3)
        except pypresence_exceptions.PyPresenceException as e:
            log(f"{YELLOW}Не удалось подключиться к Discord: {e}. Повтор через 3с...{RESET}")
            time.sleep(3)


def update_presence(rpc: Presence, payload: dict):
    try:
        rpc.update(**payload)
    except TypeError as e:
        if "activity_type" in payload and "activity_type" in str(e):
            fallback = dict(payload)
            fallback.pop("activity_type", None)
            rpc.update(**fallback)
            log(f"{YELLOW}Старая версия pypresence — 'Слушает' недоступен. "
                f"Обнови: pip install --upgrade pypresence{RESET}")
        else:
            raise


# ---------- фоновый поток: вся работа с Discord/Chrome ----------

def worker_main(config: dict, stop_event: threading.Event, status_holder: dict):
    client_id = config.get("discord_client_id")
    update_interval = config.get("update_interval", 5)
    small_icons = config.get("small_icons_enabled", False)
    play_icon = config.get("play_icon_asset")
    pause_icon = config.get("pause_icon_asset")
    configured_chrome = config.get("chrome_binary_path")
    chrome_binary_path = (
        configured_chrome if configured_chrome and os.path.exists(configured_chrome)
        else default_chrome_binary_path()
    )

    log("Подключаюсь к Discord...")
    rpc = connect_to_discord(client_id)
    log(f"{GREEN}Подключено к Discord.{RESET}")

    monitor = SoundCloudMonitor(
        chrome_binary_path=chrome_binary_path,
        debug_profile_path=config.get("debug_profile_path", "./chrome_debug_profile"),
        debug_port=config.get("debug_port", 9222),
        soundcloud_url=config.get("soundcloud_url", "https://soundcloud.com"),
    )
    log("Ищу Chrome с открытым debug-портом...")
    monitor.start()
    log(f"{GREEN}Готово. Запускай трек в SoundCloud в браузере.{RESET}")
    status_holder["ready"] = True

    last_rpc_state = None
    last_track_key = None
    last_status = None
    consecutive_failures = 0

    try:
        while not stop_event.is_set():
            data = monitor.get_now_playing()
            status = monitor.last_status
            if status != last_status:
                if status != "ok" and status in STATUS_MESSAGES:
                    extra = f" ({monitor.last_error})" if status == "ws_failed" and monitor.last_error else ""
                    log(f"{YELLOW}{STATUS_MESSAGES[status]}{extra}{RESET}")
                last_status = status

            if not data:
                if last_rpc_state is not None:
                    rpc.clear()
                    last_rpc_state = None
                    last_track_key = None
                _sleep_interruptible(update_interval, stop_event)
                continue

            title = truncate(data["title"])
            artist = truncate(data["artist"])
            position, duration, is_playing = data["position"], data["duration"], data["is_playing"]

            track_key = (title, artist)
            if track_key != last_track_key:
                log(f"{GREEN}Выбран трек: {title} — {artist}{RESET}")
                last_track_key = track_key
                if not data["artwork_url"] and monitor.artwork_debug_html:
                    log(f"{YELLOW}Обложка не найдена. Если так происходит для "
                        f"любого трека — пришли мне этот кусок HTML для починки:{RESET}")
                    log(monitor.artwork_debug_html)

            now = time.time()
            start_ts = int(now - position)
            end_ts = int(start_ts + duration) if duration else None

            payload = {
                "activity_type": ActivityType.LISTENING,
                "details": title,
                "state": artist,
            }

            # Если у трека нет своей обложки — просто не передаём large_image,
            # Discord сам подставит иконку приложения (это нормально, а не
            # баг — у части треков автор не грузил обложку вообще).
            if data["artwork_url"]:
                payload["large_image"] = data["artwork_url"]

            # small_image/small_text — маленький значок play/pause поверх
            # обложки. ВАЖНО: сюда нужна либо реальная https-ссылка на
            # картинку, либо имя ассета, заранее загруженного в Developer
            # Portal твоего приложения (discord.com/developers/applications
            # -> Rich Presence -> Art Assets). Имя-заглушка вроде "play_icon",
            # для которой ничего не загружено, Discord у ДРУГИХ людей просто
            # не сможет разрешить — из-за этого у них могла пропадать не
            # только иконка, но и остальная "живая" часть статуса. Ссылки
            # на assets/badges (см. settings_menu.py, пункт 3) — это уже
            # настоящие https-ссылки, так что должны быть видны всем.
            if small_icons and play_icon and pause_icon:
                payload["small_image"] = play_icon if is_playing else pause_icon
                payload["small_text"] = "Играет" if is_playing else "Пауза"

            # ВАЖНО про паузу: раньше, когда трек стоял на паузе, мы просто
            # не добавляли start/end в payload — но Discord у некоторых
            # зрителей после этого продолжал считать время от СТАРОГО start
            # (из последнего "живого" обновления), из-за чего вместо позиции
            # паузы вылезали дикие числа вроде "5:03:16". Явно шлём
            # start=None/end=None, чтобы гарантированно стереть прошлые
            # метки, а вместо прогресс-бара показываем зафиксированную
            # позицию текстом — это единственный способ показать "где именно
            # остановлено", потому что сам прогресс-бар Discord всегда либо
            # тикает от start к end, либо не показывается вовсе.
            payload["start"] = None
            payload["end"] = None
            if is_playing and duration:
                payload["start"] = start_ts
                payload["end"] = end_ts
            elif not is_playing:
                pos_text = format_time(position)
                dur_text = f"/{format_time(duration)}" if duration else ""
                payload["state"] = f"{artist} · ⏸ {pos_text}{dur_text}"

            if data.get("track_url"):
                payload["buttons"] = [{"label": "Открыть в SoundCloud", "url": data["track_url"]}]

            state_key = (title, artist, is_playing, duration, position if not is_playing else None)
            if state_key != last_rpc_state:
                if is_playing and duration:
                    log(f"Отправляю в Discord: start={payload.get('start')} "
                        f"end={payload.get('end')} duration={duration}s "
                        f"small_image={payload.get('small_image')}")
                else:
                    log(f"{YELLOW}Не отправляю прогресс-бар — is_playing={is_playing}, "
                        f"duration={duration}. Если трек реально играет, а duration=0 — "
                        f"значит не удалось прочитать длительность со страницы SoundCloud "
                        f"(см. пункт 2 в settings_menu.bat).{RESET}")
                try:
                    update_presence(rpc, payload)
                    last_rpc_state = state_key
                    consecutive_failures = 0
                except Exception as e:
                    consecutive_failures += 1
                    log(f"{YELLOW}Не удалось обновить Discord RPC: {e}{RESET}")
                    if consecutive_failures >= 3:
                        log(f"{YELLOW}Похоже, связь с Discord оборвалась. Переподключаюсь...{RESET}")
                        try:
                            rpc.close()
                        except Exception:
                            pass
                        rpc = connect_to_discord(client_id)
                        log(f"{GREEN}Переподключено к Discord.{RESET}")
                        consecutive_failures = 0

            _sleep_interruptible(update_interval, stop_event)
    finally:
        try:
            rpc.clear()
            rpc.close()
        except Exception:
            pass
        monitor.stop()


def _sleep_interruptible(seconds: float, stop_event: threading.Event):
    slept = 0.0
    while slept < seconds and not stop_event.is_set():
        time.sleep(0.5)
        slept += 0.5


# ---------- трей ----------

def tray_libs_available() -> bool:
    try:
        import pystray  # noqa: F401
        from PIL import Image  # noqa: F401
        return True
    except ImportError:
        return False


def open_log_file():
    try:
        if not os.path.exists(LOG_PATH):
            open(LOG_PATH, "a", encoding="utf-8").close()
        if IS_WINDOWS:
            os.startfile(LOG_PATH)
        else:
            webbrowser.open(f"file://{LOG_PATH}")
    except Exception as e:
        log(f"{YELLOW}Не удалось открыть лог: {e}{RESET}")


def open_settings():
    """Открывает мастер настроек (settings_menu.bat) — консольное меню
    с диагностикой/починкой, разбором проблем с обложкой и выбором цвета
    play/pause. Если бат-файла в папке нет (старая версия проекта без
    обновления) — просто открывает config.json, как раньше."""
    try:
        if IS_WINDOWS and os.path.exists(SETTINGS_MENU_BAT):
            subprocess.Popen(["cmd", "/c", "start", "", "settings_menu.bat"], cwd=SCRIPT_DIR)
            log("Открыл мастер настроек.")
            return
        if IS_WINDOWS:
            os.startfile(CONFIG_PATH)
        else:
            webbrowser.open(f"file://{CONFIG_PATH}")
        log("Настройки открыты. После изменений сделай Restart в трее.")
    except Exception as e:
        log(f"{YELLOW}Не удалось открыть настройки: {e}{RESET}")


def run_tray(config: dict, stop_event: threading.Event, worker: threading.Thread) -> bool:
    """Возвращает True, если нужно перезапустить процесс."""
    import pystray
    from PIL import Image

    icon_path = os.path.join(SCRIPT_DIR, "assets", "icon.png")
    image = Image.open(icon_path) if os.path.exists(icon_path) else Image.new("RGB", (64, 64), (220, 38, 38))

    restart_requested = {"flag": False}

    def on_show(icon, item):
        open_log_file()

    def on_restart(icon, item):
        restart_requested["flag"] = True
        stop_event.set()
        icon.stop()

    def on_toggle_autostart(icon, item):
        set_autostart(not is_autostart_enabled())

    def on_github(icon, item):
        url = config.get("github_url")
        if url:
            webbrowser.open(url)
        else:
            log(f"{YELLOW}github_url пока не указан в config.json.{RESET}")

    def on_quit(icon, item):
        stop_event.set()
        icon.stop()

    menu = pystray.Menu(
        pystray.MenuItem("Show App (лог)", on_show),
        pystray.MenuItem("Настройки", lambda icon, item: open_settings()),
        pystray.MenuItem("Restart", on_restart),
        pystray.MenuItem("Автозагрузка", on_toggle_autostart, checked=lambda item: is_autostart_enabled()),
        pystray.MenuItem("GitHub", on_github),
        pystray.MenuItem("Quit", on_quit),
    )

    icon = pystray.Icon("SoundCloudRPC", image, "SoundCloudRPC", menu)
    try:
        icon.run()  # блокирует до icon.stop()
    except Exception as e:
        log(f"{YELLOW}Ошибка иконки в трее: {e}{RESET}")
        try:
            while not stop_event.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            pass

    stop_event.set()
    worker.join(timeout=5)
    return restart_requested["flag"]


def run_console_mode(worker: threading.Thread, stop_event: threading.Event):
    try:
        while worker.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        log("Завершение работы...")
    stop_event.set()
    worker.join(timeout=5)


def main():
    log(f"Запуск... (v{APP_VERSION})")
    config = load_config()

    client_id = config.get("discord_client_id")
    if not client_id or client_id == "YOUR_DISCORD_CLIENT_ID":
        log(f"{YELLOW}Укажи discord_client_id в config.json{RESET}")
        sys.exit(1)

    stop_event = threading.Event()
    status_holder = {"ready": False}
    worker = threading.Thread(target=worker_main, args=(config, stop_event, status_holder), daemon=True)
    worker.start()

    while not status_holder["ready"] and worker.is_alive():
        time.sleep(0.2)

    if not worker.is_alive():
        log(f"{YELLOW}Не удалось запуститься. Смотри лог: {LOG_PATH}{RESET}")
        return

    want_tray = config.get("tray_enabled", True) and IS_WINDOWS and not FORCE_CONSOLE
    if want_tray and not tray_libs_available():
        log(f"{YELLOW}Библиотеки трея недоступны — работаю в обычной консоли.{RESET}")
        want_tray = False

    if want_tray:
        want_restart = run_tray(config, stop_event, worker)
        if want_restart:
            python = sys.executable
            os.execv(python, [python] + sys.argv)
        return

    log("Работаю в консоли. Ctrl+C для выхода.")
    run_console_mode(worker, stop_event)


if __name__ == "__main__":
    main()