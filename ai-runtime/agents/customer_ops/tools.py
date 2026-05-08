"""Customer Support Tools -- integration tools for the AI Customer Support Agent.

Provides five tools used by the Customer Support agent during inquiry handling:
  - IntentClassifierTool: Classifies customer intent and detects sentiment
  - KnowledgeSearchTool: Searches knowledge base articles for answers
  - OrderLookupTool: Looks up order status and details
  - CRMLoggingTool: Logs interactions and lookups to CRM system
  - ExchangeProcessorTool: Handles product exchange requests per return policy

All tools return realistic mock data for local development without external
dependencies. In production they would integrate with NLP services, knowledge
management systems, and order management platforms.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Intent Classifier Tool
# ---------------------------------------------------------------------------


class IntentClassifierTool(BaseTool):
    """Classifies customer intent and detects sentiment from message text.

    Analyzes customer messages to determine intent category (question,
    complaint, refund_request, order_inquiry, general, escalation) and
    sentiment (positive, neutral, frustrated, angry). Also detects
    the language of the message.

    In production this tool would integrate with NLP/LLM classification
    pipelines. For local development it uses keyword-based classification.
    """

    @property
    def name(self) -> str:
        return "classify_intent"

    @property
    def description(self) -> str:
        return (
            "Classify the intent and sentiment of a customer message. "
            "Returns intent category (question, complaint, refund_request, "
            "order_inquiry, general, escalation), sentiment (positive, neutral, "
            "frustrated, angry), and detected language."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The customer's message text.",
                },
                "customer_context": {
                    "type": "object",
                    "description": (
                        "Optional customer context including previous interactions, "
                        "customer tier, and account details."
                    ),
                },
            },
            "required": ["message"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Classify customer message intent and sentiment.

        Uses keyword-based classification for local development. In
        production this would use an NLP model or LLM.

        Args:
            params: Tool parameters with customer message and optional context.

        Returns:
            Success result with intent, sentiment, language, confidence,
            and extracted entities.
        """
        message = params.get("message", "")
        customer_context = params.get("customer_context", {})

        if not message:
            return self.error_result("No customer message provided.")

        message_lower = message.lower()

        # Detect intent
        intent = self._classify_intent(message_lower)

        # Detect sentiment
        sentiment = self._detect_sentiment(message_lower)

        # Detect language (simplified)
        language = self._detect_language(message)

        # Extract entities
        entities = self._extract_entities(message_lower)

        # Calculate confidence based on keyword matches
        confidence = self._calculate_confidence(message_lower, intent)

        # Check if escalation is needed based on context
        needs_escalation = self._check_escalation_needed(
            sentiment, customer_context, intent
        )

        return self.success_result({
            "intent": intent,
            "sentiment": sentiment,
            "language": language,
            "confidence": confidence,
            "entities": entities,
            "needs_escalation": needs_escalation,
            "escalation_reason": (
                self._get_escalation_reason(sentiment, customer_context, intent)
                if needs_escalation
                else None
            ),
            "summary": (
                f"Intent: {intent}, Sentiment: {sentiment}, "
                f"Language: {language}, Confidence: {confidence:.2f}."
            ),
        })

    def _classify_intent(self, message: str) -> str:
        """Classify message intent using keyword matching.

        Args:
            message: Lowercased message text.

        Returns:
            Intent category string.
        """
        # Order of checking matters -- more specific intents first
        refund_keywords = [
            "refund", "money back", "return", "reimburse", "charge back",
            "cancel order", "cancellation",
        ]
        if any(kw in message for kw in refund_keywords):
            return "refund_request"

        order_keywords = [
            "order", "tracking", "shipment", "delivery", "shipped",
            "where is my", "status of my", "order number", "package",
        ]
        if any(kw in message for kw in order_keywords):
            return "order_inquiry"

        complaint_keywords = [
            "complaint", "unhappy", "disappointed", "terrible", "worst",
            "unacceptable", "broken", "defective", "damaged", "wrong item",
            "never again", "disgusted",
        ]
        if any(kw in message for kw in complaint_keywords):
            return "complaint"

        escalation_keywords = [
            "manager", "supervisor", "escalate", "speak to someone",
            "human agent", "real person", "lawyer", "legal",
        ]
        if any(kw in message for kw in escalation_keywords):
            return "escalation"

        question_keywords = [
            "how", "what", "when", "where", "why", "can i", "do you",
            "is it possible", "help me", "?",
        ]
        if any(kw in message for kw in question_keywords):
            return "question"

        return "general"

    def _detect_sentiment(self, message: str) -> str:
        """Detect sentiment from message text.

        Args:
            message: Lowercased message text.

        Returns:
            Sentiment string: positive, neutral, frustrated, or angry.
        """
        angry_keywords = [
            "furious", "outraged", "disgusted", "hate", "worst ever",
            "sue", "lawyer", "legal action", "scam", "fraud", "theft",
            "!!!", "ridiculous", "absurd",
        ]
        if any(kw in message for kw in angry_keywords):
            return "angry"

        frustrated_keywords = [
            "frustrated", "annoyed", "disappointed", "unhappy", "unacceptable",
            "terrible", "awful", "horrible", "waste of time", "sick of",
            "fed up", "enough", "still waiting", "again",
        ]
        if any(kw in message for kw in frustrated_keywords):
            return "frustrated"

        positive_keywords = [
            "thank", "thanks", "great", "excellent", "wonderful", "happy",
            "love", "appreciate", "amazing", "fantastic", "perfect",
            "pleased", "satisfied",
        ]
        if any(kw in message for kw in positive_keywords):
            return "positive"

        return "neutral"

    @staticmethod
    def _detect_language(message: str) -> str:
        """Detect message language (simplified).

        Args:
            message: Original message text.

        Returns:
            Language code ('en' or 'ar').
        """
        # Simple Arabic detection by checking for Arabic Unicode range
        arabic_chars = sum(
            1 for c in message if "\u0600" <= c <= "\u06ff"
        )
        if arabic_chars > len(message) * 0.3:
            return "ar"
        return "en"

    @staticmethod
    def _extract_entities(message: str) -> dict[str, Any]:
        """Extract key entities from the message.

        Args:
            message: Lowercased message text.

        Returns:
            Dict with extracted entity types and values.
        """
        entities: dict[str, Any] = {}

        # Order number patterns (ORD-XXXX, #XXXX)
        import re

        order_patterns = re.findall(r"(?:ord[-#]?\s*\d+|#\d{4,}|\border\s*#?\s*\d+)", message)
        if order_patterns:
            entities["order_references"] = order_patterns

        # Email patterns
        emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", message)
        if emails:
            entities["emails"] = emails

        # Amount patterns
        amounts = re.findall(r"\$[\d,]+\.?\d*|\d+\.?\d*\s*(?:usd|aed|eur|gbp)", message)
        if amounts:
            entities["amounts"] = amounts

        return entities

    @staticmethod
    def _calculate_confidence(message: str, intent: str) -> float:
        """Calculate classification confidence score.

        Args:
            message: Lowercased message text.
            intent: Classified intent.

        Returns:
            Confidence score between 0.0 and 1.0.
        """
        # Longer messages with clear keywords get higher confidence
        word_count = len(message.split())
        if word_count < 3:
            base_conf = 0.60
        elif word_count < 10:
            base_conf = 0.75
        else:
            base_conf = 0.85

        # Specific intents get higher confidence
        if intent in ("refund_request", "order_inquiry", "escalation"):
            base_conf += 0.10

        return min(round(base_conf, 2), 0.98)

    @staticmethod
    def _check_escalation_needed(
        sentiment: str, customer_context: dict[str, Any], intent: str
    ) -> bool:
        """Check if automatic escalation is needed.

        Args:
            sentiment: Detected sentiment.
            customer_context: Customer context data.
            intent: Classified intent.

        Returns:
            True if escalation is recommended.
        """
        if intent == "escalation":
            return True
        if sentiment == "angry":
            return True
        if sentiment == "angry" and customer_context.get("tier") == "vip":
            return True
        return False

    @staticmethod
    def _get_escalation_reason(
        sentiment: str, customer_context: dict[str, Any], intent: str
    ) -> str:
        """Get the reason for escalation.

        Args:
            sentiment: Detected sentiment.
            customer_context: Customer context data.
            intent: Classified intent.

        Returns:
            Escalation reason string.
        """
        reasons = []
        if intent == "escalation":
            reasons.append("Customer explicitly requested escalation.")
        if sentiment == "angry":
            reasons.append("Angry sentiment detected.")
        if customer_context.get("tier") == "vip":
            reasons.append("VIP customer.")
        return " ".join(reasons) if reasons else "Automatic escalation triggered."


# ---------------------------------------------------------------------------
# Knowledge Search Tool
# ---------------------------------------------------------------------------


class KnowledgeSearchTool(BaseTool):
    """Searches knowledge base articles to find answers to customer questions.

    Performs keyword-based search against a provided knowledge base to
    find relevant articles and answers. Ranks results by relevance.

    In production this tool would integrate with a vector search engine
    or knowledge management system. For local development it works with
    data provided in the parameters or returns mock results.
    """

    @property
    def name(self) -> str:
        return "search_knowledge_base"

    @property
    def description(self) -> str:
        return (
            "Search the knowledge base for articles matching a customer query. "
            "Returns relevant articles ranked by relevance with excerpts."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query derived from the customer message.",
                },
                "knowledge_base": {
                    "type": "array",
                    "description": "List of knowledge base articles to search.",
                    "items": {"type": "object"},
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return.",
                },
                "category": {
                    "type": "string",
                    "description": "Optional category to filter results.",
                },
            },
            "required": ["query"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Search knowledge base for relevant articles.

        Performs keyword-based matching against article titles and content.
        Ranks results by the number of matching keywords.

        Args:
            params: Tool parameters with search query, knowledge_base list,
                    max_results, and optional category filter.

        Returns:
            Success result with matched articles, relevance scores,
            and suggested answer.
        """
        query = params.get("query", "")
        knowledge_base = params.get("knowledge_base", [])
        max_results = params.get("max_results", 5)
        category = params.get("category")

        if not query:
            return self.error_result("No search query provided.")

        # If no knowledge base provided, return mock results
        if not knowledge_base:
            return self._mock_search(query, max_results)

        # Keyword-based search
        query_words = set(query.lower().split())
        scored_articles: list[tuple[float, dict[str, Any]]] = []

        for article in knowledge_base:
            # Apply category filter
            if category and article.get("category", "").lower() != category.lower():
                continue

            title = (article.get("title", "") or "").lower()
            content = (article.get("content", "") or "").lower()
            tags = [t.lower() for t in article.get("tags", [])]

            # Calculate relevance score
            title_matches = sum(1 for w in query_words if w in title)
            content_matches = sum(1 for w in query_words if w in content)
            tag_matches = sum(1 for w in query_words if any(w in t for t in tags))

            # Weight title matches more heavily
            score = (title_matches * 3 + content_matches + tag_matches * 2)

            if score > 0:
                relevance = min(score / (len(query_words) * 3), 1.0)
                scored_articles.append((relevance, article))

        # Sort by relevance (descending)
        scored_articles.sort(key=lambda x: x[0], reverse=True)
        top_results = scored_articles[:max_results]

        results = []
        for relevance, article in top_results:
            results.append({
                "article_id": article.get("id", article.get("article_id", "unknown")),
                "title": article.get("title"),
                "excerpt": (article.get("content", "")[:200] + "...")
                if len(article.get("content", "")) > 200
                else article.get("content", ""),
                "category": article.get("category"),
                "relevance_score": round(relevance, 2),
                "url": article.get("url"),
            })

        # Generate suggested answer from top result
        suggested_answer = None
        if results:
            top = top_results[0][1]
            suggested_answer = top.get("content", top.get("answer", ""))

        return self.success_result({
            "results": results,
            "total_found": len(results),
            "query": query,
            "suggested_answer": suggested_answer,
            "summary": (
                f"Found {len(results)} relevant article(s) for query: '{query}'."
            ),
        })

    def _mock_search(self, query: str, max_results: int) -> dict[str, Any]:
        """Return mock search results for local development.

        Args:
            query: Search query string.
            max_results: Maximum number of results.

        Returns:
            Success result with mock articles.
        """
        mock_articles = [
            {
                "article_id": "KB-001",
                "title": "How to Return a Product",
                "excerpt": (
                    "To return a product, visit your account page, select the order, "
                    "and click 'Request Return'. Returns are accepted within 30 days "
                    "of delivery..."
                ),
                "category": "returns",
                "relevance_score": 0.85,
                "url": "/kb/returns/how-to-return",
            },
            {
                "article_id": "KB-002",
                "title": "Refund Policy",
                "excerpt": (
                    "Refunds are processed within 5-10 business days after we receive "
                    "the returned item. Original shipping costs are non-refundable..."
                ),
                "category": "refunds",
                "relevance_score": 0.78,
                "url": "/kb/refunds/policy",
            },
            {
                "article_id": "KB-003",
                "title": "Track Your Order",
                "excerpt": (
                    "You can track your order status by visiting your account page or "
                    "using the tracking number provided in your shipping confirmation email..."
                ),
                "category": "orders",
                "relevance_score": 0.72,
                "url": "/kb/orders/tracking",
            },
        ]

        results = mock_articles[:max_results]

        return self.success_result({
            "results": results,
            "total_found": len(results),
            "query": query,
            "suggested_answer": results[0]["excerpt"] if results else None,
            "note": "Mock search results -- configure knowledge base for real search.",
            "summary": f"Found {len(results)} relevant article(s) for query: '{query}'.",
        })


# ---------------------------------------------------------------------------
# Order Lookup Tool
# ---------------------------------------------------------------------------


class OrderLookupTool(BaseTool):
    """Looks up order status and details from order records.

    Searches for orders by order ID, customer email, or customer name.
    Returns order status, items, shipping details, and payment information.

    In production this tool would query the order management system.
    For local development it works with data provided in the parameters
    or returns mock order data.
    """

    @property
    def name(self) -> str:
        return "lookup_order"

    @property
    def description(self) -> str:
        return (
            "Look up order status and details by order ID, customer email, "
            "or customer name. Returns order status, items, shipping, "
            "and payment information."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "Order ID or order number to look up.",
                },
                "customer_email": {
                    "type": "string",
                    "description": "Customer email to search orders by.",
                },
                "customer_name": {
                    "type": "string",
                    "description": "Customer name to search orders by.",
                },
                "orders": {
                    "type": "array",
                    "description": "List of order records to search.",
                    "items": {"type": "object"},
                },
            },
            "required": [],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Look up order details from available records.

        Searches by order_id (exact match), customer_email (exact match),
        or customer_name (case-insensitive match).

        Args:
            params: Tool parameters with order_id, customer_email,
                    customer_name, and orders list.

        Returns:
            Success result with matched orders and status details.
        """
        order_id = (params.get("order_id") or "").strip()
        customer_email = (params.get("customer_email") or "").strip().lower()
        customer_name = (params.get("customer_name") or "").strip().lower()
        orders = params.get("orders", [])

        if not order_id and not customer_email and not customer_name:
            return self.error_result(
                "No search criteria provided. Supply order_id, "
                "customer_email, or customer_name."
            )

        # If no orders provided, return mock result
        if not orders:
            return self._mock_lookup(order_id, customer_email, customer_name)

        matched_orders: list[dict[str, Any]] = []

        for order in orders:
            ord_id = (order.get("order_id") or order.get("id") or "").strip()
            ord_email = (order.get("customer_email") or order.get("email") or "").strip().lower()
            ord_name = (order.get("customer_name") or order.get("name") or "").strip().lower()

            # Match by order ID
            if order_id and ord_id and (
                ord_id.upper() == order_id.upper()
                or ord_id.replace("-", "") == order_id.replace("-", "")
            ):
                matched_orders.append(order)
                continue

            # Match by customer email
            if customer_email and ord_email and customer_email == ord_email:
                matched_orders.append(order)
                continue

            # Match by customer name
            if customer_name and ord_name and customer_name == ord_name:
                matched_orders.append(order)

        if not matched_orders:
            return self.success_result({
                "found": False,
                "orders": [],
                "total_found": 0,
                "summary": (
                    f"No orders found matching the provided criteria "
                    f"(order_id={order_id or 'N/A'}, email={customer_email or 'N/A'})."
                ),
            })

        # Enrich order data
        enriched_orders = []
        for order in matched_orders:
            enriched = {
                "order_id": order.get("order_id") or order.get("id"),
                "status": order.get("status", "unknown"),
                "order_date": order.get("order_date") or order.get("created_at"),
                "total_amount": order.get("total_amount") or order.get("total"),
                "currency": order.get("currency", "USD"),
                "items": order.get("items", []),
                "shipping": {
                    "method": order.get("shipping_method", order.get("shipping", {}).get("method")),
                    "tracking_number": order.get(
                        "tracking_number",
                        order.get("shipping", {}).get("tracking_number"),
                    ),
                    "estimated_delivery": order.get(
                        "estimated_delivery",
                        order.get("shipping", {}).get("estimated_delivery"),
                    ),
                    "delivered_date": order.get(
                        "delivered_date",
                        order.get("shipping", {}).get("delivered_date"),
                    ),
                },
                "payment": {
                    "method": order.get("payment_method", order.get("payment", {}).get("method")),
                    "status": order.get("payment_status", order.get("payment", {}).get("status")),
                },
                "refund_eligible": self._check_refund_eligibility(order),
            }
            enriched_orders.append(enriched)

        return self.success_result({
            "found": True,
            "orders": enriched_orders,
            "total_found": len(enriched_orders),
            "summary": (
                f"Found {len(enriched_orders)} order(s) matching the provided criteria."
            ),
        })

    def _mock_lookup(
        self, order_id: str, customer_email: str, customer_name: str
    ) -> dict[str, Any]:
        """Return mock order data for local development.

        Args:
            order_id: Order ID being looked up.
            customer_email: Customer email being looked up.
            customer_name: Customer name being looked up.

        Returns:
            Success result with mock order data.
        """
        mock_order = {
            "order_id": order_id or "ORD-2024-0042",
            "status": "shipped",
            "order_date": (
                datetime.now(timezone.utc) - timedelta(days=5)
            ).strftime("%Y-%m-%d"),
            "total_amount": 149.99,
            "currency": "USD",
            "items": [
                {
                    "name": "Wireless Headphones",
                    "quantity": 1,
                    "price": 99.99,
                },
                {
                    "name": "Phone Case",
                    "quantity": 1,
                    "price": 29.99,
                },
                {
                    "name": "Screen Protector",
                    "quantity": 1,
                    "price": 20.01,
                },
            ],
            "shipping": {
                "method": "Standard Shipping",
                "tracking_number": "TRK-" + uuid.uuid4().hex[:8].upper(),
                "estimated_delivery": (
                    datetime.now(timezone.utc) + timedelta(days=3)
                ).strftime("%Y-%m-%d"),
                "delivered_date": None,
            },
            "payment": {
                "method": "Credit Card",
                "status": "paid",
            },
            "refund_eligible": True,
        }

        return self.success_result({
            "found": True,
            "orders": [mock_order],
            "total_found": 1,
            "note": "Mock order data -- configure order system for real lookups.",
            "summary": f"Found 1 order matching the provided criteria.",
        })

    @staticmethod
    def _check_refund_eligibility(order: dict[str, Any]) -> bool:
        """Check if an order is eligible for refund based on its status and age.

        Args:
            order: Order record dict.

        Returns:
            True if the order is eligible for a refund.
        """
        status = (order.get("status") or "").lower()

        # Already refunded or cancelled orders are not eligible
        if status in ("refunded", "cancelled"):
            return False

        # Check order age (30-day window)
        order_date_str = order.get("order_date") or order.get("created_at", "")
        if order_date_str:
            try:
                if isinstance(order_date_str, str):
                    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
                        try:
                            order_date = datetime.strptime(order_date_str, fmt).replace(
                                tzinfo=timezone.utc
                            )
                            break
                        except ValueError:
                            continue
                    else:
                        return True  # Cannot parse date, assume eligible
                else:
                    order_date = order_date_str

                days_since_order = (datetime.now(timezone.utc) - order_date).days
                if days_since_order > 30:
                    return False
            except (ValueError, TypeError):
                pass

        return True


# ---------------------------------------------------------------------------
# CRM Logging Tool
# ---------------------------------------------------------------------------


class CRMLoggingTool(BaseTool):
    """Logs customer interactions and context to the CRM system.

    Records every support interaction on the customer timeline so human agents
    and managers have full visibility.  In production this calls the CRM REST
    API (Salesforce / HubSpot / Zoho); locally it returns a mock log entry.
    """

    name = "crm_logging"
    description = (
        "Log a customer support interaction to the CRM system, "
        "including intent, resolution, sentiment and channel."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "customer_id": {
                "type": "string",
                "description": "CRM customer identifier",
            },
            "customer_email": {
                "type": "string",
                "description": "Customer email address",
            },
            "interaction_type": {
                "type": "string",
                "description": "Type of interaction logged",
                "enum": [
                    "inquiry",
                    "complaint",
                    "refund",
                    "exchange",
                    "escalation",
                    "general",
                ],
            },
            "channel": {
                "type": "string",
                "description": "Communication channel",
                "enum": ["chat", "email", "portal", "voice"],
            },
            "summary": {
                "type": "string",
                "description": "AI-generated summary of the interaction",
            },
            "sentiment": {
                "type": "string",
                "description": "Detected customer sentiment",
            },
            "resolution_status": {
                "type": "string",
                "description": "Current resolution status",
                "enum": ["resolved", "escalated", "pending", "closed"],
            },
            "ticket_id": {
                "type": "string",
                "description": "Associated support ticket ID",
            },
            "metadata": {
                "type": "object",
                "description": "Additional context (refund amount, order ID, etc.)",
            },
        },
        "required": ["customer_id", "interaction_type", "channel", "summary"],
    }

    async def execute(
        self, params: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        customer_id = params["customer_id"]
        interaction_type = params["interaction_type"]
        channel = params.get("channel", "chat")
        summary = params["summary"]

        crm_log_id = f"CRM-{uuid.uuid4().hex[:12].upper()}"
        timestamp = datetime.now(timezone.utc).isoformat()

        log_entry = {
            "crm_log_id": crm_log_id,
            "customer_id": customer_id,
            "customer_email": params.get("customer_email"),
            "interaction_type": interaction_type,
            "channel": channel,
            "summary": summary,
            "sentiment": params.get("sentiment"),
            "resolution_status": params.get("resolution_status", "pending"),
            "ticket_id": params.get("ticket_id"),
            "metadata": params.get("metadata", {}),
            "logged_at": timestamp,
            "actor": "ai-customer-support-agent",
        }

        logger.info(
            "CRM interaction logged: %s for customer %s (%s)",
            crm_log_id,
            customer_id,
            interaction_type,
        )

        return self.success_result(
            data=log_entry,
            message=f"Interaction logged to CRM as {crm_log_id}",
        )


# ---------------------------------------------------------------------------
# Exchange Processor Tool
# ---------------------------------------------------------------------------


class ExchangeProcessorTool(BaseTool):
    """Processes product exchange requests per the tenant's return policy.

    Validates exchange eligibility (order status, return window, product
    category), initiates the exchange, and generates a return shipping label.
    In production this integrates with the OMS / ERP; locally returns mock data.
    """

    name = "exchange_processor"
    description = (
        "Process a product exchange request — validates eligibility, "
        "initiates the exchange, and generates a return label."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "order_id": {
                "type": "string",
                "description": "Original order ID",
            },
            "item_id": {
                "type": "string",
                "description": "Item to exchange (SKU or line-item ID)",
            },
            "reason": {
                "type": "string",
                "description": "Reason for exchange",
                "enum": [
                    "defective",
                    "wrong_size",
                    "wrong_item",
                    "changed_mind",
                    "other",
                ],
            },
            "replacement_item_id": {
                "type": "string",
                "description": "Desired replacement item (SKU or ID)",
            },
            "orders": {
                "type": "array",
                "description": "Available orders list for lookup",
            },
        },
        "required": ["order_id", "reason"],
    }

    async def execute(
        self, params: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        order_id = params["order_id"]
        reason = params["reason"]
        item_id = params.get("item_id")
        replacement = params.get("replacement_item_id")

        # Check order existence
        orders = params.get("orders", [])
        matched_order = None
        for order in orders:
            oid = order.get("order_id", order.get("id", ""))
            if oid.replace("-", "").lower() == order_id.replace("-", "").lower():
                matched_order = order
                break

        if not matched_order:
            # Return mock exchange for dev
            matched_order = {
                "order_id": order_id,
                "status": "delivered",
                "order_date": (
                    datetime.now(timezone.utc) - timedelta(days=10)
                ).isoformat(),
                "items": [
                    {
                        "item_id": item_id or "ITEM-001",
                        "name": "Product",
                        "quantity": 1,
                        "price_usd": 49.99,
                    }
                ],
            }

        # Eligibility checks
        status = matched_order.get("status", "").lower()
        if status in ("refunded", "cancelled", "exchanged"):
            return self.error_result(
                f"Order {order_id} has status '{status}' and is not eligible for exchange."
            )

        # Check return window (30 days)
        order_date_str = matched_order.get("order_date", matched_order.get("date"))
        if order_date_str:
            try:
                if isinstance(order_date_str, str):
                    order_date = datetime.fromisoformat(
                        order_date_str.replace("Z", "+00:00")
                    )
                else:
                    order_date = order_date_str
                days_since = (datetime.now(timezone.utc) - order_date).days
                if days_since > 30:
                    return self.error_result(
                        f"Order {order_id} is {days_since} days old and outside "
                        f"the 30-day exchange window."
                    )
            except (ValueError, TypeError):
                pass

        exchange_id = f"EXC-{uuid.uuid4().hex[:8].upper()}"
        return_label = f"RET-{uuid.uuid4().hex[:10].upper()}"

        exchange_record = {
            "exchange_id": exchange_id,
            "order_id": order_id,
            "item_id": item_id or "unknown",
            "reason": reason,
            "replacement_item_id": replacement,
            "return_label": return_label,
            "status": "initiated",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "instructions": (
                f"Please use return label {return_label} to ship back the item. "
                f"Once we receive it, your replacement will be shipped within "
                f"2-3 business days."
            ),
        }

        logger.info(
            "Exchange initiated: %s for order %s (reason: %s)",
            exchange_id,
            order_id,
            reason,
        )

        return self.success_result(
            data=exchange_record,
            message=f"Exchange {exchange_id} initiated for order {order_id}",
        )
