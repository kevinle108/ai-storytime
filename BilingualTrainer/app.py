"""
Bilingual Flashcard Generator — English ↔ Vietnamese vocabulary with optional visuals.

Uses LangChain + GitHub Models API (same pattern as StoryTime-Generator/app.py).

Optional **Hugging Face** image generation, optional **Wikimedia Commons** thumbnails (no API key),
or text-only cards. Writes Markdown, downloaded images under `output/`, and an interactive
`flashcards_<run>.html` viewer (picture-first when images exist; optional **Always show words**).

Run `python app.py` for a local web UI, or `python app.py --cli` for terminal prompts.
"""

import argparse
import asyncio
import html
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from dotenv import load_dotenv
from flask import Flask, render_template, request, send_from_directory, url_for

try:
    from langchain.agents import create_agent
    from langchain_core.messages import HumanMessage
    from langchain_openai import ChatOpenAI
except ImportError as e:
    print("Error: Required packages not installed. Please run: pip install -r requirements.txt")
    print(f"Import error: {e}")
    raise SystemExit(1) from e

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
API_ENDPOINT = os.getenv("API_ENDPOINT", "https://models.github.ai/inference")
MODEL_NAME = os.getenv("MODEL_NAME", "openai/gpt-4o-mini")
HF_TOKEN = os.getenv("HF_TOKEN")
HF_IMAGE_MODEL = os.getenv("HF_IMAGE_MODEL", "black-forest-labs/FLUX.1-schnell")
# Optional contact URL or email for Wikimedia User-Agent policy
WIKIMEDIA_CONTACT = os.getenv("WIKIMEDIA_CONTACT", "https://github.com/")
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
OUTPUT_DIR = Path(__file__).parent / "output"
TEMPLATES_DIR = Path(__file__).parent / "templates"
UI_TEMPLATES_DIR = Path(__file__).parent / "ui_templates"

IMAGE_MODE_NONE = "0"
IMAGE_MODE_GENERATE = "1"
IMAGE_MODE_COMMONS = "2"

AGE_MAP = {
    "0": "2–3 years",
    "1": "3–5 years",
    "2": "6–8 years",
}

_agent_singleton: Any = None


def github_token_configured() -> bool:
    return bool(GITHUB_TOKEN and GITHUB_TOKEN != "your_github_token_here")


def build_user_data(
    theme: str,
    count: int,
    age_choice: str,
    image_mode: str,
) -> dict[str, Any]:
    """Build the same structure as console `collect_user_input` from explicit fields."""
    t = (theme or "").strip()
    if not t:
        t = "everyday objects around the home"
    n = max(1, min(40, int(count)))
    age_band = AGE_MAP.get(str(age_choice).strip(), "3–5 years")
    im = str(image_mode).strip()
    if im == IMAGE_MODE_GENERATE:
        mode = IMAGE_MODE_GENERATE
    elif im == IMAGE_MODE_COMMONS:
        mode = IMAGE_MODE_COMMONS
    else:
        mode = IMAGE_MODE_NONE
    user_message = (
        f"Create exactly {n} bilingual vocabulary flashcards.\n"
        f"Theme/topic: {t}\n"
        f"Age band: {age_band}\n"
        f"Languages: English and Vietnamese.\n"
        f"Remember: respond with ONLY the JSON array, no other text."
    )
    return {
        "theme": t,
        "count": str(n),
        "age_band": age_band,
        "user_message": user_message,
        "image_mode": mode,
    }


def get_or_create_agent() -> Any:
    """Single LangChain agent for the process (web server reuses one instance)."""
    global _agent_singleton
    if _agent_singleton is not None:
        return _agent_singleton
    template_path = TEMPLATES_DIR / "flashcard_generator.json"
    with open(template_path, "r", encoding="utf-8") as f:
        prompt_data = json.load(f)
        system_prompt = prompt_data.get("template", "")
    llm = ChatOpenAI(
        model=MODEL_NAME,
        temperature=0.55,
        base_url=API_ENDPOINT,
        api_key=GITHUB_TOKEN,
    )
    _agent_singleton = create_agent(llm, tools=[], system_prompt=system_prompt)
    return _agent_singleton


async def run_flashcard_generation(user_data: dict[str, Any], agent: Any) -> dict[str, Any]:
    """
    Full pipeline: LLM → parse → optional images → save MD + HTML.
    Returns a dict with ok=True and file names, or ok=False and error details.
    """
    response = await agent.ainvoke(
        {"messages": [HumanMessage(content=user_data["user_message"])]}
    )
    last = response["messages"][-1]
    raw_content = last.content if hasattr(last, "content") else str(last)

    try:
        cards_raw = parse_flashcard_json(raw_content)
    except (json.JSONDecodeError, ValueError) as e:
        return {
            "ok": False,
            "error": f"Could not parse flashcards JSON: {e}",
            "debug_output": raw_content[:4000],
        }

    cards = [normalize_card(c) for c in cards_raw]
    expected = int(user_data["count"])
    if len(cards) != expected:
        # Still succeed; note is informational only
        pass

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    image_mode = user_data["image_mode"]
    image_rel_paths: list[str | None] | None = None
    image_mode_label = "No images"

    if image_mode == IMAGE_MODE_GENERATE:
        if not HF_TOKEN:
            image_mode_label = "No images (HF_TOKEN missing)"
        else:
            image_mode_label = f"Generated images ({HF_IMAGE_MODEL})"
            img_dir = OUTPUT_DIR / f"flashcards_{run_id}_images"
            paths = await asyncio.to_thread(generate_image_files, cards, img_dir)
            prefix = f"flashcards_{run_id}_images"
            image_rel_paths = []
            for p in paths:
                if p is not None:
                    image_rel_paths.append(f"{prefix}/{p.name}")
                else:
                    image_rel_paths.append(None)

    elif image_mode == IMAGE_MODE_COMMONS:
        image_mode_label = "Wikimedia Commons thumbnails"
        img_dir = OUTPUT_DIR / f"flashcards_{run_id}_images"
        paths = await asyncio.to_thread(fetch_commons_image_files, cards, img_dir)
        prefix = f"flashcards_{run_id}_images"
        image_rel_paths = []
        for p in paths:
            if p is not None:
                image_rel_paths.append(f"{prefix}/{p.name}")
            else:
                image_rel_paths.append(None)

    metadata = {
        "languages": "English — Vietnamese",
        "theme": user_data["theme"],
        "age_band": user_data["age_band"],
        "image_mode_label": image_mode_label,
    }
    title = f"Flashcards: {user_data['theme']}"
    path = save_flashcards(
        title,
        cards,
        metadata,
        run_id=run_id,
        image_rel_paths=image_rel_paths,
    )
    path_html = save_flashcards_html(
        title,
        cards,
        metadata,
        run_id=run_id,
        image_rel_paths=image_rel_paths,
        always_show_words=bool(user_data.get("always_show_words")),
    )

    return {
        "ok": True,
        "cards_count": len(cards),
        "run_id": run_id,
        "md_name": path.name,
        "html_name": path_html.name,
        "requested_count": expected,
        "actual_count": len(cards),
    }


def parse_flashcard_json(raw: str) -> list[dict[str, Any]]:
    """Extract JSON array from model output (handles optional markdown fences)."""
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if fence:
        text = fence.group(1).strip()
    if not text.startswith("["):
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and end > start:
            text = text[start : end + 1]
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError("Expected a JSON array of flashcards")
    return data


def normalize_card(card: dict[str, Any]) -> dict[str, Any]:
    """Ensure optional visual fields exist for older JSON."""
    out = dict(card)
    out.pop("emoji", None)
    out.setdefault("image_prompt", "")
    return out


def _hf_image_prompt(card: dict[str, Any]) -> str:
    """One clear subject, calm background, and strong anti-text rules (no labels on the image)."""
    en = (card.get("english") or "").strip()
    base = (card.get("image_prompt") or "").strip()
    # Avoid phrases like 'the word "phone"'—they often cause the model to paint the spelling.
    if base:
        core = f"Toddler flashcard, picture only: {base}"
    elif en:
        core = f"Toddler flashcard, picture only: {en}"
    else:
        core = "Toddler flashcard, picture only: one simple clear subject"

    no_text = (
        "CRITICAL: The image must contain zero readable text. No words, letters, numbers, "
        "captions, labels, logos, typography, speech bubbles, street signs, book titles, or UI text. "
        "Do not spell or write the vocabulary anywhere in the image. "
        "If you show a phone, tablet, laptop, TV, book, newspaper, or sign, use a blank screen, "
        "a soft color block, or a simple pattern—never legible characters on surfaces."
    )
    style = (
        "One main subject, centered, large in the frame. "
        "Plain simple background (soft solid or very light gradient), no busy scenery or clutter. "
        "Flat cartoon style, bold shapes, thick outlines, bright friendly colors, high contrast. "
        "No watermark."
    )
    return f"{core} {style} {no_text}"


def generate_image_files(
    cards: list[dict[str, Any]],
    image_dir: Path,
) -> list[Path | None]:
    """Generate one PNG per card using Hugging Face Inference. Returns parallel list of paths or None on failure."""
    try:
        from huggingface_hub import InferenceClient
    except ImportError:
        print("huggingface_hub is not installed. Run: pip install huggingface_hub")
        return [None] * len(cards)

    if not HF_TOKEN:
        print("HF_TOKEN missing; cannot generate images.")
        return [None] * len(cards)

    image_dir.mkdir(parents=True, exist_ok=True)
    client = InferenceClient(api_key=HF_TOKEN)
    paths: list[Path | None] = []

    for i, card in enumerate(cards, start=1):
        prompt = _hf_image_prompt(card)
        out_path = image_dir / f"card_{i:02d}.png"
        try:
            image = client.text_to_image(prompt=prompt, model=HF_IMAGE_MODEL)
            image.save(out_path)
            paths.append(out_path)
            print(f"   Image {i}/{len(cards)} saved: {out_path.name}")
        except Exception as e:
            print(f"   Image {i}/{len(cards)} failed: {str(e)[:120]}")
            paths.append(None)

    return paths


def _commons_user_agent() -> str:
    return f"BilingualTrainer/1.0 ({WIKIMEDIA_CONTACT}; bilingual flashcards for education) Python"


def _queries_for_card_images(card: dict[str, Any]) -> list[str]:
    """Search phrases for Wikimedia Commons, Pexels, etc."""
    seen: set[str] = set()
    out: list[str] = []
    en = (card.get("english") or "").strip()
    if en:
        for q in (en, en.replace("-", " ")):
            if q and q not in seen:
                seen.add(q)
                out.append(q)
        if " " in en:
            first = en.split()[0]
            if first not in seen:
                seen.add(first)
                out.append(first)
    ip = (card.get("image_prompt") or "").strip()
    if ip:
        short = " ".join(ip.split()[:8])
        if short and short not in seen:
            seen.add(short)
            out.append(short)
    if not out:
        vi = (card.get("vietnamese") or "").strip()
        if vi:
            out.append(vi)
    return out


def _ext_from_url(url: str) -> str:
    path = urlparse(url).path
    ext = Path(path).suffix.lower()
    if ext in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"):
        return ext
    return ".jpg"


def _commons_thumb_url(session: Any, query: str) -> str | None:
    """Return a thumbnail URL for the first Commons file hit, or None."""
    r = session.get(
        COMMONS_API,
        params={
            "action": "query",
            "generator": "search",
            "gsrsearch": query,
            "gsrnamespace": 6,
            "gsrlimit": 1,
            "prop": "imageinfo",
            "iiprop": "url",
            "iiurlwidth": 512,
            "format": "json",
            "formatversion": 2,
        },
        timeout=45,
    )
    r.raise_for_status()
    data = r.json()
    pages = data.get("query", {}).get("pages") or []
    for p in pages:
        if p.get("missing"):
            continue
        infos = p.get("imageinfo") or []
        if not infos:
            continue
        info = infos[0]
        return info.get("thumburl") or info.get("url")
    return None


def fetch_commons_image_files(
    cards: list[dict[str, Any]],
    image_dir: Path,
) -> list[Path | None]:
    """
    Download one image per card from Wikimedia Commons (search in File namespace).
    Respects https://meta.wikimedia.org/wiki/User-Agent_policy — set WIKIMEDIA_CONTACT in .env.
    """
    try:
        import requests
    except ImportError:
        print("requests is not installed. Run: pip install requests")
        return [None] * len(cards)

    image_dir.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": _commons_user_agent()}
    session = requests.Session()
    session.headers.update(headers)

    paths: list[Path | None] = []
    delay_s = float(os.getenv("COMMONS_REQUEST_DELAY", "0.35"))
    first_http = True

    def pace() -> None:
        nonlocal first_http
        if first_http:
            first_http = False
            return
        if delay_s > 0:
            time.sleep(delay_s)

    for i, card in enumerate(cards, start=1):
        queries = _queries_for_card_images(normalize_card(card))
        thumb: str | None = None
        for q in queries:
            pace()
            try:
                thumb = _commons_thumb_url(session, q)
            except Exception as e:
                qprev = q[:40] + ("…" if len(q) > 40 else "")
                print(f"   Commons search failed ({qprev}): {str(e)[:100]}")
                thumb = None
            if thumb:
                break

        if not thumb:
            print(f"   No Commons image for card {i}/{len(cards)} ({card.get('english', '')!r})")
            paths.append(None)
            continue

        ext = _ext_from_url(thumb)
        out_path = image_dir / f"card_{i:02d}{ext}"
        try:
            pace()
            gr = session.get(thumb, timeout=60)
            gr.raise_for_status()
            out_path.write_bytes(gr.content)
            paths.append(out_path)
            print(f"   Card {i}/{len(cards)}: saved {out_path.name}")
        except Exception as e:
            print(f"   Download failed for card {i}: {str(e)[:120]}")
            paths.append(None)

    return paths


def save_flashcards(
    title: str,
    cards: list[dict[str, Any]],
    metadata: dict[str, str],
    *,
    run_id: str,
    image_rel_paths: list[str | None] | None = None,
) -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    filename = f"flashcards_{run_id}.md"
    filepath = OUTPUT_DIR / filename

    rels = image_rel_paths or [None] * len(cards)

    lines = [
        f"# {title}",
        "",
        "## Metadata",
        f"- **Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- **Languages**: {metadata.get('languages', 'English — Vietnamese')}",
        f"- **Theme**: {metadata.get('theme', '')}",
        f"- **Age band**: {metadata.get('age_band', '')}",
        f"- **Card count**: {len(cards)}",
        f"- **Images**: {metadata.get('image_mode_label', '')}",
        f"- **Interactive viewer**: `{filename.replace('.md', '.html')}` (open in a browser)",
        "",
        "---",
        "",
        "## Printable flashcards",
        "",
        "Each block is one card: **picture** (when available), **English**, **Vietnamese**. "
        "For dual-sided printing, flip on the short edge.",
        "",
    ]

    for i, card in enumerate(cards, start=1):
        card = normalize_card(card)
        en = card.get("english", "")
        vi = card.get("vietnamese", "")
        hint = card.get("hint", "")

        lines.append(f"### Card {i}")
        lines.append("")
        rel = rels[i - 1] if i - 1 < len(rels) else None
        if rel:
            lines.append(f"![{en}]({rel})")
            lines.append("")
        lines.append(f"**English:** {en}")
        lines.append("")
        lines.append(f"**Vietnamese:** {vi}")
        if hint:
            lines.append("")
            lines.append(f"*Tip for parents:* {hint}")
        lines.append("")
        lines.append("---")
        lines.append("")

    lines.extend(
        [
            "## Raw JSON",
            "",
            "```json",
            json.dumps(cards, ensure_ascii=False, indent=2),
            "```",
            "",
        ]
    )

    filepath.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nSaved flashcards to: {filepath}")
    return filepath


def save_flashcards_html(
    title: str,
    cards: list[dict[str, Any]],
    metadata: dict[str, str],
    *,
    run_id: str,
    image_rel_paths: list[str | None] | None = None,
    always_show_words: bool = False,
) -> Path:
    """Picture-first interactive viewer: image when present, then reveal English / Vietnamese."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    filename = f"flashcards_{run_id}.html"
    filepath = OUTPUT_DIR / filename

    rels = image_rel_paths or [None] * len(cards)
    payload: list[dict[str, Any]] = []
    for i, card in enumerate(cards):
        c = normalize_card(card)
        rel = rels[i] if i < len(rels) else None
        payload.append(
            {
                "english": c.get("english", ""),
                "vietnamese": c.get("vietnamese", ""),
                "hint": c.get("hint", ""),
                "imageUrl": rel,
            }
        )

    data_json = json.dumps(payload, ensure_ascii=False)
    # Avoid closing the HTML script tag if JSON text ever contains </script>
    data_json = data_json.replace("</script>", "<\\/script>")

    safe_title = html.escape(title)
    safe_sub = html.escape(metadata.get("theme", "")) + " · " + html.escape(metadata.get("age_band", ""))

    words_block_class = "words hidden" if not always_show_words else "words"
    always_js = "true" if always_show_words else "false"
    hint_start = (
        "Words stay visible when you change cards. Uncheck <strong>Always show words</strong> "
        "or tap <strong>Hide words</strong> to conceal them."
        if always_show_words
        else "Tap <strong>Show words</strong> to reveal English and Vietnamese. "
        "Check <strong>Always show words</strong> to keep them visible when you move between cards."
    )
    reveal_btn_label = "Hide words" if always_show_words else "Show words"
    reveal_aria = "true" if always_show_words else "false"
    chk_checked = " checked" if always_show_words else ""

    # Single-file HTML; paths are relative to this file (same folder as images/).
    html_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{safe_title}</title>
  <style>
    :root {{
      --bg: #fef6eb;
      --card: #ffffff;
      --text: #2c2416;
      --muted: #6b5c4c;
      --accent: #3d7ea6;
      --accent-hover: #2f6588;
      --radius: 20px;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      font-family: system-ui, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 1rem;
    }}
    header {{
      text-align: center;
      max-width: 36rem;
      margin-bottom: 0.75rem;
    }}
    header h1 {{
      font-size: 1.15rem;
      font-weight: 700;
      margin: 0 0 0.25rem 0;
      line-height: 1.3;
    }}
    header p {{
      margin: 0;
      font-size: 0.9rem;
      color: var(--muted);
    }}
    .stage {{
      width: 100%;
      max-width: 28rem;
      background: var(--card);
      border-radius: var(--radius);
      box-shadow: 0 8px 28px rgba(44, 36, 22, 0.12);
      padding: 1rem;
      display: flex;
      flex-direction: column;
      align-items: center;
      min-height: 12rem;
    }}
    .visual {{
      width: 100%;
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 220px;
    }}
    .visual img {{
      max-width: 100%;
      max-height: 280px;
      width: auto;
      height: auto;
      object-fit: contain;
      border-radius: 12px;
    }}
    .visual .no-visual {{
      font-size: 1.1rem;
      color: var(--muted);
      text-align: center;
      padding: 1.5rem;
    }}
    .hidden {{ display: none !important; }}
    .counter {{
      font-size: 0.95rem;
      font-weight: 600;
      color: var(--muted);
      margin-top: 0.5rem;
    }}
    .words {{
      width: 100%;
      text-align: center;
      margin-top: 1rem;
      padding-top: 1rem;
      border-top: 2px dashed rgba(44, 36, 22, 0.12);
    }}
    .words .en {{
      font-size: 1.75rem;
      font-weight: 800;
      letter-spacing: 0.02em;
      margin-bottom: 0.35rem;
    }}
    .words .vi {{
      font-size: 1.45rem;
      font-weight: 600;
      color: var(--accent);
    }}
    .words .hint {{
      margin-top: 0.75rem;
      font-size: 0.88rem;
      color: var(--muted);
      font-style: italic;
    }}
    .controls {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.6rem;
      justify-content: center;
      margin-top: 1.25rem;
      max-width: 28rem;
    }}
    button {{
      font: inherit;
      font-size: 1rem;
      font-weight: 600;
      padding: 0.65rem 1.1rem;
      border: none;
      border-radius: 999px;
      cursor: pointer;
      background: var(--accent);
      color: #fff;
      min-height: 44px;
      min-width: 44px;
    }}
    button:hover {{ background: var(--accent-hover); }}
    button.secondary {{
      background: #e8dfd2;
      color: var(--text);
    }}
    button.secondary:hover {{ background: #ddd2c2; }}
    button:disabled {{
      opacity: 0.45;
      cursor: not-allowed;
    }}
    .hint-start {{
      margin-top: 0.75rem;
      font-size: 0.95rem;
      color: var(--muted);
      text-align: center;
      max-width: 24rem;
    }}
    .always-row {{
      flex: 1 1 100%;
      display: flex;
      justify-content: center;
      margin-bottom: 0.15rem;
    }}
    .always-row label {{
      display: flex;
      align-items: center;
      gap: 0.45rem;
      font-size: 0.95rem;
      font-weight: 600;
      cursor: pointer;
      user-select: none;
    }}
    .always-row input {{
      width: 1.05rem;
      height: 1.05rem;
      accent-color: var(--accent);
    }}
  </style>
</head>
<body>
  <header>
    <h1 id="page-title">{safe_title}</h1>
    <p id="page-sub">{safe_sub}</p>
  </header>
  <p class="hint-start">{hint_start}</p>
  <div class="stage" aria-live="polite">
    <div class="visual" id="visual">
      <img id="card-img" alt="" class="hidden" />
      <div id="card-noimg" class="no-visual hidden">No picture for this card.</div>
    </div>
    <div class="counter" id="counter"></div>
    <div class="{words_block_class}" id="words-block">
      <div class="en" id="w-en"></div>
      <div class="vi" id="w-vi"></div>
      <div class="hint hidden" id="w-hint"></div>
    </div>
  </div>
  <div class="controls">
    <div class="always-row">
      <label><input type="checkbox" id="chk-always-words"{chk_checked} /> Always show words</label>
    </div>
    <button type="button" class="secondary" id="btn-prev" aria-label="Previous card">← Back</button>
    <button type="button" id="btn-reveal" aria-expanded="{reveal_aria}">{reveal_btn_label}</button>
    <button type="button" class="secondary" id="btn-next" aria-label="Next card">Next →</button>
  </div>
  <script type="application/json" id="flashcards-data">{data_json}</script>
  <script>
(function () {{
  const cards = JSON.parse(document.getElementById('flashcards-data').textContent);
  let index = 0;
  let alwaysShowWords = {always_js};
  let revealed = alwaysShowWords;

  const elImg = document.getElementById('card-img');
  const elNoImg = document.getElementById('card-noimg');
  const elWords = document.getElementById('words-block');
  const elHint = document.getElementById('w-hint');
  const elReveal = document.getElementById('btn-reveal');
  const elCounter = document.getElementById('counter');
  const elPrev = document.getElementById('btn-prev');
  const elNext = document.getElementById('btn-next');
  const elAlways = document.getElementById('chk-always-words');

  function setReveal(on) {{
    revealed = on;
    elWords.classList.toggle('hidden', !revealed);
    elReveal.textContent = revealed ? 'Hide words' : 'Show words';
    elReveal.setAttribute('aria-expanded', revealed ? 'true' : 'false');
    if (revealed) {{
      const c = cards[index];
      document.getElementById('w-en').textContent = c.english;
      document.getElementById('w-vi').textContent = c.vietnamese;
      if (c.hint) {{
        elHint.textContent = 'Tip: ' + c.hint;
        elHint.classList.remove('hidden');
      }} else {{
        elHint.textContent = '';
        elHint.classList.add('hidden');
      }}
    }}
  }}

  function render() {{
    const c = cards[index];
    elCounter.textContent = (index + 1) + ' / ' + cards.length;
    setReveal(revealed);
    if (c.imageUrl) {{
      elImg.src = c.imageUrl;
      elImg.classList.remove('hidden');
      elImg.alt = 'Picture for: ' + c.english;
      elNoImg.classList.add('hidden');
    }} else {{
      elImg.removeAttribute('src');
      elImg.classList.add('hidden');
      elImg.alt = '';
      elNoImg.classList.remove('hidden');
    }}
    elPrev.disabled = index <= 0;
    elNext.disabled = index >= cards.length - 1;
  }}

  elAlways.addEventListener('change', function () {{
    alwaysShowWords = elAlways.checked;
    if (alwaysShowWords) {{
      setReveal(true);
    }} else {{
      setReveal(false);
    }}
  }});

  elReveal.addEventListener('click', function () {{
    setReveal(!revealed);
  }});
  elPrev.addEventListener('click', function () {{
    if (index > 0) {{
      index--;
      revealed = alwaysShowWords;
      render();
    }}
  }});
  elNext.addEventListener('click', function () {{
    if (index < cards.length - 1) {{
      index++;
      revealed = alwaysShowWords;
      render();
    }}
  }});
  document.addEventListener('keydown', function (e) {{
    if (e.key === 'ArrowLeft') elPrev.click();
    else if (e.key === 'ArrowRight') elNext.click();
    else if (e.key === ' ' || e.key === 'Enter') {{
      e.preventDefault();
      elReveal.click();
    }}
  }});

  render();
}})();
  </script>
</body>
</html>
"""

    filepath.write_text(html_page, encoding="utf-8")
    print(f"Saved interactive viewer: {filepath}")
    return filepath


def collect_user_input() -> dict[str, Any]:
    print("\n" + "=" * 60)
    print("Bilingual Flashcard Generator (English ↔ Vietnamese)")
    print("=" * 60)
    print("\nWe'll create simple vocabulary cards for young learners.\n")

    theme = input("Theme or topic (e.g. animals, colors, breakfast): ").strip()

    count_str = input("How many cards? [default: 12]: ").strip() or "12"
    try:
        count = int(count_str)
    except ValueError:
        count = 12

    print("\nAge band:")
    print("  0) 2–3 years (very few words per card)")
    print("  1) 3–5 years (preschool)")
    print("  2) 6–8 years (early elementary)")
    age_choice = input("Select (0–2) [default: 1]: ").strip() or "1"

    print("\nImages:")
    print("  0) No images (text-only cards)")
    print("  1) AI-generated pictures (HF_TOKEN in .env; Hugging Face)")
    print("  2) Wikimedia Commons thumbnails (no extra key; internet)")
    img_choice = input("Select (0–2) [default: 0]: ").strip() or IMAGE_MODE_NONE

    return build_user_data(theme, count, age_choice, img_choice)


def default_form_state() -> dict[str, Any]:
    return {
        "theme": "",
        "count": "12",
        "age": "1",
        "image_mode": IMAGE_MODE_NONE,
        "always_show_words": False,
    }


def create_web_app() -> Flask:
    app = Flask(__name__, template_folder=str(UI_TEMPLATES_DIR))
    app.config["MAX_CONTENT_LENGTH"] = 64 * 1024

    @app.route("/")
    def index():
        token_ok = github_token_configured()
        return render_template(
            "index.html",
            token_ok=token_ok,
            form=default_form_state(),
            error=None,
            result=None,
        )

    @app.route("/generate", methods=["POST"])
    def generate():
        token_ok = github_token_configured()
        theme = request.form.get("theme", "")
        try:
            count = int(request.form.get("count") or "12")
        except ValueError:
            count = 12
        age = (request.form.get("age") or "1").strip()
        image_mode = (request.form.get("image_mode") or IMAGE_MODE_NONE).strip()
        always_show_words = request.form.get("always_show_words") == "on"

        form_state = {
            "theme": theme,
            "count": str(max(1, min(40, count))),
            "age": age if age in AGE_MAP else "1",
            "image_mode": image_mode
            if image_mode in (IMAGE_MODE_NONE, IMAGE_MODE_GENERATE, IMAGE_MODE_COMMONS)
            else IMAGE_MODE_NONE,
            "always_show_words": always_show_words,
        }

        if not token_ok:
            return render_template(
                "index.html",
                token_ok=False,
                form=form_state,
                error="Configure GITHUB_TOKEN in .env first.",
                result=None,
            ), 400

        template_path = TEMPLATES_DIR / "flashcard_generator.json"
        if not template_path.is_file():
            return render_template(
                "index.html",
                token_ok=True,
                form=form_state,
                error=f"Missing template: {template_path}",
                result=None,
            ), 500

        user_data = build_user_data(
            theme,
            int(form_state["count"]),
            form_state["age"],
            form_state["image_mode"],
        )
        user_data["always_show_words"] = always_show_words

        try:
            agent = get_or_create_agent()
        except Exception as e:
            return render_template(
                "index.html",
                token_ok=True,
                form=form_state,
                error=f"Could not initialize the model client: {e}",
                result=None,
            ), 500

        outcome = asyncio.run(run_flashcard_generation(user_data, agent))
        if not outcome.get("ok"):
            err = outcome.get("error", "Generation failed.")
            dbg = outcome.get("debug_output")
            if dbg:
                err = f"{err}\n\n--- Model output (truncated) ---\n{dbg}"
            return render_template(
                "index.html",
                token_ok=True,
                form=form_state,
                error=err,
                result=None,
            ), 422

        html_name = outcome["html_name"]
        md_name = outcome["md_name"]
        result = {
            "cards_count": outcome["cards_count"],
            "viewer_url": url_for("serve_output", filename=html_name),
            "md_url": url_for("serve_output", filename=md_name),
        }
        req_n = outcome.get("requested_count")
        act_n = outcome.get("actual_count")
        if req_n is not None and act_n is not None and req_n != act_n:
            result["count_note"] = f"Requested {req_n} cards; model returned {act_n}."

        return render_template(
            "index.html",
            token_ok=True,
            form=default_form_state(),
            error=None,
            result=result,
        )

    @app.route("/output/<path:filename>")
    def serve_output(filename: str):
        return send_from_directory(OUTPUT_DIR, filename, max_age=0)

    return app


async def main_cli() -> None:
    try:
        if sys.platform == "win32":
            import io

            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
    except Exception:
        pass

    print("\nInitializing Bilingual Flashcard Generator...")

    if not github_token_configured():
        print("\nGITHUB_TOKEN is not configured. Add it to .env (see .env.example).")
        return

    template_path = TEMPLATES_DIR / "flashcard_generator.json"
    if not template_path.is_file():
        print(f"Missing template: {template_path}")
        return

    agent = get_or_create_agent()
    user_data = collect_user_input()
    print("\nGenerating flashcards (this may take a moment)...")

    outcome = await run_flashcard_generation(user_data, agent)
    if not outcome.get("ok"):
        print(f"\n{outcome.get('error', 'Generation failed.')}")
        dbg = outcome.get("debug_output")
        if dbg:
            print("\n--- Model output (for debugging) ---\n")
            print(dbg)
        return

    if outcome.get("requested_count") != outcome.get("actual_count"):
        print(
            f"Note: requested {outcome['requested_count']} cards, "
            f"got {outcome['actual_count']}."
        )

    print("\nDone.")
    print(f"  • Cards: {outcome['cards_count']}")
    print(f"  • Markdown: {outcome['md_name']}")
    print(f"  • Interactive: {outcome['html_name']} (open this file in your browser)")


def main_web(host: str, port: int) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    app = create_web_app()
    print(f"\nBilingual Flashcard Generator — open http://{host}:{port}/ in your browser\n")
    app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bilingual flashcard generator (web UI or CLI).")
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Use terminal prompts instead of the web UI.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind address for the web server.")
    parser.add_argument("--port", type=int, default=5000, help="Port for the web server.")
    args = parser.parse_args()
    if args.cli:
        asyncio.run(main_cli())
    else:
        main_web(args.host, args.port)
