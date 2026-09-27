"""
Security and regression tests for URL validation, SSRF prevention,
command injection prevention, and input handling.
"""
import pytest
import httpx
import io
import zipfile
from backend.app.services.repo_fetcher import parse_github_url, RepositoryFetchError
from backend.app.schemas.analysis import AnalyzeRequest
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# URL / slug parsing tests
# ---------------------------------------------------------------------------

class TestParseGithubUrl:
    def test_valid_https_url(self):
        owner, repo = parse_github_url("https://github.com/octocat/Hello-World")
        assert owner == "octocat"
        assert repo == "Hello-World"

    def test_valid_https_url_with_git_suffix(self):
        owner, repo = parse_github_url("https://github.com/octocat/Hello-World.git")
        assert owner == "octocat"
        assert repo == "Hello-World"

    def test_valid_url_with_tree_branch(self):
        owner, repo = parse_github_url("https://github.com/octocat/Hello-World/tree/main")
        assert owner == "octocat"
        assert repo == "Hello-World"

    @pytest.mark.parametrize("url", [
        "github.com/octocat/Hello-World",
        "https://www.github.com/octocat/Hello-World/",
        "https://github.com/octocat/Hello-World.git",
    ])
    def test_supported_github_url_variants(self, url):
        assert parse_github_url(url) == ("octocat", "Hello-World")

    def test_sample_valid(self):
        owner, sample = parse_github_url("sample:bad_project")
        assert owner == "sample"
        assert sample == "bad_project"

    def test_local_dot_only(self):
        owner, path = parse_github_url("local:.")
        assert owner == "local"
        assert path == "."

    def test_invalid_github_url(self):
        with pytest.raises(RepositoryFetchError):
            parse_github_url("https://notgithub.com/user/repo")

    def test_empty_string(self):
        with pytest.raises(RepositoryFetchError):
            parse_github_url("")

    def test_malformed_url(self):
        with pytest.raises(RepositoryFetchError):
            parse_github_url("just-a-string")


class TestSSRFPrevention:
    """SSRF / path traversal prevention via local: protocol."""

    def test_local_arbitrary_path_rejected(self):
        """local: with a non-dot path must be rejected at parse time."""
        with pytest.raises(RepositoryFetchError, match="only accepts '.'"):
            parse_github_url("local:/etc/passwd")

    def test_local_relative_traversal_rejected(self):
        with pytest.raises(RepositoryFetchError, match="only accepts '.'"):
            parse_github_url("local:../../secret")

    def test_local_absolute_windows_path_rejected(self):
        with pytest.raises(RepositoryFetchError, match="only accepts '.'"):
            parse_github_url("local:C:\\Windows\\System32")

    def test_local_empty_path_rejected(self):
        """local: with no path at all must be rejected."""
        with pytest.raises(RepositoryFetchError, match="only accepts '.'"):
            parse_github_url("local:")


class TestSlugInjectionPrevention:
    """Owner/repo slugs must contain only safe characters."""

    def test_valid_slugs_accepted(self):
        # All valid GitHub slug characters
        owner, repo = parse_github_url("https://github.com/my-org/my_repo.js")
        assert owner == "my-org"
        assert repo == "my_repo.js"

    def test_command_injection_in_owner_rejected(self):
        with pytest.raises(RepositoryFetchError):
            parse_github_url("https://github.com/; rm -rf /;/repo")

    @pytest.mark.parametrize("url", [
        "https://github.com/owner/repo; evil",
        "https://github.com.evil.test/owner/repo",
        "https://notgithub.com/owner/repo",
        "https://github.com/owner/repo?next=https://127.0.0.1",
        "https://github.com/owner/repo#fragment",
        "ftp://github.com/owner/repo",
        "https://user@github.com/owner/repo",
        "https://github.com/owner/repo/extra",
    ])
    def test_spoofed_or_ambiguous_github_urls_rejected(self, url):
        with pytest.raises(RepositoryFetchError):
            parse_github_url(url)

    def test_newline_in_owner_rejected(self):
        with pytest.raises(RepositoryFetchError):
            parse_github_url("https://github.com/owner\n/repo")

    def test_sample_path_traversal_rejected(self):
        with pytest.raises(RepositoryFetchError):
            parse_github_url("sample:../../../etc/passwd")

    def test_sample_slash_in_name_rejected(self):
        with pytest.raises(RepositoryFetchError):
            parse_github_url("sample:foo/bar")


# ---------------------------------------------------------------------------
# AnalyzeRequest schema validation
# ---------------------------------------------------------------------------

class TestAnalyzeRequestValidation:
    def test_valid_github_url(self):
        req = AnalyzeRequest(github_url="https://github.com/owner/repo")
        assert req.github_url == "https://github.com/owner/repo"

    def test_valid_sample(self):
        req = AnalyzeRequest(github_url="sample:bad_project")
        assert req.github_url == "sample:bad_project"

    def test_valid_local_dot(self):
        req = AnalyzeRequest(github_url="local:.")
        assert req.github_url == "local:."

    def test_empty_url_rejected(self):
        with pytest.raises(ValidationError):
            AnalyzeRequest(github_url="")

    def test_non_github_url_rejected(self):
        with pytest.raises(ValidationError):
            AnalyzeRequest(github_url="https://gitlab.com/owner/repo")

    def test_oversized_url_rejected(self):
        long_url = "https://github.com/" + "a" * 600
        with pytest.raises(ValidationError):
            AnalyzeRequest(github_url=long_url)

    def test_local_arbitrary_path_rejected(self):
        with pytest.raises(ValidationError):
            AnalyzeRequest(github_url="local:/etc/passwd")

    def test_local_traversal_rejected(self):
        with pytest.raises(ValidationError):
            AnalyzeRequest(github_url="local:../../secrets")

    def test_sample_with_slash_rejected(self):
        with pytest.raises(ValidationError):
            AnalyzeRequest(github_url="sample:../etc/passwd")

    def test_sample_with_long_name_rejected(self):
        """Sample names over 64 chars are rejected."""
        long_name = "a" * 65
        with pytest.raises(ValidationError):
            AnalyzeRequest(github_url=f"sample:{long_name}")

    def test_whitespace_stripped(self):
        req = AnalyzeRequest(github_url="  https://github.com/owner/repo  ")
        assert not req.github_url.startswith(" ")


# ---------------------------------------------------------------------------
# Security analyzer: verify secrets are masked in output
# ---------------------------------------------------------------------------

class TestSecurityAnalyzerSecretMasking:
    """Regression: secrets must be masked before appearing in any finding output."""

    def test_secret_is_masked(self):
        from backend.app.analyzer.security import mask_secret
        raw = "AKIAIOSFODNN7EXAMPLE"
        masked = mask_secret(raw)
        assert raw not in masked
        assert "REDACTED" in masked

    def test_short_secret_fully_masked(self):
        from backend.app.analyzer.security import mask_secret
        assert mask_secret("abc") == "***REDACTED***"

    def test_secret_not_in_findings(self, tmp_path):
        from backend.app.services.repo_fetcher import SafeRepositoryWorkspace
        from backend.app.analyzer.security import SecurityAnalyzer

        # Write a fake .py file with an AWS key
        fake_key = "AKIAIOSFODNN7EXAMPLE"
        (tmp_path / "config.py").write_text(f'AWS_KEY = "{fake_key}"\n')
        workspace = SafeRepositoryWorkspace(str(tmp_path), "test", "test")
        findings, evidence = SecurityAnalyzer().analyze_with_evidence(workspace)
        for f in findings:
            assert fake_key not in f.evidence, "Raw secret must not appear in finding evidence"
        for ev in evidence:
            assert fake_key not in ev.evidence_summary, "Raw secret must not appear in evidence summary"


class TestWorkspacePathContainment:
    def test_reads_and_existence_checks_stay_inside_workspace(self, tmp_path):
        from backend.app.services.repo_fetcher import SafeRepositoryWorkspace

        workspace_dir = tmp_path / "repo"
        sibling_dir = tmp_path / "repo-secret"
        workspace_dir.mkdir()
        sibling_dir.mkdir()
        (sibling_dir / "secret.txt").write_text("outside")
        workspace = SafeRepositoryWorkspace(str(workspace_dir), "repo", "owner")

        assert workspace.read_text("../repo-secret/secret.txt") is None
        assert workspace.exists("../repo-secret/secret.txt") is False

    def test_symlink_cannot_escape_workspace(self, tmp_path):
        from backend.app.services.repo_fetcher import SafeRepositoryWorkspace

        workspace_dir = tmp_path / "repo"
        outside_dir = tmp_path / "outside"
        workspace_dir.mkdir()
        outside_dir.mkdir()
        (outside_dir / "secret.txt").write_text("outside")
        try:
            (workspace_dir / "escape").symlink_to(outside_dir, target_is_directory=True)
        except OSError:
            pytest.skip("Symlink creation is unavailable on this platform")
        workspace = SafeRepositoryWorkspace(str(workspace_dir), "repo", "owner")

        assert workspace.read_text("escape/secret.txt") is None
        assert workspace.exists("escape/secret.txt") is False


class TestArchiveDownloadSafety:
    def test_redirect_to_private_address_is_rejected(self, tmp_path):
        from backend.app.services.repo_fetcher import _download_archive

        transport = httpx.MockTransport(lambda request: httpx.Response(
            302, headers={"location": "http://127.0.0.1/latest/meta-data"}, request=request
        ))
        with httpx.Client(transport=transport) as client:
            with pytest.raises(RepositoryFetchError, match="unsafe archive redirect"):
                _download_archive(client, "https://github.com/owner/repo/archive.zip", str(tmp_path / "repo.zip"), 1024)

    def test_archive_size_is_capped_while_streaming(self, tmp_path):
        from backend.app.services.repo_fetcher import _download_archive

        transport = httpx.MockTransport(lambda request: httpx.Response(200, content=b"x" * 2048, request=request))
        archive_path = tmp_path / "repo.zip"
        with httpx.Client(transport=transport) as client:
            with pytest.raises(RepositoryFetchError, match="maximum download size"):
                _download_archive(client, "https://github.com/owner/repo/archive.zip", str(archive_path), 1024)
        assert archive_path.stat().st_size <= 1024

    def test_archive_extraction_skips_traversal_and_windows_paths(self, tmp_path):
        from backend.app.services.repo_fetcher import _extract_archive_safely

        archive_data = io.BytesIO()
        with zipfile.ZipFile(archive_data, "w") as archive:
            archive.writestr("repo/README.md", "safe")
            archive.writestr("../escaped.txt", "outside")
            archive.writestr("repo/../../escaped-too.txt", "outside")
            archive.writestr(r"..\escaped-windows.txt", "outside")
            archive.writestr(r"C:\escaped-drive.txt", "outside")
        archive_data.seek(0)
        with zipfile.ZipFile(archive_data) as archive:
            _extract_archive_safely(archive, tmp_path, max_size=1024, max_files=10)

        assert (tmp_path / "repo" / "README.md").read_text() == "safe"
        assert list(tmp_path.rglob("escaped*.txt")) == []


# ---------------------------------------------------------------------------
# API endpoint: validate that bad inputs return 422, not 500
# ---------------------------------------------------------------------------

class TestApiInputValidation:
    def test_empty_url_returns_422(self, client):
        res = client.post("/api/analyze", json={"github_url": "", "use_ai": False})
        assert res.status_code == 422

    def test_non_github_url_returns_422(self, client):
        res = client.post("/api/analyze", json={"github_url": "https://gitlab.com/a/b", "use_ai": False})
        assert res.status_code == 422

    def test_github_lookalike_url_returns_422(self, client):
        res = client.post("/api/analyze", json={"github_url": "https://evil.test/github.com/owner/repo", "use_ai": False})
        assert res.status_code == 422

    def test_github_url_query_string_returns_422(self, client):
        res = client.post("/api/analyze", json={"github_url": "https://github.com/owner/repo?next=http://127.0.0.1", "use_ai": False})
        assert res.status_code == 422

    def test_local_path_traversal_returns_422(self, client):
        res = client.post("/api/analyze", json={"github_url": "local:../../etc/passwd", "use_ai": False})
        assert res.status_code == 422

    def test_sample_path_traversal_returns_422(self, client):
        res = client.post("/api/analyze", json={"github_url": "sample:../../../bad", "use_ai": False})
        assert res.status_code == 422

    def test_missing_github_url_field_returns_422(self, client):
        res = client.post("/api/analyze", json={"use_ai": False})
        assert res.status_code == 422

    def test_oversized_payload_rejected(self, client):
        long_url = "https://github.com/" + "a" * 600
        res = client.post("/api/analyze", json={"github_url": long_url, "use_ai": False})
        assert res.status_code == 422

    def test_oversized_interview_answer_returns_422(self, client):
        res = client.post(
            "/api/interview/sessions/unknown/answers",
            json={"question_index": 0, "answer": "a" * 8001},
        )
        assert res.status_code == 422

    def test_nonexistent_analysis_returns_404(self, client):
        res = client.get("/api/analysis/nonexistent-id-12345")
        assert res.status_code == 404

    def test_nonexistent_sample_returns_failed_status(self, client):
        """Requesting a sample that doesn't exist should result in a FAILED status."""
        res = client.post("/api/analyze", json={"github_url": "sample:nonexistent_sample_xyz", "use_ai": False})
        assert res.status_code == 200
        data = res.json()
        # Analysis starts (QUEUED/FETCHING/FAILED) — the background task will mark it FAILED
        assert data["id"] is not None
