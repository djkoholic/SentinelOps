from ollama import chat
import logging

logger = logging.getLogger(__name__)

def call_llm(prompt, provider="ollama", model_name="qwen3:4b"):
    logger.info(f"Calling LLM with model: {model_name}")
    logger.info(f"Prompt length: {len(prompt)} characters")
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
        logger.info(f"LLM response length: {len(result)} characters")
        return result
    except Exception as e:
        logger.info(f"Error calling LLM: {str(e)}")
        raise