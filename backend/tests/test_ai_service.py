from backend.app.ai.service import AIReasoningService
from backend.app.analyzer.base import FindingResult


def _finding(**overrides):
    values = {
        "category": "Security",
        "severity": "HIGH",
        "title": "Observed issue",
        "file_path": "src/app.py",
        "line_number": 3,
        "evidence": "A concrete pattern was detected.",
        "description": "Observed description.",
        "why_it_matters": "Observed impact.",
        "recommended_fix": "Apply the suggested fix.",
        "verification_method": "Re-run the static check.",
    }
    return FindingResult(**(values | overrides))


def test_malformed_or_incomplete_ai_response_is_rejected():
    service = AIReasoningService()

    assert service._extract_json("not json") == {}
    assert service._extract_json('{"recommendations": "invalid"}') == {}
    assert service._extract_json('{"recommendations": [], "interview_questions": [], "project_explanation": []}') == {}
    assert service._extract_json('{"recommendations": [null], "interview_questions": [], "project_explanation": {}}') == {}


def test_ai_response_size_is_bounded():
    assert AIReasoningService()._extract_json(" " * 100_001) == {}


def test_grounded_fallback_does_not_claim_unobserved_controls_or_deployment():
    result = AIReasoningService()._generate_grounded_fallback(
        repo_name="example",
        languages=["Python"],
        frameworks=["FastAPI"],
        findings=[_finding()],
        architecture_summary={"components": []},
    )
    explanation = result["project_explanation"]
    fallback_text = " ".join(explanation["data_flow"] + explanation["technical_decisions"] + explanation["limitations"])

    assert "authentication" not in fallback_text.lower()
    assert "sqlite" not in fallback_text.lower()
    assert "does not infer runtime behavior" in fallback_text
    assert result["recommendations"][0]["title"] == "Resolve [HIGH] Observed issue"
