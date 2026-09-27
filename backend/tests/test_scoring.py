from backend.app.analyzer.base import FindingResult
from backend.app.analyzer.scoring import ScoringEngine

def test_scoring_penalties():
    engine = ScoringEngine()
    findings = [
        FindingResult("Security", "CRITICAL", "Hardcoded Secret", "config.py", 1, "key", "desc", "why", "fix", "verify"),
        FindingResult("Security", "HIGH", "Shell Injection", "main.py", 2, "cmd", "desc", "why", "fix", "verify"),
        FindingResult("Testing", "HIGH", "No Tests", "tests/", None, "0 tests", "desc", "why", "fix", "verify")
    ]
    
    overall, cat_scores = engine.calculate_scores(findings)
    
    assert cat_scores["Security"]["score"] == 100 - 25 - 15  # 60
    assert cat_scores["Testing"]["score"] == 100 - 15  # 85
    assert cat_scores["Code Quality"]["score"] == 100
    assert overall < 100
