# ScholarForge

Autonomous academic research paper pipeline with verified citations.

## Overview

ScholarForge automates the process of writing academic research papers for AI/ML conferences. It features:

- **Autonomous Literature Search**: Searches arXiv and Semantic Scholar
- **Citation Verification**: 4-layer verification (arXiv ID → CrossRef DOI → DataCite → S2 Title Match)
- **Zero Hallucinated References**: All citations verified against real databases
- **Human-in-the-Loop**: Pauses for human input at key decision points
- **Anti-AI-Writing Enforcement**: Detects and removes AI-writing patterns
- **Multi-Agent Peer Review**: Three reviewers with different perspectives
- **LaTeX Output**: Conference-grade `.tex` files for ICML/ICLR

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd scholarforge

# Install dependencies
pip install -e .
```

## Quick Start

1. **Initialize configuration:**
```bash
scholarforge init
```

2. **Edit `config.yaml`** with your:
   - LLM provider (OpenAI, Anthropic, DeepSeek, Ollama)
   - API key
   - Research topic

3. **Run the pipeline:**
```bash
# Basic run
scholarforge run --topic "Your research topic here"

# With README and code repository (recommended for software papers)
scholarforge run --topic "Your research topic" \
  --readme ./README.md \
  --code-repo ./src

# Auto-approve all gates (no human input)
scholarforge run --topic "Your topic" --auto-approve
```

4. **If paused for human input**, edit `READMEMISSING.md` and resume:
```bash
scholarforge resume --run-id <run-id>

# Or provide repo context during resume if not provided during run
scholarforge resume --run-id <run-id> --readme ./README.md --code-repo ./src
```

## Pipeline Stages

1. **Topic Decomposition** - Break down topic into research questions
2. **Literature Search** - Search arXiv and Semantic Scholar
3. **Knowledge Extraction** - Extract structured info from papers
4. **Citation Verification** - Verify all citations (4-layer)
5. **Gap Analysis** - Identify missing information
6. **Paper Writing** - Generate outline and write sections
7. **Anti-Slop Check** - Detect AI-writing patterns
8. **Peer Review** - Multi-agent review
9. **LaTeX Compilation** - Generate conference-ready output

## Configuration

Example `config.yaml`:

```yaml
project:
  name: "My Research Paper"
  topic: "Efficient fine-tuning methods for LLMs"
  output_dir: "./output"

llm:
  provider: "openai"
  model: "gpt-4o"
  api_key_env: "OPENAI_API_KEY"
  temperature: 0.3

literature:
  max_papers: 30
  relevance_threshold: 0.7

paper:
  target_words: 5500
  conference: "icml2026"  # or "iclr2026"

human_in_the_loop:
  mode: "cli"  # "cli", "file_watch", or "web"
  auto_approve: false
```

## Commands

```bash
# Run full pipeline
scholarforge run --topic "Your topic"

# Run with repository context
scholarforge run --topic "Your topic" --readme ./README.md --code-repo ./src

# Resume paused pipeline
scholarforge resume --run-id <run-id>

# Resume with repository context
scholarforge resume --run-id <run-id> --readme ./README.md --code-repo ./src

# Check pipeline status
scholarforge status --run-id <run-id>

# Initialize config
scholarforge init

# Show help
scholarforge --help
```

## Using README and Code Repository

ScholarForge can incorporate your project's README and source code into the paper generation process. This is especially useful for:

- **Software papers**: Describe your implementation with accurate technical details
- **Method papers**: Extract actual algorithms and approaches from working code
- **Reproducibility**: Ensure paper matches the actual implementation

### How it works

When you provide `--readme` and/or `--code-repo`:

1. **Topic Decomposition**: The LLM analyzes your README to understand what your project does and generates relevant research questions
2. **Paper Writing**: Key code files are included in the context to ensure technical accuracy
3. **Method Section**: The actual implementation informs the methodology description

### Example

```bash
# For a machine learning project
scholarforge run \
  --topic "Efficient Transformer Architecture for Edge Devices" \
  --readme ./README.md \
  --code-repo ./src \
  --code-extensions ".py,.cpp,.h"

# For a JavaScript library
scholarforge run \
  --topic "Novel Approach to Reactive State Management" \
  --readme ./README.md \
  --code-repo ./lib \
  --code-extensions ".js,.ts"
```

### What gets included

- **README**: Full content (first 5000 chars)
- **Code files**: 
  - Files with specified extensions (default: .py, .js, .ts, .java, .cpp, .c, .go, .rs)
  - Excludes: node_modules, venv, .git, build directories
  - Limits: First 50 lines per file, max 50 files total

## Output Structure

```
output/
├── pipeline_state.json
├── scholarforge.log
├── stage-1/          # Research plan
├── stage-2/          # Papers found
├── stage-3/          # Knowledge cards
├── stage-4/          # Verification report
├── stage-5/          # Gap report + READMEMISSING.md
├── stage-6/          # Paper draft
├── stage-7/          # Slop report
├── stage-8/          # Peer reviews
└── stage-9/          # LaTeX output
    ├── paper.tex
    ├── references.bib
    └── paper.pdf
```

## Anti-AI-Writing Enforcement

ScholarForge implements a three-layer defense against AI-writing patterns:

1. **Prevention**: Style guide injected into all writing prompts
2. **Detection**: `SlopDetector` scans for banned vocabulary and patterns
3. **Review**: Peer reviewers explicitly check for AI patterns

Banned patterns include:
- Words: "delve", "tapestry", "vibrant", "pivotal", "crucial", etc.
- Patterns: "Additionally," sentence starters, dangling "-ing" phrases
- Structures: "Challenges and Future Prospects" clichés, Rule of Three overuse

## Citation Verification

The 4-layer verification pipeline:

1. **arXiv ID** - Verify against arXiv API
2. **CrossRef DOI** - Verify against CrossRef (180M+ records)
3. **DataCite DOI** - Verify against DataCite (datasets, software)
4. **S2 Title Match** - Fuzzy match against Semantic Scholar

Unverified citations are optionally removed from the final output.

## License

MIT License
