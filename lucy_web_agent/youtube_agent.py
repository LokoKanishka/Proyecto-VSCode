import json
import subprocess
from typing import Optional, List, Dict, Any


def _log(msg: str) -> None:
    print(f"[LucyWebAgent] {msg}", flush=True)


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

        search_term = cleaned_query
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
        entries = data.get("entries") or []
        if not entries and isinstance(data, dict) and "webpage_url" in data:
            entries = [data]

        if channel_hint:
            ch = channel_hint.lower()
            filtered = [
                e for e in entries
                if ch in (e.get("uploader") or "").lower()
                or ch in (e.get("channel") or "").lower()
            ]
            if filtered:
                entries = filtered

        if not entries:
            _log(f"[LucyWebAgent] Sin resultados de yt-dlp para query='{cleaned_query}', channel_hint='{channel_hint}'")
            return None

        candidate = None
        if strategy == "latest":
            candidate = entries[-1]
        else:
            candidate = entries[0]

        url = (
            candidate.get("webpage_url")
            or candidate.get("url")
            or (f"https://www.youtube.com/watch?v={candidate['id']}" if candidate.get("id") else None)
        )

        title = candidate.get("title") or "(sin título)"
        uploader = candidate.get("uploader") or candidate.get("channel") or "(sin canal)"
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
