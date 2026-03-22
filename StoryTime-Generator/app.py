"""
Children's Story Time Generator - Main Application

A multi-agent AI system that generates engaging, age-appropriate children's stories
using LangChain and LangGraph with GitHub Models API.

Agents:
- Story Planner: Creates story outlines
- Story Writer: Writes narrative based on outline
- Story Validator: Reviews and approves/requests revision
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
planner_agent = None
writer_agent = None
validator_agent = None

# Validate GitHub Token
if not GITHUB_TOKEN or GITHUB_TOKEN == "your_github_token_here":
    print("⚠️  Warning: GITHUB_TOKEN not configured in .env file")
    print("Please set your GitHub token to enable API calls")


# ============================================================================
# State Management
# ============================================================================

class State(TypedDict):
    """State container for story generation workflow"""
    messages: Annotated[list, add_messages]
    story_outline: str
    story_narrative: str
    validation_status: str
    revision_count: int


# ============================================================================
# Agent Node Functions
# ============================================================================

async def planner_node(state: State) -> Command[Literal["writer", "__end__"]]:
    """
    Story Planner Agent - Creates story outline from user input
    
    Expected to generate:
    - Story title
    - Target age group
    - Main characters
    - Plot outline
    - Learning lesson/moral
    - Tone recommendations
    """
    print("\n📋 [PLANNER] Processing story outline request...")
    
    if not planner_agent:
        print("   ⚠️  Planner agent not initialized")
        return Command(update={"messages": state["messages"]}, goto="writer")
    
    # Call planner agent
    response = await planner_agent.ainvoke({"messages": state["messages"]})
    
    # Extract and display planner output
    planner_response = response["messages"][-1]
    print(f"\n   ✓ Story outline created")
    print(f"   Preview: {planner_response.content[:100]}...")
    
    # Route to writer with outline in state
    return Command(
        update={
            "messages": response["messages"],
            "story_outline": planner_response.content
        },
        goto="writer"
    )


async def writer_node(state: State) -> Command[Literal["validator", "__end__"]]:
    """
    Story Writer Agent - Generates narrative based on outline
    
    Expected to generate:
    - Age-appropriate language
    - Engaging dialogue
    - Sensory descriptions
    - Complete story arc
    """
    print("\n✍️  [WRITER] Generating story narrative...")
    
    if not writer_agent:
        print("   ⚠️  Writer agent not initialized")
        return Command(update={"messages": state["messages"]}, goto="validator")
    
    if not state["story_outline"]:
        print("   ⚠️  No outline available")
        return Command(update={"messages": state["messages"]}, goto="validator")
    
    # Prepare context by adding the outline to the prompt
    print(f"   Using outline: {state['story_outline'][:50]}...")
    
    # Call writer agent
    response = await writer_agent.ainvoke({"messages": state["messages"]})
    
    # Extract and display writer output
    writer_response = response["messages"][-1]
    print(f"\n   ✓ Story narrative generated")
    print(f"   Story length: {len(writer_response.content)} characters")
    
    # Route to validator with narrative in state
    return Command(
        update={
            "messages": response["messages"],
            "story_narrative": writer_response.content
        },
        goto="validator"
    )


async def validator_node(state: State) -> Command[Literal["writer", "__end__"]]:
    """
    Story Validator Agent - Reviews story for quality and age-appropriateness
    
    Returns:
    - APPROVED: Story is ready → route to END
    - REVISION NEEDED: Route back to writer with feedback
    """
    print("\n✅ [VALIDATOR] Reviewing story...")
    
    if not validator_agent:
        print("   ⚠️  Validator agent not initialized")
        return Command(update={"messages": state["messages"]}, goto="__end__")
    
    if not state["story_narrative"]:
        print("   ⚠️  No story to validate")
        return Command(update={"messages": state["messages"]}, goto="__end__")
    
    print(f"   Reviewing story: {state['story_narrative'][:50]}...")
    
    # Track revision attempts to prevent infinite loops
    if state["revision_count"] >= 2:
        print("   ⚠️  Max revision attempts reached, approving story")
        state["validation_status"] = "APPROVED (Max revisions)"
        state["messages"] = state["messages"] + [
            AIMessage(content="Story approved after revision attempts")
        ]
        return Command(
            update={"messages": state["messages"], "revision_count": state["revision_count"]},
            goto="__end__"
        )
    
    # Call validator agent
    response = await validator_agent.ainvoke({"messages": state["messages"]})
    
    # Extract validator feedback
    validator_response = response["messages"][-1]
    feedback = validator_response.content
    
    print(f"\n   Validator Feedback:")
    print(f"   {feedback[:200]}...")
    
    # Check if story is approved or needs revision
    if "APPROVED" in feedback.upper():
        print("\n   ✓ Story APPROVED")
        print("   → Routing to END")
        return Command(
            update={
                "messages": response["messages"],
                "validation_status": "APPROVED"
            },
            goto="__end__"
        )
    else:
        # Request revision - loop back to writer
        new_revision_count = state["revision_count"] + 1
        print(f"\n   ⚠️  Story needs revision (Attempt {new_revision_count})")
        print("   → Routing back to WRITER")
        return Command(
            update={
                "messages": response["messages"],
                "revision_count": new_revision_count,
                "validation_status": f"REVISION NEEDED (Attempt {new_revision_count})"
            },
            goto="writer"
        )


# ============================================================================
# Workflow Setup
# ============================================================================

def build_workflow():
    """Construct the StateGraph for story generation workflow"""
    
    print("\n🔨 Building workflow graph...")
    
    # Create the workflow graph
    workflow = StateGraph(State)
    
    # Add nodes
    workflow.add_node("planner", planner_node)
    workflow.add_node("writer", writer_node)
    workflow.add_node("validator", validator_node)
    
    # Set entry point
    workflow.add_edge(START, "planner")
    
    print("   ✓ Workflow graph created")
    print("   ✓ Nodes: [planner → writer → validator ⇄ (revision loop) → END]")
    
    # Compile the graph
    graph = workflow.compile()
    return graph


# ============================================================================
# Output Management
# ============================================================================

def save_story(title: str, story: str, metadata: dict) -> Path:
    """Save generated story to markdown file"""
    
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    # Create filename from title
    filename = f"story_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    filepath = OUTPUT_DIR / filename
    
    # Format story with metadata
    content = f"""# {title}

## Metadata
- **Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Age Group**: {metadata.get('age_group', 'Not specified')}
- **Theme**: {metadata.get('theme', 'Not specified')}
- **Lesson**: {metadata.get('lesson', 'Not specified')}

## Story

{story}
"""
    
    # Save with UTF-8 encoding to preserve special characters
    filepath.write_text(content, encoding='utf-8')
    print(f"\n💾 Story saved to: {filepath}")
    return filepath


# ============================================================================
# Main Application
# ============================================================================

def collect_user_input() -> dict:
    """Collect story requirements from user"""
    
    print("\n" + "=" * 60)
    print("🎨 Children's Story Time Generator")
    print("=" * 60)
    
    print("\nLet's create a story! Please provide the following information:\n")
    
    theme = input("📚 Story Theme/Topic: ").strip()
    if not theme:
        theme = "A magical adventure"
    
    print("\nAge Group:")
    print("  1) 3-5 years (Preschool)")
    print("  2) 6-8 years (Early Elementary)")
    print("  3) 9-12 years (Middle Elementary)")
    
    age_choice = input("Select age group (1-3) [default: 1]: ").strip() or "1"
    age_map = {
        "1": "3-5 years",
        "2": "6-8 years",
        "3": "9-12 years"
    }
    age_group = age_map.get(age_choice, "3-5 years")
    
    lesson = input("\n💡 Learning Lesson/Moral (optional, press Enter to skip): ").strip()
    
    length = input("\n📏 Story Length (short/medium/long) [default: medium]: ").strip().lower() or "medium"
    
    return {
        "theme": theme,
        "age_group": age_group,
        "lesson": lesson or "Not specified",
        "length": length,
        "user_input": f"Please create a {length} children's story about: {theme}. Target age group: {age_group}. Learning lesson: {lesson or 'Not specified'}"
    }


async def main():
    """Main application entry point"""
    global planner_agent, writer_agent, validator_agent
    
    # Ensure UTF-8 encoding for console output on Windows
    try:
        import sys
        if sys.platform == 'win32':
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except Exception:
        pass
    
    print("\n🚀 Initializing Story Time Generator...")
    
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
        with open(TEMPLATES_DIR / "planner.json", "r") as f:
            planner_data = json.load(f)
            planner_prompt = planner_data.get("template", "You are a story planner.")
        
        with open(TEMPLATES_DIR / "writer.json", "r") as f:
            writer_data = json.load(f)
            writer_prompt = writer_data.get("template", "You are a story writer.")
        
        with open(TEMPLATES_DIR / "validator.json", "r") as f:
            validator_data = json.load(f)
            validator_prompt = validator_data.get("template", "You are a story validator.")
        
        print("   ✓ Prompts loaded")
    except FileNotFoundError as e:
        print(f"   ⚠️  Error loading templates: {e}")
        print("   Make sure template files exist in templates/ directory")
        return
    
    # Create agents
    print("   Creating agents...")
    planner_agent = create_agent(llm, tools=[], system_prompt=planner_prompt)
    writer_agent = create_agent(llm, tools=[], system_prompt=writer_prompt)
    validator_agent = create_agent(llm, tools=[], system_prompt=validator_prompt)
    print("   ✓ All agents created")
    
    # Collect user input
    user_data = collect_user_input()
    
    # Initialize state
    initial_state = {
        "messages": [HumanMessage(content=user_data["user_input"])],
        "story_outline": "",
        "story_narrative": "",
        "validation_status": "",
        "revision_count": 0,
    }
    
    # Build and run workflow
    print("\n" + "=" * 60)
    print("🎬 Starting Story Generation Workflow")
    print("=" * 60)
    
    workflow = build_workflow()
    
    print("\n🔄 Running workflow...\n")
    final_state = await workflow.ainvoke(initial_state)
    
    # Display results
    print("\n" + "=" * 60)
    print("📖 Story Generation Complete!")
    print("=" * 60)
    
    print(f"\n✓ Outline:\n{final_state['story_outline'][:300]}...")
    print(f"\n✓ Narrative:\n{final_state['story_narrative'][:500]}...")
    print(f"\n✓ Status: {final_state['validation_status']}")
    
    # Save story
    metadata = {
        "age_group": user_data["age_group"],
        "theme": user_data["theme"],
        "lesson": user_data["lesson"]
    }
    save_story(
        title=user_data["theme"],
        story=final_state["story_narrative"],
        metadata=metadata
    )

    # output full state into a markdown file for debugging
    debug_filepath = OUTPUT_DIR / f"debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    debug_content = f"""# Debug Output

    {json.dumps(final_state, indent=4)}

    """
    with open(debug_filepath, "w") as f:
        f.write(debug_content)
    print(f"\n✅ Debug output saved to {debug_filepath}")

    # output the final story into a markdown file
    story_filepath = OUTPUT_DIR / f"story_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    story_content = f"""# {user_data['theme']}
## Age Group: {user_data['age_group']}
## Learning Lesson: {user_data['lesson']}
{final_state['story_narrative']}
    """
    with open(story_filepath, "w") as f:
        f.write(story_content)

    print(f"\n✅ Story saved to {story_filepath}")

    print("\n✅ Story generation workflow completed!")


if __name__ == "__main__":
    asyncio.run(main())
