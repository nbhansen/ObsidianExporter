"""
Test cases for Obsidian callout parser functionality.

Following TDD approach - these tests define the expected behavior
for parsing and transforming Obsidian callouts to AppFlowy format.
"""

from src.infrastructure.parsers.callout_parser import CalloutParser


class TestCalloutParser:
    """Test suite for CalloutParser following TDD methodology."""

    def test_parse_basic_info_callout(self):
        """
        Test parsing of basic info callout without custom title.

        Should transform > [!info] to AppFlowy-compatible format.
        """
        parser = CalloutParser()
        content = """> [!info]
> This is an informational callout
> with multiple lines of content."""

        expected = """> ℹ️ **Info:**
> This is an informational callout
> with multiple lines of content."""

        result = parser.transform_callouts(content)
        assert result == expected

    def test_parse_warning_callout_with_custom_title(self):
        """
        Test parsing of warning callout with custom title.

        Should use custom title instead of default "Warning".
        """
        parser = CalloutParser()
        content = """> [!warning] Important Security Notice
> Your password will expire in 7 days.
> Please update it before then."""

        expected = """> ⚠️ **Important Security Notice:**
> Your password will expire in 7 days.
> Please update it before then."""

        result = parser.transform_callouts(content)
        assert result == expected

    def test_parse_all_predefined_callout_types(self):
        """
        Test parsing of all 13 predefined Obsidian callout types.

        Should correctly map each type to its emoji and format.
        """
        parser = CalloutParser()

        test_cases = [
            ("[!note]", "📝 **Note:**"),
            ("[!abstract]", "📄 **Abstract:**"),
            ("[!summary]", "📄 **Summary:**"),
            ("[!tldr]", "📄 **TL;DR:**"),
            ("[!info]", "ℹ️ **Info:**"),
            ("[!todo]", "✅ **Todo:**"),
            ("[!tip]", "💡 **Tip:**"),
            ("[!hint]", "💡 **Hint:**"),
            ("[!important]", "💡 **Important:**"),
            ("[!success]", "✅ **Success:**"),
            ("[!check]", "✅ **Check:**"),
            ("[!done]", "✅ **Done:**"),
            ("[!question]", "❓ **Question:**"),
            ("[!help]", "❓ **Help:**"),
            ("[!faq]", "❓ **FAQ:**"),
            ("[!warning]", "⚠️ **Warning:**"),
            ("[!caution]", "⚠️ **Caution:**"),
            ("[!attention]", "⚠️ **Attention:**"),
            ("[!failure]", "❌ **Failure:**"),
            ("[!fail]", "❌ **Fail:**"),
            ("[!missing]", "❌ **Missing:**"),
            ("[!danger]", "⚡ **Danger:**"),
            ("[!error]", "⚡ **Error:**"),
            ("[!bug]", "🐛 **Bug:**"),
            ("[!example]", "📋 **Example:**"),
            ("[!quote]", "💬 **Quote:**"),
            ("[!cite]", "💬 **Cite:**"),
        ]

        for callout_type, expected_prefix in test_cases:
            content = f"> {callout_type}\n> Test content"
            expected = f"> {expected_prefix}\n> Test content"
            result = parser.transform_callouts(content)
            assert result == expected, f"Failed for callout type: {callout_type}"

    def test_parse_case_insensitive_callout_types(self):
        """
        Test that callout types are case-insensitive.

        [!INFO], [!Info], [!info] should all work the same.
        """
        parser = CalloutParser()

        test_cases = [
            "> [!INFO]\n> Content",
            "> [!Info]\n> Content",
            "> [!info]\n> Content",
            "> [!iNfO]\n> Content",
        ]

        expected = "> ℹ️ **Info:**\n> Content"

        for content in test_cases:
            result = parser.transform_callouts(content)
            assert result == expected

    def test_parse_collapsible_callout_markers(self):
        """
        Test that collapsible markers (+/-) are stripped from output.

        [!info]+, [!info]-, [!info] should all transform the same way.
        """
        parser = CalloutParser()

        test_cases = [
            "> [!info]+\n> Expandable content",
            "> [!info]-\n> Collapsible content",
            "> [!info]\n> Regular content",
        ]

        for content in test_cases:
            result = parser.transform_callouts(content)
            assert "> ℹ️ **Info:**" in result
            assert "+" not in result
            assert "-" not in result  # Only the collapsible marker, not content dashes

    def test_parse_unknown_callout_type(self):
        """
        Test handling of unknown/custom callout types.

        Should use generic format with capitalized type name.
        """
        parser = CalloutParser()
        content = """> [!custom]
> This is a custom callout type
> that isn't predefined."""

        expected = """> **Custom:**
> This is a custom callout type
> that isn't predefined."""

        result = parser.transform_callouts(content)
        assert result == expected

    def test_parse_multiple_callouts_in_content(self):
        """
        Test parsing multiple callouts within the same content.

        Should transform each callout independently.
        """
        parser = CalloutParser()
        content = """# Document with Multiple Callouts

> [!info]
> This is important information.

Some regular content here.

> [!warning] Critical Alert
> This is a warning message.

More content.

> [!tip]
> Here's a helpful tip."""

        result = parser.transform_callouts(content)

        # Should contain all transformed callouts
        assert "> ℹ️ **Info:**" in result
        assert "> ⚠️ **Critical Alert:**" in result
        assert "> 💡 **Tip:**" in result

        # Should preserve non-callout content
        assert "# Document with Multiple Callouts" in result
        assert "Some regular content here." in result
        assert "More content." in result

    def test_parse_callout_with_empty_content(self):
        """
        Test parsing callout with no content lines.

        Should handle edge case gracefully.
        """
        parser = CalloutParser()
        content = "> [!note]"

        expected = "> 📝 **Note:**"

        result = parser.transform_callouts(content)
        assert result == expected

    def test_parse_callout_with_complex_content(self):
        """
        Test parsing callout containing complex markdown.

        Should preserve internal markdown formatting.
        """
        parser = CalloutParser()
        content = """> [!example] Code Example
> Here's how to use `markdown`:
>
> ```python
> def hello():
>     print("Hello, World!")
> ```
>
> - List item 1
> - List item 2
>
> **Bold text** and *italic text*."""

        result = parser.transform_callouts(content)

        # Should transform the callout header
        assert "> 📋 **Code Example:**" in result

        # Should preserve internal markdown
        assert "> Here's how to use `markdown`:" in result
        assert "> ```python" in result
        assert "> def hello():" in result
        assert "> - List item 1" in result
        assert "> **Bold text** and *italic text*." in result

    def test_preserve_non_callout_blockquotes(self):
        """
        Test that regular blockquotes are not transformed.

        Only lines matching callout pattern should be changed.
        """
        parser = CalloutParser()
        content = """> This is a regular blockquote
> without any callout syntax.

> [!info]
> This is an actual callout.

> Another regular blockquote
> that should remain unchanged."""

        result = parser.transform_callouts(content)

        # Should preserve regular blockquotes
        assert "> This is a regular blockquote" in result
        assert "> without any callout syntax." in result
        assert "> Another regular blockquote" in result
        assert "> that should remain unchanged." in result

        # Should transform actual callout
        assert "> ℹ️ **Info:**" in result

    def test_parse_mixed_content_with_callouts(self):
        """
        Test parsing content that mixes callouts with other elements.

        Should only transform callout blocks, leave everything else intact.
        """
        parser = CalloutParser()
        content = """# Main Title

Regular paragraph with some text.

> [!tip] Pro Tip
> This is helpful advice.

## Subsection

1. Numbered list item
2. Another item

> Regular quote without callout syntax
> This should not be transformed.

> [!warning]
> This is a warning.

Final paragraph."""

        result = parser.transform_callouts(content)

        # Non-callout content should be unchanged
        assert "# Main Title" in result
        assert "Regular paragraph with some text." in result
        assert "## Subsection" in result
        assert "1. Numbered list item" in result
        assert "Final paragraph." in result

        # Regular blockquote should be unchanged
        assert "> Regular quote without callout syntax" in result
        assert "> This should not be transformed." in result

        # Callouts should be transformed
        assert "> 💡 **Pro Tip:**" in result
        assert "> ⚠️ **Warning:**" in result
