complete set of instructions to write paper


  Here are the complete instructions with paths filled in:

  ---
  Starting a new paper with ScholarForge

  1. Edit config.yaml

  nano /Users/umittal/Desktop/Paper_Writing_Code/scholarforge/config.yaml
  Change the topic and name fields:
  project:
    name: "Your Paper Name"
    topic: "Your research topic here"

  2. Clear the old output

  rm -rf /Users/umittal/Desktop/Paper_Writing_Code/scholarforge/output/

  3. Load your API key and run

  cd /Users/umittal/Desktop/Paper_Writing_Code/scholarforge
  set -a && source .env && set +a

  /Users/umittal/Library/Python/3.11/bin/scholarforge run \
    --topic "Your research topic here" \
    --readme /Users/umittal/Desktop/Div_Category_Preference_Model/martech_hierarchy_preference_model/README.md
   \
    --code-repo /Users/umittal/Desktop/Div_Category_Preference_Model/martech_hierarchy_preference_model

  4. The pipeline pauses 3 times — resume with this command each time

  /Users/umittal/Library/Python/3.11/bin/scholarforge resume \
    --run-id <run-id-shown-in-output> \
    --readme /Users/umittal/Desktop/Div_Category_Preference_Model/martech_hierarchy_preference_model/README.md
   \
    --code-repo /Users/umittal/Desktop/Div_Category_Preference_Model/martech_hierarchy_preference_model

  ┌───────────────────┬────────────────────────────────────────────────────────────────────────────────────┐
  │       Gate        │                             What to do before resuming                             │
  ├───────────────────┼────────────────────────────────────────────────────────────────────────────────────┤
  │ literature_review │ Glance at output/stage-2/result.json to confirm papers look relevant               │
  ├───────────────────┼────────────────────────────────────────────────────────────────────────────────────┤
  │ gap_analysis      │ Fill in output/stage-5/READMEMISSING.md with real dataset stats, NDCG@5/MRR        │
  │                   │ results, baselines, ablations                                                      │
  ├───────────────────┼────────────────────────────────────────────────────────────────────────────────────┤
  │ final_review      │ Read peer review in output/stage-8/result.json, then resume to compile LaTeX       │
  └───────────────────┴────────────────────────────────────────────────────────────────────────────────────┘

  5. Final output

  output/stage-9/paper.tex       ← upload to Overleaf
  output/stage-9/references.bib  ← upload alongside paper.tex
  output/stage-6/paper_draft.md  ← readable draft

  ---
  The most important step: Do not skip filling READMEMISSING.md at the gap_analysis gate — that is where you
  provide your real results, or the Experiments section will be fabricated.