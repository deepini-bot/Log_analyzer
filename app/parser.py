import re
from datetime import datetime
from collections import Counter

LINE_RE = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?)\s+"
    r"(?P<level>TRACE|DEBUG|INFO|WARN|WARNING|ERROR|FATAL|CRITICAL)\s+"
    r"(?:(?P<service>[\w./-]+):\s*)?(?P<message>.*)$", re.I
)
BRACKETED_RE = re.compile(
    r"^\[(?P<ts>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?)\]\s*"
    r"\[(?P<level>TRACE|DEBUG|INFO|WARN|WARNING|ERROR|FATAL|CRITICAL)\]\s*"
    r"(?:\[(?P<service>[\w./-]+)\]\s*)?(?P<message>.*)$", re.I
)
ALT_RE = re.compile(r"^(?P<ts>\S+)\s+\[(?P<level>\w+)\]\s+(?P<service>[\w./-]+)\s+-\s+(?P<message>.*)$", re.I)
VARIABLES = [
    (re.compile(r"\b0x[0-9a-fA-F]+\b"), "<HEX>"),
    (re.compile(r"\b\d{8}-[0-9a-fA-F-]{27,}\b"), "<UUID>"),
    (re.compile(r"\b\d+(?:\.\d+)?\b"), "<NUM>"),
    (re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b"), "<IP>"),
    (re.compile(r"'[^']*'|\"[^\"]*\""), "<STR>"),
]

def normalize_message(message: str) -> str:
    value = message.lower().strip()
    for pattern, replacement in VARIABLES:
        value = pattern.sub(replacement, value)
    return re.sub(r"\s+", " ", value)

def parse_line(line: str, index: int = 0):
    line = line.strip()
    if not line:
        return None
    match = BRACKETED_RE.match(line) or LINE_RE.match(line) or ALT_RE.match(line)
    if match:
        d = match.groupdict()
        ts = d.get("ts")
        try:
            datetime.fromisoformat(ts.replace(",", "."))
        except Exception:
            ts = None
        level = (d.get("level") or "INFO").upper()
        if level == "WARNING":
            level = "WARN"
        message = d.get("message") or line
        return {"timestamp": ts, "level": level, "service": d.get("service") or "unknown",
                "message": message, "template": normalize_message(message), "line_number": index + 1}
    return {"timestamp": None, "level": "INFO", "service": "unknown", "message": line,
            "template": normalize_message(line), "line_number": index + 1}

def parse_logs(text: str):
    return [e for i, line in enumerate(text.splitlines()) if (e := parse_line(line, i))]

def assign_template_frequency(events):
    counts = Counter(e["template"] for e in events)
    for e in events:
        e["template_frequency"] = counts[e["template"]]
