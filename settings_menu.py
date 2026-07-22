"""
settings_menu.py

Консольное меню настроек SoundCloudRPC.
Запускается через settings_menu.bat (двойной клик), либо из пункта
"Настройки" в трее.

Пункты:
  1) Диагностика и починка — проверяет Python/библиотеки/Chrome/конфиг,
     ставит недостающие зависимости, показывает хвост лога.
  2) Не работают обложки — смотрит лог на предмет "Обложка не найдена"
     и сохраняет кусок HTML для починки селекторов.
  3) Цвет play/pause в статусе Discord — выбор из готового набора
     цветных иконок (assets/badges), прописывает пути в config.json.
"""

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

# На Windows консоль по умолчанию открывается не в UTF-8, из-за чего
# кириллица превращается в крякозябры. chcp 65001 в settings_menu.bat
# уже переключает кодовую страницу, а это дополнительно переключает сам
# Python на UTF-8, чтобы print() не путался с кодировкой консоли.
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdin.reconfigure(encoding="utf-8")
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")
LOG_PATH = os.path.join(SCRIPT_DIR, "soundcloud_rpc.log")

REPO_ROOT = "https://raw.githubusercontent.com/fanfancik/SoundCloudRPC/main"
DEFAULT_BADGE_REPO = f"{REPO_ROOT}/assets/badges"

# "classic" — твои старые красные иконки, которые уже лежат в assets/
# (play_icon.png / pause_icon.png), просто отданные по прямой https-ссылке
# вместо имени ассета (имя ассета Discord не может разрешить у других людей,
# если оно не загружено в Developer Portal — из-за этого играющий статус
# у зрителей мог выглядеть "битым").
BADGE_COLORS = {
    "1": ("classic", "твои старые красные — play_icon.png / pause_icon.png"),
    "2": ("orange", "#FF5500 — фирменный цвет SoundCloud"),
    "3": ("red", "#E01E37"),
    "4": ("blue", "#3B82F6"),
    "5": ("green", "#22C55E"),
    "6": ("purple", "#A855F7"),
    "7": ("pink", "#EC4899"),
    "8": ("white", "#FFFFFF"),
}


def _icon_urls_for(color_name: str, repo_base: str):
    if color_name == "classic":
        return f"{REPO_ROOT}/assets/play_icon.png", f"{REPO_ROOT}/assets/pause_icon.png"
    return f"{repo_base}/cloud_play_{color_name}.png", f"{repo_base}/cloud_pause_{color_name}.png"


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def pause():
    input("\nНажми Enter, чтобы вернуться в меню...")


def load_config() -> dict:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(cfg: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------
# 1) Диагностика и починка
# ---------------------------------------------------------------------

def check_python():
    ok = sys.version_info >= (3, 9)
    print(f"Python: {sys.version.split()[0]}  {'[OK]' if ok else '[!! нужен 3.9+]'}")


def check_module(name: str) -> bool:
    try:
        __import__(name)
        print(f"  [OK] {name}")
        return True
    except ImportError:
        print(f"  [--] {name} не установлен")
        return False


def repair_dependencies():
    print("\nПроверяю библиотеки...")
    checks = {
        "pypresence": "pypresence>=4.7.0",
        "websocket": "websocket-client>=1.7.0",
        "colorama": "colorama>=0.4.6",
        "pystray": "pystray>=0.19.5",
        "PIL": "Pillow>=10.0.0",
    }
    missing = [spec for mod, spec in checks.items() if not check_module(mod)]
    if missing:
        print(f"\nСтавлю недостающее: {', '.join(missing)}")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", *missing])
            print("Готово.")
        except subprocess.CalledProcessError as e:
            print(f"Не получилось поставить автоматически: {e}")
            print("Попробуй вручную: pip install -r requirements.txt --upgrade")
    else:
        print("Все библиотеки на месте и актуальны.")


def check_config(cfg: dict) -> bool:
    cid = cfg.get("discord_client_id")
    if not cid or cid == "YOUR_DISCORD_CLIENT_ID":
        print("  [--] discord_client_id не задан в config.json")
        return False
    print(f"  [OK] discord_client_id = {cid}")
    return True


def auto_fix_icon_assets(cfg: dict) -> bool:
    """play_icon_asset/pause_icon_asset раньше могли быть именами ассетов
    ("play_icon") вместо ссылок — Discord не может показать такое зрителям,
    если ассет не загружен в Developer Portal. Если видим не-ссылку —
    молча чиним на классические красные иконки из assets/ (они у тебя уже
    есть) и сохраняем config.json."""
    play_a = cfg.get("play_icon_asset") or ""
    pause_a = cfg.get("pause_icon_asset") or ""
    looks_broken = (play_a and not play_a.startswith("http")) or (pause_a and not pause_a.startswith("http"))
    if not looks_broken:
        return False
    print("  [!!] play_icon_asset/pause_icon_asset — это не ссылка, а имя ассета.")
    print("       Discord не может показать такое у других людей. Чиню на")
    print("       твои же красные иконки из assets/, только теперь по ссылке...")
    play_url, pause_url = _icon_urls_for("classic", DEFAULT_BADGE_REPO)
    cfg["play_icon_asset"] = play_url
    cfg["pause_icon_asset"] = pause_url
    cfg.setdefault("badge_repo_base", DEFAULT_BADGE_REPO)
    cfg["small_icons_enabled"] = True
    save_config(cfg)
    print(f"  [OK] Поправил: play={play_url}")
    print(f"                 pause={pause_url}")
    print("       Сделай Restart в трее после этого.")
    return True


def check_chrome_debug_port(cfg: dict) -> bool:
    port = cfg.get("debug_port", 9222)
    url = f"http://127.0.0.1:{port}/json/version"
    try:
        with urllib.request.urlopen(url, timeout=2) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        print(f"  [OK] Chrome debug-порт {port} отвечает ({data.get('Browser', '')})")
        return True
    except Exception as e:
        print(f"  [--] Chrome debug-порт {port} не отвечает ({e})")
        print("       Запусти start_chrome_debug.bat и открой в нём soundcloud.com.")
        return False


def check_soundcloud_tab(cfg: dict) -> bool:
    port = cfg.get("debug_port", 9222)
    url = f"http://127.0.0.1:{port}/json/list"
    try:
        with urllib.request.urlopen(url, timeout=2) as resp:
            targets = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"  [--] Не удалось получить список вкладок Chrome ({e})")
        return False
    for t in targets:
        if t.get("type") == "page" and "soundcloud.com" in t.get("url", ""):
            print(f"  [OK] Нашёл вкладку SoundCloud: {t.get('url')}")
            return True
    print("  [--] Вкладка soundcloud.com среди открытых вкладок не найдена.")
    return False


def tail_log(n: int = 15):
    if not os.path.exists(LOG_PATH):
        print("  Лог пока пуст — программа ни разу толком не запускалась.")
        return
    with open(LOG_PATH, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    print(f"\nПоследние {min(n, len(lines))} строк лога ({LOG_PATH}):")
    for line in lines[-n:]:
        print("  " + line.rstrip())


def menu_diagnose():
    clear()
    print("=== 1. Диагностика и починка ===\n")
    check_python()
    repair_dependencies()
    print()
    cfg = load_config()
    check_config(cfg)
    auto_fix_icon_assets(cfg)
    check_chrome_debug_port(cfg)
    check_soundcloud_tab(cfg)
    tail_log()
    print("\nЕсли Chrome/вкладка не найдены — запусти start_chrome_debug.bat,")
    print("открой в нём soundcloud.com, нажми Play хотя бы раз, и заново запусти run.bat.")
    pause()


# ---------------------------------------------------------------------
# 2) Не работают обложки
# ---------------------------------------------------------------------

def menu_artwork():
    clear()
    print("=== 2. Не работают обложки ===\n")
    cfg = load_config()
    if not check_chrome_debug_port(cfg):
        pause()
        return
    if not check_soundcloud_tab(cfg):
        print("\nОткрой soundcloud.com в Chrome (через start_chrome_debug.bat) и включи трек.")
        pause()
        return
    if not os.path.exists(LOG_PATH):
        print("Лог пуст. Сначала запусти run.bat, включи трек, подожди 10-15 секунд,")
        print("и вернись в этот пункт меню.")
        pause()
        return
    with open(LOG_PATH, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    marker = "Обложка не найдена"
    if marker in content:
        idx = content.rfind(marker)
        snippet = content[idx: idx + 700]
        print("Нашёл запись о проблеме с обложкой. Кусок HTML, который поймала программа:\n")
        print(snippet)
        dump_path = os.path.join(SCRIPT_DIR, "artwork_debug.txt")
        with open(dump_path, "w", encoding="utf-8") as f:
            f.write(snippet)
        print(f"\nСохранил это в: {dump_path}")
        print("Пришли содержимое этого файла в Issue на GitHub (или мне) — по нему")
        print("можно поправить селекторы под новую вёрстку SoundCloud.")
    else:
        print("В логе нет свежих записей о проблемах с обложкой — сейчас, похоже, всё ок.")
        print("Если у друзей в Discord обложка всё равно не показывается, а у тебя видна —")
        print("это может быть не про SoundCloud, а про сам Discord-профиль приложения:")
        print("зайди на discord.com/developers/applications и убедись, что приложение")
        print("не в статусе Unverified/ограничено (это влияет на то, что видят другие).")
    pause()


# ---------------------------------------------------------------------
# 3) Цвет play/pause
# ---------------------------------------------------------------------

def menu_color():
    clear()
    print("=== 3. Цвет иконки play/pause в статусе Discord ===\n")
    print("Discord показывает такую иконку (small_image) только по прямой https-ссылке —")
    print("файл с твоего диска отправить нельзя. Пункт 1 ниже — это твои же старые")
    print("красные иконки (assets/play_icon.png), просто отданные ссылкой. Остальные —")
    print("новый набор в assets/badges (тоже нужно закоммитить в GitHub, см. ниже).\n")
    for key, (name, desc) in BADGE_COLORS.items():
        print(f"  {key}) {name}  ({desc})")
    choice = input("\nВыбери номер (Enter — отмена): ").strip()
    if choice not in BADGE_COLORS:
        print("Отмена.")
        pause()
        return
    color_name, _ = BADGE_COLORS[choice]

    cfg = load_config()
    repo_base = (cfg.get("badge_repo_base") or "").rstrip("/") or DEFAULT_BADGE_REPO
    cfg["badge_repo_base"] = repo_base
    cfg["accent_color"] = color_name
    cfg["small_icons_enabled"] = True
    play_url, pause_url = _icon_urls_for(color_name, repo_base)
    cfg["play_icon_asset"] = play_url
    cfg["pause_icon_asset"] = pause_url
    save_config(cfg)

    print(f"\nГотово! Значок '{color_name}' сохранён в config.json:")
    print(f"  play  -> {play_url}")
    print(f"  pause -> {pause_url}")
    if color_name != "classic":
        print("\nВАЖНО: если ты ещё не закоммитил папку assets/badges в GitHub — сделай это,")
        print("иначе эти иконки будут видны только тебе, а у друзей ничего не покажется.")
    print("После этого сделай Restart в трее (или перезапусти run.bat).")
    pause()


# ---------------------------------------------------------------------

def open_path(path: str):
    try:
        if os.name == "nt":
            os.startfile(path)  # noqa: S606
        else:
            subprocess.call(["xdg-open", path])
    except Exception as e:
        print(f"Не получилось открыть: {e}")


def main_menu():
    while True:
        clear()
        print("========================================")
        print("        SoundCloudRPC — Настройки")
        print("========================================\n")
        print("  1) Что-то не работает (диагностика и починка)")
        print("  2) Не работают обложки")
        print("  3) Настроить цвет play/pause")
        print("  4) Открыть config.json вручную")
        print("  5) Посмотреть лог целиком (последние 40 строк)")
        print("  0) Выход")
        choice = input("\nВыбери пункт: ").strip()
        if choice == "1":
            menu_diagnose()
        elif choice == "2":
            menu_artwork()
        elif choice == "3":
            menu_color()
        elif choice == "4":
            open_path(CONFIG_PATH)
            pause()
        elif choice == "5":
            clear()
            tail_log(40)
            pause()
        elif choice == "0":
            break
        else:
            print("Не понял, попробуй ещё раз.")
            time.sleep(1)


if __name__ == "__main__":
    main_menu()
