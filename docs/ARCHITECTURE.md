# Architecture

This repository is designed as a long-running personal research paper agent hosted
on GitHub and scheduled by GitHub Actions.

## Pipeline

```text
GitHub Actions
  -> load config and history
  -> check whether this cycle should run
  -> fetch candidate papers from arXiv
  -> deduplicate against data/history.json
  -> score research relevance
  -> score paper quality
  -> select final papers
  -> download and parse PDFs
  -> call DeepSeek for Chinese analysis
  -> render and send HTML email
  -> update data/history.json
  -> commit and push history changes
```

## Runtime Boundaries

- GitHub Actions is the scheduler and runtime environment.
- The workflow may trigger daily; the agent should enforce the configured
  research update interval in `config/config.yaml`.
- `data/history.json` is the long-term memory.
- GitHub Secrets store all sensitive credentials.
- The local computer is only used for development, not for scheduled operation.

## Module Responsibilities

### `sources`

Fetch paper metadata from external sources. The first implementation target is
arXiv. Future sources can follow the same interface.

### `dedup`

Remove papers that have already been recommended or are near-duplicates.

Deduplication levels:

1. Exact arXiv ID match.
2. Title similarity.
3. Semantic duplicate detection using author overlap, abstract similarity, and
   research-task similarity.

### `ranking`

Compute two scores:

- `Research Relevance Score`: 0-100, based on keyword and semantic alignment
  with the research profile.
- `Paper Quality Score`: weighted score using relevance, author/institution
  reputation, venue quality, and community signal.

### `pdf`

Download arXiv PDFs and extract useful sections where possible. If parsing fails,
the pipeline should gracefully fall back to metadata and abstract-level analysis.

### `llm`

Call DeepSeek and render prompts. Prompt text is stored outside Python code in
`prompts/paper_analysis.md` so it can be iterated easily.

### `email`

Render the selected papers and DeepSeek analyses into an HTML email and deliver
it via SMTP.

### `memory`

Read, validate, and write `data/history.json`. The history file acts as the
agent's persistent memory.

## Reliability Principles

- Do not call DeepSeek for papers that are already known duplicates.
- Mark a paper as pushed only after email delivery succeeds.
- Do not recommend low-quality papers just to satisfy a target count.
- Keep failures visible in GitHub Actions logs.
- Keep secrets out of code, config files, prompts, and history.
