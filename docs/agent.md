# Working on VoYatra with Codex

Use [specs.md](specs.md) for current behavior and rebuild requirements, [skills.md](skills.md) for procedures, and [plan.md](plan.md) for the showcase record. Project agent definitions are checked in under [`.codex/agents/`](../.codex/agents/). This document describes the division of work and how to judge a result.

## Roles and boundaries

- **`batch-processing`** takes saved HTML, a CSV, or both. It traces rows to cards or CSV line numbers, checks the extraction contract, and reports missing data and possible duplicates. Give it the intended route and any explicit output or Kafka destination. Its deliverable is a fixture or batch report with reproducible counts and enough source evidence to review discrepancies.
- **`connectivitytokafka`** takes a broker, topic and a delivery question. It establishes which listener, settings and consumer group are in use, then checks stack, broker, acknowledgement and receipt independently. Provide the approved scope for any test publish. Its deliverable is an evidence trail from producer to consumer, or the first unverified boundary.
- **`debugger`** takes a failing command, observed symptom or artifact. It reconstructs the failure, isolates the first incorrect stage and verifies a targeted fix when requested. Give it relevant versions, working directory and a sanitized reproducer. Its deliverable is a root cause or a bounded hypothesis, plus results for the original failure and a known-good case.

## How to hand off work

1. Give the agent the concrete question, checkout path, exact entry point and expected result. Include the route and inputs for extraction, and the broker/topic and approximate send time for delivery.
2. Specify whether the task is inspection, a code fix, a local export, or an authorized publish. Identify where outputs belong. Keep test traffic isolated from existing demo and shared topics whenever the task permits a separate topic.
3. Use one owner for each boundary. For example, have batch processing provide a checked CSV and counts, then have Kafka connectivity replay that CSV only if requested. For a failure spanning boundaries, have the debugger identify the earliest failed stage and pass the smallest reproducer to the relevant specialist.
4. Reconcile the reports before delivery. Compare extracted rows, CSV rows, producer attempts, acknowledgements and messages observed. A mismatch requires a reason or an explicit unknown. Capture which rows were synthetic, which were replayed and which came from current source cards.
5. Validate code changes through the original entry point and record what was actually run. Review the diff for changes to schema, defaults, consumer offsets or publication behavior that would affect existing callers.

## Maintainer standards

- Resolve docs and code discrepancies against the current entry point, effective environment and relevant logs. The legacy setup scripts, alternate pipelines and crawler notes may reflect a different environment.
- Prefer a hand-authored offline fixture when diagnosing extraction. Include separate examples for real listings, synthetic data, search forms, sparse cards and malformed input. Keep private saved pages, personal data and credentials out of logs and Git.
- Preserve missing values and identify defaults when reporting. A generated flight number, route label entered at the prompt, publication date, or placeholder fare must be distinguished from data observed on a card.
- Describe every claim with the evidence it requires. For example, a parser finding two rows supports extraction, a broker offset supports acknowledgement, and Kafka UI or consumer output at that offset supports receipt.
- Treat CSVs and browser content as input data. Keep output files within the requested location and record any test records added to a Kafka topic. Retain existing topics and consumer offsets during ordinary troubleshooting.

## Suggested handoffs

- **Extraction quality** — “Inspect this saved Mumbai-to-Delhi results page and its CSV. Validate two rows against cards and report blanks, suspicious prices and possible duplicates. Produce a report without publishing.”
- **Kafka delivery** — “Verify the local stack, then send one smoke event to the specified disposable topic. Report the broker, topic, partition, offset and independent receipt evidence.”
- **Regression diagnosis** — “This saved page yielded no rows. Reproduce with a local fixture, identify the first failing check and verify the requested fix against a known-good results page and a form-only page.”
