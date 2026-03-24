#!/bin/bash
# Example: Run ScholarForge with README and code repository

# Set your API key
export OPENAI_API_KEY="your-api-key-here"

# Example 1: Machine learning project
scholarforge run \
  --topic "LoRA-CL: Efficient Continual Learning with Low-Rank Adaptation" \
  --readme ./my-ml-project/README.md \
  --code-repo ./my-ml-project/src \
  --code-extensions ".py,.yaml,.yml" \
  --config config.yaml

# Example 2: Systems/Software project
# scholarforge run \
#   --topic "Distributed Key-Value Store with Strong Consistency Guarantees" \
#   --readme ./my-system/README.md \
#   --code-repo ./my-system \
#   --code-extensions ".go,.proto" \
#   --config config.yaml

# Example 3: Resume with repo context
# scholarforge resume \
#   --run-id sf-20240324-143000 \
#   --readme ./my-project/README.md \
#   --code-repo ./my-project/src
