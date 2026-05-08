"""Prompt Manager -- centralized prompt template management for all agents.

Manages versioned prompt templates with variable substitution. Templates
are organized by category and can be scoped to specific agents. Includes
built-in templates for common AI workforce patterns (classification,
resolution, action determination, reporting).
"""

import logging
import re
from datetime import datetime, timezone
from string import Template
from typing import Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Template model
# ---------------------------------------------------------------------------

class PromptTemplate(BaseModel):
    """A versioned prompt template with variable substitution support."""

    name: str = Field(..., description="Unique template name (e.g. 'classify_intent')")
    version: str = Field(default="1.0", description="Semantic version string")
    template_text: str = Field(..., description="Template text with ${variable} placeholders")
    variables: list[str] = Field(default_factory=list, description="Expected variable names")
    category: str = Field(default="general", description="Template category for organization")
    agent_id: Optional[str] = Field(default=None, description="Optional agent scope (None = global)")
    description: str = Field(default="", description="Human-readable description of the template")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO timestamp of creation",
    )


# ---------------------------------------------------------------------------
# Prompt Manager
# ---------------------------------------------------------------------------

class PromptManager:
    """Centralized prompt template management for the AI workforce platform.

    Stores versioned prompt templates organized by category. Templates use
    Python ``string.Template`` style ``${variable}`` placeholders for safe
    variable substitution at render time.

    Built-in templates cover common patterns used across agents:
    classification, resolution, action determination, and reporting.
    """

    # Recognized template categories
    CATEGORIES: list[str] = [
        "classification",
        "resolution",
        "action",
        "reporting",
        "general",
    ]

    def __init__(self):
        """Initialize the prompt manager and load built-in templates."""
        # Storage: {name: {version: PromptTemplate}}
        self._templates: dict[str, dict[str, PromptTemplate]] = {}
        self._load_builtin_templates()
        logger.info(
            "PromptManager initialized with %d built-in templates",
            sum(len(v) for v in self._templates.values()),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register_template(self, template: PromptTemplate) -> None:
        """Register a new prompt template (or a new version of an existing one).

        Args:
            template: The PromptTemplate to register.
        """
        if template.name not in self._templates:
            self._templates[template.name] = {}

        if template.version in self._templates[template.name]:
            logger.warning(
                "Overwriting template '%s' version '%s'",
                template.name,
                template.version,
            )

        self._templates[template.name][template.version] = template
        logger.debug(
            "Template registered: name=%s version=%s category=%s",
            template.name,
            template.version,
            template.category,
        )

    def get_template(
        self,
        name: str,
        version: str = "latest",
    ) -> PromptTemplate:
        """Retrieve a prompt template by name and version.

        Args:
            name: Template name.
            version: Version string, or ``"latest"`` for the newest version.

        Returns:
            The matching PromptTemplate.

        Raises:
            KeyError: If the template name or version is not found.
        """
        versions = self._templates.get(name)
        if not versions:
            raise KeyError(f"Template '{name}' not found")

        if version == "latest":
            # Return the highest version by semantic comparison
            latest_key = sorted(versions.keys(), key=self._version_sort_key)[-1]
            return versions[latest_key]

        if version not in versions:
            raise KeyError(
                f"Template '{name}' version '{version}' not found. "
                f"Available versions: {list(versions.keys())}"
            )
        return versions[version]

    def render(
        self,
        name: str,
        variables: dict[str, Any],
        version: str = "latest",
    ) -> str:
        """Render a template with variable substitution.

        Uses Python ``string.Template.safe_substitute`` so that missing
        variables are left as-is rather than raising an error.

        Args:
            name: Template name.
            variables: Dict of variable names to values.
            version: Version string, or ``"latest"``.

        Returns:
            Rendered prompt string.

        Raises:
            KeyError: If the template is not found.
        """
        template = self.get_template(name, version)
        tmpl = Template(template.template_text)
        rendered = tmpl.safe_substitute(**{k: str(v) for k, v in variables.items()})
        logger.debug("Rendered template '%s' (version=%s)", name, version)
        return rendered

    def list_templates(
        self,
        category: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> list[PromptTemplate]:
        """List templates, optionally filtered by category and/or agent.

        Args:
            category: Filter by category (e.g. ``"classification"``).
            agent_id: Filter by agent ID. ``None`` returns global templates.

        Returns:
            List of matching PromptTemplate objects (latest version of each).
        """
        results: list[PromptTemplate] = []
        for name, versions in self._templates.items():
            # Pick latest version
            latest_key = sorted(versions.keys(), key=self._version_sort_key)[-1]
            tmpl = versions[latest_key]

            if category is not None and tmpl.category != category:
                continue
            if agent_id is not None and tmpl.agent_id != agent_id:
                continue

            results.append(tmpl)
        return results

    def get_system_prompt(self, agent_id: str, task_type: str) -> str:
        """Convenience method to build a system prompt for an agent.

        Looks for an agent-specific template first (``{agent_id}_{task_type}``),
        then falls back to the generic task-type template, and finally falls
        back to a default system prompt.

        Args:
            agent_id: Agent identifier (e.g. ``"customer_ops"``).
            task_type: Task type (e.g. ``"classification"``).

        Returns:
            Rendered system prompt string.
        """
        # Try agent-specific template
        agent_template_name = f"{agent_id}_{task_type}"
        try:
            return self.get_template(agent_template_name).template_text
        except KeyError:
            pass

        # Try generic task-type template
        try:
            return self.get_template(task_type).template_text
        except KeyError:
            pass

        # Default system prompt
        return (
            f"You are an AI agent (id: {agent_id}) performing a "
            f"'{task_type}' task. Follow instructions carefully and "
            f"provide structured, actionable output."
        )

    # ------------------------------------------------------------------
    # Version helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _version_sort_key(version: str) -> tuple[int, ...]:
        """Parse a version string into a tuple for sorting.

        Handles versions like ``"1.0"``, ``"2.1.3"``, etc.  Non-numeric
        parts are treated as ``0``.
        """
        parts: list[int] = []
        for segment in version.split("."):
            try:
                parts.append(int(segment))
            except ValueError:
                parts.append(0)
        return tuple(parts)

    # ------------------------------------------------------------------
    # Built-in templates
    # ------------------------------------------------------------------

    def _load_builtin_templates(self) -> None:
        """Register the default set of built-in prompt templates."""

        builtins: list[PromptTemplate] = [
            # -- Classification templates --
            PromptTemplate(
                name="classify_intent",
                version="1.0",
                template_text=(
                    "Classify the following customer message into one of these categories: "
                    "${categories}.\n\n"
                    "Message: ${message}\n\n"
                    "Respond with a JSON object containing:\n"
                    "- \"intent\": the classified category\n"
                    "- \"confidence\": a float between 0 and 1\n"
                    "- \"reasoning\": brief explanation"
                ),
                variables=["categories", "message"],
                category="classification",
                description="Classify a customer message into predefined intent categories.",
            ),
            PromptTemplate(
                name="classify_sentiment",
                version="1.0",
                template_text=(
                    "Analyze the sentiment of the following message and classify it as "
                    "one of: positive, negative, neutral, mixed.\n\n"
                    "Message: ${message}\n\n"
                    "Additional context: ${context}\n\n"
                    "Respond with a JSON object containing:\n"
                    "- \"sentiment\": the sentiment label\n"
                    "- \"score\": a float from -1.0 (very negative) to 1.0 (very positive)\n"
                    "- \"reasoning\": brief explanation"
                ),
                variables=["message", "context"],
                category="classification",
                description="Analyze sentiment of a message on a scale from negative to positive.",
            ),
            PromptTemplate(
                name="extract_entities",
                version="1.0",
                template_text=(
                    "Extract key entities from the following text. Identify entity types "
                    "such as: ${entity_types}.\n\n"
                    "Text: ${text}\n\n"
                    "Respond with a JSON array of objects, each containing:\n"
                    "- \"entity\": the extracted entity text\n"
                    "- \"type\": the entity type\n"
                    "- \"confidence\": a float between 0 and 1"
                ),
                variables=["entity_types", "text"],
                category="classification",
                description="Extract named entities from unstructured text.",
            ),

            # -- Resolution templates --
            PromptTemplate(
                name="resolve_with_knowledge",
                version="1.0",
                template_text=(
                    "Using the following knowledge base articles, resolve the customer "
                    "query.\n\n"
                    "Knowledge articles:\n${articles}\n\n"
                    "Customer query: ${query}\n\n"
                    "Provide a clear resolution. If the articles do not contain "
                    "sufficient information, state what additional information is needed.\n\n"
                    "Respond with a JSON object containing:\n"
                    "- \"resolution\": the answer or resolution\n"
                    "- \"sources\": list of article IDs used\n"
                    "- \"confidence\": a float between 0 and 1\n"
                    "- \"needs_escalation\": boolean"
                ),
                variables=["articles", "query"],
                category="resolution",
                description="Resolve a customer query using knowledge base articles.",
            ),
            PromptTemplate(
                name="validate_data",
                version="1.0",
                template_text=(
                    "Validate the following data against the rules provided.\n\n"
                    "Data:\n${data}\n\n"
                    "Validation rules:\n${rules}\n\n"
                    "Respond with a JSON object containing:\n"
                    "- \"is_valid\": boolean\n"
                    "- \"violations\": list of rule violations (empty if valid)\n"
                    "- \"suggestions\": list of suggested corrections"
                ),
                variables=["data", "rules"],
                category="resolution",
                description="Validate data against a set of business rules.",
            ),

            # -- Action templates --
            PromptTemplate(
                name="determine_action",
                version="1.0",
                template_text=(
                    "Based on the analysis below, determine the best action to take.\n\n"
                    "Analysis:\n${analysis}\n\n"
                    "Available actions:\n${available_actions}\n\n"
                    "Constraints:\n${constraints}\n\n"
                    "Respond with a JSON object containing:\n"
                    "- \"action\": the chosen action identifier\n"
                    "- \"parameters\": dict of action parameters\n"
                    "- \"reasoning\": explanation for the choice\n"
                    "- \"confidence\": a float between 0 and 1"
                ),
                variables=["analysis", "available_actions", "constraints"],
                category="action",
                description="Determine the best action from available options based on analysis.",
            ),
            PromptTemplate(
                name="generate_response",
                version="1.0",
                template_text=(
                    "Generate a professional response based on the following context.\n\n"
                    "Tone: ${tone}\n"
                    "Customer name: ${customer_name}\n"
                    "Issue summary: ${issue_summary}\n"
                    "Resolution: ${resolution}\n\n"
                    "Guidelines:\n"
                    "- Be empathetic and professional\n"
                    "- Reference the specific issue\n"
                    "- Clearly state the resolution\n"
                    "- Include next steps if applicable\n\n"
                    "Generate the response text only, no JSON wrapping."
                ),
                variables=["tone", "customer_name", "issue_summary", "resolution"],
                category="action",
                description="Generate a professional customer-facing response.",
            ),
            PromptTemplate(
                name="score_candidate",
                version="1.0",
                template_text=(
                    "Score the following candidate against the job requirements.\n\n"
                    "Job requirements:\n${requirements}\n\n"
                    "Candidate profile:\n${candidate_profile}\n\n"
                    "Scoring criteria:\n${scoring_criteria}\n\n"
                    "Respond with a JSON object containing:\n"
                    "- \"overall_score\": integer 1-100\n"
                    "- \"category_scores\": dict of criteria to scores\n"
                    "- \"strengths\": list of candidate strengths\n"
                    "- \"gaps\": list of areas where candidate falls short\n"
                    "- \"recommendation\": one of 'strong_yes', 'yes', 'maybe', 'no'"
                ),
                variables=["requirements", "candidate_profile", "scoring_criteria"],
                category="action",
                description="Score a job candidate against specified requirements.",
            ),
            PromptTemplate(
                name="assess_risk",
                version="1.0",
                template_text=(
                    "Assess the risk level of the following scenario.\n\n"
                    "Scenario:\n${scenario}\n\n"
                    "Risk factors to consider:\n${risk_factors}\n\n"
                    "Historical context:\n${historical_context}\n\n"
                    "Respond with a JSON object containing:\n"
                    "- \"risk_level\": one of 'critical', 'high', 'medium', 'low'\n"
                    "- \"risk_score\": integer 1-100\n"
                    "- \"factors\": list of identified risk factors with severity\n"
                    "- \"mitigation\": list of recommended mitigation actions\n"
                    "- \"reasoning\": detailed explanation"
                ),
                variables=["scenario", "risk_factors", "historical_context"],
                category="action",
                description="Assess risk level for a given scenario with mitigation recommendations.",
            ),

            # -- Reporting templates --
            PromptTemplate(
                name="summarize_task",
                version="1.0",
                template_text=(
                    "Summarize the following task execution for stakeholder reporting.\n\n"
                    "Task ID: ${task_id}\n"
                    "Agent: ${agent_id}\n"
                    "Task type: ${task_type}\n"
                    "Input summary: ${input_summary}\n"
                    "Actions taken:\n${actions_taken}\n"
                    "Outcome: ${outcome}\n"
                    "Duration: ${duration}\n\n"
                    "Provide a concise summary suitable for a status report. "
                    "Include key metrics and any follow-up items."
                ),
                variables=[
                    "task_id", "agent_id", "task_type", "input_summary",
                    "actions_taken", "outcome", "duration",
                ],
                category="reporting",
                description="Summarize a completed task execution for stakeholder reporting.",
            ),

            # -- General templates --
            PromptTemplate(
                name="general_instruction",
                version="1.0",
                template_text=(
                    "You are an AI assistant within the KreupAI digital workforce platform.\n\n"
                    "Your role: ${role}\n"
                    "Current task: ${task}\n"
                    "Additional instructions: ${instructions}\n\n"
                    "Follow the instructions carefully and provide structured output."
                ),
                variables=["role", "task", "instructions"],
                category="general",
                description="General-purpose instruction template for any agent task.",
            ),
        ]

        for tmpl in builtins:
            self.register_template(tmpl)
