"""
Bilingual Flashcard Generator — simple English ↔ Vietnamese vocabulary cards for young children.

Uses LangChain + GitHub Models API (same pattern as StoryTime-Generator/app.py).
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
OUTPUT_DIR = Path(__file__).parent / "output"
TEMPLATES_DIR = Path(__file__).parent / "templates"


def parse_flashcard_json(raw: str) -> list[dict[str, Any]]:
    """Extract JSON array from model output (handles optional markdown fences)."""
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if fence:
        text = fence.group(1).strip()
    # Find outermost [...] if model added prose
    if not text.startswith("["):
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and end > start:
            text = text[start : end + 1]
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError("Expected a JSON array of flashcards")
    return data


def save_flashcards(
    title: str,
    cards: list[dict[str, Any]],
    metadata: dict[str, str],
) -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    filename = f"flashcards_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    filepath = OUTPUT_DIR / filename

    lines = [
        f"# {title}",
        "",
        "## Metadata",
        f"- **Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- **Languages**: {metadata.get('languages', 'English — Vietnamese')}",
        f"- **Theme**: {metadata.get('theme', '')}",
        f"- **Age band**: {metadata.get('age_band', '')}",
        f"- **Card count**: {len(cards)}",
        "",
        "---",
        "",
        "## Printable flashcards",
        "",
        "Each block is one card: **English** on one side, **Vietnamese** on the other. "
        "Cut along the dashed line if you print double-sided.",
        "",
    ]

    for i, card in enumerate(cards, start=1):
        en = card.get("english", "")
        vi = card.get("vietnamese", "")
        hint = card.get("hint", "")
        lines.append(f"### Card {i}")
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

    # Compact JSON for reuse in apps
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
        cards = parse_flashcard_json(raw_content)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"\nCould not parse flashcards JSON: {e}")
        print("\n--- Model output (for debugging) ---\n")
        print(raw_content[:4000])
        return

    expected = int(user_data["count"])
    if len(cards) != expected:
        print(f"Note: requested {expected} cards, got {len(cards)}.")

    title = f"Flashcards: {user_data['theme']}"
    metadata = {
        "languages": "English — Vietnamese",
        "theme": user_data["theme"],
        "age_band": user_data["age_band"],
    }
    path = save_flashcards(title, cards, metadata)

    print("\nDone.")
    print(f"  • Cards: {len(cards)}")
    print(f"  • File: {path.name}")


if __name__ == "__main__":
    asyncio.run(main())
