"""Search and knowledge retrieval tools for the AI Digital Workforce Platform.

Provides tools for semantic vector search across a knowledge base and
direct article lookup by ID or topic. All tools return realistic mock data
for local development.
"""

import logging
from datetime import datetime
from typing import Any

from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mock data
# ---------------------------------------------------------------------------

_MOCK_KB_ARTICLES: list[dict[str, Any]] = [
    {
        "id": "kb_001",
        "title": "Getting Started with the AI Workforce Platform",
        "content": (
            "The AI Digital Workforce Platform allows you to deploy intelligent "
            "agents that automate business processes. This guide covers initial "
            "setup, agent configuration, and connecting your first integration.\n\n"
            "Step 1: Configure your workspace.\n"
            "Step 2: Define agent roles and capabilities.\n"
            "Step 3: Connect CRM, ERP, and email integrations.\n"
            "Step 4: Deploy your first agent workflow."
        ),
        "category": "onboarding",
        "tags": ["getting-started", "setup", "agents", "integrations"],
        "last_updated": "2026-02-15T10:00:00Z",
        "author": "Product Team",
    },
    {
        "id": "kb_002",
        "title": "CRM Integration Guide",
        "content": (
            "Connecting your CRM system to the AI platform enables agents to "
            "search contacts, update leads, and log activities automatically.\n\n"
            "Supported CRM systems: Salesforce, HubSpot, Dynamics 365.\n\n"
            "Configuration steps:\n"
            "1. Navigate to Settings > Integrations > CRM.\n"
            "2. Select your CRM provider and enter API credentials.\n"
            "3. Map custom fields to the platform schema.\n"
            "4. Test the connection and verify data sync."
        ),
        "category": "integrations",
        "tags": ["crm", "salesforce", "hubspot", "configuration"],
        "last_updated": "2026-03-01T14:30:00Z",
        "author": "Engineering Team",
    },
    {
        "id": "kb_003",
        "title": "Purchase Order Approval Workflow",
        "content": (
            "Purchase orders created through the platform follow a multi-step "
            "approval workflow:\n\n"
            "1. Agent creates PO based on request.\n"
            "2. Budget check is performed automatically.\n"
            "3. PO is routed to the appropriate approver based on amount:\n"
            "   - Under $5,000: Auto-approved\n"
            "   - $5,000 - $50,000: Manager approval\n"
            "   - Over $50,000: VP approval required\n"
            "4. Approved PO is sent to the vendor."
        ),
        "category": "workflows",
        "tags": ["purchase-order", "approval", "erp", "procurement"],
        "last_updated": "2026-02-20T11:15:00Z",
        "author": "Operations Team",
    },
    {
        "id": "kb_004",
        "title": "Data Security and Compliance",
        "content": (
            "The platform implements enterprise-grade security controls:\n\n"
            "- All data encrypted at rest (AES-256) and in transit (TLS 1.3).\n"
            "- Role-based access control (RBAC) for all resources.\n"
            "- Audit logging for every agent action.\n"
            "- SOC 2 Type II and ISO 27001 certified.\n"
            "- GDPR and CCPA compliant data handling.\n\n"
            "For compliance questions, contact security@company.com."
        ),
        "category": "security",
        "tags": ["security", "compliance", "gdpr", "encryption", "audit"],
        "last_updated": "2026-03-05T09:00:00Z",
        "author": "Security Team",
    },
    {
        "id": "kb_005",
        "title": "Troubleshooting Agent Errors",
        "content": (
            "Common agent errors and their resolutions:\n\n"
            "ERROR: ToolExecutionTimeout\n"
            "  Cause: External API did not respond within the timeout.\n"
            "  Fix: Check integration health in Settings > Integrations.\n\n"
            "ERROR: InsufficientPermissions\n"
            "  Cause: Agent role lacks required permission.\n"
            "  Fix: Update role permissions in Settings > Roles.\n\n"
            "ERROR: RateLimitExceeded\n"
            "  Cause: Too many API calls in a short period.\n"
            "  Fix: Configure rate limiting in agent settings."
        ),
        "category": "troubleshooting",
        "tags": ["errors", "debugging", "agents", "support"],
        "last_updated": "2026-03-08T16:45:00Z",
        "author": "Support Team",
    },
]


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


class SemanticSearchTool(BaseTool):
    """Perform semantic (vector) search across the knowledge base."""

    @property
    def name(self) -> str:
        return "semantic_search"

    @property
    def description(self) -> str:
        return (
            "Search the knowledge base using semantic (vector) similarity. "
            "Finds articles and content that are conceptually related to the "
            "query, even without exact keyword matches. Supports namespace "
            "filtering and metadata filters."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language search query.",
                },
                "namespace": {
                    "type": "string",
                    "description": "Namespace to restrict the search to (e.g. 'docs', 'policies').",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return.",
                    "default": 5,
                },
                "filters": {
                    "type": "object",
                    "description": "Metadata filters to apply (e.g. {\"category\": \"security\"}).",
                },
            },
            "required": ["query"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        query = params.get("query")
        namespace = params.get("namespace")
        limit = params.get("limit", 5)
        filters = params.get("filters", {})

        if not query:
            return self.error_result("query is required")

        logger.info(
            "Semantic search: query=%r namespace=%r limit=%d filters=%r",
            query,
            namespace,
            limit,
            filters,
        )

        query_lower = query.lower()

        # Simple keyword-based relevance scoring for mock purposes
        scored_articles: list[tuple[float, dict[str, Any]]] = []
        for article in _MOCK_KB_ARTICLES:
            # Apply metadata filters
            if filters:
                skip = False
                for key, value in filters.items():
                    article_value = article.get(key)
                    if isinstance(article_value, list):
                        if value not in article_value:
                            skip = True
                            break
                    elif article_value != value:
                        skip = True
                        break
                if skip:
                    continue

            # Calculate mock relevance score
            score = 0.0
            searchable = f"{article['title']} {article['content']} {' '.join(article['tags'])}".lower()
            query_words = query_lower.split()
            for word in query_words:
                if word in searchable:
                    score += 0.2
            # Cap at 0.99
            score = min(round(score, 2), 0.99)
            if score > 0:
                scored_articles.append((score, article))

        # Sort by score descending
        scored_articles.sort(key=lambda x: x[0], reverse=True)
        scored_articles = scored_articles[:limit]

        results: list[dict[str, Any]] = []
        for score, article in scored_articles:
            results.append({
                "id": article["id"],
                "title": article["title"],
                "content": article["content"][:300] + "..." if len(article["content"]) > 300 else article["content"],
                "score": score,
                "metadata": {
                    "category": article["category"],
                    "tags": article["tags"],
                    "last_updated": article["last_updated"],
                    "author": article["author"],
                },
            })

        logger.info("Semantic search returned %d results", len(results))
        return self.success_result({
            "results": results,
            "total": len(results),
            "query": query,
            "namespace": namespace,
        })


class KnowledgeBaseLookupTool(BaseTool):
    """Look up a specific knowledge base article by ID or topic."""

    @property
    def name(self) -> str:
        return "knowledge_base_lookup"

    @property
    def description(self) -> str:
        return (
            "Look up a specific article in the knowledge base by its ID or "
            "by topic keyword. Returns the full article content including "
            "title, body, category, tags, and last updated date."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "article_id": {
                    "type": "string",
                    "description": "The unique ID of the article to retrieve.",
                },
                "topic": {
                    "type": "string",
                    "description": "Topic keyword to search for an article.",
                },
            },
            "required": [],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        article_id = params.get("article_id")
        topic = params.get("topic", "").lower()

        if not article_id and not topic:
            return self.error_result(
                "At least one of article_id or topic must be provided"
            )

        logger.info(
            "Knowledge base lookup: article_id=%r topic=%r", article_id, topic
        )

        # Search by ID first
        if article_id:
            for article in _MOCK_KB_ARTICLES:
                if article["id"] == article_id:
                    logger.info("Found article %s", article_id)
                    return self.success_result({"article": article})
            return self.error_result(f"Article '{article_id}' not found")

        # Search by topic
        for article in _MOCK_KB_ARTICLES:
            searchable = f"{article['title']} {' '.join(article['tags'])}".lower()
            if topic in searchable:
                logger.info("Found article %s for topic %r", article["id"], topic)
                return self.success_result({"article": article})

        logger.warning("No article found for topic %r", topic)
        return self.error_result(f"No article found for topic '{topic}'")
