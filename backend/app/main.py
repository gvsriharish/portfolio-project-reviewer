import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.database.session import engine
from backend.app.database.base import Base
import backend.app.models.findings
import backend.app.models.evidence  # registers FindingEvidence table with SQLAlchemy metadata
import backend.app.models.claims    # registers Claim + association tables
import backend.app.models.verification  # registers VerificationResult
import backend.app.models.phase6_9  # registers Phase 6–9 artifact tables

from backend.app.database.migrations import run_migrations
from backend.app.api.endpoints import health, analyze, sample_projects, evidence, claims, insights, phase6_9

Base.metadata.create_all(bind=engine)
run_migrations(engine)  # idempotent in-place upgrade of pre-Phase-2 SQLite DBs

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Turn Your GitHub Repository Into Evidence of Real Engineering Skill. Deterministic claim auditing, engineering evidence graph, and proof of improvement.",
    version="1.0.0",
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(health.router, prefix=settings.API_PREFIX, tags=["Health"])
app.include_router(analyze.router, prefix=settings.API_PREFIX, tags=["Analysis"])
app.include_router(sample_projects.router, prefix=settings.API_PREFIX, tags=["Sample Projects"])
app.include_router(evidence.router, prefix=settings.API_PREFIX, tags=["Evidence"])
app.include_router(claims.router, prefix=settings.API_PREFIX, tags=["Claim Auditor"])
app.include_router(insights.router, prefix=settings.API_PREFIX, tags=["Evidence Graph & Trust Report"])
app.include_router(phase6_9.router, prefix=settings.API_PREFIX, tags=["Portfolio, Monitor, Interview & Passport"])

@app.get("/")
def read_root():
    return {
        "project": settings.PROJECT_NAME,
        "tagline": "Turn Your GitHub Repository Into Evidence of Real Engineering Skill.",
        "documentation": f"{settings.API_PREFIX}/docs",
        "api_prefix": settings.API_PREFIX
    }
