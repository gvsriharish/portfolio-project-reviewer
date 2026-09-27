def test_health_endpoint(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

def test_sample_projects_list(client):
    res = client.get("/api/sample-projects")
    assert res.status_code == 200
    samples = res.json()
    assert len(samples) >= 2
    assert any(s["id"] == "bad_project" for s in samples)
    assert any(s["id"] == "improved_project" for s in samples)

def test_analyze_sample_project(client):
    res = client.post("/api/analyze", json={"github_url": "sample:bad_project", "use_ai": False})
    assert res.status_code == 200
    data = res.json()
    analysis_id = data["id"]
    assert data["repo_name"] == "bad_project"
    
    status_res = client.get(f"/api/analysis/{analysis_id}")
    assert status_res.status_code == 200

def test_comparison_endpoint(client):
    # Run bad project
    bad_res = client.post("/api/analyze", json={"github_url": "sample:bad_project", "use_ai": False})
    bad_id = bad_res.json()["id"]

    # Run improved project
    good_res = client.post("/api/analyze", json={"github_url": "sample:improved_project", "use_ai": False})
    good_id = good_res.json()["id"]

    # Compare
    comp_res = client.get(f"/api/analysis/compare?before_id={bad_id}&after_id={good_id}")
    assert comp_res.status_code == 200
    comp_data = comp_res.json()
    assert comp_data["before_id"] == bad_id
    assert comp_data["after_id"] == good_id
    assert "overall_score_delta" in comp_data
    assert "category_deltas" in comp_data
