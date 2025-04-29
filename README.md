# Prompt Sensitivity Checker 🧪

This tool tests how sensitive large language models (LLMs) like GPT-3.5 are to small changes in prompt wording.

## 🔍 What It Does
- Generates 5 slight variations of a base prompt
- Sends them to OpenAI’s API (gpt-3.5-turbo-0125)
- Prints each response, token usage, and cost
- Outputs a side-by-side cost analysis using `tabulate`

## 🛠️ Requirements

- Python 3.7+
- OpenAI API key
- Packages in `requirements.txt`

Install dependencies:

```bash
pip install -r requirements.txt
