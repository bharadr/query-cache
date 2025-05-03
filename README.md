# LLM Query Cache 🧪

This is a prototype of a cache that uses an LLM to check for questions that are semantically equivalent.

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
