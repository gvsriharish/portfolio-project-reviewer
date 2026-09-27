from typing import List, Dict, Any, Tuple
from backend.app.analyzer.base import FindingResult

SEVERITY_PENALTIES = {
    'CRITICAL': 25,
    'HIGH': 15,
    'MEDIUM': 8,
    'LOW': 3,
    'INFO': 0
}

CATEGORY_WEIGHTS = {
    'Code Quality': 0.20,
    'Security': 0.25,
    'Documentation': 0.15,
    'Testing': 0.15,
    'Architecture': 0.10,
    'Dependencies': 0.10,
    'Git Hygiene': 0.05
}

ALL_CATEGORIES = list(CATEGORY_WEIGHTS.keys()) + ['Portfolio Readiness']

class ScoringEngine:
    def calculate_scores(self, findings: List[FindingResult]) -> Tuple[int, Dict[str, Dict[str, Any]]]:
        findings_by_cat: Dict[str, List[FindingResult]] = {cat: [] for cat in ALL_CATEGORIES}
        for f in findings:
            cat = f.category if f.category in findings_by_cat else 'Code Quality'
            findings_by_cat[cat].append(f)

        category_scores: Dict[str, Dict[str, Any]] = {}
        weighted_sum = 0.0
        total_weight = 0.0

        for cat in ALL_CATEGORIES:
            cat_findings = findings_by_cat[cat]
            penalties: List[str] = []
            score = 100

            sev_counts = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0, 'INFO': 0}
            for f in cat_findings:
                sev = f.severity.upper()
                sev_counts[sev] = sev_counts.get(sev, 0) + 1
                deduction = SEVERITY_PENALTIES.get(sev, 0)
                if deduction > 0:
                    score -= deduction
                    penalties.append(f"-{deduction} pts: [{sev}] {f.title}")

            score = max(0, min(100, score))

            if score >= 90:
                summary = "Strong result under this scoring rubric, with few deductions."
            elif score >= 75:
                summary = "Good result under this scoring rubric; review the listed deductions."
            elif score >= 50:
                summary = "Several detected findings reduce this category score."
            else:
                summary = "Multiple detected findings substantially reduce this category score."

            category_scores[cat] = {
                'category': cat,
                'score': score,
                'max_score': 100,
                'findings_count': len(cat_findings),
                'severity_counts': sev_counts,
                'penalty_breakdown': penalties,
                'summary': summary
            }

            weight = CATEGORY_WEIGHTS.get(cat, 0.0)
            if weight > 0:
                weighted_sum += score * weight
                total_weight += weight

        overall_score = int(round(weighted_sum / total_weight)) if total_weight > 0 else 50
        overall_score = max(0, min(100, overall_score))

        doc_score = category_scores['Documentation']['score']
        test_score = category_scores['Testing']['score']
        code_score = category_scores['Code Quality']['score']
        sec_score = category_scores['Security']['score']
        portfolio_score = int(round(doc_score * 0.4 + code_score * 0.25 + test_score * 0.2 + sec_score * 0.15))
        category_scores['Portfolio Readiness']['score'] = portfolio_score
        category_scores['Portfolio Readiness']['summary'] = (
            "Higher readiness under this rubric" if portfolio_score >= 80 else
            "Moderate readiness under this rubric — review documentation and testing findings" if portfolio_score >= 60 else
            "Lower readiness under this rubric — review the detected findings"
        )

        return overall_score, category_scores
