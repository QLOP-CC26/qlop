from __future__ import annotations

import re
from difflib import get_close_matches

SKILL_ALIASES: dict[str, str] = {
    "js": "JavaScript", "ts": "TypeScript", "py": "Python",
    "k8s": "Kubernetes", "tf": "TensorFlow", "pt": "PyTorch",
    "pg": "PostgreSQL", "postgres": "PostgreSQL", "mongo": "MongoDB",
    "gcp": "Google Cloud Platform", "aws": "Amazon Web Services",
    "react.js": "React", "reactjs": "React", "vue.js": "Vue",
    "vuejs": "Vue", "node.js": "Node.js", "nodejs": "Node.js",
    "next.js": "Next.js", "nextjs": "Next.js", "nuxtjs": "Nuxt",
    "nest.js": "NestJS", "nestjs": "NestJS",
    "express.js": "Express", "expressjs": "Express",
    "angular.js": "Angular", "angularjs": "Angular",
    "spring boot": "Spring Boot", "springboot": "Spring Boot",
    "scikit-learn": "Scikit-learn", "sklearn": "Scikit-learn",
    "scikit learn": "Scikit-learn",
    "hugging face": "HuggingFace", "huggingface": "HuggingFace",
    "github actions": "GitHub Actions", "gitlab ci": "GitLab CI",
    "ci/cd": "CI/CD", "cicd": "CI/CD",
    "apache spark": "Spark", "pyspark": "PySpark",
    "ruby on rails": "Rails", "ror": "Rails",
    "asp.net": "ASP.NET", ".net": ".NET", "dotnet": ".NET",
    "visual studio code": "VS Code", "vscode": "VS Code",
    "google cloud": "Google Cloud Platform",
    "microsoft azure": "Azure", "amazon web services": "AWS",
    "weights and biases": "Weights & Biases", "wandb": "Weights & Biases",
    "react native": "React Native", "flutter": "Flutter",
    "power bi": "Power BI", "sql server": "SQL Server", "mssql": "SQL Server",
    "elastic": "Elasticsearch", "elasticsearch": "Elasticsearch",
    "argo cd": "ArgoCD", "argocd": "ArgoCD",
    "apache airflow": "Airflow", "llama index": "LlamaIndex",
    "llamaindex": "LlamaIndex",
}


def safe_role_filename(role_name: str) -> str:
    """Replace path-unsafe characters (slashes) with underscores."""
    return re.sub(r"[\\/]", "_", role_name)


def fuzzy_match_skill(skill: str, vocab_keys: list[str], threshold: float = 0.6) -> str | None:
    matches = get_close_matches(skill, vocab_keys, n=1, cutoff=threshold)
    return matches[0] if matches else None


def flatten_skills(skills: list[str]) -> list[str]:
    """Lowercase and deduplicate a flat skill list."""
    seen: set[str] = set()
    flat: list[str] = []
    for s in skills:
        lowered = s.lower().strip()
        if lowered and lowered not in seen:
            seen.add(lowered)
            flat.append(lowered)
    return flat


def safe_float(value: object) -> float:
    try:
        val = float(value)  # type: ignore[arg-type]
        if not __import__("math").isfinite(val):
            return 0.0
        return val
    except (ValueError, TypeError):
        return 0.0
