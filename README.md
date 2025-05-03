# Semantic Prompt Caching for OpenAI API

A sophisticated caching system that reduces API costs by intelligently detecting and caching semantically equivalent prompts. This tool uses GPT-3.5 to determine if prompts are functionally equivalent, even when worded differently, saving significant costs on repeated API calls.

## 🚀 Features

- **Semantic Prompt Matching**: Uses AI to detect if prompts are functionally equivalent, not just exact matches
- **Automatic Caching**: Stores responses for future use, avoiding redundant API calls
- **Cost Tracking**: Detailed breakdown of API costs and savings
- **Multiple Operation Modes**:
  - Manual prompt entry with auto-generated variations
  - Batch processing from JSON file
  - Cache performance evaluation
  - Cache management

## 💡 How It Works

The system uses GPT-3.5 to analyze whether a new prompt is semantically equivalent to any cached prompt. Two prompts are considered equivalent if they:
1. Seek the same core information
2. Have the same constraints/requirements
3. Expect the same response format
4. Only differ in superficial ways (phrasing, examples)

For example, these would be considered equivalent:
- "Summarize the key points of this article"
- "What are the main ideas in this text?"

## 🛠️ Setup

1. Install dependencies:
```bash
pip install openai tabulate
```

2. Set your OpenAI API key:
```bash
export OPENAI_API_KEY='your-api-key-here'
```

## 📖 Usage

Run the program and select an option:
```bash
python main.py
```

### Option 1: Manual Prompt Entry
Enter a base prompt and the system will:
- Generate 5 variations of your prompt
- Check cache for semantic matches
- Display responses and cost analysis
- Save new responses to cache

### Option 2: Batch Processing
Processes prompts from `query_cache_data.json`:
- Runs multiple variations of questions
- Checks answers against expected results
- Provides detailed cost analysis with cache statistics

### Option 3: Cache Performance Evaluation
Evaluates how well the semantic caching is working:
- Calculates precision, recall, F1 score
- Identifies unexpected cache hits/misses
- Helps tune the caching algorithm

### Option 4: Clear Cache
Removes all cached prompts from the cache directory.

## 📊 Output Example

```
📊 Detailed Cost Analysis
+-------------+---------------+-------------------+--------------+------------+--------+
| Prompt      | Prompt Tokens | Completion Tokens | Total Tokens | Cost       | Source |
+-------------+---------------+-------------------+--------------+------------+--------+
| Variation 1 | 15            | 82                | 97           | $0.000131  | API    |
| Variation 2 | 18            | 82                | 100          | $0.000132  | Cache  |
+-------------+---------------+-------------------+--------------+------------+--------+

✅ Summary:
🔢 Total Prompts: 5
🔍 Cache Hits: 3
🌐 API Calls: 2
💰 Total Estimated Cost: $0.000394
💵 Estimated Savings: $0.000236
```

## 📁 File Structure

- `main.py` - Main application code
- `cache/` - Directory storing cached prompts and responses
- `query_cache_data.json` - Test data for batch processing

## ⚙️ Configuration

The system uses these OpenAI settings:
- Model: `gpt-3.5-turbo-0125`
- Temperature: 0.7 (for responses)
- Temperature: 0.0 (for semantic matching)
- Confidence threshold: 0.8 for cache matches

## 💰 Cost Savings

The system can significantly reduce API costs by:
- Detecting semantically similar prompts
- Caching responses for reuse
- Providing detailed cost tracking
- Showing estimated savings from cache hits

## ⚠️ Important Notes

- Cache files are stored locally in the `cache/` directory
- Semantic matching uses API calls (but typically costs less than full responses)
- Confidence threshold (0.8) can be adjusted for stricter/looser matching
- The system is conservative to avoid false positive cache matches

## 🤝 Contributing

Feel free to submit issues or pull requests to improve the semantic matching algorithm, add new features, or optimize performance.
