from ollama import chat

def call_llm(prompt, provider="ollama", model_name="qwen3:4b"):
    print(f"[DEBUG] Calling LLM with model: {model_name}")
    print(f"[DEBUG] Prompt length: {len(prompt)} characters")
    try:
        response = chat(
            model=model_name,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        result = response.message.content
        print(f"[DEBUG] LLM response length: {len(result)} characters")
        return result
    except Exception as e:
        print(f"[DEBUG] Error calling LLM: {str(e)}")
        raise