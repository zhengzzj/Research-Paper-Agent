# Research-Paper-Agent

个人科研文献智能推送 Agent。项目目标是在 GitHub Repository 中长期运行，通过
GitHub Actions 定时发现论文、分析论文、发送 HTML 邮件，并用
`data/history.json` 维护科研文献记忆。

当前阶段是项目骨架设计与落地，尚未实现完整业务代码。

## Target

这个 Agent 面向计算机与体育交叉研究，重点关注：

- Computational Sports
- Soccer Video Understanding
- Soccer Tactical Analysis
- Sports Data Analytics
- Video Retrieval
- Temporal Grounding
- Video Event Detection
- Multimodal Large Language Models
- LLM Agent
- AI for Science
- Visual Analytics
- Immersive Analytics
- HCI

## Repository Structure

```text
Research-Paper-Agent/
├── .github/
│   └── workflows/
│       └── paper_agent.yml
├── config/
│   ├── config.yaml
│   ├── research_profile.yaml
│   └── scoring.yaml
├── data/
│   └── history.json
├── docs/
│   ├── ARCHITECTURE.md
│   └── ROADMAP.md
├── prompts/
│   └── paper_analysis.md
├── src/
│   └── research_agent/
│       ├── main.py
│       ├── sources/
│       ├── dedup/
│       ├── ranking/
│       ├── pdf/
│       ├── llm/
│       ├── email/
│       ├── memory/
│       └── utils/
├── templates/
│   └── email_report.html
├── tests/
├── requirements.txt
└── README.md
```

## Runtime Flow

```text
GitHub Actions
  -> check configured run interval
  -> fetch arXiv candidates
  -> deduplicate with data/history.json
  -> calculate Research Relevance Score
  -> calculate Paper Quality Score
  -> analyze selected papers with DeepSeek
  -> send HTML email through SMTP
  -> update data/history.json
  -> commit and push memory updates
```

## Secrets

Sensitive values must be configured in GitHub Secrets:

- `DEEPSEEK_API_KEY`
- `EMAIL_ADDRESS`
- `EMAIL_PASSWORD`
- `EMAIL_SMTP_HOST`
- `EMAIL_SMTP_PORT`
- `EMAIL_TO`

Do not commit API keys, passwords, or private tokens into this repository.

## Current Status

The repository currently contains the architecture skeleton, configuration files,
prompt template, email template, empty history store, and GitHub Actions workflow
draft.

Next implementation target: Phase 1 MVP closed loop. See
[`docs/ROADMAP.md`](docs/ROADMAP.md).
