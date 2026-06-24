from ollama import chat
import json_repair
import logging

logger = logging.getLogger(__name__)

def call_llm(prompt, provider="ollama", model_name="qwen3:4b"):
    print(f"Calling LLM with model: {model_name}")
    print(f"Prompt: {prompt}")
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
        result = json_repair.loads(result)
        print(f"LLM response: {result}")
        return result
    except Exception as e:
        print(f"Error calling LLM: {str(e)}")
        raise