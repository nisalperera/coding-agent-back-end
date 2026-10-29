from __future__ import annotations

from collections.abc import Mapping

TECHNOLOGY_CATALOG: Mapping[str, tuple[str, ...]] = {
    "languages": (
        "python",
        "typescript",
        "javascript",
        "java",
        "go",
        "rust",
        "cpp",
    ),
    "frameworks": ("fastapi", "django", "flask", "react", "nextjs", "spring", "gin", "actix"),
    "runtimes": ("node", "bun", "deno", "python", "jvm"),
    "databaseCategories": ("sql", "nosql", "cache", "search", "vector"),
}

FRAMEWORK_LANGUAGE_COMPATIBILITY: Mapping[str, tuple[str, ...]] = {
    "fastapi": ("python",),
    "django": ("python",),
    "flask": ("python",),
    "react": ("typescript", "javascript"),
    "nextjs": ("typescript", "javascript"),
    "spring": ("java",),
    "gin": ("go",),
    "actix": ("rust",),
}

RUNTIME_LANGUAGE_COMPATIBILITY: Mapping[str, tuple[str, ...]] = {
    "node": ("typescript", "javascript"),
    "bun": ("typescript", "javascript"),
    "deno": ("typescript", "javascript"),
    "python": ("python",),
    "jvm": ("java",),
}
