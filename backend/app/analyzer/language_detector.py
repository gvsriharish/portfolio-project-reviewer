import os
import json
from typing import List, Dict, Set
from backend.app.services.repo_fetcher import SafeRepositoryWorkspace

EXTENSION_MAP = {
    '.py': 'Python',
    '.ts': 'TypeScript',
    '.tsx': 'TypeScript (React)',
    '.js': 'JavaScript',
    '.jsx': 'JavaScript (React)',
    '.html': 'HTML',
    '.css': 'CSS',
    '.scss': 'SCSS',
    '.go': 'Go',
    '.rs': 'Rust',
    '.java': 'Java',
    '.cpp': 'C++',
    '.c': 'C',
    '.cs': 'C#',
    '.rb': 'Ruby',
    '.php': 'PHP',
    '.sh': 'Shell',
    '.sql': 'SQL'
}

class LanguageDetector:
    def detect_languages(self, workspace: SafeRepositoryWorkspace) -> List[str]:
        lang_counts: Dict[str, int] = {}
        for f in workspace.files:
            ext = os.path.splitext(f)[1].lower()
            if ext in EXTENSION_MAP:
                lang = EXTENSION_MAP[ext]
                lang_counts[lang] = lang_counts.get(lang, 0) + 1
        
        sorted_langs = sorted(lang_counts.items(), key=lambda x: x[1], reverse=True)
        return [lang for lang, count in sorted_langs]

    def detect_frameworks(self, workspace: SafeRepositoryWorkspace) -> List[str]:
        frameworks: Set[str] = set()

        reqs = workspace.read_text('requirements.txt') or ''
        pyproject = workspace.read_text('pyproject.toml') or ''
        combined_py = (reqs + '\n' + pyproject).lower()

        if 'fastapi' in combined_py:
            frameworks.add('FastAPI')
        if 'flask' in combined_py:
            frameworks.add('Flask')
        if 'django' in combined_py:
            frameworks.add('Django')
        if 'sqlalchemy' in combined_py:
            frameworks.add('SQLAlchemy')
        if 'pytorch' in combined_py or 'torch' in combined_py:
            frameworks.add('PyTorch')
        if 'tensorflow' in combined_py:
            frameworks.add('TensorFlow')
        if 'streamlit' in combined_py:
            frameworks.add('Streamlit')
        if 'pytest' in combined_py:
            frameworks.add('Pytest')
        if 'google-genai' in combined_py or 'google.generativeai' in combined_py:
            frameworks.add('Google Gemini AI')

        pkg_json_str = workspace.read_text('package.json') or workspace.read_text('frontend/package.json') or ''
        if pkg_json_str:
            try:
                pkg_data = json.loads(pkg_json_str)
                deps = {**pkg_data.get('dependencies', {}), **pkg_data.get('devDependencies', {})}
                deps_lower = {k.lower(): v for k, v in deps.items()}

                if 'react' in deps_lower:
                    frameworks.add('React')
                if 'next' in deps_lower:
                    frameworks.add('Next.js')
                if 'vue' in deps_lower:
                    frameworks.add('Vue')
                if 'svelte' in deps_lower:
                    frameworks.add('Svelte')
                if 'express' in deps_lower:
                    frameworks.add('Express')
                if 'tailwindcss' in deps_lower:
                    frameworks.add('Tailwind CSS')
                if 'vite' in deps_lower:
                    frameworks.add('Vite')
                if 'jest' in deps_lower or 'vitest' in deps_lower:
                    frameworks.add('Jest/Vitest')
            except Exception:
                pass

        return sorted(list(frameworks))
