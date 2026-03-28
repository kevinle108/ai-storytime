"""
Bilingual Flashcard Generator — English ↔ Vietnamese vocabulary with optional visuals.

Uses LangChain + GitHub Models API (same pattern as StoryTime-Generator/app.py).

Ways to incorporate images for young learners (pedagogy + implementation options):

1. **Emoji anchors** — One emoji per word links sound/meaning to a universal symbol (fast, offline,
   works in any Markdown viewer). Good for attention and memory for pre-readers.

2. **Generated illustrations** — Optional Hugging Face text-to-image (see StoryTime-Generator
   test_hf_image.py) gives a consistent “picture side” for print or screen; pair with words on
   the flip side for classic dual-coding.

3. **Picture-first / guess the word** — `save_flashcards_html` writes a single-page viewer: image
   or emoji first, then **Show words** for English and Vietnamese (keyboard: arrows, Space).

4. **Stock / encyclopedia** — Openverse, Wikimedia Commons, or Unsplash APIs could supply
   photos for concrete nouns; needs licensing awareness and stable URLs.

5. **Matching game** — Export JSON and shuffle images vs. word pairs in a small web or paper
   activity (same deck, different layout).

This app implements (1) always, (2) optionally when HF_TOKEN is set and the user chooses it, and
(3) as `output/flashcards_<run>.html` next to the Markdown export.
"""

import asyncio
import html
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

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
OUTPUT_DIR = Path(__file__).parent / "output"
TEMPLATES_DIR = Path(__file__).parent / "templates"

IMAGE_MODE_EMOJI_ONLY = "0"
IMAGE_MODE_GENERATE = "1"


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
    out.setdefault("emoji", "")
    out.setdefault("image_prompt", "")
    return out


def _hf_image_prompt(card: dict[str, Any]) -> str:
    base = (card.get("image_prompt") or "").strip()
    en = (card.get("english") or "").strip()
    if base:
        return f"{base}. Children's book illustration, simple flat shapes, bright friendly colors, no text, no letters, no watermark."
    return (
        f"Simple cute illustration of {en}. Children's book style, flat colors, no text, no letters."
    )


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
        "Each block is one card: **picture** (emoji and/or generated image), **English**, "
        "**Vietnamese**. For dual-sided printing, flip on the short edge.",
        "",
    ]

    for i, card in enumerate(cards, start=1):
        card = normalize_card(card)
        en = card.get("english", "")
        vi = card.get("vietnamese", "")
        hint = card.get("hint", "")
        emoji = (card.get("emoji") or "").strip()

        lines.append(f"### Card {i}")
        lines.append("")
        if emoji:
            lines.append(f"**Visual:** {emoji}")
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
) -> Path:
    """Picture-first interactive viewer: image or emoji, then reveal English / Vietnamese."""
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
                "emoji": (c.get("emoji") or "").strip() or "🙂",
                "imageUrl": rel,
            }
        )

    data_json = json.dumps(payload, ensure_ascii=False)
    # Avoid closing the HTML script tag if JSON text ever contains </script>
    data_json = data_json.replace("</script>", "<\\/script>")

    safe_title = html.escape(title)
    safe_sub = html.escape(metadata.get("theme", "")) + " · " + html.escape(metadata.get("age_band", ""))

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
    .visual .emoji-fallback {{
      font-size: 6rem;
      line-height: 1;
      user-select: none;
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
  </style>
</head>
<body>
  <header>
    <h1 id="page-title">{safe_title}</h1>
    <p id="page-sub">{safe_sub}</p>
  </header>
  <p class="hint-start">Look at the picture. What is it? Then tap <strong>Show words</strong>.</p>
  <div class="stage" aria-live="polite">
    <div class="visual" id="visual">
      <img id="card-img" alt="" class="hidden" />
      <div id="card-emoji" class="emoji-fallback hidden" aria-hidden="true"></div>
    </div>
    <div class="counter" id="counter"></div>
    <div class="words hidden" id="words-block">
      <div class="en" id="w-en"></div>
      <div class="vi" id="w-vi"></div>
      <div class="hint hidden" id="w-hint"></div>
    </div>
  </div>
  <div class="controls">
    <button type="button" class="secondary" id="btn-prev" aria-label="Previous card">← Back</button>
    <button type="button" id="btn-reveal" aria-expanded="false">Show words</button>
    <button type="button" class="secondary" id="btn-next" aria-label="Next card">Next →</button>
  </div>
  <script type="application/json" id="flashcards-data">{data_json}</script>
  <script>
(function () {{
  const cards = JSON.parse(document.getElementById('flashcards-data').textContent);
  let index = 0;
  let revealed = false;

  const elImg = document.getElementById('card-img');
  const elEmoji = document.getElementById('card-emoji');
  const elWords = document.getElementById('words-block');
  const elHint = document.getElementById('w-hint');
  const elReveal = document.getElementById('btn-reveal');
  const elCounter = document.getElementById('counter');
  const elPrev = document.getElementById('btn-prev');
  const elNext = document.getElementById('btn-next');

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
      elEmoji.classList.add('hidden');
    }} else {{
      elImg.removeAttribute('src');
      elImg.classList.add('hidden');
      elImg.alt = '';
      elEmoji.textContent = c.emoji || '🙂';
      elEmoji.classList.remove('hidden');
    }}
    elPrev.disabled = index <= 0;
    elNext.disabled = index >= cards.length - 1;
  }}

  elReveal.addEventListener('click', function () {{
    setReveal(!revealed);
  }});
  elPrev.addEventListener('click', function () {{
    if (index > 0) {{
      index--;
      revealed = false;
      render();
    }}
  }});
  elNext.addEventListener('click', function () {{
    if (index < cards.length - 1) {{
      index++;
      revealed = false;
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


def collect_user_input() -> dict[str, str]:
    print("\n" + "=" * 60)
    print("Bilingual Flashcard Generator (English ↔ Vietnamese)")
    print("=" * 60)
    print("\nWe'll create simple vocabulary cards for young learners.\n")

    theme = input("Theme or topic (e.g. animals, colors, breakfast): ").strip()
    if not theme:
        theme = "everyday objects around the home"

    count_str = input("How many cards? [default: 12]: ").strip() or "12"
    try:
        count = max(1, min(40, int(count_str)))
    except ValueError:
        count = 12

    print("\nAge band:")
    print("  0) 2–3 years (very few words per card)")
    print("  1) 3–5 years (preschool)")
    print("  2) 6–8 years (early elementary)")
    age_choice = input("Select (0–2) [default: 1]: ").strip() or "1"
    age_map = {
        "0": "2–3 years",
        "1": "3–5 years",
        "2": "6–8 years",
    }
    age_band = age_map.get(age_choice, "3–5 years")

    print("\nImages:")
    print("  0) Emoji only (fast, no Hugging Face)")
    print("  1) Emoji + generate pictures (HF_TOKEN in .env; slower, uses API quota)")
    img_choice = input("Select (0–1) [default: 0]: ").strip() or IMAGE_MODE_EMOJI_ONLY
    image_mode = IMAGE_MODE_GENERATE if img_choice == IMAGE_MODE_GENERATE else IMAGE_MODE_EMOJI_ONLY

    user_message = (
        f"Create exactly {count} bilingual vocabulary flashcards.\n"
        f"Theme/topic: {theme}\n"
        f"Age band: {age_band}\n"
        f"Languages: English and Vietnamese.\n"
        f"Remember: respond with ONLY the JSON array, no other text."
    )

    return {
        "theme": theme,
        "count": str(count),
        "age_band": age_band,
        "user_message": user_message,
        "image_mode": image_mode,
    }


async def main() -> None:
    try:
        if sys.platform == "win32":
            import io

            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
    except Exception:
        pass

    print("\nInitializing Bilingual Flashcard Generator...")

    if not GITHUB_TOKEN or GITHUB_TOKEN == "your_github_token_here":
        print("\nGITHUB_TOKEN is not configured. Add it to .env (see .env.example).")
        return

    template_path = TEMPLATES_DIR / "flashcard_generator.json"
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            prompt_data = json.load(f)
            system_prompt = prompt_data.get("template", "")
    except FileNotFoundError:
        print(f"Missing template: {template_path}")
        return

    llm = ChatOpenAI(
        model=MODEL_NAME,
        temperature=0.55,
        base_url=API_ENDPOINT,
        api_key=GITHUB_TOKEN,
    )
    agent = create_agent(llm, tools=[], system_prompt=system_prompt)

    user_data = collect_user_input()
    print("\nGenerating flashcards (this may take a moment)...")

    response = await agent.ainvoke(
        {"messages": [HumanMessage(content=user_data["user_message"])]}
    )
    last = response["messages"][-1]
    raw_content = last.content if hasattr(last, "content") else str(last)

    try:
        cards_raw = parse_flashcard_json(raw_content)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"\nCould not parse flashcards JSON: {e}")
        print("\n--- Model output (for debugging) ---\n")
        print(raw_content[:4000])
        return

    cards = [normalize_card(c) for c in cards_raw]

    expected = int(user_data["count"])
    if len(cards) != expected:
        print(f"Note: requested {expected} cards, got {len(cards)}.")

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    image_mode = user_data["image_mode"]
    image_rel_paths: list[str | None] | None = None
    image_mode_label = "Emoji only"

    if image_mode == IMAGE_MODE_GENERATE:
        if not HF_TOKEN:
            print("\nHF_TOKEN not set; skipping image generation. Add HF_TOKEN to .env for option 1.")
            image_mode_label = "Emoji only (HF_TOKEN missing)"
        else:
            image_mode_label = f"Emoji + generated images ({HF_IMAGE_MODEL})"
            img_dir = OUTPUT_DIR / f"flashcards_{run_id}_images"
            print("\nGenerating images with Hugging Face (this may take a while)...")
            paths = await asyncio.to_thread(generate_image_files, cards, img_dir)
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
    )

    print("\nDone.")
    print(f"  • Cards: {len(cards)}")
    print(f"  • Markdown: {path.name}")
    print(f"  • Interactive: {path_html.name} (open this file in your browser)")


if __name__ == "__main__":
    asyncio.run(main())
