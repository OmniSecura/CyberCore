from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from typing import Any

# Map Bandit severity/confidence strings → our normalized values
_SEVERITY = {"HIGH": "high", "MEDIUM": "medium", "LOW": "low"}
_CONFIDENCE = {"HIGH": "high", "MEDIUM": "medium", "LOW": "low"}

# Bandit test IDs that map to CWE numbers
_CWE_MAP: dict[str, str] = {
    "B101": "CWE-617",   # assert used
    "B102": "CWE-78",    # use of exec
    "B103": "CWE-732",   # setting permissions
    "B104": "CWE-605",   # hardcoded bind all interfaces
    "B105": "CWE-259",   # hardcoded password string
    "B106": "CWE-259",   # hardcoded password funcarg
    "B107": "CWE-259",   # hardcoded password default
    "B108": "CWE-377",   # probable insecure temp file/dir usage
    "B110": "CWE-390",   # try/except/pass
    "B112": "CWE-390",   # try/except/continue
    "B201": "CWE-94",    # flask debug
    "B301": "CWE-502",   # pickle
    "B302": "CWE-502",   # marshal
    "B303": "CWE-327",   # use of MD5/SHA1
    "B304": "CWE-327",   # ciphers (DES/Blowfish)
    "B305": "CWE-327",   # cipher modes ECB
    "B306": "CWE-377",   # mktemp
    "B307": "CWE-78",    # eval
    "B308": "CWE-79",    # mark_safe
    "B310": "CWE-601",   # urllib open
    "B311": "CWE-330",   # random
    "B312": "CWE-605",   # telnet
    "B313": "CWE-611",   # xml
    "B314": "CWE-611",   # xml
    "B315": "CWE-611",   # xml
    "B316": "CWE-611",   # xml
    "B317": "CWE-611",   # xml
    "B318": "CWE-611",   # xml
    "B319": "CWE-611",   # xml
    "B320": "CWE-611",   # xml
    "B321": "CWE-319",   # FTP
    "B322": "CWE-78",    # input py2
    "B323": "CWE-295",   # ssl verify disabled
    "B324": "CWE-327",   # hashlib
    "B325": "CWE-330",   # mktemp
    "B401": "CWE-319",   # import telnetlib
    "B402": "CWE-319",   # import ftplib
    "B403": "CWE-502",   # import pickle
    "B404": "CWE-78",    # import subprocess
    "B405": "CWE-611",   # import xml.etree
    "B406": "CWE-611",   # import xml.sax
    "B407": "CWE-611",   # import xml.expat
    "B408": "CWE-611",   # import xml.dom
    "B409": "CWE-611",   # import xml.minidom
    "B410": "CWE-611",   # import lxml
    "B411": "CWE-611",   # xmlrpc
    "B412": "CWE-330",   # import httpoxy
    "B413": "CWE-327",   # pycrypto
    "B501": "CWE-295",   # request with no cert validation
    "B502": "CWE-326",   # ssl.wrap_socket
    "B503": "CWE-326",   # ssl.wrap_socket v2
    "B504": "CWE-326",   # ssl.wrap_socket v3
    "B505": "CWE-326",   # weak cryptographic key
    "B506": "CWE-20",    # yaml load
    "B507": "CWE-295",   # ssh no host key verification
    "B601": "CWE-78",    # paramiko exec_command
    "B602": "CWE-78",    # subprocess shell=True
    "B603": "CWE-78",    # subprocess without shell
    "B604": "CWE-78",    # any function with shell=True
    "B605": "CWE-78",    # start process with shell
    "B606": "CWE-78",    # start process with no shell
    "B607": "CWE-78",    # start process with partial path
    "B608": "CWE-89",    # SQL injection
    "B609": "CWE-78",    # wildcard injection
    "B610": "CWE-89",    # django extra
    "B611": "CWE-89",    # django rawsql
    "B701": "CWE-94",    # jinja2 autoescape
    "B702": "CWE-79",    # mako templates
    "B703": "CWE-79",    # django mark_safe
}


def parse(report: dict, source_dir: Path) -> list[dict[str, Any]]:
    """
    Convert a Bandit JSON report into our normalised finding dicts.
    source_dir is used to strip absolute path prefixes from file_path.
    """
    findings = []
    for item in report.get("results", []):
        rule_id = item.get("test_id", "UNKNOWN")
        sev_raw = item.get("issue_severity", "LOW").upper()
        conf_raw = item.get("issue_confidence", "LOW").upper()

        file_path = item.get("filename", "")
        try:
            file_path = str(Path(file_path).relative_to(source_dir))
        except ValueError:
            pass

        snippet = item.get("code", "").strip() or None
        message = item.get("issue_text", "").strip()
        title = item.get("test_name", rule_id).replace("_", " ").title()

        fingerprint = hashlib.sha256(
            f"{rule_id}:{file_path}:{item.get('line_number', 0)}:{message}".encode()
        ).hexdigest()[:64]

        # Bandit reports a `line_range` list, but newer versions can return [],
        # which used to raise IndexError on `[-1]`. Fall back to line_number.
        line_range = item.get("line_range") or []
        line_end = line_range[-1] if line_range else item.get("line_number")

        findings.append({
            "id": str(uuid.uuid4()),
            "tool": "bandit",
            "rule_id": rule_id,
            "severity": _SEVERITY.get(sev_raw, "low"),
            "confidence": _CONFIDENCE.get(conf_raw, "low"),
            "title": title,
            "message": message,
            "file_path": file_path,
            "line_start": item.get("line_number"),
            "line_end": line_end,
            "code_snippet": snippet,
            "cwe": _CWE_MAP.get(rule_id),
            "owasp": None,
            "fingerprint": fingerprint,
        })

    return findings
