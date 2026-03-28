"""
Bilingual Flashcard Generator — English ↔ Vietnamese vocabulary with optional visuals.

Uses LangChain + GitHub Models API (same pattern as StoryTime-Generator/app.py).

Ways to incorporate images for young learners (pedagogy + implementation options):

1. **Emoji anchors** — One emoji per word links sound/meaning to a universal symbol (fast, offline,
   works in any Markdown viewer). Good for attention and memory for pre-readers.

2. **Generated illustrations** — Optional Hugging Face text-to-image (see StoryTime-Generator
   test_hf_image.py) gives a consistent “picture side” for print or screen; pair with words on
   the flip side for classic dual-coding.

3. **Picture-first / guess the word** — Show only the image (or emoji) first; child names the
   word in either language before revealing text (can be done with a second HTML or print layout).

4. **Stock / encyclopedia** — Openverse, Wikimedia Commons, or Unsplash APIs could supply
   photos for concrete nouns; needs licensing awareness and stable URLs.

5. **Matching game** — Export JSON and shuffle images vs. word pairs in a small web or paper
   activity (same deck, different layout).

This app implements (1) always and (2) optionally when HF_TOKEN is set and the user chooses it.
"""

import asyncio
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

    print("\nDone.")
    print(f"  • Cards: {len(cards)}")
    print(f"  • File: {path.name}")


if __name__ == "__main__":
    asyncio.run(main())
