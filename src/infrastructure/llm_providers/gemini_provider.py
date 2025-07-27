"""
Gemini LLM provider implementation.

This module implements the LLMProvider protocol for Google's Gemini API,
providing intelligent assistance for complex parsing scenarios in the
Obsidian to AppFlowy conversion process.
"""

import os
import re
from typing import Any, List, Optional

from src.domain.llm_assistant import LLMResponse

try:
    from google import genai
except ImportError:
    genai = None  # type: ignore


class GeminiProvider:
    """
    Gemini LLM provider implementation.

    Implements the LLMProvider protocol to provide intelligent assistance
    using Google's Gemini API for complex parsing scenarios.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gemini-2.5-flash",
        requests_per_minute: int = 60,
    ) -> None:
        """
        Initialize Gemini provider.

        Args:
            api_key: Gemini API key (if None, reads from GEMINI_API_KEY env var)
            model_name: Model to use for requests
            requests_per_minute: Rate limit for requests
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name
        self.requests_per_minute = requests_per_minute
        self._client = None

    def is_available(self) -> bool:
        """Check if the provider is available and configured."""
        return (
            genai is not None
            and self.api_key is not None
            and self.api_key.strip() != ""
        )

    def generate(self, prompt: str) -> LLMResponse:
        """
        Generate response synchronously.

        Args:
            prompt: Input prompt for the model

        Returns:
            LLM response with content and metadata

        Raises:
            Exception: If API call fails
        """
        if not self.is_available():
            raise Exception("Gemini provider not available")

        try:
            client = self._get_client()
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )

            return self._parse_response(response.text, self._infer_task_type(prompt))

        except Exception as e:
            raise Exception(f"Gemini API error: {str(e)}") from e

    async def generate_async(self, prompt: str) -> LLMResponse:
        """
        Generate response asynchronously.

        Args:
            prompt: Input prompt for the model

        Returns:
            LLM response with content and metadata

        Raises:
            Exception: If API call fails
        """
        if not self.is_available():
            raise Exception("Gemini provider not available")

        try:
            client = self._get_client()
            response = await client.models.generate_content_async(
                model=self.model_name,
                contents=prompt,
            )

            return self._parse_response(response.text, self._infer_task_type(prompt))

        except Exception as e:
            raise Exception(f"Gemini API error: {str(e)}") from e

    def _get_client(self) -> Any:
        """Get or create Gemini client."""
        if self._client is None:
            if not genai:
                raise Exception("google-genai package not installed")
            self._client = genai.Client(api_key=self.api_key)  # type: ignore
        return self._client

    def _infer_task_type(self, prompt: str) -> str:
        """Infer the task type from the prompt."""
        if "wikilink" in prompt.lower() or "[[" in prompt:
            return "wikilink_resolution"
        elif "parse" in prompt.lower() and "structure" in prompt.lower():
            return "structure_parsing"
        elif "ambiguous" in prompt.lower() or "syntax" in prompt.lower():
            return "ambiguous_syntax"
        else:
            return "general"

    def _parse_response(self, response_text: str, task_type: str) -> LLMResponse:
        """
        Parse raw response into structured LLMResponse.

        Args:
            response_text: Raw response from the API
            task_type: Type of task to help with parsing

        Returns:
            Structured LLM response
        """
        cleaned_text = response_text.strip()

        if task_type == "wikilink_resolution":
            # Extract filename from response
            content = self._extract_filename(cleaned_text)
        else:
            content = cleaned_text

        confidence = self._estimate_confidence(cleaned_text)
        reasoning = f"Gemini {self.model_name} response for {task_type}"

        return LLMResponse(
            content=content,
            confidence=confidence,
            reasoning=reasoning,
        )

    def _extract_filename(self, text: str) -> str:
        """Extract filename from wikilink resolution response."""
        # Look for markdown file references
        md_pattern = r"([a-zA-Z0-9\-_]+\.md)"
        match = re.search(md_pattern, text)
        if match:
            return match.group(1)

        # Look for quoted filenames
        quoted_pattern = r"[\"']([^\"']+\.md)[\"']"
        match = re.search(quoted_pattern, text)
        if match:
            return match.group(1)

        # Look for any filename-like strings
        filename_pattern = r"([a-zA-Z0-9\-_]+(?:\.md)?)"
        words = text.split()
        for word in words:
            if re.match(filename_pattern, word) and (
                word.endswith(".md") or len(word) > 3
            ):
                if not word.endswith(".md"):
                    word += ".md"
                return word

        # Fallback: return the original text
        return text

    def _estimate_confidence(self, response_text: str) -> float:
        """
        Estimate confidence based on response characteristics.

        Args:
            response_text: Response text to analyze

        Returns:
            Confidence level between 0.0 and 1.0
        """
        text = response_text.lower()

        # High confidence indicators
        if any(
            phrase in text
            for phrase in ["exact match", "definitely", "clearly", "certainly"]
        ):
            return 0.95

        # Medium-high confidence
        if any(
            phrase in text for phrase in ["likely", "probably", "best match", "similar"]
        ):
            return 0.75

        # Medium confidence
        if any(phrase in text for phrase in ["might", "could", "possibly"]):
            return 0.6

        # Low confidence indicators
        if any(
            phrase in text
            for phrase in [
                "not sure",
                "uncertain",
                "don't know",
                "unclear",
                "ambiguous",
            ]
        ):
            return 0.3

        # Default confidence based on response length and specificity
        if len(response_text) <= 25 and ".md" in response_text:
            return 0.85  # Short, specific response with .md extension

        if len(response_text) <= 25 and "." in response_text:
            return 0.8  # Short, specific response

        return 0.7  # Default medium confidence

    def _format_wikilink_prompt(self, wikilink: str, available_files: List[str]) -> str:
        """
        Format prompt for wikilink resolution.

        Args:
            wikilink: The wikilink to resolve
            available_files: List of available files

        Returns:
            Formatted prompt string
        """
        # Limit files list to prevent context overflow
        max_files = 50
        if len(available_files) > max_files:
            files_sample = available_files[:max_files]
            files_list = "\n".join(f"- {f}" for f in files_sample)
            files_list += f"\n... and {len(available_files) - max_files} more files"
        else:
            files_list = "\n".join(f"- {f}" for f in available_files)

        return f"""Help resolve this Obsidian wikilink to the best matching filename.

Wikilink: {wikilink}

Available files:
{files_list}

Find the best match based on:
1. Exact filename similarity
2. Common abbreviations (e.g., "ML" for "Machine Learning")
3. Semantic similarity
4. Path components

Return only the most likely filename. If uncertain, return your best guess."""
