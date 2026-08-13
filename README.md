# L1 Message Triage System — KaStack AI/ML Engineer Intern Assignment

Rule-based system that classifies 900 messages into 6 categories, extracts tasks/events, and detects + masks sensitive information. No external AI API calls at runtime, no dataset upload anywhere.

**Live demo:** `<add cloud-hosted URL here>`
**Video walkthrough:** `<add Loom link here>`

## How it works

**1. Classification (`classify.py`)** — The dataset is generated from ~60 fixed templates, each wrapped in one of 9 "noise" prefixes (`Important:`, `FYI:`, `Quick update:`, etc.) distributed *evenly* across all templates — so these prefixes carry no real signal, and a naive keyword classifier would misfire on them. The pipeline strips known prefixes, then runs the core sentence through ordered rule groups: `Sensitive → Meeting/Event → Action Required → Promotional → Personal Info → General Info (fallback)`. Sensitive is checked first so it always overrides other labels. Every result includes a `reason` and a `confidence` score (0.6 for the fallback, higher for exact template matches).

**2. Task/Event Extraction (`extract.py`)** — Runs only on `action_required`/`meeting_or_event` messages. Pulls title, date/time, location/deadline via regex. Nothing is guessed — missing fields (`time`, `person`, `location`) are stored as `null`. `person` is always `null` since no message names an assignee. `priority` is the one *derived* field (no urgency words exist in the data), computed from days-until-deadline: ≤3 days = high, 4–7 = medium, else low — logged per item in `priority_basis`.

**3. Sensitive Detection (`sensitive.py`)** — Regex matching on known sensitive-value shapes (OTP, password, card/bank/account numbers, recovery codes, ID numbers, tokens, addresses, contact/health details) — chosen over ML since these formats are fixed and explainable. `mask_value()` keeps 2 characters as a shape hint and masks the rest before anything is written or displayed — raw values never hit a log, file, or screen. Each finding includes `risk` and `recommended_action` (`do_not_store`, `do_not_send_to_external_service`, `ask_for_confirmation`).

## Running it

```bash
cd src
python3 pipeline.py ../data/messages.csv ../data/mandatory_demo_ids.csv
```

Outputs to `output/`: `classifications.json` (900), `tasks_events.json` (350), `sensitive_report.json` (100), `mandatory_ids_coverage.json` (all 15 covered).

## Results

| Category | Count |
|---|---|
| General Information | 255 |
| Action Required | 200 |
| Meeting or Event | 150 |
| Sensitive Information | 100 |
| Promotional | 100 |
| Personal Information | 95 |

## Assumptions & limitations

- **Priority is derived**, not extracted — computed from deadline proximity since no urgency language exists in the data.
- **`person` is always null** — no message names a task assignee; sender ≠ assignee, so it's not inferred.
- **Tuned to this dataset's templates** — free-form/unstructured messages would need broader pattern coverage or a fallback ML model; the rule-group architecture supports adding that later.
- **Regex over ML for sensitive detection** — deliberate, given fixed-format values; wouldn't generalize as-is to unstructured prose.
- **One sensitive match per message** — dataset never has two sensitive values in one message, so only the first match is returned.

## AI-tool usage declaration

Built with Claude (Anthropic) as a pair-programming assistant — used for scaffolding the pipeline, writing/iterating on the regex rules, and drafting this README. All classification logic is deterministic local code with no LLM calls at runtime. I reviewed and understand every rule in `classify.py`, `extract.py`, and `sensitive.py`, and can explain any of them.

## Repo hygiene

`data/` (the dataset) is excluded via `.gitignore`. The demo dashboard embeds only masked/classified output, never the raw dataset.