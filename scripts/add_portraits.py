import json
from pathlib import Path

path = Path("data/dexter/seed/characters.json")
chars = json.loads(path.read_text(encoding="utf-8"))

# PROBLEMS #28 contract: images must be self-hosted (never external CDN).
# Portraits are bundled under spoilerless/app/static/characters/*.webp and
# served by the backend at /api/static/characters/<id>.webp; the seed stores
# the relative URL so any origin (Vite dev proxy, Vercel /api rewrite) works.
images = {
    "dexter:character:dexter_morgan": "/api/static/characters/dexter_morgan.webp",
    "dexter:character:debra_morgan": "/api/static/characters/debra_morgan.webp",
    "dexter:character:angel_batista": "/api/static/characters/angel_batista.webp",
    "dexter:character:maria_laguerta": "/api/static/characters/maria_laguerta.webp",
    "dexter:character:james_doakes": "/api/static/characters/james_doakes.webp",
    "dexter:character:rita_bennett": "/api/static/characters/rita_bennett.webp",
}

changed = 0
for c in chars:
    url = images.get(c["id"])
    if url:
        c["image_url"] = url
        changed += 1
    else:
        # Keep the no-image contract explicit: drop any stray image_url so the
        # seed stays the single source of truth (self-healing upsert deletes
        # keys absent from the row anyway).
        c.pop("image_url", None)

path.write_text(json.dumps(chars, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"updated {changed} characters")
