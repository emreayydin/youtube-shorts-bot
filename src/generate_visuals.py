"""AI visuals via fal.ai Flux — one on-theme image per fact/section, animated for
free with Ken-Burns in the renderer.

Orientation-aware: shorts use 9:16 (portrait), long-form uses 16:9 (landscape).
Degrades gracefully — if FAL_KEY is missing or a call fails, the caller falls back
to the free Pexels montage, so the bot never breaks.

Env:
  FAL_KEY          – fal.ai API key
  FLUX_HERO_MODEL  – default fal-ai/flux-pro/v1.1 (best; hero image)
  FLUX_FACT_MODEL  – default fal-ai/flux/dev       (cheaper; the rest)
"""
import os
import urllib.request
import requests

FAL_RUN = "https://fal.run"
HERO_MODEL = os.environ.get("FLUX_HERO_MODEL", "fal-ai/flux-pro/v1.1")
FACT_MODEL = os.environ.get("FLUX_FACT_MODEL", "fal-ai/flux/dev")

_SIZE = {"portrait": "portrait_16_9", "landscape": "landscape_16_9"}


def _download(url: str, path: str) -> str:
    with urllib.request.urlopen(url, timeout=120) as r, open(path, "wb") as f:
        f.write(r.read())
    return path


def flux_image(prompt: str, out_path: str, orientation: str = "portrait",
               model: str = FACT_MODEL, style: str = "cinematic, dramatic lighting, highly detailed") -> str:
    """Generates one image. Returns local path. Raises on failure."""
    key = os.environ["FAL_KEY"]
    body = {
        "prompt": f"{prompt}, {style}",
        "image_size": _SIZE.get(orientation, "portrait_16_9"),
        "num_images": 1,
        "enable_safety_checker": True,
    }
    r = requests.post(f"{FAL_RUN}/{model}", headers={
        "Authorization": f"Key {key}", "Content-Type": "application/json",
    }, json=body, timeout=180)
    if r.status_code != 200:
        raise RuntimeError(f"fal {model} {r.status_code}: {r.text[:300]}")
    return _download(r.json()["images"][0]["url"], out_path)


def images_for_prompts(prompts: list[str], out_dir: str, orientation: str = "portrait",
                       hero_last: bool = True, style: str = "cinematic, dramatic lighting, highly detailed") -> list[str]:
    """Generates one image per prompt. Returns paths in order; skips failures.
    The last prompt uses the best model (hero) when hero_last is True."""
    if not os.environ.get("FAL_KEY") or not prompts:
        return []
    os.makedirs(out_dir, exist_ok=True)
    paths, n = [], len(prompts)
    for i, p in enumerate(prompts):
        model = HERO_MODEL if (hero_last and i == n - 1) else FACT_MODEL
        try:
            paths.append(flux_image(p, os.path.join(out_dir, f"img_{i}.png"),
                                    orientation=orientation, model=model, style=style))
        except Exception as e:
            print(f"Flux Bild {i} fehlgeschlagen: {e}")
            paths.append(None)  # keep index alignment; renderer handles None
    return paths


def visuals_for_sections(content: dict, sections: list[dict], out_dir: str,
                         orientation: str = "landscape",
                         style: str = "cinematic, dramatic lighting, highly detailed") -> dict | None:
    """One image per narration section (intro/fact_i/outro) -> {label: path}.
    Uses each fact's 'image_prompt'; hero model for the last fact. None if no FAL_KEY."""
    if not os.environ.get("FAL_KEY"):
        return None
    os.makedirs(out_dir, exist_ok=True)
    facts = content.get("facts", [])
    n = len(facts)
    out, fact_i = {}, 0
    for s in sections:
        label = s["label"]
        if label == "intro":
            prompt = content.get("hook_visual") or content.get("topic") or content.get("title", "")
            model = FACT_MODEL
        elif label == "outro":
            prompt = content.get("hook_visual") or content.get("topic") or content.get("title", "")
            model = FACT_MODEL
        else:
            fact_i += 1
            f = facts[fact_i - 1] if fact_i - 1 < n else {}
            prompt = f.get("image_prompt") or f.get("headline") or content.get("title", "")
            model = HERO_MODEL if fact_i == n else FACT_MODEL
        if not prompt:
            continue
        try:
            out[label] = flux_image(prompt, os.path.join(out_dir, f"{label}.png"),
                                    orientation=orientation, model=model, style=style)
        except Exception as e:
            print(f"Flux {label} fehlgeschlagen: {e}")
    return out or None
