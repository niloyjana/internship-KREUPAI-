"""AI Runtime API -- FastAPI application.

Initializes the FastAPI app with all routers, middleware, and the
orchestration engine with its dependencies (LLM gateway, PII redactor,
cost tracker, failure handler, config resolver, memory manager).

Database persistence (PostgreSQL + Redis) is initialised at startup
when the corresponding environment variables are set. The application
works fully without them -- falling back to in-memory storage.
"""

import logging
import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Customer Operations (3 agents)
from agents.customer_ops.support_agent import CustomerSupportAgent
from agents.customer_ops.service_desk_analyst import ServiceDeskAnalystAgent
from agents.customer_ops.executive_assistant import ExecutiveAssistantAgent

# Sales & Marketing (4 agents)
from agents.sales_marketing.sdr import SDRAgent
from agents.sales_marketing.account_exec_assistant import AccountExecAssistantAgent
from agents.sales_marketing.marketing_campaign_coordinator import MarketingCampaignCoordinatorAgent
from agents.sales_marketing.content_operations_specialist import ContentOperationsSpecialistAgent

# HR & People Operations (3 agents)
from agents.hr_people_ops.recruiter import RecruiterAgent
from agents.hr_people_ops.onboarding_coordinator import OnboardingCoordinatorAgent
from agents.hr_people_ops.payroll_analyst import PayrollAnalystAgent

# Finance & Procurement (5 agents)
from agents.finance_procurement.ap_officer import APOfficerAgent
from agents.finance_procurement.ar_officer import AROfficerAgent
from agents.finance_procurement.gl_analyst import GLAnalystAgent
from agents.finance_procurement.procurement_officer import ProcurementOfficerAgent
from agents.finance_procurement.inventory_planner import InventoryPlannerAgent

# Delivery & Operations (5 agents)
from agents.delivery_ops.logistics_coordinator import LogisticsCoordinatorAgent
from agents.delivery_ops.project_coordinator import ProjectCoordinatorAgent
from agents.delivery_ops.qa_coordinator import QACoordinatorAgent
from agents.delivery_ops.document_control_officer import DocumentControlOfficerAgent
from agents.delivery_ops.data_analyst_assistant import DataAnalystAssistantAgent

# Governance, Risk & Control (5 agents)
from agents.governance_risk.compliance_officer import ComplianceOfficerAgent
from agents.governance_risk.legal_contract_analyst import LegalContractAnalystAgent
from agents.governance_risk.cybersecurity_analyst import CybersecurityAnalystAgent
from agents.governance_risk.risk_analyst import RiskAnalystAgent
from agents.governance_risk.business_analyst_assistant import BusinessAnalystAssistantAgent
from api.routers import agent_execute, health, ap_officer_router
from db.database import close_db, create_tables, init_db, init_redis
from llm.cost_tracker import CostTracker
from llm.gateway import LLMGateway
from memory.manager import MemoryManager
from orchestrator.config_resolver import ConfigResolver
from orchestrator.engine import OrchestrationEngine
from orchestrator.failure_handler import FailureHandler
from orchestrator.pii_redactor import PIIRedactor

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Application lifespan (startup / shutdown)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize runtime dependencies on startup and clean up on shutdown."""

    logger.info("AI Runtime starting up...")

    # ------------------------------------------------------------------
    # Database & Redis initialisation
    # ------------------------------------------------------------------
    db_ready = await init_db()
    redis_ready = await init_redis()

    if db_ready:
        await create_tables()
        logger.info("PostgreSQL persistence enabled.")
    else:
        logger.info("Running without PostgreSQL -- in-memory storage only.")

    if redis_ready:
        logger.info("Redis caching enabled.")
    else:
        logger.info("Running without Redis -- in-memory working memory only.")

    # Store connectivity flags on app state for the health check
    app.state.db_ready = db_ready
    app.state.redis_ready = redis_ready

    # ------------------------------------------------------------------
    # Core dependencies
    # ------------------------------------------------------------------
    # Create shared dependencies
    llm_gateway = LLMGateway()
    pii_redactor = PIIRedactor()
    cost_tracker = CostTracker()
    config_resolver = ConfigResolver()
    failure_handler = FailureHandler()
    memory_manager = MemoryManager()

    # Create orchestration engine
    engine = OrchestrationEngine(
        llm_gateway=llm_gateway,
        pii_redactor=pii_redactor,
        cost_tracker=cost_tracker,
        config_resolver=config_resolver,
        failure_handler=failure_handler,
        memory_manager=memory_manager,
    )

    # Register agents -- Customer Operations
    engine.register_agent("ai-customer-support-agent", CustomerSupportAgent(llm_gateway, pii_redactor))
    engine.register_agent("ai-service-desk-analyst", ServiceDeskAnalystAgent(llm_gateway, pii_redactor))
    engine.register_agent("ai-executive-assistant", ExecutiveAssistantAgent(llm_gateway, pii_redactor))

    # Register agents -- Sales & Marketing
    engine.register_agent("ai-sdr", SDRAgent(llm_gateway, pii_redactor))
    engine.register_agent("ai-account-exec-assistant", AccountExecAssistantAgent(llm_gateway, pii_redactor))
    engine.register_agent("ai-marketing-campaign-coordinator", MarketingCampaignCoordinatorAgent(llm_gateway, pii_redactor))
    engine.register_agent("ai-content-operations-specialist", ContentOperationsSpecialistAgent(llm_gateway, pii_redactor))

    # Register agents -- HR & People Operations
    engine.register_agent("ai-recruiter", RecruiterAgent(llm_gateway, pii_redactor))
    engine.register_agent("ai-onboarding-coordinator", OnboardingCoordinatorAgent(llm_gateway, pii_redactor))
    engine.register_agent("ai-payroll-analyst", PayrollAnalystAgent(llm_gateway, pii_redactor))

    # Register agents -- Finance & Procurement
    engine.register_agent("ai-ap-officer", APOfficerAgent(llm_gateway, pii_redactor))
    engine.register_agent("ai-ar-officer", AROfficerAgent(llm_gateway, pii_redactor))
    engine.register_agent("ai-gl-analyst", GLAnalystAgent(llm_gateway, pii_redactor))
    engine.register_agent("ai-procurement-officer", ProcurementOfficerAgent(llm_gateway, pii_redactor))
    engine.register_agent("ai-inventory-planner", InventoryPlannerAgent(llm_gateway, pii_redactor))

    # Register agents -- Delivery & Operations
    engine.register_agent("ai-logistics-coordinator", LogisticsCoordinatorAgent(llm_gateway, pii_redactor))
    engine.register_agent("ai-project-coordinator", ProjectCoordinatorAgent(llm_gateway, pii_redactor))
    engine.register_agent("ai-qa-coordinator", QACoordinatorAgent(llm_gateway, pii_redactor))
    engine.register_agent("ai-document-control-officer", DocumentControlOfficerAgent(llm_gateway, pii_redactor))
    engine.register_agent("ai-data-analyst-assistant", DataAnalystAssistantAgent(llm_gateway, pii_redactor))

    # Register agents -- Governance, Risk & Control
    engine.register_agent("ai-compliance-officer", ComplianceOfficerAgent(llm_gateway, pii_redactor))
    engine.register_agent("ai-legal-contract-analyst", LegalContractAnalystAgent(llm_gateway, pii_redactor))
    engine.register_agent("ai-cybersecurity-analyst", CybersecurityAnalystAgent(llm_gateway, pii_redactor))
    engine.register_agent("ai-risk-analyst", RiskAnalystAgent(llm_gateway, pii_redactor))
    engine.register_agent("ai-business-analyst-assistant", BusinessAnalystAssistantAgent(llm_gateway, pii_redactor))

    # Inject dependencies into the agent_execute router
    agent_execute.configure(
        engine=engine,
        llm_gateway=llm_gateway,
        pii_redactor=pii_redactor,
        cost_tracker=cost_tracker,
    )

    ap_officer_router.configure(engine=engine)

    # Store on app state for access from other places if needed
    app.state.engine = engine
    app.state.llm_gateway = llm_gateway
    app.state.pii_redactor = pii_redactor
    app.state.cost_tracker = cost_tracker
    app.state.config_resolver = config_resolver
    app.state.failure_handler = failure_handler
    app.state.memory_manager = memory_manager

    logger.info(
        "AI Runtime ready. Agents loaded: %d. Default LLM provider: %s",
        engine.agent_count,
        llm_gateway.default_provider,
    )

    yield

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------
    logger.info("AI Runtime shutting down...")
    await close_db()


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="ADWP AI Runtime",
    description="AI Agent Runtime Engine for AI Digital Workforce Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/v1", tags=["health"])
app.include_router(agent_execute.router, prefix="/v1", tags=["agent"])
app.include_router(ap_officer_router.router, prefix="/v1/finance", tags=["finance"])
