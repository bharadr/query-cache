import openai
import os
import json
import hashlib
from pathlib import Path
from tabulate import tabulate

# Use your env variable
openai.api_key = os.getenv("OPENAI_API_KEY")

# Pricing constants (gpt-3.5-turbo-0125)
PROMPT_COST_PER_1K = 0.50  # in USD
COMPLETION_COST_PER_1K = 1.50  # in USD

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

def get_cache_key(prompt):
    # Create a unique key for the cache based on the prompt
    return hashlib.sha256(prompt.encode()).hexdigest()

def check_cache(prompt):
    # Check if the prompt is already in the cache
    cache_key = get_cache_key(prompt)
    cache_file = CACHE_DIR / f"{cache_key}.json"
    
    if cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            print(f"🔍 Cache hit! Using cached response.")
            return (
                cache_data["reply"], 
                cache_data["prompt_tokens"], 
                cache_data["completion_tokens"], 
                cache_data["cost"],
                True  # Indicates a cache hit
            )
        except Exception as e:
            print(f"⚠️ Cache read error: {e}. Will call API.")
    
    return None

def save_to_cache(prompt, reply, prompt_tokens, completion_tokens, cost):
    # Save the response to the cache
    cache_key = get_cache_key(prompt)
    cache_file = CACHE_DIR / f"{cache_key}.json"
    
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

def get_response_and_usage(prompt):
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
    cost = (prompt_tokens / 1000) * PROMPT_COST_PER_1K + (completion_tokens / 1000) * COMPLETION_COST_PER_1K
    
    # Save to cache for future use
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
            response_data = get_response_and_usage(prompt)
            
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
        for i, prompt in enumerate(variants):
            print(f"\n🧪 Variant {i+1}: {prompt}")
            try:
                response_data = get_response_and_usage(prompt)
                
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

        # Show question totals
        print("\n" + "-"*60)
        print(f"✅ Question Summary:")
        print(f"🔢 Total Variants: {len(question_results)}")
        print(f"🔍 Cache Hits: {cache_hits}")
        print(f"🌐 API Calls: {api_calls}")
        print(f"🧾 Total Prompt Tokens: {total_prompt_tokens}")
        print(f"🧾 Total Completion Tokens: {total_completion_tokens}")
        print(f"🧾 Total Tokens: {total_prompt_tokens + total_completion_tokens}")
        print(f"💰 Total Estimated Cost: ${total_cost:.6f}")
        
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

def main():
    print("Select an option:")
    print("1. Enter a prompt manually")
    print("2. Process all queries from query_cache_data.json")
    
    choice = input("Enter your choice (1 or 2): ").strip()
    
    if choice == "1":
        process_user_prompt()
    elif choice == "2":
        process_query_cache_data()
    else:
        print("Invalid choice. Please run the program again and select 1 or 2.")

if __name__ == "__main__":
    main()
