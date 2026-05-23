"""SQLAlchemy ORM models for the AI Runtime database.

Tables:
  - agent_executions  -- records every agent task execution
  - conversation_history -- per-execution LLM message log
  - agent_metrics -- aggregated per-agent performance stats
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for all AI Runtime models."""

    pass


# ---------------------------------------------------------------------------
# AgentExecution
# ---------------------------------------------------------------------------

class AgentExecution(Base):
    """Persisted record of a single agent execution request."""

    __tablename__ = "agent_executions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    execution_id: Mapped[str] = mapped_column(
        String(255), name="execution_id", nullable=False, index=True,
        comment="External execution identifier from the workflow service",
    )
    agent_type: Mapped[str] = mapped_column(
        String(255), name="agent_type", nullable=False, index=True,
        comment="Agent identifier, e.g. ai-ap-officer",
    )
    tenant_id: Mapped[str] = mapped_column(
        String(255), name="tenant_id", nullable=False, index=True,
        comment="Tenant identifier for RLS",
    )
    input_data: Mapped[dict | None] = mapped_column(
        JSON, name="input_data", nullable=True,
        comment="Redacted task payload sent to the agent",
    )
    output_data: Mapped[dict | None] = mapped_column(
        JSON, name="output_data", nullable=True,
        comment="Agent output / result",
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending",
        comment="pending | running | completed | failed | escalated",
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        name="started_at",
        default=lambda: datetime.now(timezone.utc),
        comment="When the execution started",
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), name="completed_at", nullable=True,
        comment="When the execution finished",
    )
    error: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Error message if the execution failed",
    )
    cost_usd: Mapped[float] = mapped_column(
        Float, name="cost_usd", nullable=False, default=0.0,
        comment="Total LLM cost in USD",
    )
    tokens_used: Mapped[int] = mapped_column(
        Integer, name="tokens_used", nullable=False, default=0,
        comment="Total tokens consumed (input + output)",
    )
    duration_ms: Mapped[int] = mapped_column(
        Integer, name="duration_ms", nullable=False, default=0,
        comment="Execution wall-clock time in milliseconds",
    )
    model: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
        comment="LLM model used, e.g. gpt-4o",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        name="created_at",
        server_default=func.now(),
    )

    __table_args__ = (
        Index("ix_agent_exec_tenant_agent", "tenant_id", "agent_type"),
        Index("ix_agent_exec_tenant_status", "tenant_id", "status"),
    )


# ---------------------------------------------------------------------------
# ConversationHistory
# ---------------------------------------------------------------------------

class ConversationHistory(Base):
    """Individual message in an agent execution conversation."""

    __tablename__ = "conversation_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    execution_id: Mapped[str] = mapped_column(
        String(255), name="execution_id", nullable=False, index=True,
        comment="Foreign key back to agent_executions.execution_id",
    )
    tenant_id: Mapped[str] = mapped_column(
        String(255), name="tenant_id", nullable=False, index=True,
    )
    role: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="system | user | assistant | tool",
    )
    content: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Message content (may be null for tool-call messages)",
    )
    metadata_json: Mapped[dict | None] = mapped_column(
        JSON, name="metadata_json", nullable=True,
        comment="Extra metadata (tool_calls, pii_detected, etc.)",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        name="created_at",
        server_default=func.now(),
    )

    __table_args__ = (
        Index("ix_conv_exec_tenant", "execution_id", "tenant_id"),
    )


# ---------------------------------------------------------------------------
# AgentMetrics
# ---------------------------------------------------------------------------

class AgentMetrics(Base):
    """Aggregated performance metrics per agent per tenant.

    Updated after each execution to maintain running averages.
    """

    __tablename__ = "agent_metrics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    agent_type: Mapped[str] = mapped_column(
        String(255), name="agent_type", nullable=False,
        comment="Agent identifier",
    )
    tenant_id: Mapped[str] = mapped_column(
        String(255), name="tenant_id", nullable=False,
        comment="Tenant identifier",
    )
    total_executions: Mapped[int] = mapped_column(
        BigInteger, name="total_executions", nullable=False, default=0,
    )
    successful_executions: Mapped[int] = mapped_column(
        BigInteger, name="successful_executions", nullable=False, default=0,
    )
    failed_executions: Mapped[int] = mapped_column(
        BigInteger, name="failed_executions", nullable=False, default=0,
    )
    avg_duration_ms: Mapped[float] = mapped_column(
        Float, name="avg_duration_ms", nullable=False, default=0.0,
    )
    total_tokens: Mapped[int] = mapped_column(
        BigInteger, name="total_tokens", nullable=False, default=0,
    )
    total_cost_usd: Mapped[float] = mapped_column(
        Float, name="total_cost_usd", nullable=False, default=0.0,
    )
    success_rate: Mapped[float] = mapped_column(
        Float, name="success_rate", nullable=False, default=0.0,
        comment="Ratio of successful / total executions (0-1)",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        name="updated_at",
        server_default=func.now(),
        onupdate=func.now(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        name="created_at",
        server_default=func.now(),
    )

    __table_args__ = (
        Index("ix_metrics_agent_tenant", "agent_type", "tenant_id", unique=True),
    )


# ---------------------------------------------------------------------------
# Business Domain Models (Hydration)
# ---------------------------------------------------------------------------

class FinanceInvoice(Base):
    """Business model for vendor invoices (synced from main DB)."""

    __tablename__ = "finance_invoices"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), name="tenantId", nullable=False, index=True)
    vendor_id: Mapped[str | None] = mapped_column(String(255), name="vendorId", nullable=True)
    vendor_name: Mapped[str] = mapped_column(String(255), name="vendorName", nullable=False)
    invoice_number: Mapped[str] = mapped_column(String(255), name="invoiceNumber", nullable=False)
    invoice_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), name="invoiceDate", nullable=False)
    total_amount: Mapped[float] = mapped_column(Float, name="totalAmount", nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    po_reference: Mapped[str | None] = mapped_column(String(255), name="poReference", nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), name="createdAt", server_default=func.now())


class PurchaseRequisition(Base):
    """Business model for purchase orders/requisitions (synced from main DB)."""

    __tablename__ = "purchase_requisitions"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), name="tenantId", nullable=False, index=True)
    pr_number: Mapped[str] = mapped_column(String(255), name="prNumber", nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_amount: Mapped[float] = mapped_column(Float, name="estimatedAmount", nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), name="createdAt", server_default=func.now())


class QaTestResult(Base):
    """Business model for QA test results (synced from main DB)."""

    __tablename__ = "qa_test_results"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), name="tenantId", nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, name="durationMs", nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), name="createdAt", server_default=func.now())


class QaDefect(Base):
    """Business model for QA defects (synced from main DB)."""

    __tablename__ = "qa_defects"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), name="tenantId", nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), name="createdAt", server_default=func.now())


class QaBaselineResult(Base):
    """Business model for QA baseline results (synced from main DB)."""

    __tablename__ = "qa_baseline_results"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), name="tenantId", nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), name="createdAt", server_default=func.now())


class QaRequirement(Base):
    """Business model for QA requirements (synced from main DB)."""

    __tablename__ = "qa_requirements"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), name="tenantId", nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), name="createdAt", server_default=func.now())

