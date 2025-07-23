"""
Test cases for fallback parser functionality.

Following TDD approach - these tests define the expected behavior
for the fallback parser that uses LLM assistance when standard
parsing methods are insufficient.
"""

from pathlib import Path
from unittest.mock import Mock

from src.domain.fallback_parser import FallbackParser, ParsingComplexity
from src.domain.llm_assistant import LLMResponse
from src.domain.models import ResolvedWikiLink, WikiLink


class TestFallbackParser:
    """Test suite for FallbackParser following TDD methodology."""

    def test_detect_parsing_complexity(self):
        """
        Test detection of content complexity that requires fallback.

        Should identify when content is too complex for standard parsing.
        """
        parser = FallbackParser(llm_assistant=Mock())

        # Simple cases should not need fallback
        simple_content = "This is [[simple link]] text."
        assert parser.assess_complexity(simple_content) == ParsingComplexity.SIMPLE

        # Nested structures should be marked as complex
        complex_content = """
> [!info] Outer
> > [!warning] Inner with [[link|alias]]
> > > Triple nested with ^block-ref
"""
        assert parser.assess_complexity(complex_content) == ParsingComplexity.COMPLEX

        # Ambiguous syntax should be marked as ambiguous
        ambiguous_content = "This has [[[triple brackets]]] syntax"
        assert (
            parser.assess_complexity(ambiguous_content) == ParsingComplexity.AMBIGUOUS
        )

    def test_fallback_wikilink_resolution(self):
        """
        Test fallback wikilink resolution using LLM assistance.

        Should use LLM to resolve wikilinks when standard resolution fails.
        """
        # Mock LLM assistant
        mock_llm = Mock()
        mock_llm.is_available.return_value = True
        mock_llm.get_assistance.return_value = LLMResponse(
            content="project-planning-notes.md",
            confidence=0.85,
            reasoning="Found file with similar name pattern",
        )

        parser = FallbackParser(llm_assistant=mock_llm)

        # Wikilink that failed standard resolution
        failed_wikilink = WikiLink(
            original="[[Project Planning Note]]",
            target="Project Planning Note",
            alias=None,
            header=None,
            block_id=None,
            is_embed=False,
        )

        # Available files in vault
        vault_files = [
            Path("project-planning-notes.md"),
            Path("project-overview.md"),
            Path("planning/notes.md"),
        ]

        result = parser.resolve_wikilink_fallback(
            wikilink=failed_wikilink,
            vault_files=vault_files,
            current_file=Path("index.md"),
        )

        assert isinstance(result, ResolvedWikiLink)
        assert result.resolved_path == Path("project-planning-notes.md")
        assert result.is_broken is False
        assert result.resolution_method == "llm_fuzzy_match"
        assert result.confidence == 0.85

    def test_fallback_with_unavailable_llm(self):
        """
        Test fallback behavior when LLM is unavailable.

        Should return None when LLM assistance is not available.
        """
        mock_llm = Mock()
        mock_llm.is_available.return_value = False

        parser = FallbackParser(llm_assistant=mock_llm)

        failed_wikilink = WikiLink(
            original="[[Unknown Note]]",
            target="Unknown Note",
            alias=None,
            header=None,
            block_id=None,
            is_embed=False,
        )

        result = parser.resolve_wikilink_fallback(
            wikilink=failed_wikilink, vault_files=[], current_file=Path("test.md")
        )

        assert result is None
        mock_llm.get_assistance.assert_not_called()

    def test_parse_complex_nested_structure(self):
        """
        Test parsing of complex nested structures with LLM assistance.

        Should handle deeply nested callouts and mixed content.
        """
        mock_llm = Mock()
        mock_llm.is_available.return_value = True
        mock_llm.get_assistance.return_value = LLMResponse(
            content="""{
                "type": "callout",
                "callout_type": "info",
                "children": [
                    {"type": "callout", "callout_type": "warning", "nested": true}
                ]
            }""",
            confidence=0.9,
            reasoning="Successfully parsed nested structure",
        )

        parser = FallbackParser(llm_assistant=mock_llm)

        complex_content = """
> [!info] Complex Structure
> > [!warning] Nested with [[link]]
> > More content
"""

        result = parser.parse_complex_structure(complex_content)

        assert result is not None
        assert result["type"] == "callout"
        assert mock_llm.get_assistance.called

    def test_confidence_based_fallback_decision(self):
        """
        Test that fallback is only used when confidence is low.

        Should check standard parser confidence before using fallback.
        """
        mock_llm = Mock()
        parser = FallbackParser(llm_assistant=mock_llm, confidence_threshold=0.7)

        # High confidence from standard parser - no fallback needed
        high_confidence_result = ResolvedWikiLink(
            original=Mock(),
            resolved_path=Path("found.md"),
            is_broken=False,
            target_exists=True,
            resolution_method="exact_match",
            confidence=0.95,
        )

        should_fallback = parser.should_use_fallback(high_confidence_result)
        assert should_fallback is False

        # Low confidence - fallback needed
        low_confidence_result = ResolvedWikiLink(
            original=Mock(),
            resolved_path=Path("maybe.md"),
            is_broken=False,
            target_exists=True,
            resolution_method="fuzzy_match",
            confidence=0.5,
        )

        should_fallback = parser.should_use_fallback(low_confidence_result)
        assert should_fallback is True

    def test_parse_ambiguous_bracket_syntax(self):
        """
        Test parsing of ambiguous bracket syntax variations.

        Should handle edge cases like triple brackets intelligently.
        """
        mock_llm = Mock()
        mock_llm.is_available.return_value = True
        mock_llm.get_assistance.return_value = LLMResponse(
            content='{"type": "wikilink", "target": "triple brackets", "corrected": "[[triple brackets]]"}',
            confidence=0.8,
            reasoning="Triple brackets likely a typo",
        )

        parser = FallbackParser(llm_assistant=mock_llm)

        ambiguous = "Text with [[[triple brackets]]] issue"
        result = parser.parse_ambiguous_syntax(ambiguous)

        assert result is not None
        assert result["corrected"] == "[[triple brackets]]"
        assert result["type"] == "wikilink"

    def test_caching_fallback_results(self):
        """
        Test that fallback results are cached appropriately.

        Should not call LLM twice for identical requests.
        """
        mock_llm = Mock()
        mock_llm.is_available.return_value = True
        mock_llm.get_assistance.return_value = LLMResponse(
            content="cached-result.md", confidence=0.9, reasoning="Cached"
        )

        parser = FallbackParser(llm_assistant=mock_llm, enable_cache=True)

        wikilink = WikiLink(
            original="[[Cached Link]]",
            target="Cached Link",
            alias=None,
            header=None,
            block_id=None,
            is_embed=False,
        )

        vault_files = [Path("cached-result.md")]

        # First call
        result1 = parser.resolve_wikilink_fallback(
            wikilink, vault_files, Path("test.md")
        )

        # Second call with same parameters
        result2 = parser.resolve_wikilink_fallback(
            wikilink, vault_files, Path("test.md")
        )

        # LLM should only be called once
        assert mock_llm.get_assistance.call_count == 1
        assert result1.resolved_path == result2.resolved_path

    def test_fallback_with_context_hints(self):
        """
        Test fallback resolution with additional context hints.

        Should use surrounding content to improve resolution accuracy.
        """
        mock_llm = Mock()
        mock_llm.is_available.return_value = True
        mock_llm.get_assistance.return_value = LLMResponse(
            content="machine-learning-notes.md",
            confidence=0.9,
            reasoning="Context suggests ML-related content",
        )

        parser = FallbackParser(llm_assistant=mock_llm)

        wikilink = WikiLink(
            original="[[ML Notes]]",
            target="ML Notes",
            alias=None,
            header=None,
            block_id=None,
            is_embed=False,
        )

        # Provide context from surrounding text
        context = {
            "surrounding_text": "discussing neural networks and deep learning",
            "section_header": "Machine Learning Research",
        }

        vault_files = [
            Path("machine-learning-notes.md"),
            Path("ml-projects.md"),
            Path("notes/ml-theory.md"),
        ]

        result = parser.resolve_wikilink_fallback(
            wikilink=wikilink,
            vault_files=vault_files,
            current_file=Path("research.md"),
            context=context,
        )

        assert result.resolved_path == Path("machine-learning-notes.md")
        assert result.confidence >= 0.85

    def test_batch_fallback_processing(self):
        """
        Test batch processing of multiple fallback requests.

        Should efficiently handle multiple items needing fallback.
        """
        mock_llm = Mock()
        mock_llm.is_available.return_value = True

        parser = FallbackParser(llm_assistant=mock_llm)

        # Multiple wikilinks that need fallback
        wikilinks = [
            WikiLink("[[Note One]]", "Note One", None, None, None, False),
            WikiLink("[[Note Two]]", "Note Two", None, None, None, False),
            WikiLink("[[Note Three]]", "Note Three", None, None, None, False),
        ]

        # Mock individual processing responses
        responses = [
            LLMResponse("note-one.md", 0.9, "Found match"),
            LLMResponse("note-two.md", 0.85, "Found match"),
            LLMResponse("note-three.md", 0.8, "Found match"),
        ]
        mock_llm.get_assistance.side_effect = responses

        results = parser.resolve_wikilinks_batch_fallback(
            wikilinks=wikilinks,
            vault_files=[
                Path("note-one.md"),
                Path("note-two.md"),
                Path("note-three.md"),
            ],
            current_file=Path("index.md"),
        )

        assert len(results) == 3
        assert all(not r.is_broken for r in results)
        assert results[0].resolved_path == Path("note-one.md")
