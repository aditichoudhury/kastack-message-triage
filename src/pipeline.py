"""
pipeline.py
-----------
Entry point. Reads messages.csv in chronological order (as required by
the assignment rules), runs Part 1/2/3 over every row, and writes three
structured output files:
  output/classifications.json   (Part 1)
  output/tasks_events.json      (Part 2)
  output/sensitive_report.json  (Part 3)

Usage:
    python pipeline.py path/to/messages.csv path/to/mandatory_demo_ids.csv
"""
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

from classify import classify_message, strip_noise_prefix
from extract import extract_action, extract_event
from sensitive import detect_sensitive


def load_messages(csv_path):
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    # Enforce chronological order per assignment rules, rather than assuming the file is sorted.
    rows.sort(key=lambda r: r["timestamp"])
    return rows


def run_pipeline(messages_csv, mandatory_ids_csv, out_dir):
    rows = load_messages(messages_csv)

    classifications = []
    tasks_events = []
    sensitive_report = []

    for row in rows:
        mid = row["message_id"]
        text = row["message"].strip().strip('"')
        ts = datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S")

        # Part 1
        result = classify_message(mid, text)
        classifications.append(result)

        # Part 3 (independent detection pass — also used internally by Part 1
        # to prioritise the sensitive_information label)
        core, _ = strip_noise_prefix(text)
        sens = detect_sensitive(mid, core)
        if sens:
            sensitive_report.append(sens)

        # Part 2 — only for messages classified as action_required or meeting_or_event
        if result["category"] == "action_required":
            tasks_events.append(extract_action(mid, core, ts))
        elif result["category"] == "meeting_or_event":
            tasks_events.append(extract_event(mid, core, ts))

    out_dir = Path(out_dir)
    out_dir.mkdir(exist_ok=True, parents=True)
    (out_dir / "classifications.json").write_text(json.dumps(classifications, indent=2))
    (out_dir / "tasks_events.json").write_text(json.dumps(tasks_events, indent=2))
    (out_dir / "sensitive_report.json").write_text(json.dumps(sensitive_report, indent=2))

    # Summary + mandatory-ID coverage check
    mandatory_ids = []
    if mandatory_ids_csv and Path(mandatory_ids_csv).exists():
        with open(mandatory_ids_csv, encoding="utf-8-sig") as f:
            mandatory_ids = [r["message_id"] for r in csv.DictReader(f)]

    by_id = {c["message_id"]: c for c in classifications}
    mandatory_report = [
        {"message_id": mid, "category": by_id.get(mid, {}).get("category", "MISSING")}
        for mid in mandatory_ids
    ]
    (out_dir / "mandatory_ids_coverage.json").write_text(json.dumps(mandatory_report, indent=2))

    cat_counts = {}
    for c in classifications:
        cat_counts[c["category"]] = cat_counts.get(c["category"], 0) + 1

    print(f"Processed {len(rows)} messages.")
    print("Category breakdown:", json.dumps(cat_counts, indent=2))
    print(f"Tasks/events extracted: {len(tasks_events)}")
    print(f"Sensitive messages detected: {len(sensitive_report)}")
    print(f"Mandatory IDs covered: {len(mandatory_report)} (see mandatory_ids_coverage.json)")


if __name__ == "__main__":
    messages_csv = sys.argv[1] if len(sys.argv) > 1 else "../data_local_only/messages.csv"
    mandatory_csv = sys.argv[2] if len(sys.argv) > 2 else "../data_local_only/mandatory_demo_ids.csv"
    run_pipeline(messages_csv, mandatory_csv, "../output")
