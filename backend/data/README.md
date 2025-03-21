# Data Directory

This directory contains critical configuration and reference files for the AI report generation system.

## Files

### `brand_guide.txt`
Contains the brand voice, tone, and style guidelines. This file defines:
- Writing style and tone
- Document structure
- Formatting rules
- Terminology preferences
- Common phrases and expressions to use/avoid

### `prompts.json`
System prompts for the AI agents:
- `writer_system_prompt`: Instructions for the report writer agent
- `reviewer_system_prompt`: Instructions for the report reviewer agent

### `reference_reports.jsonl`
JSONL file containing example report pairs (input/output) used for style reference.
Each line contains a JSON object with:
```json
{
  "messages": [
    {"role": "user", "content": "User input/request"},
    {"role": "assistant", "content": "Corresponding report output"}
  ]
}
```

## Important Notes

1. These files are **version controlled** and should be included in git commits
2. They are essential for the AI system to function correctly
3. Any changes to these files will affect all generated reports
4. The content should be reviewed and approved before deployment

## Usage

These files are loaded by the `AIAgentLoop` class in `backend/utils/agents_loop.py` and used to:
1. Guide the writing style and format
2. Provide system instructions to the AI models
3. Offer reference examples for consistency

## Maintenance

When updating these files:
1. Test changes locally first
2. Ensure JSON/JSONL files are properly formatted
3. Keep the brand guide concise and clear
4. Document significant changes in commit messages 