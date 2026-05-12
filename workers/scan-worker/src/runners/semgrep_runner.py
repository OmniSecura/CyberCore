from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)

# Base ruleset always applied (multi-language OWASP coverage)
_BASE_CONFIGS = ["p/owasp-top-ten", "p/secrets"]

# Language-specific rulesets keyed by extension groups
LANG_CONFIGS: dict[str, list[str]] = {
    "python":     ["p/python"],
    "javascript": ["p/javascript"],
    "typescript": ["p/typescript"],
    "java":       ["p/java"],
    "go":         ["p/go"],
    "php":        ["p/php"],
    "ruby":       ["p/ruby"],
    "c":          ["p/c"],
    "rust":       ["p/rust"],
}

# File extensions → language key
EXT_LANG: dict[str, str] = {
    ".py":   "python",
    ".pyw":  "python",
    ".js":   "javascript",
    ".mjs":  "javascript",
    ".cjs":  "javascript",
    ".jsx":  "javascript",
    ".ts":   "typescript",
    ".tsx":  "typescript",
    ".java": "java",
    ".go":   "go",
    ".php":  "php",
    ".rb":   "ruby",
    ".c":    "c",
    ".h":    "c",
    ".rs":   "rust",
}


def detect_configs(source_dir: Path) -> list[str]:
    """
    Inspect source_dir and return a de-duplicated list of Semgrep config IDs
    appropriate for the detected languages, always including the base configs.
    """
    detected_langs: set[str] = set()
    for path in source_dir.rglob("*"):
        lang = EXT_LANG.get(path.suffix.lower())
        if lang:
            detected_langs.add(lang)

    configs = list(_BASE_CONFIGS)
    for lang in sorted(detected_langs):
        for cfg in LANG_CONFIGS.get(lang, []):
            if cfg not in configs:
                configs.append(cfg)

    log.info("Semgrep configs for %s: %s", source_dir.name, configs)
    return configs


def run(source_dir: Path, configs: list[str] | None = None) -> dict:
    """
    Run Semgrep against source_dir with the given config list.
    If configs is None, auto-detects based on file types in source_dir.
    Returns the merged JSON report dict.
    Raises RuntimeError on Semgrep internal errors (exit code ≥ 2).
    """
    if configs is None:
        configs = detect_configs(source_dir)

    cmd = ["semgrep"]
    for cfg in configs:
        cmd += ["--config", cfg]
    cmd += [
        "--json",
        "--no-git-ignore",
        "--timeout", "60",
        str(source_dir),
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        timeout=480,
    )

    # Exit codes: 0 = clean, 1 = findings found, 2+ = error
    if result.returncode >= 2:
        raise RuntimeError(
            f"Semgrep error (exit {result.returncode}): {result.stderr.strip()}"
        )

    raw = result.stdout.strip()
    if not raw:
        log.warning("Semgrep produced no output")
        return {"results": []}

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Semgrep output is not valid JSON: {exc}") from exc
