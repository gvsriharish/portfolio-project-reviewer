EXPLAIN_FINDINGS_PROMPT = """
You are a senior principal engineer and mentor reviewing a developer repository.
You have been provided with deterministic static analysis findings from a codebase.

Repository: {repo_name}
Languages: {languages}
Frameworks: {frameworks}

Findings:
{findings_json}

Provide:
1. Prioritized Roadmap categorized into:
   - "Fix First" (Urgent: Security risks, exposed secrets, broken syntax, zero tests)
   - "Improve Next" (Important: Code complexity, missing setup guides, unpinned dependencies)
   - "Portfolio Improvements" (Recruiter polish: Visual demo, architecture diagrams, technical decision narratives)

2. "Explain My Project" summary:
   - Plain-English overview of what this project does
   - Architecture summary and component relationships
   - Key files and their architectural role
   - Notable technical decisions and limitations

3. Project-Specific Interview Preparation:
   - 2 Beginner questions testing core fundamentals
   - 2 Intermediate questions testing architectural choices and data flow
   - 2 Advanced questions testing scalability, security, and trade-offs

Format output strictly as JSON matching the requested schema.
"""
