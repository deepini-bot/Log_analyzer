from datetime import datetime
from uuid import uuid4
from .embeddings import cosine_similarity_matrix

def event_time(event):
    try:
        return datetime.fromisoformat(event["timestamp"].replace(",", ".")) if event.get("timestamp") else None
    except Exception:
        return None

def correlate_incidents(events, embedding_service, similarity_threshold=.55, time_window_seconds=300):
    candidates = [e for e in events if e.get("is_anomaly") or e.get("level") in ("WARN", "ERROR", "FATAL", "CRITICAL")]
    if not candidates:
        return []
    vectors = embedding_service.encode([e.get("message", "") for e in candidates])
    sims = cosine_similarity_matrix(vectors)
    used, groups = set(), []
    for i, event in enumerate(candidates):
        if i in used:
            continue
        group = [i]
        used.add(i)
        t0 = event_time(event)
        for j in range(i + 1, len(candidates)):
            if j in used:
                continue
            t1 = event_time(candidates[j])
            time_ok = not (t0 and t1) or abs((t1 - t0).total_seconds()) <= time_window_seconds
            same_service = event.get("service") == candidates[j].get("service")
            if time_ok and (sims[i, j] >= similarity_threshold or same_service):
                group.append(j)
                used.add(j)
        groups.append([candidates[k] for k in group])
    incidents = []
    for group in groups:
        times = [event_time(e) for e in group if event_time(e)]
        levels = [e.get("level") for e in group]
        services = sorted({e.get("service", "unknown") for e in group})
        severity = "critical" if any(x in levels for x in ("FATAL", "CRITICAL")) else ("high" if "ERROR" in levels else "medium")
        title_message = group[0].get("message") or group[0].get("template") or "related events"
        incidents.append({
            "incident_id": f"INC-{uuid4().hex[:8].upper()}",
            "title": f"{', '.join(services[:2])} — {title_message[:100]}",
            "severity": severity,
            "start_time": min(times).isoformat() if times else None,
            "end_time": max(times).isoformat() if times else None,
            "event_count": len(group),
            "summary": f"{len(group)} suspicious or high-severity events across {', '.join(services)}.",
            "events": group,
            "investigation": None
        })
    return incidents
