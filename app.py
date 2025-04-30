import openai
import os
import json
import time
import random
from pathlib import Path
from tabulate import tabulate

# Use your env variable
openai.api_key = os.getenv("OPENAI_API_KEY")

# Pricing constants (gpt-3.5-turbo-0125)
PROMPT_COST_PER_1M = 0.50  # in USD
COMPLETION_COST_PER_1M = 1.50  # in USD

# Cache configuration
CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

def generate_variations(prompt):
    return [
        prompt,
        prompt + " Please elaborate.",
        prompt.replace(".", "?"),
        "In your opinion, " + prompt.lower(),
        prompt + " Be concise.",
    ]

def load_all_cached_prompts():
    """Load all prompts from the cache files"""
    cached_items = []
    for cache_file in CACHE_DIR.glob('*.json'):
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
                cached_items.append({
                    "prompt": data["prompt"],
                    "cache_file": cache_file,
                    "reply": data["reply"],
                    "prompt_tokens": data["prompt_tokens"],
                    "completion_tokens": data["completion_tokens"],
                    "cost": data["cost"]
                })
        except Exception as e:
            print(f"⚠️ Error reading cache file {cache_file}: {e}")
    return cached_items

def check_prompt_equivalence(new_prompt, cached_prompts):
    """Check if a prompt is functionally equivalent to any of the cached prompts in a single API call"""
    
    # First check for exact matches to avoid unnecessary API calls
    for idx, cache_item in enumerate(cached_prompts):
        if new_prompt == cache_item["prompt"]:
            return idx, True
    
    # If no exact matches, prepare prompts for comparison
    prompts_text = "\n\n".join([f"Cached prompt {i+1}: {p['prompt']}" for i, p in enumerate(cached_prompts)])
    
    system_message = """
    You are a prompt analysis expert. Your task is to determine if a new prompt is functionally 
    equivalent to any cached prompts. Two prompts are functionally equivalent if they meet ALL of the following criteria:

    1. They seek the same core information or aim to accomplish the same task
    2. They impose the same essential constraints or requirements
    3. They would expect the same format and level of detail in the response
    4. Any differences between them are superficial (phrasing, examples used, etc.) rather than substantive

    Be precise and conservative in your judgment - only consider prompts equivalent if you're highly confident 
    they would produce interchangeable responses.
    """
    
    examples = """
    Examples of EQUIVALENT prompts:
    - "Summarize the key points of this article" vs "What are the main ideas in this text?"
    - "Write a thank you email to John for his help on the project" vs "Compose a message expressing gratitude to John for his project assistance"
    
    Examples of NON-EQUIVALENT prompts:
    - "Summarize the article" vs "Analyze the strengths and weaknesses of the article"
    - "Write a short story about dragons" vs "Write a short story about dragons with a moral lesson"
    """
    
    user_message = f"""
    New prompt: {new_prompt}
    
    {prompts_text}
    
    {examples}
    
    Is the new prompt functionally equivalent to any of the cached prompts?
    
    Follow these steps:
    1. Analyze the core intent of the new prompt
    2. For each cached prompt, compare it to the new prompt using the functional equivalence criteria
    3. Determine if there's a match and provide your reasoning
    
    Respond in JSON format:
    {{
        "reasoning": "your step-by-step analysis",
        "is_equivalent": true/false,
        "equivalent_prompt_index": null or index of the matching prompt (1-based),
        "confidence": 0.0-1.0 (your confidence in this judgment)
    }}
    """
    
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo-0125",  # Consider using gpt-4 for higher precision if budget allows
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            temperature=0.0,
            response_format={"type": "json_object"},  # Force structured JSON output
            max_tokens=500  # Allow enough tokens for detailed reasoning
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # Only consider it a match if confidence is high
        if result["is_equivalent"] and result["confidence"] >= 0.8:
            prompt_num = result["equivalent_prompt_index"] - 1  # Convert to 0-based index
            if 0 <= prompt_num < len(cached_prompts):
                return prompt_num, True
        
        return -1, False
    except Exception as e:
        print(f"⚠️ Error comparing prompts: {e}")
        return -1, False

def check_cache(prompt):
    # Load all cached prompts
    cached_items = load_all_cached_prompts()
    
    # If no cached prompts, return None
    if not cached_items:
        return None
    
    # Check for semantic equivalence with any cached prompt
    matched_idx, is_equivalent = check_prompt_equivalence(prompt, cached_items)
    
    if is_equivalent and matched_idx >= 0:
        cache_item = cached_items[matched_idx]
        print(f"🔍 Cache hit! Prompt matches cached prompt: \"{cache_item['prompt']}\"")
        return (
            cache_item["reply"],
            cache_item["prompt_tokens"],
            cache_item["completion_tokens"],
            cache_item["cost"],
            True  # Indicates a cache hit
        )
    
    # No match found
    return None

def save_to_cache(prompt, reply, prompt_tokens, completion_tokens, cost):
    # Generate a unique filename using current timestamp and a random component
    import time
    import random
    
    timestamp = int(time.time())
    random_component = random.randint(1000, 9999)
    cache_file = CACHE_DIR / f"prompt_{timestamp}_{random_component}.json"
    
    cache_data = {
        "prompt": prompt,
        "reply": reply,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "cost": cost
    }
    
    try:
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f)
    except Exception as e:
        print(f"⚠️ Cache write error: {e}")

def get_response_and_usage(prompt, idx):
    # First check if we have this in cache
    cache_result = check_cache(prompt)
    if cache_result:
        return cache_result
    
    # If not in cache, call the API
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo-0125",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )

    reply = response.choices[0].message.content
    usage = response.usage
    prompt_tokens = usage.prompt_tokens
    completion_tokens = usage.completion_tokens

    # Cost calculation
    cost = (prompt_tokens / 1000000) * PROMPT_COST_PER_1M + (completion_tokens / 1000000) * COMPLETION_COST_PER_1M
    
    # Save to cache for future use
    if idx == 0:
        save_to_cache(prompt, reply, prompt_tokens, completion_tokens, cost)

    return reply.strip(), prompt_tokens, completion_tokens, cost, False  # False indicates not from cache

def process_user_prompt():
    base_prompt = input("Enter your base prompt:\n> ").strip()
    print("\nGenerating variations...\n")

    variations = generate_variations(base_prompt)

    results = []  # Store results for table
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_cost = 0.0
    cache_hits = 0
    api_calls = 0

    for i, prompt in enumerate(variations):
        print(f"\n🧪 Variation {i+1}: {prompt}")
        try:
            response_data = get_response_and_usage(prompt, i)
            
            # Unpack the response data
            if len(response_data) == 5:  # New format with cache info
                response, p_tokens, c_tokens, cost, from_cache = response_data
                if from_cache:
                    cache_hits += 1
                else:
                    api_calls += 1
            else:  # Backward compatibility
                response, p_tokens, c_tokens, cost = response_data
                api_calls += 1
                
        except Exception as e:
            print(f"❌ Error: {e}")
            continue

        # Add cache indicator to the response display
        cache_indicator = "🔍 [CACHED]" if len(response_data) == 5 and response_data[4] else ""
        print(f"\n📤 Response: {cache_indicator}\n{response}")
        
        results.append([
            f"Variation {i+1}",
            p_tokens,
            c_tokens,
            p_tokens + c_tokens,
            f"${cost:.6f}",
            "Cache" if len(response_data) == 5 and response_data[4] else "API"
        ])

        total_prompt_tokens += p_tokens
        total_completion_tokens += c_tokens
        total_cost += cost

    # After all prompts, show full table
    print("\n" + "="*60)
    print("📊 Detailed Cost Analysis")
    headers = ["Prompt", "Prompt Tokens", "Completion Tokens", "Total Tokens", "Cost", "Source"]
    print(tabulate(results, headers=headers, tablefmt="grid"))

    # Show totals
    print("\n" + "-"*60)
    print("✅ Summary:")
    print(f"🔢 Total Prompts: {len(results)}")
    print(f"🔍 Cache Hits: {cache_hits}")
    print(f"🌐 API Calls: {api_calls}")
    print(f"🧾 Total Prompt Tokens: {total_prompt_tokens}")
    print(f"🧾 Total Completion Tokens: {total_completion_tokens}")
    print(f"🧾 Total Tokens: {total_prompt_tokens + total_completion_tokens}")
    print(f"💰 Total Estimated Cost: ${total_cost:.6f}")
    
    # Show savings if any cache hits
    if cache_hits > 0:
        # Assuming average cost per query is total_cost / len(results)
        avg_cost_per_query = total_cost / len(results) if len(results) > 0 else 0
        estimated_savings = avg_cost_per_query * cache_hits
        print(f"💵 Estimated Savings: ${estimated_savings:.6f}")
    
    print("-"*60)

def process_query_cache_data():
    # Load the questions from query_cache_data.json
    try:
        with open('query_cache_data.json', 'r') as f:
            questions_data = json.load(f)
    except Exception as e:
        print(f"Error loading query_cache_data.json: {e}")
        return

    all_results = []  # Store results for the final table
    grand_total_prompt_tokens = 0
    grand_total_completion_tokens = 0
    grand_total_cost = 0.0
    grand_total_cache_hits = 0
    grand_total_api_calls = 0

    # Loop through each question
    for question_data in questions_data:
        question_id = question_data["question_id"]
        topic = question_data["topic"]
        variants = question_data["variants"]
        expected_answer = question_data["answer"]
        
        print(f"\n{'='*80}")
        print(f"Processing {question_id}: {topic} (Expected Answer: {expected_answer})")
        print(f"{'='*80}")
        
        question_results = []  # Store results for this question
        total_prompt_tokens = 0
        total_completion_tokens = 0
        total_cost = 0.0
        cache_hits = 0
        api_calls = 0

        # Loop through all the variant prompts for this question
        for i, variant_obj in enumerate(variants):
            # Extract text from variant object
            prompt = variant_obj["text"]
            print(f"\n🧪 Variant {i+1}: {prompt}")
            try:
                response_data = get_response_and_usage(prompt, i)
                # Unpack the response data
                if len(response_data) == 5:  # Format with cache info
                    response, p_tokens, c_tokens, cost, from_cache = response_data
                    if from_cache:
                        cache_hits += 1
                        grand_total_cache_hits += 1
                    else:
                        api_calls += 1
                        grand_total_api_calls += 1
                else:  # Backward compatibility
                    response, p_tokens, c_tokens, cost = response_data
                    api_calls += 1
                    grand_total_api_calls += 1
                    
            except Exception as e:
                print(f"❌ Error: {e}")
                continue

            # Add cache indicator to the response display
            cache_indicator = "🔍 [CACHED]" if len(response_data) == 5 and response_data[4] else ""
            print(f"\n📤 Response: {cache_indicator}\n{response}")
            
            # Check if response contains the expected answer
            answer_match = "✅" if expected_answer.lower() in response.lower() else "❌"
            
            question_results.append([
                f"Variant {i+1}",
                prompt[:50] + "..." if len(prompt) > 50 else prompt,
                p_tokens,
                c_tokens,
                p_tokens + c_tokens,
                f"${cost:.6f}",
                "Cache" if len(response_data) == 5 and response_data[4] else "API",
                answer_match
            ])

            # Add to the question totals
            total_prompt_tokens += p_tokens
            total_completion_tokens += c_tokens
            total_cost += cost
            
            # Add to the grand totals
            grand_total_prompt_tokens += p_tokens
            grand_total_completion_tokens += c_tokens
            grand_total_cost += cost

        # After all variants for this question, show question table
        print("\n" + "-"*80)
        print(f"📊 Results for {question_id}: {topic}")
        headers = ["Variant", "Prompt", "Prompt Tokens", "Completion Tokens", "Total Tokens", "Cost", "Source", "Answer Match"]
        print(tabulate(question_results, headers=headers, tablefmt="grid"))
        # Add question summary to all results
        all_results.extend(question_results)

    # After all questions, show grand total summary
    print("\n" + "="*80)
    print("📊 GRAND TOTAL SUMMARY")
    print("="*80)
    print(f"🔢 Total Questions: {len(questions_data)}")
    print(f"🔢 Total Variants Processed: {len(all_results)}")
    print(f"🔍 Total Cache Hits: {grand_total_cache_hits}")
    print(f"🌐 Total API Calls: {grand_total_api_calls}")
    print(f"🧾 Total Prompt Tokens: {grand_total_prompt_tokens}")
    print(f"🧾 Total Completion Tokens: {grand_total_completion_tokens}")
    print(f"🧾 Total Tokens: {grand_total_prompt_tokens + grand_total_completion_tokens}")
    print(f"💰 Total Estimated Cost: ${grand_total_cost:.6f}")
    
    # Show savings if any cache hits
    if grand_total_cache_hits > 0:
        # Assuming average cost per query is total_cost / len(results)
        avg_cost_per_query = grand_total_cost / (grand_total_cache_hits + grand_total_api_calls) if (grand_total_cache_hits + grand_total_api_calls) > 0 else 0
        estimated_savings = avg_cost_per_query * grand_total_cache_hits
        print(f"💵 Estimated Savings: ${estimated_savings:.6f}")
    
    print("="*80)

def evaluate_cache_performance():
    try:
        with open('query_cache_data.json', 'r') as f:
            questions_data = json.load(f)
    except Exception as e:
        print(f"Error loading query_cache_data.json: {e}")
        return
    
    # Load all cached prompts
    cached_items = load_all_cached_prompts()
    cached_prompts = [item["prompt"] for item in cached_items]
    
    # Initialize metrics
    true_positives = 0   # Prompts that should be cached and are cached
    false_positives = 0  # Prompts that should not be cached but are cached
    true_negatives = 0   # Prompts that should not be cached and are not cached
    false_negatives = 0  # Prompts that should be cached but are not cached
    
    # Detailed records for analysis
    cache_hits = []
    cache_misses = []
    unexpected_cache_hits = []
    unexpected_cache_misses = []
    
    # Evaluate each prompt variant
    for question in questions_data:
        question_id = question["question_id"]
        topic = question["topic"]
        variants = question["variants"]
        
        for variant in variants[1:]:
            prompt = variant["text"]
            should_be_cached = variant["should_be_cached"]
            
            # Check if this prompt matches any cached prompt using our semantic comparison
            matched_idx, is_cached = check_prompt_equivalence(prompt, cached_items) if cached_items else (-1, False)
            
            # Update metrics
            if should_be_cached and is_cached:
                true_positives += 1
                cache_hits.append({
                    "question_id": question_id,
                    "topic": topic,
                    "prompt": prompt
                })
            elif should_be_cached and not is_cached:
                false_negatives += 1
                unexpected_cache_misses.append({
                    "question_id": question_id,
                    "topic": topic,
                    "prompt": prompt
                })
            elif not should_be_cached and is_cached:
                false_positives += 1
                unexpected_cache_hits.append({
                    "question_id": question_id,
                    "topic": topic,
                    "prompt": prompt
                })
            else:  # not should_be_cached and not is_cached
                true_negatives += 1
                cache_misses.append({
                    "question_id": question_id,
                    "topic": topic,
                    "prompt": prompt
                })
    
    # Calculate precision and recall
    if true_positives + false_positives > 0:
        precision = true_positives / (true_positives + false_positives)
    else:
        precision = 0
        
    if true_positives + false_negatives > 0:
        recall = true_positives / (true_positives + false_negatives)
    else:
        recall = 0
    
    if precision + recall > 0:
        f1_score = 2 * (precision * recall) / (precision + recall)
    else:
        f1_score = 0
    
    accuracy = (true_positives + true_negatives) / (true_positives + true_negatives + false_positives + false_negatives)
    
    # Print results
    print("\n" + "="*80)
    print("CACHE EVALUATION METRICS")
    print("="*80)
    print(f"Total prompts evaluated: {true_positives + true_negatives + false_positives + false_negatives}")
    print(f"True Positives (correctly cached): {true_positives}")
    print(f"False Positives (incorrectly cached): {false_positives}")
    print(f"True Negatives (correctly not cached): {true_negatives}")
    print(f"False Negatives (incorrectly not cached): {false_negatives}")
    print("-"*80)
    print(f"Precision: {precision:.4f} - Of all cached items, what fraction should have been cached")
    print(f"Recall: {recall:.4f} - Of all items that should be cached, what fraction were actually cached")
    print(f"F1 Score: {f1_score:.4f} - Harmonic mean of precision and recall")
    print(f"Accuracy: {accuracy:.4f} - Overall correct decisions")
    print("="*80)
    
    # Print detailed information
    if unexpected_cache_hits:
        print("\nUnexpected Cache Hits (False Positives):")
        for item in unexpected_cache_hits:
            print(f"  - {item['question_id']} ({item['topic']}): \"{item['prompt']}\"")
    
    if unexpected_cache_misses:
        print("\nUnexpected Cache Misses (False Negatives):")
        for item in unexpected_cache_misses:
            print(f"  - {item['question_id']} ({item['topic']}): \"{item['prompt']}\"")

def clear_cache():
    """Clear all cached prompts from the cache directory"""
    count = 0
    try:
        for cache_file in CACHE_DIR.glob('*.json'):
            cache_file.unlink()
            count += 1
        print(f"✅ Successfully cleared {count} items from cache.")
    except Exception as e:
        print(f"⚠️ Error clearing cache: {e}")

def main():
    print("Select an option:")
    print("1. Enter a prompt manually")
    print("2. Process all queries from query_cache_data.json")
    print("3. Evaluate cache performance")
    print("4. Clear cache")
    
    choice = input("Enter your choice (1, 2, 3, or 4): ").strip()
    
    if choice == "1":
        process_user_prompt()
    elif choice == "2":
        process_query_cache_data()
    elif choice == "3":
        evaluate_cache_performance()
    elif choice == "4":
        clear_cache()
    else:
        print("Invalid choice. Please run the program again and select 1, 2, 3, or 4.")

if __name__ == "__main__":
    main()
