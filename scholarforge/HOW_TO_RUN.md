# ScholarForge — How to Run (Complete Guide)

Autonomous academic paper writing pipeline. Give it a research topic + your code repo,
and it produces a conference-ready LaTeX paper with verified citations.

---

## Before you start — choose your approach

**At the beginning of every new paper, decide which mode to use:**

| | Option A: ScholarForge + API key | Option B: Claude Code (no API key) |
|---|---|---|
| **How it works** | Standalone Python pipeline calls Anthropic API directly | Claude Code (the CLI) does all the work step by step |
| **API key needed** | Yes — separate Anthropic API key in `.env` | No — covered by your Claude Code subscription |
| **Control** | Runs autonomously end-to-end | You stay in the loop at every step |
| **Best for** | Running unattended, walk away | More control, iterating section by section |
| **Cost** | ~$0.50–$2 per paper (Haiku model) | No extra cost |

### If you choose Option B (Claude Code):
Open Claude Code and say:
> "I want to write a paper about [topic]. My README is at [path] and my code is at [path]. Let's start from the beginning."

Claude Code will do the literature search, write each section, generate LaTeX, and ask you for real results before writing the Experiments section — no API key, no `.env` file needed.

### If you choose Option A (ScholarForge + API key):
Continue with the steps below.

---

## Prerequisites (Option A only)

- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com) (Claude Haiku is used by default — cheap)
- Git

---

## Step 1 — Install

```bash
git clone https://github.com/mittalutkarsh/Paper_Writing_Code.git
cd Paper_Writing_Code/scholarforge
python3 -m pip install -e .
```

Verify installation:
```bash
/Users/<your-username>/Library/Python/3.11/bin/scholarforge --help
# Or if scholarforge is on your PATH:
scholarforge --help
```

---

## Step 2 — Set up your API key

```bash
cd Paper_Writing_Code/scholarforge
echo "ANTHROPIC_API_KEY=sk-ant-your-key-here" > .env
```

> **Security:** `.env` is in `.gitignore` and will never be pushed to GitHub.
> Disable or delete your key at [console.anthropic.com](https://console.anthropic.com)
> when not in use to avoid unexpected charges.

To load the key into your shell session before running any command:
```bash
set -a && source .env && set +a
```

---

## Step 3 — Configure your topic

Edit `config.yaml`:
```bash
nano config.yaml
```

Change these two fields:
```yaml
project:
  name: "Your Paper Title"
  topic: "Your research topic — be specific"
```

Everything else (LLM provider, conference format, word count) can stay as-is for a first run.

**Default settings:**
- Model: `claude-haiku-4-5-20251001` (fast, cheap)
- Conference: `icml2026`
- Target length: 5,500 words
- Citations: up to 30 papers from arXiv + Semantic Scholar

---

## Step 4 — Run the pipeline

```bash
cd Paper_Writing_Code/scholarforge
set -a && source .env && set +a

/Users/<your-username>/Library/Python/3.11/bin/scholarforge run \
  --topic "Your research topic here" \
  --readme /path/to/your/project/README.md \
  --code-repo /path/to/your/project/
```

- `--readme` and `--code-repo` are optional but strongly recommended.
  They give the LLM your actual implementation details, making the
  Method section technically accurate.
- The run ID will be printed (e.g. `sf-20260323-163117`). Save it.

---

## Step 5 — Handle the 3 human-review gates

The pipeline pauses at 3 checkpoints. Each time, run the **resume command**:

```bash
set -a && source .env && set +a

/Users/<your-username>/Library/Python/3.11/bin/scholarforge resume \
  --run-id sf-XXXXXXXX-XXXXXX \
  --readme /path/to/your/project/README.md \
  --code-repo /path/to/your/project/
```

### Gate 1: `literature_review` (after Stage 4)

The pipeline found papers and verified their citations. Check what was found:
```bash
cat output/stage-2/result.json           # papers discovered
cat output/stage-4/verification_report.json  # which citations are verified
```
If the papers look relevant, just resume. If not, you can adjust `config.yaml`
(`literature.max_papers`, `arxiv_categories`) and start fresh.

---

### Gate 2: `gap_analysis` (after Stage 5) ← MOST IMPORTANT

**This is where you provide your real experimental results.**

Open `output/stage-5/READMEMISSING.md` and fill in your answers:

```bash
nano output/stage-5/READMEMISSING.md
```

The file contains questions about:
- Dataset scale (customers, items, training rows)
- Brands and markets in scope
- **Your real model metrics** (e.g. NDCG@5, MRR from your evaluation script)
- Baseline comparisons
- Ablation study results
- Training convergence (epochs, final loss)

Mark each completed item with `[x]` and fill in your answers after each question.

> **WARNING:** If you skip this step and resume without filling in real results,
> the pipeline will hallucinate numbers in the Experiments section.
> All results in the paper MUST come from your actual training runs.

---

### Gate 3: `final_review` (after Stage 8)

The multi-agent peer review has run. Read the feedback:
```bash
python3 -c "import json; d=json.load(open('output/stage-8/result.json')); print(d.get('meta_review', {}).get('decision')); [print(r['weaknesses']) for r in d.get('individual_reviews', [])]"
```

Review the draft in `output/stage-6/paper_draft.md`, then resume to compile LaTeX.

---

## Step 6 — Get your paper

After the final resume, output is in `output/stage-9/`:

```
output/stage-9/
├── paper.tex        ← Upload to Overleaf
└── references.bib   ← Upload alongside paper.tex
```

Also available as Markdown: `output/stage-6/paper_draft.md`

**To compile PDF locally** (requires LaTeX):
```bash
cd output/stage-9/
pdflatex paper.tex && bibtex paper && pdflatex paper.tex && pdflatex paper.tex
```

**To compile on Overleaf:**
1. Go to [overleaf.com](https://overleaf.com) → New Project → Upload
2. Upload `paper.tex` and `references.bib`
3. Click Compile

---

## Full output directory structure

```
output/
├── pipeline_state.json     ← Tracks current stage + passed gates
├── scholarforge.log        ← Full execution log
├── stage-1/result.json     ← Research plan + search queries
├── stage-2/result.json     ← Papers found (arXiv + Semantic Scholar)
├── stage-3/result.json     ← Knowledge cards extracted from papers
├── stage-4/
│   ├── result.json         ← Verification report (structured)
│   └── verification_report.json
├── stage-5/
│   ├── result.json         ← Gap analysis
│   └── READMEMISSING.md    ← Fill this in with your real results
├── stage-6/
│   ├── result.json         ← Paper draft (structured)
│   └── paper_draft.md      ← Full paper in Markdown
├── stage-7/result.json     ← Anti-slop check report
├── stage-8/result.json     ← Peer review (3 reviewers + meta-review)
└── stage-9/
    ├── paper.tex           ← Final LaTeX
    ├── references.bib      ← BibTeX citations
    └── figures/            ← Generated figures (if any)
```

---

## Starting a new paper (reuse the same install)

```bash
cd Paper_Writing_Code/scholarforge

# 1. Update the topic in config.yaml
nano config.yaml

# 2. Delete the previous run's output
rm -rf output/

# 3. Load API key and run
set -a && source .env && set +a
/Users/<your-username>/Library/Python/3.11/bin/scholarforge run \
  --topic "New topic here" \
  --readme /path/to/readme \
  --code-repo /path/to/code
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `scholarforge: command not found` | Use full path: `/Users/<username>/Library/Python/3.11/bin/scholarforge` |
| `No API key found in ANTHROPIC_API_KEY` | Run `set -a && source .env && set +a` before the command |
| `Pipeline failed: '\n  "title"'` | Already fixed in this repo — pull latest |
| `Pipeline failed: 'knowledge_cards'` | Already fixed in this repo — pull latest |
| `Pipeline failed: 'article'` | Already fixed in this repo — pull latest |
| Pipeline keeps re-running stages 6–8 | Already fixed — stages are skipped if already complete |
| PDF not generated | `pdflatex` not installed locally — use Overleaf instead |

---

## config.yaml reference

```yaml
project:
  name: "Paper display name"
  topic: "Research topic (used for literature search)"
  output_dir: "./output"

llm:
  provider: "anthropic"
  model: "claude-haiku-4-5-20251001"   # cheap + fast; change to claude-sonnet-4-6 for better quality
  api_key_env: "ANTHROPIC_API_KEY"
  temperature: 0.3
  max_tokens: 4096

literature:
  max_papers: 30                        # increase for broader coverage
  arxiv_categories: [cs.AI, cs.LG, cs.IR, cs.CV, stat.ML]

paper:
  target_words: 5500
  conference: "icml2026"               # or "iclr2026"

human_in_the_loop:
  auto_approve: false                  # set true to skip all gates (not recommended)
```
