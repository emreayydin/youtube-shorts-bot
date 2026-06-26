"""Fetches free vertical stock videos from Pexels for background montage.

Requires a free Pexels API key in env var PEXELS_API_KEY.
Returns multiple clips so the renderer can cut between them for a dynamic,
fast-paced "dopamine" edit. If no key/results, returns [] and the renderer
falls back to an animated gradient.
"""
import os
import json
import urllib.request
import urllib.parse
from pathlib import Path


# Maps trivia categories to good visual search terms (several for variety)
CATEGORY_QUERIES = {
    "Wissenschaft": ["laboratory", "science abstract", "chemistry", "molecules", "experiment"],
    "Geschichte":   ["ancient ruins", "old castle", "history", "ancient temple", "vintage"],
    "Natur":        ["nature forest", "ocean waves", "mountains", "waterfall", "wildlife"],
    "Technologie":  ["technology", "circuit board", "data network", "futuristic", "ai robot"],
    "Weltrekorde":  ["stadium", "fireworks", "crowd cheering", "sport action", "city lights"],
    "Psychologie":  ["brain", "abstract mind", "neurons", "meditation", "human face"],
    "Astronomie":   ["galaxy", "stars space", "nebula", "planet earth", "milky way"],
    "Biologie":     ["microscope cells", "wildlife nature", "underwater ocean", "jungle", "insects macro"],
}
DEFAULT_QUERIES = ["abstract background", "particles", "gradient motion", "neon lights", "slow motion"]

_HEADERS_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) YouTubeShortsBot/1.0"


def _search_pexels(query: str, api_key: str, limit: int = 8,
                   orientation: str = "portrait") -> list[str]:
    """Returns up to `limit` video file URLs for the query in the given orientation."""
    params = urllib.parse.urlencode({
        "query": query,
        "orientation": orientation,
        "size": "medium",
        "per_page": 15,
    })
    url = f"https://api.pexels.com/videos/search?{params}"
    req = urllib.request.Request(url, headers={
        "Authorization": api_key,
        "User-Agent": _HEADERS_UA,
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print(f"Pexels-Suche fehlgeschlagen ('{query}'): {e}")
        return []

    portrait = orientation == "portrait"
    urls = []
    for video in data.get("videos", []):
        if portrait:
            candidates = [f for f in video.get("video_files", [])
                          if f.get("height", 0) >= 1280 and f.get("width", 1) < f.get("height", 1)]
        else:
            candidates = [f for f in video.get("video_files", [])
                          if f.get("height", 0) >= 720 and f.get("width", 1) > f.get("height", 1)]
        if candidates:
            best = min(candidates, key=lambda f: f["height"])  # smallest HD = fast DL
            urls.append(best["link"])
        if len(urls) >= limit:
            break
    return urls


def _download(url: str, output_path: str) -> str | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _HEADERS_UA})
        with urllib.request.urlopen(req, timeout=60) as resp, open(output_path, "wb") as f:
            f.write(resp.read())
        return output_path
    except Exception as e:
        print(f"Download fehlgeschlagen: {e}")
        return None


def fetch_background_clips(category: str, output_dir: str, count: int = 5,
                          tags: list[str] = None, orientation: str = "portrait") -> list[str]:
    """
    Downloads up to `count` distinct clips for the category in the given orientation.
    Returns a list of local file paths (possibly empty).
    """
    api_key = os.environ.get("PEXELS_API_KEY")
    if not api_key:
        return []

    queries = list(CATEGORY_QUERIES.get(category, DEFAULT_QUERIES))
    if tags:
        queries = tags[:3] + queries  # specific tags first

    # Collect candidate URLs across queries until we have enough
    seen, urls = set(), []
    for q in queries:
        for u in _search_pexels(q, api_key, orientation=orientation):
            if u not in seen:
                seen.add(u)
                urls.append(u)
        if len(urls) >= count:
            break

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    paths = []
    for i, u in enumerate(urls[:count]):
        dest = str(Path(output_dir) / f"clip_{i}.mp4")
        if _download(u, dest):
            paths.append(dest)
    if paths:
        print(f"{len(paths)} Hintergrund-Clips geladen")
    return paths


# Backwards-compatible single-clip helper
def fetch_background_video(category: str, output_path: str, tags: list[str] = None) -> str | None:
    clips = fetch_background_clips(category, str(Path(output_path).parent), count=1, tags=tags)
    if clips:
        os.replace(clips[0], output_path)
        return output_path
    return None


if __name__ == "__main__":
    clips = fetch_background_clips("Astronomie", "/tmp/bgclips", count=5)
    print("Clips:", clips)
