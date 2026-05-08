"""Tests for PromptManager.

Verifies built-in template retrieval, variable rendering, custom
template registration, and category-based listing.
"""

import pytest

from llm.prompt_manager import PromptManager, PromptTemplate


class TestPromptManager:
    """Tests for the PromptManager class."""

    def test_get_builtin_template(self):
        """Built-in templates are available after initialization."""
        pm = PromptManager()

        template = pm.get_template("classify_intent")

        assert isinstance(template, PromptTemplate)
        assert template.name == "classify_intent"
        assert template.category == "classification"
        assert template.version == "1.0"
        assert "${categories}" in template.template_text
        assert "${message}" in template.template_text

    def test_render_template(self):
        """Rendering a template substitutes variables correctly."""
        pm = PromptManager()

        rendered = pm.render(
            "classify_intent",
            variables={
                "categories": "billing, shipping, returns, general",
                "message": "I want to return my order",
            },
        )

        assert "billing, shipping, returns, general" in rendered
        assert "I want to return my order" in rendered
        # Template placeholders should be replaced
        assert "${categories}" not in rendered
        assert "${message}" not in rendered

    def test_register_custom_template(self):
        """Custom templates can be registered and retrieved."""
        pm = PromptManager()

        custom = PromptTemplate(
            name="custom_greeting",
            version="1.0",
            template_text="Hello ${name}, welcome to ${company}!",
            variables=["name", "company"],
            category="general",
            description="A custom greeting template",
        )

        pm.register_template(custom)

        retrieved = pm.get_template("custom_greeting")
        assert retrieved.name == "custom_greeting"
        assert retrieved.description == "A custom greeting template"

        rendered = pm.render(
            "custom_greeting",
            variables={"name": "Alice", "company": "KreupAI"},
        )
        assert "Hello Alice, welcome to KreupAI!" == rendered

    def test_list_templates_by_category(self):
        """Templates can be filtered by category."""
        pm = PromptManager()

        classification_templates = pm.list_templates(category="classification")
        action_templates = pm.list_templates(category="action")
        reporting_templates = pm.list_templates(category="reporting")

        # classification should include classify_intent, classify_sentiment, extract_entities
        assert len(classification_templates) >= 3
        assert all(t.category == "classification" for t in classification_templates)

        # action should include determine_action, generate_response, score_candidate, assess_risk
        assert len(action_templates) >= 4
        assert all(t.category == "action" for t in action_templates)

        # reporting should include summarize_task
        assert len(reporting_templates) >= 1
        assert all(t.category == "reporting" for t in reporting_templates)

    def test_get_template_not_found_raises(self):
        """Requesting a nonexistent template raises KeyError."""
        pm = PromptManager()

        with pytest.raises(KeyError, match="not found"):
            pm.get_template("nonexistent_template")

    def test_render_with_missing_variables(self):
        """Missing variables are left as placeholders (safe_substitute)."""
        pm = PromptManager()

        rendered = pm.render(
            "classify_intent",
            variables={"categories": "billing, returns"},
            # Intentionally omitting "message"
        )

        assert "billing, returns" in rendered
        # safe_substitute leaves missing vars as-is
        assert "${message}" in rendered
