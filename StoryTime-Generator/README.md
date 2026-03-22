# Children's Story Time Generator

A multi-agent AI system that generates engaging, age-appropriate children's stories using LangChain and LangGraph.

## Project Overview

This application uses three specialized AI agents to collaboratively create children's stories:

- **Story Planner Agent** → Creates story outlines based on theme, age group, and learning objectives
- **Story Writer Agent** → Writes engaging narratives following the planner's outline
- **Story Validator Agent** → Reviews stories for quality, age-appropriateness, and accepts/rejects for revision

## Features

- **Age-Appropriate Content**: Generates stories tailored for age groups 3-5, 6-8, and 9-12
- **Multi-Agent Workflow**: Orchestrates specialized agents using LangGraph for collaborative story generation
- **Revision Loop**: Automatic revision handling when validator requests improvements
- **Markdown Output**: Stories saved as formatted markdown files with metadata

## Installation

### Prerequisites

- Python 3.10+
- GitHub Account with GitHub Models API access
- GitHub Token for authentication

### Setup

1. Clone the repository and navigate to the project directory:
   ```bash
   cd StoryTime-Generator
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   ```

3. Activate the virtual environment:
   - On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```
   - On Windows:
     ```bash
     venv\Scripts\activate
     ```

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Configure environment variables:
   - Copy `.env.example` to `.env`
   - Add your GitHub token: `GITHUB_TOKEN=your_token_here`

## Usage

Run the application:
```bash
python app.py
```

You'll be prompted to provide:
- **Story Theme**: The topic or concept for your story
- **Age Group**: Target age range (3-5, 6-8, or 9-12)
- **Learning Lesson** (optional): A specific moral or lesson to include
- **Story Length** (optional): Preference for story length

The application will generate a story and save it to the `output/` directory.

## Project Structure

```
StoryTime-Generator/
├── app.py                          ← Main orchestration file
├── requirements.txt                ← Python dependencies
├── .env                           ← Environment variables (GITHUB_TOKEN)
├── .env.example                   ← Template for .env
├── .gitignore                     ← Git ignore rules
├── README.md                      ← This file
├── IMPLEMENTATION_CHECKLIST.md    ← Implementation progress tracker
├── Dev-Tools/                     ← Development utilities
├── templates/
│   ├── planner.json              ← Story outline generation prompt
│   ├── writer.json               ← Story narrative writing prompt
│   └── validator.json            ← Story quality validation prompt
└── output/                        ← Generated stories
    ├── story_*.md
    └── ...
```

## API Configuration

- **API Endpoint**: https://models.github.ai/inference
- **Model**: openai/gpt-4o-mini
- **Authentication**: GitHub Token

## Development

### Debug Mode

Run with debug output:
```bash
python -u app.py
```

### Testing

See `IMPLEMENTATION_CHECKLIST.md` for testing procedures and sample inputs.

## Key Classes & Functions

- `State` - TypedDict for message state management
- `planner_node()` - Creates story outlines
- `writer_node()` - Writes story narratives
- `validator_node()` - Reviews and validates stories
- `StateGraph` - Orchestrates the multi-agent workflow

## Resources

- [LangChain Documentation](https://python.langchain.com/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [GitHub Models](https://models.github.ai/)

## Example

For an example multi-agent implementation, see the reference project in:
`../EXAMPLE/CodeYouAIClass2026Lab7/python-langchain/`

## License

This project is part of the Code You AI Class 2026.
