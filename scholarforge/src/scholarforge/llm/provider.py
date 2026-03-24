"""LLM Provider Abstraction.

Requirements:
1. Single interface for all providers (OpenAI, Anthropic via proxy, DeepSeek, Ollama, etc.)
2. All providers use the OpenAI-compatible chat completions format
3. Support for system prompts, temperature, max_tokens
4. Retry logic with exponential backoff (3 retries, 2/4/8 second delays)
5. Structured JSON output extraction
6. Token usage logging
"""

import json
import re
import time
from typing import Any, Optional

import openai
from openai import OpenAI

from ..config import LLMConfig
from ..utils.logger import get_logger

logger = get_logger(__name__)


class LLMProvider:
    """Unified LLM client for all OpenAI-compatible APIs."""
    
    def __init__(self, config: LLMConfig):
        """Initialize LLM provider.
        
        Args:
            config: LLM configuration
        """
        self.config = config
        self.api_key = config.get_api_key()
        
        if not self.api_key and config.provider != "ollama":
            logger.warning(f"No API key found in {config.api_key_env}")
        
        # Initialize OpenAI client
        client_kwargs = {}
        if config.base_url:
            client_kwargs["base_url"] = config.base_url
        if self.api_key:
            client_kwargs["api_key"] = self.api_key
        else:
            client_kwargs["api_key"] = "dummy-key"  # For Ollama
            
        self.client = OpenAI(**client_kwargs)
        self.model = config.model
        
        logger.info(f"Initialized LLM provider: {config.provider} with model {config.model}")
    
    def complete(
        self, 
        system: str, 
        user: str, 
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """Generate a completion.
        
        Args:
            system: System prompt
            user: User prompt
            temperature: Override temperature (optional)
            max_tokens: Override max_tokens (optional)
            
        Returns:
            Generated text
            
        Raises:
            Exception: If all retries fail
        """
        temp = temperature if temperature is not None else self.config.temperature
        max_tok = max_tokens if max_tokens is not None else self.config.max_tokens
        
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ]
        
        # Retry with exponential backoff
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temp,
                    max_tokens=max_tok
                )
                
                content = response.choices[0].message.content
                
                # Log token usage
                if response.usage:
                    logger.debug(
                        f"Tokens used: prompt={response.usage.prompt_tokens}, "
                        f"completion={response.usage.completion_tokens}, "
                        f"total={response.usage.total_tokens}"
                    )
                
                return content
                
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    delay = 2 ** (attempt + 1)  # 2, 4, 8 seconds
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    logger.error(f"All {max_retries} attempts failed")
                    raise
        
        return ""  # Should never reach here
    
    def complete_json(
        self, 
        system: str, 
        user: str, 
        schema_hint: str = "",
        temperature: Optional[float] = None
    ) -> dict[str, Any]:
        """Generate a completion and parse as JSON.
        
        Args:
            system: System prompt
            user: User prompt
            schema_hint: Optional JSON schema hint
            temperature: Override temperature (optional)
            
        Returns:
            Parsed JSON as dictionary
            
        Raises:
            ValueError: If JSON parsing fails after retries
        """
        # Append JSON instruction to system prompt
        json_instruction = "\n\nRespond ONLY in valid JSON. No markdown, no preamble."
        if schema_hint:
            json_instruction += f"\nJSON schema: {schema_hint}"
        
        full_system = system + json_instruction
        
        # Retry parsing
        max_retries = 3
        for attempt in range(max_retries):
            try:
                content = self.complete(full_system, user, temperature)
                parsed = self._extract_json(content)
                return parsed
                
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"JSON parse attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                else:
                    logger.error(f"Failed to parse JSON after {max_retries} attempts")
                    raise ValueError(f"Could not parse LLM response as JSON: {e}")
        
        return {}  # Should never reach here
    
    def _extract_json(self, text: str) -> dict[str, Any]:
        """Extract JSON from text, handling markdown fences.
        
        Args:
            text: Raw text that may contain JSON
            
        Returns:
            Parsed JSON dictionary
            
        Raises:
            json.JSONDecodeError: If no valid JSON found
        """
        # Try direct parse first
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Try to extract from markdown code block
        patterns = [
            r'```json\s*(.*?)\s*```',  # ```json ... ```
            r'```\s*(.*?)\s*```',       # ``` ... ```
            r'\{.*\}',                  # Raw JSON object
            r'\[.*\]',                  # Raw JSON array
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            for match in matches:
                try:
                    return json.loads(match.strip())
                except json.JSONDecodeError:
                    continue
        
        # Last resort: try to find JSON-like structure
        json_start = text.find('{')
        json_end = text.rfind('}')
        if json_start != -1 and json_end != -1 and json_end > json_start:
            try:
                return json.loads(text[json_start:json_end+1])
            except json.JSONDecodeError:
                pass
        
        raise json.JSONDecodeError("No valid JSON found in response", text, 0)
