import json
import subprocess
from typing import Optional, List, Dict, Any


def _log(msg: str) -> None:
    print(f"[LucyWebAgent] {msg}", flush=True)


def _choose_best_entry(
    entries: List[Dict[str, Any]],
    channel_hint: Optional[str],
    strategy: str,
) -> Optional[Dict[str, Any]]:
    if not entries:
        return None

    if channel_hint:
        hint = channel_hint.lower()
        for entry in entries:
            uploader = (entry.get("uploader") or "").lower()
            channel = (entry.get("channel") or "").lower()
            if hint in uploader or hint in channel:
                return entry

    if strategy == "latest":
        dated_entries = [
            e for e in entries if isinstance(e.get("upload_date"), str) and e["upload_date"].isdigit()
        ]
        if dated_entries:
            dated_entries.sort(key=lambda e: e.get("upload_date"), reverse=True)
            return dated_entries[0]

    return entries[0]


def find_youtube_video_url(
    query: str,
    channel_hint: Optional[str] = None,
    strategy: str = "latest",
) -> Optional[str]:
    """
    Dado un texto de búsqueda y (opcionalmente) un identificador/dica de canal,
    intenta encontrar una URL de video de YouTube que encaje.

    Por ahora solo define la interfaz.
    La implementación real podrá usar Playwright, Selenium, o un cliente HTTP.

    Estrategias posibles:
    - "latest": el video más reciente que encaje con la búsqueda.
    - "live_or_latest": si hay vivo, usar ese; si no, el último video.

    Devuelve:
    - Una URL completa de YouTube (https://www.youtube.com/watch?v=...)
      si tuvo éxito.
    - None si no pudo encontrar nada aceptable.
    """
    try:
        cleaned_query = (query or "").strip()
        if not cleaned_query:
            _log("Empty query provided to find_youtube_video_url.")
            return None

        search_term = f"{cleaned_query} {channel_hint}".strip() if channel_hint else cleaned_query
        cmd = [
            "yt-dlp",
            "--dump-single-json",
            "--skip-download",
            "--no-warnings",
            "--flat-playlist",
            f"ytsearch10:{search_term}",
        ]
        _log(f"Running yt-dlp search: {' '.join(cmd)}")
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            _log(f"yt-dlp failed (code {proc.returncode}): {proc.stderr.strip()}")
            return None

        stdout = proc.stdout or ""
        if not stdout.strip():
            _log("yt-dlp returned empty output.")
            return None

        data = json.loads(stdout)
        entries = data.get("entries")
        if not entries:
            _log("yt-dlp returned no entries.")
            return None

        best = _choose_best_entry(entries, channel_hint, strategy)
        if not best:
            _log("No suitable video found after filtering entries.")
            return None

        url = best.get("webpage_url") or best.get("url")
        if not url:
            video_id = best.get("id")
            url = f"https://www.youtube.com/watch?v={video_id}" if video_id else None

        title = best.get("title") or "(sin título)"
        uploader = best.get("uploader") or best.get("channel") or "(sin canal)"
        _log(f"Elegí video: titulo='{title}', canal='{uploader}', url='{url}'")

        return url

    except Exception as exc:
        _log(f"Error while searching YouTube: {exc}")
        return None


if __name__ == "__main__":
    import sys

    q = " ".join(sys.argv[1:]) or "alejandro dolina"
    url = find_youtube_video_url(q)
    if url:
        print(url)
    else:
        print("No se encontró ningún video para esa búsqueda.")
