"""
soundcloud.py

Читает текущий трек SoundCloud напрямую через Chrome DevTools Protocol
(websocket), БЕЗ Selenium и БЕЗ chromedriver.
"""

import json
import os
import platform
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from typing import Optional, Dict

try:
    import websocket  # пакет "websocket-client"
except ImportError:
    websocket = None

# ВАЖНО: селектор слайдера жёстко привязан к обёртке таймлайна.
# Раньше был общий "[role='slider']" как запасной вариант — он иногда
# попадал на слайдер громкости (у него тоже role="slider"), из-за чего
# длительность трека определялась неправильно (полоса "застывала").
JS_EXTRACT = r"""
(function() {
  function q(selectors) {
    for (const sel of selectors) {
      const el = document.querySelector(sel);
      if (el) return el;
    }
    return null;
  }

  const widget = document.querySelector('.playbackSoundBadge')
    || document.querySelector('[class*="playbackSoundBadge"]');

  const titleEl = q([
    '.playbackSoundBadge__titleLink',
    '.playbackSoundBadge__title span',
    '.playbackSoundBadge__title'
  ]);
  const artistEl = q([
    '.playbackSoundBadge__lightLink',
    '.playbackSoundBadge__usernameLink',
    '.playbackSoundBadge__soundBy a'
  ]);

  const artEl = document.querySelector('.playbackSoundBadge__avatar [style*="background-image"]') || q([
    '.playbackSoundBadge__avatar span.sc-artwork',
    '.playbackSoundBadge__avatar span.image__lightOutline',
    '.playbackSoundBadge__avatar .sc-artwork',
    '.playbackSoundBadge__avatar span'
  ]);

  let finalArtEl = artEl;
  if ((!finalArtEl || !finalArtEl.getAttribute('style')) && titleEl) {
    // Запасной вариант: SoundCloud обычно ставит на обложку aria-label,
    // совпадающий с названием трека — ищем по нему, это надёжнее
    // конкретных названий CSS-классов, которые могут поменяться.
    const titleText = titleEl.innerText.trim();
    const labeled = document.querySelectorAll('[aria-label][style*="background-image"]');
    for (const el of labeled) {
      const label = el.getAttribute('aria-label') || '';
      if (titleText && label.includes(titleText)) {
        finalArtEl = el;
        break;
      }
    }
  }

  // Запасной, более широкий поиск обложки: ищем ЛЮБОЙ <img> внутри
  // всего виджета плеера, либо любой элемент с background-image.
  // Это на случай, если SoundCloud поменял вёрстку конкретно аватарки.
  let artwork_img_src = null;
  if (widget) {
    const img = widget.querySelector('img');
    if (img) {
      artwork_img_src = img.currentSrc || img.getAttribute('src') || img.getAttribute('data-src');
    }
  }

  // Ещё один запасной вариант, который раньше отсутствовал: SoundCloud
  // иногда задаёт фон обложки не через inline style="background-image:...",
  // а через CSS-класс во внешней таблице стилей — в этом случае
  // getAttribute('style') ничего не находит, хотя картинка реально видна
  // на странице. getComputedStyle видит и такой вариант тоже.
  let artwork_style = finalArtEl ? finalArtEl.getAttribute('style') : null;
  if (!artwork_style && !artwork_img_src && widget) {
    const avatarWrap = widget.querySelector('.playbackSoundBadge__avatar') || widget;
    const candidates = avatarWrap.querySelectorAll('*');
    for (const el of candidates) {
      const bg = window.getComputedStyle(el).backgroundImage;
      if (bg && bg.includes('url(')) {
        artwork_style = 'background-image: ' + bg;
        break;
      }
    }
  }

  let artwork_debug_html = null;
  if (!artwork_img_src && !artwork_style && widget) {
    artwork_debug_html = widget.innerHTML.slice(0, 600);
  }

  const passedEl = q([
    ".playbackTimeline__timePassed span[aria-hidden='true']",
    '.playbackTimeline__timePassed'
  ]);
  const durEl = q([
    ".playbackTimeline__duration span[aria-hidden='true']",
    '.playbackTimeline__duration'
  ]);

  // строго внутри обёртки таймлайна, БЕЗ общего запасного варианта
  const sliderEl = document.querySelector(".playbackTimeline__progressWrapper [role='slider']");
  const playBtn = document.querySelector('.playControls__play');

  return {
    widget_found: !!widget,
    title: titleEl ? titleEl.innerText.trim() : null,
    title_href: titleEl ? titleEl.getAttribute('href') : null,
    artist: artistEl ? artistEl.innerText.trim() : null,
    artwork_style: artwork_style,
    artwork_img_src: artwork_img_src,
    artwork_debug_html: artwork_debug_html,
    time_passed_text: passedEl ? passedEl.innerText.trim() : null,
    duration_text: durEl ? durEl.innerText.trim() : null,
    aria_valuenow: sliderEl ? sliderEl.getAttribute('aria-valuenow') : null,
    aria_valuemax: sliderEl ? sliderEl.getAttribute('aria-valuemax') : null,
    is_playing: playBtn ? playBtn.className.includes('playing') : false
  };
})()
"""


def default_chrome_binary_path() -> str:
    system = platform.system()
    if system == "Windows":
        candidates = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ]
    elif system == "Darwin":
        candidates = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]
    else:
        for name in ("google-chrome", "google-chrome-stable", "chromium-browser", "chromium"):
            found = shutil.which(name)
            if found:
                return found
        candidates = ["/usr/bin/google-chrome", "/usr/bin/chromium-browser", "/usr/bin/chromium"]

    for c in candidates:
        if os.path.exists(c):
            return c
    return candidates[0] if candidates else "google-chrome"


def clean_text(raw: Optional[str]) -> Optional[str]:
    """
    SoundCloud иногда дублирует текст для скринридеров вида
    "Current track: <название> <название>" внутри одного элемента —
    innerText захватывает и скрытую подпись, и видимый текст вместе.
    Эта функция убирает префикс и склеенный дубликат.
    """
    if not raw:
        return raw
    text = raw.strip()
    for prefix in ("Current track:", "Текущий трек:", "Now playing:"):
        if text.lower().startswith(prefix.lower()):
            text = text[len(prefix):].strip()
            break
    # если строка — это буквально "X X" (одно и то же дважды подряд)
    half = len(text) // 2
    if half > 0:
        first, second = text[:half].strip(), text[half:].strip()
        if first and first == second:
            text = first
    return text


def strip_artist_prefix(title: Optional[str]) -> Optional[str]:
    """
    SoundCloud иногда отдаёт заголовок вида "Artist1, Artist2 – Track Name".
    Исполнители там и так уже показаны отдельным полем — оставляем
    только "Track Name". Специально ищем именно "–"/"—" (не обычный
    дефис "-"), чтобы не обрезать треки, у которых дефис — часть
    настоящего названия (например "Song - Remix").
    """
    if not title:
        return title
    for sep in (" – ", " — "):
        if sep in title:
            _, _, rest = title.partition(sep)
            rest = rest.strip()
            if rest:
                return rest
    return title


class SoundCloudMonitor:
    def __init__(self, chrome_binary_path: str, debug_profile_path: str,
                 debug_port: int = 9222,
                 soundcloud_url: str = "https://soundcloud.com"):
        self.chrome_binary_path = chrome_binary_path
        self.debug_profile_path = debug_profile_path
        self.debug_port = debug_port
        self.soundcloud_url = soundcloud_url
        self._ws = None
        self._msg_id = 0
        self._current_target_id = None
        self.last_status = "init"
        self.last_error = None
        self.artwork_debug_html = None

    def _is_debug_port_open(self) -> bool:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{self.debug_port}/json/version", timeout=1)
            return True
        except (urllib.error.URLError, OSError):
            return False

    def _launch_chrome(self):
        subprocess.Popen([
            self.chrome_binary_path,
            f"--remote-debugging-port={self.debug_port}",
            f"--user-data-dir={self.debug_profile_path}",
            "--remote-allow-origins=*",
            "--start-maximized",
            self.soundcloud_url,
        ])

    def _wait_for_debug_port(self, timeout: int = 20):
        start = time.time()
        while time.time() - start < timeout:
            if self._is_debug_port_open():
                return
            time.sleep(0.5)
        raise RuntimeError("Не удалось дождаться запуска Chrome с debug-портом.")

    def start(self):
        if websocket is None:
            raise RuntimeError("Не установлена библиотека websocket-client.")
        if not self._is_debug_port_open():
            self._launch_chrome()
        self._wait_for_debug_port()

    def stop(self):
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
        self._ws = None

    def _find_soundcloud_target(self) -> Optional[dict]:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{self.debug_port}/json/list", timeout=2) as resp:
                targets = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, OSError, json.JSONDecodeError):
            return None
        for t in targets:
            if t.get("type") == "page" and "soundcloud.com" in t.get("url", ""):
                return t
        return None

    def _connect(self, ws_url: str) -> bool:
        try:
            if self._ws:
                self._ws.close()
            self._ws = websocket.create_connection(ws_url, timeout=3, origin="*")
            self.last_error = None
            return True
        except Exception as e:
            self._ws = None
            self.last_error = str(e)
            return False

    def _evaluate(self, expression: str):
        if not self._ws:
            return None
        self._msg_id += 1
        msg_id = self._msg_id
        payload = {"id": msg_id, "method": "Runtime.evaluate",
                   "params": {"expression": expression, "returnByValue": True}}
        try:
            self._ws.send(json.dumps(payload))
            deadline = time.time() + 3
            while time.time() < deadline:
                raw = self._ws.recv()
                data = json.loads(raw)
                if data.get("id") == msg_id:
                    return data.get("result", {}).get("result", {}).get("value")
            return None
        except Exception as e:
            self._ws = None
            self.last_error = str(e)
            return None

    @staticmethod
    def _time_to_seconds(t) -> int:
        if not t:
            return 0
        try:
            parts = [int(p) for p in str(t).strip().split(":")]
        except ValueError:
            return 0
        parts.reverse()
        seconds = 0
        for i, p in enumerate(parts):
            seconds += p * (60 ** i)
        return seconds

    @staticmethod
    def _extract_bg_image_url(style) -> Optional[str]:
        if not style:
            return None
        m = re.search(r'url\(["\']?(.*?)["\']?\)', style)
        return m.group(1) if m else None

    def get_now_playing(self) -> Optional[Dict]:
        try:
            target = self._find_soundcloud_target()
            if not target:
                self.last_status = "no_target"
                self._ws = None
                return None

            if not self._ws or self._current_target_id != target["id"]:
                ws_url = target.get("webSocketDebuggerUrl")
                if not ws_url or not self._connect(ws_url):
                    self.last_status = "ws_failed"
                    return None
                self._current_target_id = target["id"]

            data = self._evaluate(JS_EXTRACT)
            if data is None:
                self.last_status = "eval_failed"
                return None
            if not data.get("widget_found"):
                self.last_status = "widget_not_found"
                return None
            if not data.get("title"):
                self.last_status = "title_missing"
                return None

            self.last_status = "ok"

            artwork_url = data.get("artwork_img_src") or self._extract_bg_image_url(data.get("artwork_style"))
            if artwork_url:
                artwork_url = re.sub(r"-large\.", "-t500x500.", artwork_url)
                artwork_url = re.sub(r"-t\d+x\d+\.", "-t500x500.", artwork_url)
            else:
                self.artwork_debug_html = data.get("artwork_debug_html")

            # Приоритет — видимый текст таймлайна (надёжнее). aria-атрибуты
            # слайдера используем только как запасной вариант и только если
            # значение разумное (>5 сек) — иначе могли схватить не тот слайдер.
            position = self._time_to_seconds(data.get("time_passed_text"))
            duration = self._time_to_seconds(data.get("duration_text"))
            if not duration:
                aria_max = data.get("aria_valuemax")
                if aria_max:
                    try:
                        candidate = int(float(aria_max))
                        if candidate > 5:
                            duration = candidate
                            position = int(float(data.get("aria_valuenow") or 0))
                    except (TypeError, ValueError):
                        pass

            track_url = data.get("title_href")
            if track_url and track_url.startswith("/"):
                track_url = "https://soundcloud.com" + track_url

            return {
                "title": strip_artist_prefix(clean_text(data["title"])),
                "artist": clean_text(data.get("artist")) or "SoundCloud",
                "artwork_url": artwork_url,
                "position": position or 0,
                "duration": duration or 0,
                "is_playing": bool(data.get("is_playing")),
                "track_url": track_url,
            }
        except Exception as e:
            self.last_status = "exception"
            self.last_error = str(e)
            self._ws = None
            return None
