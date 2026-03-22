# Children's Story Time Generator - Implementation Checklist

## Project Overview
Build a multi-agent AI system that generates engaging, age-appropriate children's stories using:
- **Story Planner Agent** → Creates story outline
- **Story Writer Agent** → Writes the narrative
- **Story Validator Agent** → Reviews and approves/requests revision

---

## Phase 1: Foundation & Setup

### Step 1: Create Project Structure
- [ ] Create project directory structure for `StoryTime-Generator/`
- [ ] Create `templates/` folder for agent prompts
- [ ] Create `output/` folder for generated stories
- [ ] Create `requirements.txt` with dependencies
- [ ] Create `README.md` with project documentation

**Dependencies to include:**
```
langchain>=0.3.0
langchain-openai>=0.2.0
langchain-community>=0.3.0
langgraph>=0.2.0
python-dotenv>=1.0.0
langchain-mcp-adapters>=0.1.0
```

### Step 2: Set Up Environment & Authentication
- [ ] Create `.env` file with `GITHUB_TOKEN`
- [ ] Create `.env.example` as template
- [ ] Create `.gitignore` (exclude `.env` and `__pycache__/`)
- [ ] Configure GitHub Models API connection
- [ ] Test API connectivity with a simple script

### Step 3: Initialize Python Project
- [ ] Create virtual environment (`python -m venv venv`)
- [ ] Activate virtual environment
- [ ] Install dependencies from `requirements.txt`
- [ ] Create `app.py` entry point
- [ ] Verify imports work correctly

---

## Phase 2: Agent Prompt Engineering

### Step 4: Create Story Planner Prompt
- [ ] Create `templates/planner.json`
- [ ] Define planner agent role and responsibilities
- [ ] Include instructions for:
  - [ ] Understanding child age group (3-5, 6-8, 9-12)
  - [ ] Creating story outlines with characters and plot
  - [ ] Defining pacing and story structure
  - [ ] Identifying learning objectives/moral
- [ ] Add example inputs and expected outputs
- [ ] Test prompt with sample user input

**Planner should output:**
- Story title
- Target age group
- Main characters (with descriptions)
- Plot outline (beginning, middle, end)
- Learning lesson/moral
- Tone/style recommendations for writer

### Step 5: Create Story Writer Prompt
- [ ] Create `templates/writer.json`
- [ ] Define writer agent role and responsibilities
- [ ] Include instructions for:
  - [ ] Age-appropriate language and vocabulary
  - [ ] Dialogue and character voice
  - [ ] Sensory descriptions and engagement
  - [ ] Story pacing and flow
  - [ ] Following the planner's outline
- [ ] Add guidelines for story structure
- [ ] Test prompt with sample outline

**Writer should output:**
- Complete story narrative
- Age-appropriate language
- Engaging dialogue and descriptions
- Clear story arc with beginning-middle-end

### Step 6: Create Story Validator Prompt
- [ ] Create `templates/validator.json`
- [ ] Define validator agent role and responsibilities
- [ ] Include instructions for:
  - [ ] Checking age-appropriateness
  - [ ] Verifying engaging language
  - [ ] Confirming lesson/moral clarity
  - [ ] Story structure and flow
  - [ ] Grammar and clarity
- [ ] Define "REVISION NEEDED" vs "APPROVED" criteria
- [ ] Test prompt with sample stories

**Validator should output:**
- Approval status (APPROVED or REVISION NEEDED)
- Specific feedback if revisions needed
- Recommendations for improvement

---

## Phase 3: Multi-Agent Orchestration

### Step 7: Build State Management
- [ ] Define `State` TypedDict with message field
- [ ] Import necessary modules from LangGraph
- [ ] Set up message aggregation using `add_messages`
- [ ] Implement state passing between agents
- [ ] Test state updates with debug prints

### Step 8: Implement Agent Nodes
- [ ] Create `planner_node()` function
  - [ ] Accept user input (theme, age group, lesson)
  - [ ] Call planner agent with input
  - [ ] Return structured outline
  - [ ] Add debug logging
  
- [ ] Create `writer_node()` function
  - [ ] Accept planner output
  - [ ] Call writer agent with outline
  - [ ] Generate story narrative
  - [ ] Add debug logging
  
- [ ] Create `validator_node()` function
  - [ ] Accept writer output
  - [ ] Call validator agent
  - [ ] Determine approval status
  - [ ] Route back to writer if revision needed
  - [ ] Add debug logging

- [ ] Implement handoff logic between agents
  - [ ] Use `Command` to route between nodes
  - [ ] Handle approval and revision routing
  - [ ] Track conversation history through state

### Step 9: Build Workflow Graph
- [ ] Create `StateGraph` with State definition
- [ ] Add three nodes to graph:
  - [ ] planner_node
  - [ ] writer_node
  - [ ] validator_node
- [ ] Set START point to planner_node
- [ ] Connect nodes with proper transitions:
  - [ ] planner → writer
  - [ ] writer → validator
  - [ ] validator → writer (if revision needed)
  - [ ] validator → END (if approved)
- [ ] Compile graph
- [ ] Test graph structure

---

## Phase 4: User Interface & Input

### Step 10: Create Input Collection
- [ ] Implement user input prompts in `main()` function:
  - [ ] Story theme/topic
  - [ ] Target age group (3-5, 6-8, 9-12)
  - [ ] Optional learning lesson/moral
  - [ ] Optional story length preference
- [ ] Validate user input
- [ ] Prepare input for planner agent
- [ ] Add example prompts

### Step 11: Implement Output Formatting
- [ ] Create output directory structure
- [ ] Implement story saving to markdown file:
  - [ ] Include metadata (age group, theme, date, lesson)
  - [ ] Format story with proper headings and sections
  - [ ] Add character descriptions if available
  - [ ] Save with descriptive filename
- [ ] Display story to user in terminal
- [ ] Optionally save generation logs
- [ ] Add option to save multiple formats (later enhancement)

---

## Phase 5: Testing & Enhancement

### Step 12: Test with Sample Inputs
- [ ] Test Story 1: Simple fairy tale (age 3-5)
  - [ ] Input: "A brave little rabbit"
  - [ ] Verify age-appropriate output
  - [ ] Check story completeness
  
- [ ] Test Story 2: Adventure story (age 6-8)
  - [ ] Input: "A treasure hunt in the forest"
  - [ ] Verify engaging narrative
  - [ ] Check pacing and plot
  
- [ ] Test Story 3: Educational story (age 9-12)
  - [ ] Input: "Learning about space exploration"
  - [ ] Verify learning objective is met
  - [ ] Check vocabulary level
  
- [ ] Test revision loop:
  - [ ] Trigger validator rejection
  - [ ] Verify routing back to writer
  - [ ] Check revision handling
  
- [ ] Save all test outputs to `output/` directory
- [ ] Review generated stories for quality

### Step 13: Refine Prompts Based on Results
- [ ] Analyze generated stories
- [ ] Identify areas for improvement:
  - [ ] Adjust tone for different age groups
  - [ ] Improve story structure/engagement
  - [ ] Enhance vocabulary matching
  - [ ] Refine character development
- [ ] Update prompts in `templates/`
- [ ] Retest with previously failing inputs
- [ ] Document improvements made

### Step 14: Add Advanced Features (Optional)
- [ ] Add support for multiple story genres:
  - [ ] Fairy tales
  - [ ] Adventure stories
  - [ ] Educational stories
  - [ ] Mystery stories
  
- [ ] Add story illustrations concept generation
  - [ ] Generate descriptions for illustrators
  - [ ] Include character appearance details
  
- [ ] Add interactive story branching (advanced)
  - [ ] Generate multiple path options
  - [ ] Create choose-your-own-adventure stories
  
- [ ] Add story series generation
  - [ ] Generate related stories with recurring characters
  - [ ] Build character continuity
  
- [ ] Add HTML/PDF export (later enhancement)
- [ ] Create web UI (future phase)

---

## File Structure (Final)
```
StoryTime-Generator/
├── app.py                          ← Main orchestration file
├── requirements.txt                ← Python dependencies
├── .env                           ← Environment variables (GITHUB_TOKEN)
├── .env.example                   ← Template for .env
├── .gitignore                     ← Git ignore rules
├── README.md                      ← Project documentation
├── IMPLEMENTATION_CHECKLIST.md    ← This file
├── templates/
│   ├── planner.json              ← Story outline generation prompt
│   ├── writer.json               ← Story narrative writing prompt
│   └── validator.json            ← Story quality validation prompt
└── output/                        ← Generated stories (created at runtime)
    ├── story_1.md
    ├── story_2.md
    └── ...
```

---

## Progress Tracking

**Current Phase:** [ ] Phase 1 [ ] Phase 2 [ ] Phase 3 [ ] Phase 4 [ ] Phase 5

**Overall Completion:** _____ %

### Notes & Issues
- [ ] Issue: 
- [ ] Issue: 
- [ ] Issue: 

---

## Quick Reference

### API Configuration
- **API Endpoint:** https://models.github.ai/inference
- **Model:** openai/gpt-4o-mini
- **Auth:** GITHUB_TOKEN environment variable

### Key Classes & Functions
- `State` - Message state container
- `planner_node()` - Creates story outline
- `writer_node()` - Writes story narrative
- `validator_node()` - Reviews story quality
- `StateGraph` - Orchestrates agent workflow

### Common Commands
```bash
# Activate virtual environment
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py

# Run with debug output
python -u app.py
```

---

## Resources
- [LangChain Documentation](https://python.langchain.com/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [GitHub Models](https://models.github.ai/)
- [Example Project Reference](../EXAMPLE/CodeYouAIClass2026Lab7/python-langchain/)

