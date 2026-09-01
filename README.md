# Azure AI Cloud Developer (AI-200) Hands-On Lab Guide

**[▶ Open the live guide](https://naytron.github.io/ai-200-labs/)**

A self-contained HTML study site with step-by-step labs covering every domain of the
[Microsoft Certified: Azure AI Cloud Developer Associate (Exam AI-200)](https://learn.microsoft.com/credentials/certifications/exams/ai-200/) certification, plus an identity, governance, and monitoring study aid.

AI-200 is a **developer** exam, so every lab gives you the same task three ways — an **Azure Portal**
click-path, the equivalent **Azure CLI (Bash)** commands, and the **Python / SDK** code (or the YAML
manifest / KQL query where that is the real artifact) — and wraps it in exam context: what the question
bank is actually testing, and which plausible-looking answers are wrong.

## Contents

| # | Domain | Exam weight | Labs |
|---|--------|-------------|------|
| 1 | Develop containerized solutions on Azure | 20–25% | 6 |
| 2 | Develop AI solutions by using Azure data management services | 25–30% | 7 |
| 3 | Connect to and consume Azure services | 20–25% | 5 |
| 4 | Secure, monitor, and troubleshoot Azure solutions | 20–25% | 5 |

Each lab opens with a **“What the exam is testing”** callout and closes with the **traps & gotchas**
(the distractors that show up in the real question bank). Labs are tagged **Foundational**, **Core**
or **Advanced**, and the guide has live search plus a level filter.

The live guide also includes a first-class **identity, governance, and monitoring companion** for
Domain 4. It preserves the current official AI-200 scope framing, decision tables, scenarios,
gotchas, KQL examples, and Microsoft Learn sources, and adds an interactive set of **100 true/false
questions** with an explanation for every answer. Use its dedicated search to filter both the cheat
sheet and the practice questions.

## How it's built

The site is a single `index.html` generated from plain-Python data and Markdown source files — no
framework or build dependencies beyond Python 3.

```
src/
  build.py              # renders index.html
  domains/
    d1.py … d4.py       # lab content, one module per exam domain
  study-aids/
    identity-governance-monitoring.md
```

To rebuild after editing the content:

```bash
python src/build.py
```

That writes `index.html` at the repo root, which is what GitHub Pages serves.

## How to use this guide

1. Read the **exam callout** before the steps.
2. Work the **Portal** path first for orientation with blade and wizard names.
3. Rebuild it with the **Azure CLI** and **Python / SDK** panes — AI-200 tests SDK method names,
   trigger/binding names and CLI flags directly.
4. Read the **traps** afterwards.
5. Use the **identity study aid** for Domain 4 review, then answer its true/false questions and read
   each explanation.

> **Cost warning.** AKS clusters, Container Apps environments, Cosmos DB throughput, Azure Database for
> PostgreSQL flexible servers and Managed Redis bill continuously. Run the cleanup block at the end of
> each lab, and prefer deleting the whole resource group when you are done.

Command syntax reflects Azure CLI 2.x and the current Azure Python SDKs. Azure and its SDKs change
frequently — verify against Microsoft Learn before relying on any specific flag or method name.

## License

MIT — see [LICENSE](LICENSE).
