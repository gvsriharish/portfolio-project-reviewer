from fastapi import APIRouter
from typing import List
from backend.app.schemas.analysis import SampleProjectInfo

router = APIRouter()

SAMPLE_PROJECTS = [
    SampleProjectInfo(
        id="bad_project",
        name="Legacy Student Portfolio (Unimproved)",
        description="A realistic repository containing typical beginner gaps: exposed synthetic API keys, missing README setup steps, zero automated tests, and bare exception handling.",
        expected_score_range="35 - 55 / 100",
        key_traits=[
            "Exposed credential pattern",
            "Bare except clauses",
            "No test suite",
            "Unpinned dependencies",
            "Missing .gitignore"
        ]
    ),
    SampleProjectInfo(
        id="improved_project",
        name="Recruiter-Ready Portfolio (Improved)",
        description="The remediated and polished version of the portfolio: secure environment configuration, clean modular AST code, full Pytest test coverage, and comprehensive README documentation.",
        expected_score_range="88 - 98 / 100",
        key_traits=[
            "Zero exposed secrets",
            "Strict typed exception handling",
            "Automated unit test suite",
            "Pinned dependencies",
            "Complete README & MIT License"
        ]
    )
]

@router.get("/sample-projects", response_model=List[SampleProjectInfo])
def list_sample_projects():
    return SAMPLE_PROJECTS
