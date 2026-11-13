from collections import defaultdict
from datetime import datetime
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

LEVEL_WEIGHT = {"TRACE": 0.0, "DEBUG": 0.05, "INFO": 0.1, "WARN": 0.55,
                "ERROR": 0.85, "FATAL": 1.0, "CRITICAL": 1.0}

def parse_time(value):
    try:
        return datetime.fromisoformat(value.replace(",", ".")) if value else None
    except Exception:
        return None

def build_features(events):
    by_service = defaultdict(list)
    for i, e in enumerate(events):
        by_service[e["service"]].append((i, e))
    X = np.zeros((len(events), 6))
    for service, items in by_service.items():
        previous = None
        for i, e in items:
            ts = parse_time(e.get("timestamp"))
            delta = (ts - previous).total_seconds() if ts and previous else 0
            if ts:
                previous = ts
            msg = e.get("message", "")
            X[i] = [LEVEL_WEIGHT.get(e.get("level", "INFO"), .1),
                    min(len(msg), 2000) / 2000,
                    1 / max(e.get("template_frequency", 1), 1),
                    min(max(delta, 0), 3600) / 3600,
                    min(len(msg.split()), 100) / 100,
                    float(e.get("level") in ("ERROR", "FATAL", "CRITICAL"))]
    return X

def detect_anomalies(events, contamination=.08):
    if not events:
        return events
    X = build_features(events)
    if len(events) < 8:
        raw = X[:, 0] * .65 + X[:, 5] * .35
        scores = (raw - raw.min()) / (raw.max() - raw.min() + 1e-9)
        labels = raw >= max(.55, np.quantile(raw, .75))
    else:
        Xs = StandardScaler().fit_transform(X)
        model = IsolationForest(n_estimators=150, contamination=min(max(contamination, .01), .25), random_state=42)
        model.fit(Xs)
        raw = -model.decision_function(Xs)
        scores = (raw - raw.min()) / (raw.max() - raw.min() + 1e-9)
        labels = model.predict(Xs) == -1
    for i, e in enumerate(events):
        e["anomaly_score"] = float(round(scores[i], 4))
        e["is_anomaly"] = bool(labels[i])
        reasons = []
        if e.get("level") in ("ERROR", "FATAL", "CRITICAL"):
            reasons.append("high-severity log level")
        if e.get("template_frequency", 1) <= 2:
            reasons.append("rare log template")
        if e["is_anomaly"]:
            reasons.append("unusual feature combination")
        e["reasons"] = reasons
    return events

def detect_temporal_spikes(events, window_seconds=60):
    buckets = defaultdict(list)
    for e in events:
        ts = parse_time(e.get("timestamp"))
        if ts:
            key = (e.get("service", "unknown"), int(ts.timestamp()) // window_seconds)
            buckets[key].append(e)
    counts = np.array([len(v) for v in buckets.values()])
    if len(counts) < 3:
        return []
    median = float(np.median(counts))
    mad = float(np.median(np.abs(counts - median))) + 1e-6
    threshold = max(3.0, median + 3.5 * 1.4826 * mad)
    result = []
    for (service, bucket), items in buckets.items():
        critical = sum(e.get("level") in ("WARN", "ERROR", "FATAL", "CRITICAL") for e in items)
        if len(items) >= threshold and critical >= 2:
            result.append({"service": service, "bucket": bucket, "count": len(items),
                           "critical_count": critical, "threshold": threshold})
    return result
