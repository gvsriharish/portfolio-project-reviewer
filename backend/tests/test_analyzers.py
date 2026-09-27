import os
import pytest
from backend.app.services.repo_fetcher import SafeRepositoryWorkspace
from backend.app.analyzer.orchestrator import AnalysisOrchestrator
from backend.app.analyzer.scoring import ScoringEngine

def test_bad_project_analysis():
    bad_dir = os.path.abspath("sample_projects/bad_project")
    workspace = SafeRepositoryWorkspace(bad_dir, "bad_project", "sample", is_sample=True)
    orchestrator = AnalysisOrchestrator()
    
    results = orchestrator.run_full_analysis(workspace)
    
    assert results['overall_score'] <= 60
    finding_titles = [f.title for f in results['findings']]
    assert any("AWS Access Key" in t or "Secret Key" in t for t in finding_titles)
    assert any("Bare 'except:'" in t for t in finding_titles)
    assert any("Automated Tests" in t for t in finding_titles)
    assert any("Missing .gitignore" in t for t in finding_titles)

def test_improved_project_analysis():
    good_dir = os.path.abspath("sample_projects/improved_project")
    workspace = SafeRepositoryWorkspace(good_dir, "improved_project", "sample", is_sample=True)
    orchestrator = AnalysisOrchestrator()
    
    results = orchestrator.run_full_analysis(workspace)
    
    assert results['overall_score'] >= 85
    finding_titles = [f.title for f in results['findings']]
    assert not any("AWS Access Key" in t for t in finding_titles)
    assert not any("Bare 'except:'" in t for t in finding_titles)
    assert not any("Zero Automated Tests" in t for t in finding_titles)
