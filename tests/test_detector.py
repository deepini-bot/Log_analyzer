from app.parser import parse_logs, assign_template_frequency
from app.detector import detect_anomalies

def test_anomaly_scores_are_bounded():
    text = "\n".join([f"2026-01-01 10:00:{i:02d} INFO api: request completed" for i in range(10)] +
                     ["2026-01-01 10:01:00 ERROR api: database connection timeout"])
    events = parse_logs(text)
    assign_template_frequency(events)
    detect_anomalies(events)
    assert len(events) == 11
    assert all(0 <= e["anomaly_score"] <= 1 for e in events)
