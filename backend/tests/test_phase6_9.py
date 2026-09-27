def test_phase6_to_phase9_api_chain(client):
    response = client.post('/api/analyze', json={'github_url': 'sample:bad_project', 'use_ai': False})
    assert response.status_code == 200
    analysis_id = response.json()['id']

    portfolio = client.get(f'/api/portfolio/{analysis_id}')
    assert portfolio.status_code == 200
    assert portfolio.json()['payload']['analysis_id'] == analysis_id
    assert portfolio.json()['payload']['claims'] is not None

    monitor = client.get(f'/api/monitor/{analysis_id}')
    assert monitor.status_code == 200
    assert monitor.json()['current']['analysis_id'] == analysis_id
    assert monitor.json()['current']['commit_sha'] is None  # no fabricated Git metadata

    session = client.post(f'/api/interview/{analysis_id}/sessions', json={'mode': 'Project Defense', 'limit': 3})
    assert session.status_code == 200
    session_data = session.json()
    assert session_data['questions']
    answer = client.post(f"/api/interview/sessions/{session_data['id']}/answers", json={'question_index': 0, 'answer': 'The repository evidence supports this explanation.'})
    assert answer.status_code == 200
    assert answer.json()['evaluation']['rating'] in {'STRONG', 'PARTIAL', 'UNSUPPORTED', 'WEAK'}

    passport = client.get(f'/api/passport/{analysis_id}')
    assert passport.status_code == 200
    assert passport.json()['payload_hash']
    verification = client.post(f'/api/passport/{analysis_id}/verify')
    assert verification.status_code == 200
    assert verification.json()['status'] == 'VALID'


def test_monitor_detects_finding_and_evidence_changes():
    from backend.app.services.phase6_9 import compare_snapshots
    before = {'score': 70, 'finding_count': 2, 'finding_keys': ['security:a', 'testing:b'], 'evidence_files': ['README.md'], 'claim_statuses': {'uses python': 'SUPPORTED'}}
    after = {'score': 82, 'finding_count': 1, 'finding_keys': ['testing:b', 'docs:c'], 'evidence_files': ['app.py'], 'claim_statuses': {'uses python': 'UNVERIFIED'}}
    result = compare_snapshots(before, after)
    assert result['new_findings'] == ['docs:c']
    assert result['resolved_findings'] == ['security:a']
    assert result['new_evidence'] == ['app.py']
    assert result['lost_evidence'] == ['README.md']
    assert result['claim_status_changes'][0]['before'] == 'SUPPORTED'


def test_passport_modified_payload_is_detected(client, db_session):
    response = client.post('/api/analyze', json={'github_url': 'sample:improved_project', 'use_ai': False})
    analysis_id = response.json()['id']
    client.get(f'/api/passport/{analysis_id}')
    from backend.app.models.phase6_9 import ProofPassport
    row = db_session.query(ProofPassport).filter(ProofPassport.analysis_id == analysis_id).first()
    row.payload = {**row.payload, 'tampered': True}
    db_session.commit()
    assert client.post(f'/api/passport/{analysis_id}/verify').json()['status'] == 'MODIFIED'


def test_portfolio_technology_evidence_has_explicit_status(client):
    response = client.post('/api/analyze', json={'github_url': 'sample:bad_project', 'use_ai': False})
    analysis_id = response.json()['id']
    payload = client.get(f'/api/portfolio/{analysis_id}').json()['payload']
    assert payload['technologies']
    assert all(t['status'] in {'VERIFIED', 'INFERRED', 'UNVERIFIED', 'OBSERVED', 'SUPPORTED', 'PARTIALLY_SUPPORTED'} for t in payload['technologies'])
    assert all('evidence' in t and 'source' in t for t in payload['technologies'])


def test_compare_snapshots_detects_changed_finding_claim_recommendation_and_verification():
    from backend.app.services.phase6_9 import compare_snapshots
    before = {
        'finding_keys': ['security:a'], 'finding_count': 1,
        'finding_details': {'security:a': {'severity': 'HIGH', 'file_path': 'a.py', 'evidence': 'old', 'description': 'old desc'}},
        'claim_statuses': {'uses python': 'SUPPORTED'},
        'recommendation_statuses': {'r1': 'OPEN'},
        'verification_results': {'security:a': 'FAIL'},
        'category_scores': {'Security': 60},
    }
    after = {
        'finding_keys': ['security:a'], 'finding_count': 1,
        'finding_details': {'security:a': {'severity': 'MEDIUM', 'file_path': 'b.py', 'evidence': 'new', 'description': 'new desc'}},
        'claim_statuses': {'uses python': 'UNVERIFIED', 'uses react': 'SUPPORTED'},
        'recommendation_statuses': {'r1': 'RESOLVED'},
        'verification_results': {'security:a': 'PASS'},
        'category_scores': {'Security': 82},
    }
    result = compare_snapshots(before, after)
    assert result['changed_findings'][0]['status'] == 'CHANGED'
    assert set(result['changed_findings'][0]['changes']) == {'severity', 'file_path', 'evidence', 'description'}
    assert any(x['status'] == 'CLAIM STATUS CHANGED' for x in result['claim_status_changes'])
    assert any(x['status'] == 'NEW CLAIM' for x in result['claim_status_changes'])
    assert result['recommendation_changes'][0]['after'] == 'RESOLVED'
    assert result['verification_changes'][0]['after'] == 'PASS'
    assert result['category_score_changes']['Security']['after'] == 82


def test_interview_multiple_unsupported_technologies_are_not_strong():
    from backend.app.services.phase6_9 import evaluate_answer
    q = {'expected_topics': ['FastAPI'], 'evidence_reference': 'main.py', 'evidence_summary': 'FastAPI import detected'}
    result = evaluate_answer(q, 'We use FastAPI with PostgreSQL, Redis and Kubernetes.')
    assert result['rating'] == 'PARTIAL'
    assert {'postgresql', 'redis', 'kubernetes'} <= set(result['unsupported_claims'])


def test_interview_empty_answer_is_weak():
    from backend.app.services.phase6_9 import evaluate_answer
    assert evaluate_answer({'expected_topics': ['FastAPI']}, '   ')['rating'] == 'WEAK'


def test_repeated_interview_submission_replaces_existing_answer(client):
    analysis_id = client.post('/api/analyze', json={'github_url': 'sample:bad_project', 'use_ai': False}).json()['id']
    session = client.post(f'/api/interview/{analysis_id}/sessions', json={'mode': 'Project Defense', 'limit': 1}).json()
    sid = session['id']
    client.post(f'/api/interview/sessions/{sid}/answers', json={'question_index': 0, 'answer': 'first answer'})
    client.post(f'/api/interview/sessions/{sid}/answers', json={'question_index': 0, 'answer': 'second answer'})
    stored = client.get(f'/api/interview/sessions/{sid}').json()
    assert len(stored['answers']) == 1
    assert stored['answers'][0]['answer'] == 'second answer'


def test_passport_without_previous_analysis_has_explicit_history_message(client, db_session):
    from backend.app.models.findings import AnalysisRun
    for old in db_session.query(AnalysisRun).filter(AnalysisRun.repo_url == 'sample:improved_project').all():
        db_session.delete(old)
    db_session.commit()
    analysis_id = client.post('/api/analyze', json={'github_url': 'sample:improved_project', 'use_ai': False}).json()['id']
    payload = client.get(f'/api/passport/{analysis_id}').json()['payload']
    assert payload['improvements'] == 'Improvement history unavailable: no previous analysis was found.'
    assert payload['engineering_confidence']['label'] == 'Portfolio Reviewer Score'


def test_passport_with_previous_analysis_contains_improvement_history(client):
    repo = 'sample:improved_project'
    first = client.post('/api/analyze', json={'github_url': repo, 'use_ai': False}).json()['id']
    # Ensure the previous snapshot exists before the second analysis.
    client.get(f'/api/monitor/{first}')
    second = client.post('/api/analyze', json={'github_url': repo, 'use_ai': False}).json()['id']
    payload = client.get(f'/api/passport/{second}').json()['payload']
    assert payload['improvements'] != 'Improvement history unavailable: no previous analysis was found.'
    assert isinstance(payload['improvements'], dict)
    assert 'changed_findings' in payload['improvements']


def test_passport_hash_changes_when_payload_is_modified_and_restores(client, db_session):
    from backend.app.models.phase6_9 import ProofPassport
    analysis_id = client.post('/api/analyze', json={'github_url': 'sample:improved_project', 'use_ai': False}).json()['id']
    client.get(f'/api/passport/{analysis_id}')
    row = db_session.query(ProofPassport).filter(ProofPassport.analysis_id == analysis_id).first()
    original = dict(row.payload)
    row.payload = {**original, 'tampered': True}
    db_session.commit()
    assert client.post(f'/api/passport/{analysis_id}/verify').json()['status'] == 'MODIFIED'
    row.payload = original
    db_session.commit()
    assert client.post(f'/api/passport/{analysis_id}/verify').json()['status'] == 'VALID'


def test_phase6_9_end_to_end_with_improvement_snapshot(client, db_session):
    from backend.app.models.findings import AnalysisRun, Finding
    repo = 'sample:improved_project'
    first = client.post('/api/analyze', json={'github_url': repo, 'use_ai': False}).json()['id']
    client.get(f'/api/portfolio/{first}')
    client.get(f'/api/monitor/{first}')
    first_findings = db_session.query(Finding).filter(Finding.analysis_id == first).all()

    second = client.post('/api/analyze', json={'github_url': repo, 'use_ai': False}).json()['id']
    second_findings = db_session.query(Finding).filter(Finding.analysis_id == second).all()
    # Simulate the repository's improved state at the persisted-analysis layer:
    # remove one matching finding from the second snapshot.
    if first_findings and second_findings:
        second_findings[0].finding_key = first_findings[0].finding_key
        db_session.delete(second_findings[0])
        db_session.commit()

    client.get(f'/api/monitor/{second}')
    passport = client.get(f'/api/passport/{second}').json()
    assert 'improvements' in passport['payload']
    assert passport['payload']['improvements'] != 'Improvement history unavailable: no previous analysis was found.'
    sid = client.post(f'/api/interview/{second}/sessions', json={'mode': 'Project Defense', 'limit': 1}).json()['id']
    q = client.get(f'/api/interview/sessions/{sid}').json()['questions'][0]
    client.post(f'/api/interview/sessions/{sid}/answers', json={'question_index': 0, 'answer': str(q['expected_topics'][0]) + ' is supported by repository evidence.'})
    assert client.post(f'/api/passport/{second}/verify').json()['status'] == 'VALID'
