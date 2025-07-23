"""
Test cases for LLM assistant functionality.

Following TDD approach - these tests define the expected behavior
for the LLM abstraction layer that provides intelligent fallback
for complex parsing scenarios.
"""

from unittest.mock import Mock

from src.domain.llm_assistant import (
    LLMAssistant,
    LLMProvider,
    LLMResponse,
    ParseAssistanceRequest,
    ParseAssistanceType,
)


class TestLLMAssistant:
    """Test suite for LLMAssistant following TDD methodology."""

    def test_create_llm_assistant_with_provider(self):
        """
        Test creating LLM assistant with a specific provider.

        Should initialize with the given provider and configuration.
        """
        mock_provider = Mock(spec=LLMProvider)
        assistant = LLMAssistant(provider=mock_provider)

        assert assistant.provider == mock_provider
        assert assistant.is_available() == mock_provider.is_available.return_value

    def test_llm_assistant_graceful_degradation(self):
        """
        Test that LLM assistant handles unavailable provider gracefully.

        Should return None for assistance requests when provider unavailable.
        """
        mock_provider = Mock(spec=LLMProvider)
        mock_provider.is_available.return_value = False

        assistant = LLMAssistant(provider=mock_provider)

        request = ParseAssistanceRequest(
            type=ParseAssistanceType.WIKILINK_RESOLUTION,
            content="[[My Important Note]]",
            context={"vault_files": ["my-important-notes.md", "other-note.md"]},
        )

        result = assistant.get_assistance(request)
        assert result is None
        mock_provider.generate.assert_not_called()

    def test_fuzzy_wikilink_resolution(self):
        """
        Test LLM assistance for fuzzy wikilink resolution.

        Should suggest best matching file when exact match fails.
        """
        mock_provider = Mock(spec=LLMProvider)
        mock_provider.is_available.return_value = True
        mock_provider.generate.return_value = LLMResponse(
            content="my-important-notes.md",
            confidence=0.85,
            reasoning="Found similar file with matching keywords",
        )

        assistant = LLMAssistant(provider=mock_provider)

        request = ParseAssistanceRequest(
            type=ParseAssistanceType.WIKILINK_RESOLUTION,
            content="[[My Important Note]]",
            context={
                "vault_files": [
                    "my-important-notes.md",
                    "other-note.md",
                    "unrelated.md",
                ],
                "current_file": "index.md",
            },
        )

        result = assistant.get_assistance(request)

        assert result is not None
        assert result.content == "my-important-notes.md"
        assert result.confidence >= 0.8
        assert "similar" in result.reasoning.lower()

    def test_complex_nested_structure_parsing(self):
        """
        Test LLM assistance for complex nested markdown structures.

        Should help parse nested callouts with embedded wikilinks.
        """
        complex_content = """
> [!info] Parent Callout
> Some introductory text
> > [!warning] Nested Warning
> > This contains [[complex|link]] and more
> > > Even deeper nesting with ^block-ref
> Back to parent level
"""

        expected_structure = {
            "type": "callout",
            "callout_type": "info",
            "title": "Parent Callout",
            "children": [
                {"type": "text", "content": "Some introductory text"},
                {
                    "type": "callout",
                    "callout_type": "warning",
                    "title": "Nested Warning",
                    "children": [
                        {
                            "type": "text",
                            "content": "This contains [[complex|link]] and more",
                            "wikilinks": [{"target": "complex", "alias": "link"}],
                        },
                        {
                            "type": "nested_content",
                            "content": "Even deeper nesting with ^block-ref",
                            "block_refs": ["block-ref"],
                        },
                    ],
                },
                {"type": "text", "content": "Back to parent level"},
            ],
        }

        mock_provider = Mock(spec=LLMProvider)
        mock_provider.is_available.return_value = True
        mock_provider.generate.return_value = LLMResponse(
            content=str(expected_structure),
            confidence=0.9,
            reasoning="Successfully parsed nested structure",
        )

        assistant = LLMAssistant(provider=mock_provider)

        request = ParseAssistanceRequest(
            type=ParseAssistanceType.COMPLEX_STRUCTURE,
            content=complex_content,
            context={"parse_type": "nested_callouts"},
        )

        result = assistant.get_assistance(request)

        assert result is not None
        assert result.confidence >= 0.8
        # The actual structure parsing would be validated by the caller

    def test_cache_llm_responses(self):
        """
        Test that LLM responses are cached to avoid repeated API calls.

        Should return cached response for identical requests.
        """
        mock_provider = Mock(spec=LLMProvider)
        mock_provider.is_available.return_value = True
        mock_provider.generate.return_value = LLMResponse(
            content="cached-result.md", confidence=0.9, reasoning="Cached response"
        )

        assistant = LLMAssistant(provider=mock_provider, enable_cache=True)

        request = ParseAssistanceRequest(
            type=ParseAssistanceType.WIKILINK_RESOLUTION,
            content="[[Repeated Request]]",
            context={"vault_files": ["file1.md", "file2.md"]},
        )

        # First call
        result1 = assistant.get_assistance(request)
        assert mock_provider.generate.call_count == 1

        # Second call with same request
        result2 = assistant.get_assistance(request)
        assert mock_provider.generate.call_count == 1  # Should not increase
        assert result1.content == result2.content

    def test_rate_limiting(self):
        """
        Test that LLM assistant respects rate limits.

        Should throttle requests when rate limit is reached.
        """
        mock_provider = Mock(spec=LLMProvider)
        mock_provider.is_available.return_value = True
        mock_provider.generate.return_value = LLMResponse(
            content="result", confidence=0.9, reasoning="Test"
        )

        # Configure with low rate limit for testing
        assistant = LLMAssistant(
            provider=mock_provider, rate_limit_per_minute=2, enable_cache=False
        )

        request = ParseAssistanceRequest(
            type=ParseAssistanceType.WIKILINK_RESOLUTION,
            content="[[Test]]",
            context={},
        )

        # Make requests up to rate limit
        result1 = assistant.get_assistance(request)
        assert result1 is not None

        result2 = assistant.get_assistance(request)
        assert result2 is not None

        # Third request should be rate limited
        result3 = assistant.get_assistance(request)
        assert result3 is None  # Rate limited

    def test_parse_ambiguous_syntax(self):
        """
        Test LLM assistance for ambiguous markdown syntax.

        Should help interpret edge cases like triple brackets.
        """
        mock_provider = Mock(spec=LLMProvider)
        mock_provider.is_available.return_value = True
        mock_provider.generate.return_value = LLMResponse(
            content='{"interpretation": "nested_wikilink", "target": "triple brackets"}',
            confidence=0.75,
            reasoning="Triple brackets likely a typo for nested wikilink",
        )

        assistant = LLMAssistant(provider=mock_provider)

        request = ParseAssistanceRequest(
            type=ParseAssistanceType.AMBIGUOUS_SYNTAX,
            content="This has [[[triple brackets]]] in it",
            context={"syntax_type": "brackets"},
        )

        result = assistant.get_assistance(request)

        assert result is not None
        assert result.confidence >= 0.7
        assert "triple brackets" in result.content

    def test_confidence_threshold(self):
        """
        Test that results below confidence threshold are filtered.

        Should return None if LLM confidence is too low.
        """
        mock_provider = Mock(spec=LLMProvider)
        mock_provider.is_available.return_value = True
        mock_provider.generate.return_value = LLMResponse(
            content="uncertain-result.md",
            confidence=0.3,  # Low confidence
            reasoning="Not sure about this match",
        )

        assistant = LLMAssistant(provider=mock_provider, min_confidence_threshold=0.6)

        request = ParseAssistanceRequest(
            type=ParseAssistanceType.WIKILINK_RESOLUTION,
            content="[[Ambiguous]]",
            context={},
        )

        result = assistant.get_assistance(request)
        assert result is None  # Filtered due to low confidence

    def test_provider_error_handling(self):
        """
        Test graceful handling of provider errors.

        Should return None and log error when provider fails.
        """
        mock_provider = Mock(spec=LLMProvider)
        mock_provider.is_available.return_value = True
        mock_provider.generate.side_effect = Exception("API Error")

        assistant = LLMAssistant(provider=mock_provider)

        request = ParseAssistanceRequest(
            type=ParseAssistanceType.WIKILINK_RESOLUTION,
            content="[[Test]]",
            context={},
        )

        result = assistant.get_assistance(request)
        assert result is None  # Graceful failure

    def test_format_prompt_for_wikilink_resolution(self):
        """
        Test prompt formatting for wikilink resolution requests.

        Should create appropriate prompt with context.
        """
        assistant = LLMAssistant(provider=Mock(spec=LLMProvider))

        request = ParseAssistanceRequest(
            type=ParseAssistanceType.WIKILINK_RESOLUTION,
            content="[[Project Notes]]",
            context={
                "vault_files": [
                    "project-notes.md",
                    "project-planning.md",
                    "notes/projects.md",
                ],
                "current_file": "index.md",
            },
        )

        prompt = assistant._format_prompt(request)

        assert "[[Project Notes]]" in prompt
        assert "project-notes.md" in prompt
        assert "wikilink" in prompt.lower()
        assert "best match" in prompt.lower()
