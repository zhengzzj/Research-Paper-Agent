# Roadmap

## Phase 0: Repository Foundation

Status: in progress

- Establish package structure.
- Add configuration files.
- Add research profile.
- Add scoring configuration.
- Add empty history store.
- Add GitHub Actions workflow skeleton.
- Document architecture and development route.

## Phase 1: MVP Closed Loop

Goal: one scheduled run can discover papers, send one email, and update history.

- Implement config loading.
- Implement arXiv candidate retrieval.
- Implement exact arXiv ID deduplication.
- Implement simple keyword and embedding relevance scoring.
- Implement initial quality score with graceful defaults.
- Implement DeepSeek analysis based on title and abstract.
- Implement HTML email rendering and SMTP sending.
- Implement history update after successful email delivery.
- Add basic tests for deduplication, scoring, and history persistence.

## Phase 2: Better Matching and Scoring

Goal: improve recommendation precision.

- Add title similarity deduplication.
- Add semantic duplicate detection.
- Add stronger embedding-based relevance scoring.
- Add score explanations.
- Add institution and venue signal extraction when available.
- Add configurable thresholds and debug logs for rejected papers.

## Phase 3: PDF-Level Deep Analysis

Goal: generate richer paper reports.

- Download final selected arXiv PDFs.
- Parse Abstract, Introduction, Related Work, Method, Experiment, and Conclusion.
- Fall back safely when PDFs are difficult to parse.
- Improve DeepSeek prompts for sports-AI research insights.
- Generate 3-5 concrete follow-up research ideas per paper.

## Phase 4: Long-Term Reliability

Goal: make the agent robust enough for unattended use.

- Add retries and timeouts for network calls.
- Add schema validation for `data/history.json`.
- Add dry-run mode.
- Add failure notifications.
- Add run summaries in GitHub Actions logs.
- Add tests that mock arXiv, DeepSeek, and SMTP.

## Phase 5: Source Expansion

Goal: enrich quality signals beyond arXiv.

- Add Semantic Scholar.
- Add Papers With Code.
- Add optional GitHub repository signal detection.
- Add venue and citation metadata where available.

