import asyncio
import random
import json
from app.logging_config import get_logger
from typing import Dict, Any, Optional, List
import google.generativeai as genai
from app.config import settings
from app.models.schemas import LLMResponse
from app.logging_config import ctx_request_id

logger = get_logger(__name__)

class LLMProviderError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)

class GeminiProvider:
    def __init__(
        self,
        api_keys: Optional[List[str]] = None,
        primary_model: str = settings.llm_model or settings.gemini_model_fast,
        fallback_model: str = settings.llm_fallback_model or settings.gemini_model_fallback_fast,
        timeout_seconds: float = settings.llm_timeout_seconds
    ):
        self.api_keys = api_keys or settings.get_gemini_api_keys()
        self.primary_model = primary_model
        self.fallback_model = fallback_model
        self.timeout_seconds = timeout_seconds

    def _configure_key(self, key: str):
        genai.configure(api_key=key)

    async def generate(self, prompt: str, system: str) -> LLMResponse:
        keys_to_try = self.api_keys if self.api_keys else [settings.gemini_api_key]
        
        models_to_try = [self.primary_model]
        if self.fallback_model and self.fallback_model != self.primary_model:
            models_to_try.append(self.fallback_model)
        if settings.gemini_model_heavy not in models_to_try:
            models_to_try.append(settings.gemini_model_heavy)

        last_error = None
        timeout_count = 0

        # Stage cascade: cycle through all available API keys and models
        for k_idx, key in enumerate(keys_to_try):
            if not key or not key.strip():
                continue
            self._configure_key(key)
            key_is_backup = (k_idx > 0)

            for m_idx, model_name in enumerate(models_to_try):
                model_is_fallback = (m_idx > 0)
                
                # Try up to 2 attempts with jittered backoff per model/key combination
                for attempt in range(2):
                    try:
                        logger.info(
                            "gemini_request_attempt",
                            model=model_name,
                            key_index=k_idx,
                            attempt=attempt + 1,
                            is_fallback=model_is_fallback
                        )

                        model = genai.GenerativeModel(
                            model_name=model_name,
                            system_instruction=system,
                            generation_config={
                                "temperature": 0.0,
                                "response_mime_type": "application/json"
                            }
                        )

                        # Enforce hard timeout per attempt
                        response = await asyncio.wait_for(
                            asyncio.to_thread(model.generate_content, prompt),
                            timeout=self.timeout_seconds
                        )

                        # Extract token counts
                        input_toks = 0
                        output_toks = 0
                        if hasattr(response, "usage_metadata") and response.usage_metadata:
                            input_toks = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
                            output_toks = getattr(response.usage_metadata, "candidates_token_count", 0) or 0

                        # Calculate estimated USD cost
                        est_cost = (
                            (input_toks / 1000.0) * settings.gemini_input_cost_per_1k +
                            (output_toks / 1000.0) * settings.gemini_output_cost_per_1k
                        )

                        logger.info(
                            "gemini_request_success",
                            model=model_name,
                            key_index=k_idx,
                            input_tokens=input_toks,
                            output_tokens=output_toks,
                            cost_usd=round(est_cost, 6)
                        )

                        return LLMResponse(
                            content=response.text,
                            model=model_name,
                            input_tokens=input_toks,
                            output_tokens=output_toks,
                            cost_usd=est_cost,
                            fallback_used=model_is_fallback or key_is_backup,
                            model_fallback_used=model_is_fallback,
                            key_fallback_used=key_is_backup,
                            timeout_count=timeout_count
                        )

                    except asyncio.TimeoutError:
                        timeout_count += 1
                        last_error = f"TimeoutError: Gemini call timed out after {self.timeout_seconds}s on {model_name}"
                        logger.warning(
                            "gemini_timeout_error",
                            model=model_name,
                            key_index=k_idx,
                            attempt=attempt + 1,
                            timeout_s=self.timeout_seconds
                        )
                        break  # Move immediately to fallback on timeout

                    except Exception as e:
                        err_str = str(e).lower()
                        last_error = str(e)
                        logger.warning(
                            "gemini_error_encountered",
                            model=model_name,
                            key_index=k_idx,
                            attempt=attempt + 1,
                            error=str(e)
                        )

                        # Check for rate limit or quota expiration
                        if "429" in err_str or "resource_exhausted" in err_str or "quota" in err_str:
                            # Immediate break to next API key
                            break

                        # Jittered backoff before attempt 2
                        if attempt == 0:
                            jitter = random.uniform(0.5, 1.5)
                            await asyncio.sleep(1.0 + jitter)

        logger.error("gemini_all_fallbacks_exhausted", last_error=last_error)
        raise LLMProviderError("ALL_FALLBACKS_EXHAUSTED", f"Gemini generation failed across all keys/models. Last error: {last_error}")

    from typing import AsyncGenerator
    async def generate_streaming(self, prompt: str, system: str) -> AsyncGenerator[str, None]:
        keys_to_try = self.api_keys if self.api_keys else [settings.gemini_api_key]
        last_error = None
        
        for k_idx, key in enumerate(keys_to_try):
            if not key or not key.strip():
                continue
            self._configure_key(key)
            
            try:
                model = genai.GenerativeModel(
                    model_name=self.primary_model,
                    system_instruction=system,
                    generation_config={
                        "temperature": 0.0
                    }
                )
                
                response = await asyncio.wait_for(
                    model.generate_content_async(prompt, stream=True),
                    timeout=self.timeout_seconds
                )
                
                async for chunk in response:
                    if chunk.text:
                        yield chunk.text
                return
                
            except asyncio.TimeoutError:
                last_error = f"TimeoutError: Gemini stream timed out after {self.timeout_seconds}s"
                logger.warning("gemini_streaming_timeout_error", key_index=k_idx)
            except Exception as e:
                last_error = str(e)
                logger.warning("gemini_streaming_error", error=last_error, key_index=k_idx)
        
        raise LLMProviderError("STREAMING_FAILED", f"Gemini streaming failed. Last error: {last_error}")

