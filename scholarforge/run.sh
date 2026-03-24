#!/bin/bash
export ANTHROPIC_API_KEY=$(cat .env | tr -d '[:space:]')
/Users/umittal/Library/Python/3.11/bin/scholarforge run \
  --topic "Two-Tower Recommendation Model for Customer Division and Category Preference Prediction in Retail" \
  --readme "/Users/umittal/Desktop/Div_Category_Preference_Model/martech_hierarchy_preference_model/README.md" \
  --code-repo "/Users/umittal/Desktop/Div_Category_Preference_Model/martech_hierarchy_preference_model" \
  --config config.yaml
