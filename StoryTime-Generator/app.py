"""
Children's Story Book Generator - Main Application

A multi-agent AI system that generates illustrated children's picture books
using LangChain and LangGraph with GitHub Models API.

Agents:
- Story Generator: Creates rhyming stories with short sentences
- Paginator: Breaks story into 5-10 pages with visual focus notes
- Illustration Briefer: Creates detailed scene descriptions for illustrators
"""

import os
import json
import asyncio
from datetime import datetime
from typing import TypedDict, Annotated, Literal
from pathlib import Path
from dotenv import load_dotenv

# LangGraph and LangChain imports
try:
    from langgraph.graph import StateGraph, START, END
    from langgraph.graph.message import add_messages
    from langgraph.types import Command
    from langchain_core.messages import HumanMessage, AIMessage
    from langchain_openai import ChatOpenAI
    from langchain.agents import create_agent
except ImportError as e:
    print(f"Error: Required packages not installed. Please run: pip install -r requirements.txt")
    print(f"Import error: {e}")
    exit(1)

# Load environment variables
load_dotenv()

# Configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
API_ENDPOINT = os.getenv("API_ENDPOINT", "https://models.github.ai/inference")
MODEL_NAME = os.getenv("MODEL_NAME", "openai/gpt-4o-mini")
OUTPUT_DIR = Path(__file__).parent / "output"
TEMPLATES_DIR = Path(__file__).parent / "templates"

# Global variables for agents (will be set in main)
story_generator_agent = None
paginator_agent = None
illustration_briefer_agent = None

# Validate GitHub Token
if not GITHUB_TOKEN or GITHUB_TOKEN == "your_github_token_here":
    print("⚠️  Warning: GITHUB_TOKEN not configured in .env file")
    print("Please set your GitHub token to enable API calls")


# ============================================================================
# State Management
# ============================================================================

class State(TypedDict):
    """State container for story book generation workflow"""
    messages: Annotated[list, add_messages]
    story_text: str
    pages: list  # List of dicts with page_number, story_text, visual_focus
    illustration_briefs: list  # List of dicts with page_number and brief


# ============================================================================
# Agent Node Functions
# ============================================================================

# ============================================================================
# Agent Node Functions
# ============================================================================

async def story_generator_node(state: State) -> Command[Literal["paginator", "__end__"]]:
    """
    Story Generator Agent - Creates rhyming story with short sentences
    
    Expected to generate:
    - Story 300-400 words
    - Simple sentences (3-8 words)
    - AABB rhyme scheme
    - Age-appropriate content
    - Clear beginning-middle-end structure
    """
    print("\n📖 [STORY GENERATOR] Creating rhyming story...")
    
    if not story_generator_agent:
        print("   ⚠️  Story generator agent not initialized")
        return Command(update={"messages": state["messages"]}, goto="__end__")
    
    # Call story generator agent
    response = await story_generator_agent.ainvoke({"messages": state["messages"]})
    
    # Extract and display generator output
    generator_response = response["messages"][-1]
    print(f"\n   ✓ Story generated")
    print(f"   Story length: {len(generator_response.content)} characters")
    print(f"   Preview: {generator_response.content[:100]}...")
    
    # Route to paginator with story in state
    return Command(
        update={
            "messages": response["messages"],
            "story_text": generator_response.content
        },
        goto="paginator"
    )


async def paginator_node(state: State) -> Command[Literal["illustration_briefer", "__end__"]]:
    """
    Paginator Agent - Breaks story into 5-10 pages with visual notes
    
    Expected to generate:
    - JSON array of pages
    - Each page: page_number, story_text, visual_focus
    - Logical scene breaks
    - Balanced page lengths
    """
    print("\n📄 [PAGINATOR] Breaking story into pages...")
    
    if not paginator_agent:
        print("   ⚠️  Paginator agent not initialized")
        return Command(update={"messages": state["messages"]}, goto="illustration_briefer")
    
    if not state["story_text"]:
        print("   ⚠️  No story available")
        return Command(update={"messages": state["messages"]}, goto="illustration_briefer")
    
    # Add story context to the messages
    messages_with_story = state["messages"] + [
        HumanMessage(content=f"Here is the story to paginate:\n\n{state['story_text']}")
    ]
    
    print(f"   Paginating story...")
    
    # Call paginator agent
    response = await paginator_agent.ainvoke({"messages": messages_with_story})
    
    # Extract paginator output
    paginator_response = response["messages"][-1]
    
    # Parse JSON response
    try:
        import json
        pages = json.loads(paginator_response.content)
        print(f"\n   ✓ Story paginated into {len(pages)} pages")
        for page in pages:
            print(f"   • Page {page['page_number']}: {len(page['story_text'])} chars - Focus: {page['visual_focus'][:40]}...")
    except json.JSONDecodeError:
        print(f"   ⚠️  Failed to parse page JSON, attempting recovery...")
        pages = []
    
    # Route to illustration briefer with pages in state
    return Command(
        update={
            "messages": response["messages"],
            "pages": pages
        },
        goto="illustration_briefer"
    )


async def illustration_briefer_node(state: State) -> Command[Literal["__end__"]]:
    """
    Illustration Briefer Agent - Creates scene descriptions for each page
    
    Expected to generate for each page:
    - [SETTING] description
    - [CHARACTERS] positioning and expressions
    - [KEY ELEMENTS] visual items
    - [COLOR PALETTE] suggested colors
    - [STYLE] artistic recommendations
    """
    print("\n🎨 [ILLUSTRATION BRIEFER] Creating illustration briefs...")
    
    if not illustration_briefer_agent:
        print("   ⚠️  Illustration briefer agent not initialized")
        return Command(update={"messages": state["messages"]}, goto="__end__")
    
    if not state["pages"]:
        print("   ⚠️  No pages available")
        return Command(update={"messages": state["messages"]}, goto="__end__")
    
    print(f"   Creating briefs for {len(state['pages'])} pages...")
    
    illustration_briefs = []
    
    # Generate brief for each page
    for page in state["pages"]:
        page_num = page.get("page_number", "?")
        story_text = page.get("story_text", "")
        visual_focus = page.get("visual_focus", "")
        
        # Prepare context for briefer
        brief_prompt = f"Story text: {story_text}\n\nVisual focus: {visual_focus}"
        messages_for_brief = [HumanMessage(content=brief_prompt)]
        
        # Generate brief
        brief_response = await illustration_briefer_agent.ainvoke({"messages": messages_for_brief})
        brief_text = brief_response["messages"][-1].content
        
        illustration_briefs.append({
            "page_number": page_num,
            "brief": brief_text
        })
        
        print(f"   ✓ Brief created for page {page_num}")
    
    print(f"\n   ✓ All {len(illustration_briefs)} illustration briefs generated")
    
    # Route to END
    return Command(
        update={
            "messages": state["messages"],
            "illustration_briefs": illustration_briefs
        },
        goto="__end__"
    )


# ============================================================================
# Workflow Setup
# ============================================================================

def build_workflow():
    """Construct the StateGraph for story book generation workflow"""
    
    print("\n🔨 Building workflow graph...")
    
    # Create the workflow graph
    workflow = StateGraph(State)
    
    # Add nodes
    workflow.add_node("story_generator", story_generator_node)
    workflow.add_node("paginator", paginator_node)
    workflow.add_node("illustration_briefer", illustration_briefer_node)
    
    # Set entry point
    workflow.add_edge(START, "story_generator")
    
    print("   ✓ Workflow graph created")
    print("   ✓ Nodes: [story_generator → paginator → illustration_briefer → END]")
    
    # Compile the graph
    graph = workflow.compile()
    return graph


# ============================================================================
# Output Management
# ============================================================================

def save_story(title: str, story_data: dict, metadata: dict) -> Path:
    """Save generated story book with pages and illustration briefs"""
    
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    # Create filename from title
    filename = f"book_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    filepath = OUTPUT_DIR / filename
    
    # Extract data
    story_text = story_data.get("story_text", "")
    pages = story_data.get("pages", [])
    illustration_briefs = story_data.get("illustration_briefs", [])
    
    # Build content
    content = f"""# {title}

## Metadata
- **Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Target Age Group**: {metadata.get('age_group', 'Not specified')}
- **Theme**: {metadata.get('theme', 'Not specified')}
- **Total Pages**: {len(pages)}

## Full Story

{story_text}

---

## Pages & Illustrations

"""
    
    # Add each page with its illustration brief
    for page in pages:
        page_num = page.get("page_number", "?")
        page_text = page.get("story_text", "")
        
        content += f"\n### Page {page_num}\n\n**Story Text:**\n\n{page_text}\n\n"
        
        # Find corresponding illustration brief
        brief_data = next((b for b in illustration_briefs if b.get("page_number") == page_num), None)
        if brief_data:
            content += f"**Illustration Brief:**\n\n{brief_data['brief']}\n\n"
        
        content += "---\n"
    
    # Save with UTF-8 encoding
    filepath.write_text(content, encoding='utf-8')
    print(f"\n💾 Story book saved to: {filepath}")
    return filepath


# ============================================================================
# Main Application
# ============================================================================

def collect_user_input() -> dict:
    """Collect story requirements from user"""
    
    print("\n" + "=" * 60)
    print("📚 Children's Story Book Generator")
    print("=" * 60)
    
    print("\nLet's create an illustrated children's story book!")
    print("(We'll generate a rhyming story, break it into pages,")
    print("and create illustration briefs for each page.)\n")
    
    theme = input("📖 Story Theme/Topic: ").strip()
    if not theme:
        theme = "A magical adventure"
    
    print("\nTarget Age Group:")
    print("  0) Under 3 years (Toddler/Infant)")
    print("  1) 3-5 years (Preschool)")
    print("  2) 6-8 years (Early Elementary)")
    print("  3) 9-12 years (Middle Elementary)")
    
    age_choice = input("Select age group (0-3) [default: 0]: ").strip() or "0"
    age_map = {
        "0": "Under 3 years",
        "1": "3-5 years",
        "2": "6-8 years",
        "3": "9-12 years"
    }
    age_group = age_map.get(age_choice, "3-5 years")
    
    # Create the user input prompt for story generation
    user_input = f"Please create a children's picture book story about: {theme}. Target age group: {age_group}. The story should have simple sentences with rhyming patterns and be suitable for illustration."
    
    return {
        "theme": theme,
        "age_group": age_group,
        "user_input": user_input
    }


async def main():
    """Main application entry point"""
    global story_generator_agent, paginator_agent, illustration_briefer_agent
    
    # Ensure UTF-8 encoding for console output on Windows
    try:
        import sys
        if sys.platform == 'win32':
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except Exception:
        pass
    
    print("\n🚀 Initializing Story Book Generator...")
    
    # Check configuration
    if not GITHUB_TOKEN or GITHUB_TOKEN == "your_github_token_here":
        print("\n⚠️  GITHUB_TOKEN is not configured properly")
        print("Setup instructions:")
        print("1. Edit .env file")
        print("2. Add your GitHub token from https://github.com/settings/tokens")
        print("\nContinuing will fail without proper authentication.\n")
        return
    
    # Initialize LLM
    print("   Initializing ChatOpenAI with GitHub Models API...")
    llm = ChatOpenAI(
        model=MODEL_NAME,
        temperature=0.7,
        base_url=API_ENDPOINT,
        api_key=GITHUB_TOKEN
    )
    print("   ✓ LLM initialized")
    
    # Load prompts from templates
    print("   Loading agent prompts...")
    try:
        with open(TEMPLATES_DIR / "story_generator.json", "r") as f:
            generator_data = json.load(f)
            generator_prompt = generator_data.get("template", "You are a story generator.")
        
        with open(TEMPLATES_DIR / "paginator.json", "r") as f:
            paginator_data = json.load(f)
            paginator_prompt = paginator_data.get("template", "You are a paginator.")
        
        with open(TEMPLATES_DIR / "illustration_briefer.json", "r") as f:
            briefer_data = json.load(f)
            briefer_prompt = briefer_data.get("template", "You are an illustration briefer.")
        
        print("   ✓ Prompts loaded")
    except FileNotFoundError as e:
        print(f"   ⚠️  Error loading templates: {e}")
        print("   Make sure template files exist in templates/ directory")
        return
    
    # Create agents
    print("   Creating agents...")
    story_generator_agent = create_agent(llm, tools=[], system_prompt=generator_prompt)
    paginator_agent = create_agent(llm, tools=[], system_prompt=paginator_prompt)
    illustration_briefer_agent = create_agent(llm, tools=[], system_prompt=briefer_prompt)
    print("   ✓ All agents created")
    
    # Collect user input
    user_data = collect_user_input()
    
    # Initialize state
    initial_state = {
        "messages": [HumanMessage(content=user_data["user_input"])],
        "story_text": "",
        "pages": [],
        "illustration_briefs": [],
    }
    
    # Build and run workflow
    print("\n" + "=" * 60)
    print("🎬 Starting Story Book Generation Workflow")
    print("=" * 60)
    
    graph = build_workflow()
    
    # Run the workflow
    result = await graph.ainvoke(initial_state)
    
    print("\n" + "=" * 60)
    print("✨ Story Book Generation Complete!")
    print("=" * 60)
    
    # Save the generated story book
    metadata = {
        "age_group": user_data["age_group"],
        "theme": user_data["theme"],
    }
    
    title = f"{user_data['theme'].title()} - A Picture Book"
    story_file = save_story(title, result, metadata)
    
    print("\n📊 Generation Summary:")
    print(f"   • Theme: {user_data['theme']}")
    print(f"   • Target Age: {user_data['age_group']}")
    print(f"   • Story Pages: {len(result.get('pages', []))}")
    print(f"   • Illustration Briefs: {len(result.get('illustration_briefs', []))}")
    print(f"   • Output File: {story_file.name}")
    
    print("\n✅ All done! Your illustrated story book is ready.")


if __name__ == "__main__":
    asyncio.run(main())
