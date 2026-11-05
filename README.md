# AI Client Hunter

**Find relevant companies. Identify the right person. Give them a reason to reply.**

A lightweight AI skill for B2B prospect research, public contact discovery and evidence-based outreach drafts. It uses the search and browser tools already available in your agent.

## Install

```sh
npx skills add perceptcore/ai-client-hunter --skill ai-client-hunter
```

For Codex and Claude Code explicitly:

```sh
npx skills add perceptcore/ai-client-hunter --skill ai-client-hunter --agent codex claude-code
```

The installer needs Node.js/npm. You can also copy the complete [skill folder](skills/ai-client-hunter) into your agent's skills directory. The skill requires no Python runtime, API keys or paid enrichment service. Live research uses your agent's existing tools and normal usage allowance.

## Use

```text
Use $ai-client-hunter to research 10 UK B2B software companies.
My offer is positioning and comparison-page writing.
Find founders or marketing leads with a public professional contact route.
Keep sources and draft an initial email plus two follow-ups in English.
Save the research and drafts under campaigns/uk-software.
```

You can also supply a website list, continue existing research, find contacts for known accounts, or draft from supplied findings.

The output is a prospect CSV and outreach Markdown, or a table for a small request. Research includes company fit, the relevant finding, named person and role, public route, source URLs/date and unresolved gaps. Generic inboxes stay separate from personal contacts. Messages remain drafts for review.

## Scope

The current v0.3 package contains [one instruction file](skills/ai-client-hunter/SKILL.md), agent UI metadata and its MIT license. It has no custom crawler, cache, Python helpers, campaign schema or mandatory export pipeline. Earlier implementations remain in Git history; existing user-owned campaign files are not changed by this release.

The skill does not guess emails, probe mail servers, buy credits or send messages. It makes no claim of higher accuracy, lower token cost or better conversion than ordinary AI research.

## Contribute

Improve the [instructions](skills/ai-client-hunter/SKILL.md) with a concrete research problem and a concise correction. Read [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md). Use synthetic examples in public issues and contributions.

## PerceptCore

**[PerceptCore — AI Brand Intelligence](https://perceptcore.com/)**

*Shape how AI sees your brand.*

[MIT](LICENSE) — Copyright (c) 2026 PerceptCore.
