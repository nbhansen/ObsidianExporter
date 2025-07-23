"""
Test cases for Gemini LLM provider implementation.

Following TDD approach - these tests define the expected behavior
for the Gemini provider that implements the LLMProvider protocol.
"""

import os
from unittest.mock import Mock, patch

import pytest

from src.domain.llm_assistant import LLMResponse
from src.infrastructure.llm_providers.gemini_provider import GeminiProvider


class TestGeminiProvider:
    """Test suite for GeminiProvider following TDD methodology."""

    def test_create_gemini_provider_with_api_key(self):
        """
        Test creating Gemini provider with API key.

        Should initialize with the given API key.
        """
        api_key = "test-api-key-123"
        provider = GeminiProvider(api_key=api_key)

        assert provider.api_key == api_key
        assert provider.model_name == "gemini-2.5-flash"  # Default model

    def test_create_gemini_provider_with_custom_model(self):
        """
        Test creating Gemini provider with custom model.

        Should use the specified model instead of default.
        """
        api_key = "test-api-key-123"
        model_name = "gemini-2.5-pro"
        provider = GeminiProvider(api_key=api_key, model_name=model_name)

        assert provider.model_name == model_name

    @patch.dict(os.environ, {"GEMINI_API_KEY": "env-api-key"})
    def test_create_gemini_provider_from_environment(self):
        """
        Test creating Gemini provider from environment variable.

        Should read API key from GEMINI_API_KEY environment variable.
        """
        provider = GeminiProvider()

        assert provider.api_key == "env-api-key"

    def test_is_available_with_api_key(self):
        """
        Test availability check when API key is provided.

        Should return True when API key is available.
        """
        provider = GeminiProvider(api_key="test-key")
        assert provider.is_available() is True

    def test_is_available_without_api_key(self):
        """
        Test availability check when no API key is provided.

        Should return False when API key is missing.
        """
        with patch.dict(os.environ, {}, clear=True):
            provider = GeminiProvider()
            assert provider.is_available() is False

    @patch("src.infrastructure.llm_providers.gemini_provider.genai")
    def test_generate_response_success(self, mock_genai):
        """
        Test successful response generation.

        Should call Gemini API and return structured response.
        """
        # Mock the genai client and response
        mock_client = Mock()
        mock_genai.Client.return_value = mock_client

        mock_response = Mock()
        mock_response.text = "resolved-filename.md"
        mock_client.models.generate_content.return_value = mock_response

        provider = GeminiProvider(api_key="test-key")
        prompt = "Find the best matching file for [[My Note]]"

        result = provider.generate(prompt)

        assert isinstance(result, LLMResponse)
        assert result.content == "resolved-filename.md"
        assert 0.7 <= result.confidence <= 1.0  # Default confidence range
        assert "gemini" in result.reasoning.lower()

        # Verify API call
        mock_client.models.generate_content.assert_called_once()
        call_args = mock_client.models.generate_content.call_args
        assert call_args[1]["model"] == "gemini-2.5-flash"
        assert call_args[1]["contents"] == prompt

    @patch("src.infrastructure.llm_providers.gemini_provider.genai")
    def test_generate_response_with_custom_model(self, mock_genai):
        """
        Test response generation with custom model.

        Should use the specified model for API calls.
        """
        mock_client = Mock()
        mock_genai.Client.return_value = mock_client

        mock_response = Mock()
        mock_response.text = "result"
        mock_client.models.generate_content.return_value = mock_response

        provider = GeminiProvider(api_key="test-key", model_name="gemini-2.5-pro")
        result = provider.generate("test prompt")

        call_args = mock_client.models.generate_content.call_args
        assert call_args[1]["model"] == "gemini-2.5-pro"

    @patch("src.infrastructure.llm_providers.gemini_provider.genai")
    def test_generate_response_api_error(self, mock_genai):
        """
        Test handling of API errors.

        Should raise appropriate exception when API fails.
        """
        mock_client = Mock()
        mock_genai.Client.return_value = mock_client
        mock_client.models.generate_content.side_effect = Exception("API Error")

        provider = GeminiProvider(api_key="test-key")

        with pytest.raises(Exception, match="API Error"):
            provider.generate("test prompt")

    @pytest.mark.asyncio
    @patch("src.infrastructure.llm_providers.gemini_provider.genai")
    async def test_generate_async_response_success(self, mock_genai):
        """
        Test successful async response generation.

        Should handle async API calls properly.
        """
        mock_client = Mock()
        mock_genai.Client.return_value = mock_client

        # Mock async response
        mock_response = Mock()
        mock_response.text = "async-result.md"

        async def mock_async_generate(*args, **kwargs):
            return mock_response

        mock_client.models.generate_content_async = Mock(
            side_effect=mock_async_generate
        )

        provider = GeminiProvider(api_key="test-key")
        result = await provider.generate_async("test prompt")

        assert isinstance(result, LLMResponse)
        assert result.content == "async-result.md"
        mock_client.models.generate_content_async.assert_called_once()

    def test_estimate_confidence_from_response(self):
        """
        Test confidence estimation from response characteristics.

        Should estimate confidence based on response length and specificity.
        """
        provider = GeminiProvider(api_key="test-key")

        # High confidence - specific filename
        high_conf = provider._estimate_confidence("specific-filename.md")
        assert high_conf >= 0.8

        # Medium confidence - descriptive response
        medium_conf = provider._estimate_confidence(
            "The file you're looking for is probably project-notes.md based on similarity"
        )
        assert 0.5 <= medium_conf < 0.8

        # Low confidence - uncertain response
        low_conf = provider._estimate_confidence("I'm not sure, maybe try checking...")
        assert low_conf < 0.5

    def test_parse_wikilink_resolution_response(self):
        """
        Test parsing of wikilink resolution responses.

        Should extract filename from various response formats.
        """
        provider = GeminiProvider(api_key="test-key")

        # Simple filename response
        result1 = provider._parse_response("project-notes.md", "wikilink_resolution")
        assert result1.content == "project-notes.md"

        # Response with explanation
        result2 = provider._parse_response(
            "Based on the context, the best match is 'meeting-notes.md'",
            "wikilink_resolution",
        )
        assert "meeting-notes.md" in result2.content

    def test_format_wikilink_prompt(self):
        """
        Test formatting of wikilink resolution prompts.

        Should create effective prompts for the Gemini model.
        """
        provider = GeminiProvider(api_key="test-key")

        prompt = provider._format_wikilink_prompt(
            "[[Project Notes]]", ["project-notes.md", "project-planning.md", "notes.md"]
        )

        assert "[[Project Notes]]" in prompt
        assert "project-notes.md" in prompt
        assert "best match" in prompt.lower()
        assert "filename" in prompt.lower()

    def test_rate_limiting_headers(self):
        """
        Test handling of rate limiting from API.

        Should respect rate limits and handle 429 responses.
        """
        # This would be implemented when we add proper rate limiting
        # For now, just test that the provider can be configured with rate limits
        provider = GeminiProvider(api_key="test-key", requests_per_minute=30)
        assert hasattr(provider, "requests_per_minute")
        assert provider.requests_per_minute == 30

    def test_context_window_management(self):
        """
        Test handling of large prompts that exceed context window.

        Should truncate or summarize prompts appropriately.
        """
        provider = GeminiProvider(api_key="test-key")

        # Very long prompt that might exceed context window
        long_files_list = [f"file-{i}.md" for i in range(1000)]

        prompt = provider._format_wikilink_prompt("[[Test]]", long_files_list)

        # Should limit the number of files shown to prevent context overflow
        assert len(prompt) < 10000  # Reasonable limit
        assert "..." in prompt or len(
            [f for f in long_files_list if f in prompt]
        ) < len(long_files_list)
