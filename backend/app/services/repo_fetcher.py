import os
import re
import shutil
import zipfile
import tempfile
import stat
from typing import Tuple, List, Dict, Optional, Generator
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from urllib.parse import urljoin, urlsplit
import httpx

from backend.app.core.config import settings

BINARY_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.webp', '.bmp',
    '.mp4', '.webm', '.mp3', '.wav', '.ogg',
    '.zip', '.tar', '.gz', '.rar', '.7z',
    '.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx',
    '.exe', '.dll', '.so', '.dylib', '.bin', '.obj', '.o', '.class',
    '.pyc', '.pyo', '.pyd', '.wasm', '.node', '.jar', '.war'
}

IGNORED_DIRECTORIES = {
    '.git', '.svn', '.hg', 'node_modules', '__pycache__', '.pytest_cache',
    '.venv', 'venv', 'env', 'dist', 'build', '.idea', '.vscode', '.next', '.nuxt'
}

class RepositoryFetchError(Exception):
    pass

class SafeRepositoryWorkspace:
    def __init__(self, workspace_path: str, repo_name: str, owner: str, is_sample: bool = False):
        self.workspace_path = str(Path(workspace_path).resolve())
        self.repo_name = repo_name
        self.owner = owner
        self.is_sample = is_sample
        self._file_cache: Dict[str, str] = {}
        self._all_files: List[str] = []
        self._scan_files()

    def _scan_files(self):
        file_list = []
        for root, dirs, files in os.walk(self.workspace_path):
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRECTORIES]
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, self.workspace_path).replace('\\', '/')
                file_list.append(rel_path)
                
                if len(file_list) >= settings.MAX_REPO_FILES:
                    break
            if len(file_list) >= settings.MAX_REPO_FILES:
                break
        self._all_files = sorted(file_list)

    @property
    def files(self) -> List[str]:
        return self._all_files

    def read_text(self, rel_path: str) -> Optional[str]:
        rel_path = rel_path.replace('\\', '/')
        if rel_path in self._file_cache:
            return self._file_cache[rel_path]
        
        ext = os.path.splitext(rel_path)[1].lower()
        if ext in BINARY_EXTENSIONS:
            return None

        full_path = (Path(self.workspace_path) / rel_path).resolve()
        if not full_path.is_relative_to(Path(self.workspace_path)):
            return None

        if not full_path.exists() or not full_path.is_file():
            return None

        try:
            if full_path.stat().st_size > settings.MAX_FILE_SIZE_KB * 1024:
                return None
            with full_path.open('r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                self._file_cache[rel_path] = content
                return content
        except Exception:
            return None

    def exists(self, rel_path: str) -> bool:
        full_path = (Path(self.workspace_path) / rel_path.replace('\\', '/')).resolve()
        return full_path.is_relative_to(Path(self.workspace_path)) and full_path.exists()

# Safe characters for GitHub owner and repo names.
_SAFE_SLUG_RE = re.compile(r'^[\w\-\.]{1,100}$')


def _safe_slug(value: str, label: str) -> str:
    """Validate that an owner/repo slug contains only safe characters."""
    if not _SAFE_SLUG_RE.match(value):
        raise RepositoryFetchError(f'Invalid {label} name: {value!r}')
    return value


def parse_github_url(url: str) -> Tuple[str, str]:
    if not isinstance(url, str):
        raise RepositoryFetchError('Repository URL must be text')
    url = url.strip()
    if any(ord(char) < 32 or ord(char) == 127 for char in url):
        raise RepositoryFetchError('Repository URL contains unsupported control characters')
    if url.startswith('sample:'):
        sample_name = url.split(':', 1)[1]
        # Restrict to simple alphanumeric/dash/underscore names — no path components.
        if not re.match(r'^[\w\-]{1,64}$', sample_name):
            raise RepositoryFetchError(f'Invalid sample project name: {sample_name!r}')
        return ('sample', sample_name)
    if url.startswith('local:'):
        # local: is an internal-only protocol for self-analysis (uses the current
        # working directory). Only the literal '.' is allowed from the API layer.
        # See AnalyzeRequest.validate_url which enforces this.
        local_path = url.split(':', 1)[1]
        if local_path != '.':
            raise RepositoryFetchError(
                "The 'local:' protocol only accepts '.' (current directory). "
                "Use a public GitHub URL for remote repositories."
            )
        return ('local', local_path)

    if url.startswith(('github.com/', 'www.github.com/')):
        url = 'https://' + url
    try:
        parsed = urlsplit(url)
        if parsed.scheme.lower() not in {'http', 'https'} or parsed.hostname not in {'github.com', 'www.github.com'}:
            raise ValueError
        if parsed.username or parsed.password or parsed.port or parsed.query or parsed.fragment:
            raise ValueError
        parts = [part for part in parsed.path.split('/') if part]
        if len(parts) == 4 and parts[2] == 'tree':
            parts = parts[:2]
        if len(parts) != 2:
            raise ValueError
        owner, repo = parts
        if repo.endswith('.git'):
            repo = repo[:-4]
        owner = _safe_slug(owner, 'owner')
        repo = _safe_slug(repo, 'repository')
        if owner in {'.', '..'} or repo in {'.', '..'}:
            raise ValueError
        return owner, repo
    except (ValueError, TypeError):
        raise RepositoryFetchError('Invalid GitHub URL format; use https://github.com/owner/repository') from None


_ARCHIVE_HOSTS = {'github.com', 'api.github.com', 'codeload.github.com'}


def _download_archive(client: httpx.Client, url: str, path: str, max_bytes: int) -> bool:
    """Download an archive with an explicit redirect allowlist and byte cap."""
    for _ in range(6):
        parsed = urlsplit(url)
        try:
            port = parsed.port
        except ValueError:
            raise RepositoryFetchError('GitHub returned an unsafe archive redirect') from None
        if parsed.scheme != 'https' or parsed.hostname not in _ARCHIVE_HOSTS or parsed.username or parsed.password or port not in {None, 443}:
            raise RepositoryFetchError('GitHub returned an unsafe archive redirect')
        with client.stream('GET', url, follow_redirects=False) as response:
            if response.status_code in {301, 302, 303, 307, 308}:
                location = response.headers.get('location')
                if not location:
                    return False
                url = urljoin(url, location)
                continue
            if response.status_code != 200:
                return False
            size = 0
            with open(path, 'wb') as output:
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > max_bytes:
                        raise RepositoryFetchError('Repository exceeds maximum download size limit')
                    output.write(chunk)
            if size > 100:
                return True
            os.remove(path)
            return False
    raise RepositoryFetchError('GitHub returned too many archive redirects')


def _extract_archive_safely(zf: zipfile.ZipFile, extraction_root: Path, max_size: int, max_files: int) -> None:
    """Extract only regular files whose resolved paths stay inside the workspace."""
    total_extracted_size = 0
    extracted_files = 0
    extraction_root = extraction_root.resolve()
    for member in zf.infolist():
        normalized_name = member.filename.replace('\\', '/')
        member_path = PurePosixPath(normalized_name)
        if (member_path.is_absolute() or not member_path.parts
                or any(part in {'..', ''} for part in member_path.parts)
                or re.match(r'^[A-Za-z]:', normalized_name)):
            continue
        if stat.S_ISLNK(member.external_attr >> 16):
            continue
        if not member.is_dir():
            extracted_files += 1
            if extracted_files > max_files:
                continue
        total_extracted_size += member.file_size
        if total_extracted_size > max_size:
            raise RepositoryFetchError('Extracted repository exceeds maximum size limit.')
        target = (extraction_root / Path(*member_path.parts)).resolve()
        if not target.is_relative_to(extraction_root):
            continue
        if member.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member) as source, target.open('wb') as output:
                shutil.copyfileobj(source, output, length=1024 * 64)

@contextmanager
def fetch_repository(target: str) -> Generator[SafeRepositoryWorkspace, None, None]:
    owner, repo = parse_github_url(target)
    
    if owner == 'sample':
        sample_dir = os.path.join(settings.SAMPLE_PROJECTS_DIR, repo)
        if not os.path.exists(sample_dir):
            raise RepositoryFetchError(f'Sample project not found: {repo}')
        workspace = SafeRepositoryWorkspace(
            workspace_path=sample_dir,
            repo_name=repo,
            owner='sample',
            is_sample=True
        )
        yield workspace
        return

    if owner == 'local':
        if not os.path.exists(repo):
            raise RepositoryFetchError(f'Local directory not found: {repo}')
        workspace = SafeRepositoryWorkspace(
            workspace_path=repo,
            repo_name=os.path.basename(os.path.abspath(repo)),
            owner='local',
            is_sample=False
        )
        yield workspace
        return

    temp_dir = tempfile.mkdtemp(prefix=f'review_{owner}_{repo}_', dir=settings.SCRATCH_DIR)
    try:
        zip_urls = [
            f'https://github.com/{owner}/{repo}/archive/refs/heads/main.zip',
            f'https://github.com/{owner}/{repo}/archive/refs/heads/master.zip',
            f'https://api.github.com/repos/{owner}/{repo}/zipball'
        ]
        
        zip_path = os.path.join(temp_dir, 'repo.zip')
        downloaded = False
        
        headers = {'User-Agent': 'Portfolio-Project-Reviewer-Agent'}
        with httpx.Client(timeout=30.0, follow_redirects=False, headers=headers) as client:
            for zip_url in zip_urls:
                try:
                    if _download_archive(client, zip_url, zip_path, settings.MAX_REPO_SIZE_MB * 1024 * 1024):
                        downloaded = True
                        break
                except RepositoryFetchError:
                    raise
                except httpx.RequestError:
                    continue

        if not downloaded:
            raise RepositoryFetchError(f'Could not download public repository {owner}/{repo}. Ensure the repository is public and accessible.')

        if os.path.exists(zip_path):
            with zipfile.ZipFile(zip_path, 'r') as zf:
                _extract_archive_safely(
                    zf, Path(temp_dir), settings.MAX_REPO_SIZE_MB * 1024 * 1024, settings.MAX_REPO_FILES
                )
            os.remove(zip_path)

        subdirs = [os.path.join(temp_dir, d) for d in os.listdir(temp_dir) if os.path.isdir(os.path.join(temp_dir, d))]
        actual_root = temp_dir
        if len(subdirs) == 1 and not os.path.exists(os.path.join(temp_dir, 'README.md')) and not os.path.exists(os.path.join(temp_dir, 'package.json')):
            actual_root = subdirs[0]

        workspace = SafeRepositoryWorkspace(
            workspace_path=actual_root,
            repo_name=repo,
            owner=owner,
            is_sample=False
        )
        yield workspace
    finally:
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass
