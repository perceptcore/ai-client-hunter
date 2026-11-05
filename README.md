# AI Client Hunter

**Find the right companies. Bring a reason to contact them.**

AI Client Hunter is an open-source skill for agencies and consultants researching B2B prospects. It helps an AI agent qualify accounts, find public business contacts, and draft outreach grounded in evidence.

**v0.1 is a working, host-run skill.** Your Codex, Claude Code, or other compatible agent performs the research and writing with its available tools. Two local Python helpers normalize campaign data, preserve progress, and export review artifacts. This is not a standalone lead database or email sender.

## Install

From the project where you want to use the skill:

```sh
npx skills add perceptcore/ai-client-hunter --skill ai-client-hunter
```

To select Codex and Claude Code explicitly:

```sh
npx skills add perceptcore/ai-client-hunter --skill ai-client-hunter --agent codex claude-code
```

The installer needs Node.js/npm. Helpers need Python 3.10+ and use only the standard library. Research needs the host agent's web search or browser access; offline work can use supplied sources. No Apollo, Hunter, provider API key, or paid enrichment service is required by this repository. Your host's normal model and tool usage still applies.

Alternatively, copy the complete [skill directory](skills/ai-client-hunter) into your agent's supported skills location. Keep its references, assets, and scripts together.

## Ask for a useful result

```text
Use $ai-client-hunter to find 20 B2B software companies serving UK service
businesses. My offer is comparison-page research and writing. Look for
founders or marketing leads. Research public sources, keep your evidence,
and draft outreach in English. Save everything under campaigns/uk-software.
```

Other entry points:

- Research a list: “Qualify the companies in websites.csv against this ICP and offer.”
- Find contacts: “Continue this campaign and find published business contacts for the qualified accounts.”
- Draft outreach: “Use these account findings to draft an initial email and two follow-ups.”
- AI visibility: “Review these original AI answers, check specific brand claims, and identify supported outreach opportunities.”

The skill supports the full workflow or individual research, contact, and drafting modes. It asks for consequential missing brief details and preserves unknowns.

## How it works

| Step | Work performed |
| --- | --- |
| Brief | ICP, offer, markets, contact roles, target count, outreach language |
| Research | Company fit and a specific opportunity, with source URLs and collection dates |
| Contacts | Relevant roles and exact published business addresses, when found |
| Drafting | One initial message and two follow-ups based on cited findings |
| Review | Local CSV and Markdown exports with unresolved gaps visible |

The default batch is 10 companies and the default outreach language is English. Checkpoints let later runs continue completed research. The target count is a goal; the skill does not pad the list with unsupported accounts.

### AI visibility

Use actual model answers collected by an available host tool or supplied by the user. Preserve prompt, original answer, provider/model/date when available, and source context. Missing metadata stays unknown. One missing mention is one observation, not a brand-wide score. Drafts citing AI findings with incomplete collection metadata remain held.

## Campaign outputs

Each campaign keeps its brief, research, suppression lists, and progress in local JSON. The agent updates records; helpers validate structure, not the truth of claims.

| Export | Contents |
| --- | --- |
| `prospects.csv` | Company fit, reasons, evidence IDs, status, suppression flag |
| `contacts.csv` | Public contacts, company qualification, source metadata, verification limits |
| `account-briefs.md` | Account decisions, sources, original AI observations |
| `outreach.md` | Review drafts or explicit hold reasons |

Public email listings do not establish deliverability. Generic inboxes are labelled. Suppressed/excluded accounts do not receive exported message bodies. Conflicting cited evidence stays held. CSV exports neutralize spreadsheet formula prefixes. Contacts from review/excluded accounts remain research records, not a send list.

## Run the synthetic example

These companies, addresses, and findings are fictional reserved `.test` fixtures. No live research or sending is involved. From this repository root:

```sh
python skills/ai-client-hunter/scripts/prepare_campaign.py check --campaign skills/ai-client-hunter/assets/synthetic-campaign --check-only
python skills/ai-client-hunter/scripts/export_campaign.py --campaign skills/ai-client-hunter/assets/synthetic-campaign --out outputs/synthetic
```

Inspect the committed [prospects](examples/synthetic-outputs/prospects.csv), [contacts](examples/synthetic-outputs/contacts.csv), [account briefs](examples/synthetic-outputs/account-briefs.md), and [outreach](examples/synthetic-outputs/outreach.md). They demonstrate qualified, review, and excluded accounts and a draft sequence.

To initialize a campaign, adapt the packaged [brief](skills/ai-client-hunter/assets/brief.json) and optional [website CSV](skills/ai-client-hunter/assets/websites.csv):

```sh
python skills/ai-client-hunter/scripts/prepare_campaign.py init --campaign campaigns/my-campaign --brief my-brief.json --websites my-websites.csv
```

The agent updates `data.json` using the [record format](skills/ai-client-hunter/references/data-format.md). Resume with `check`; add seeds with `import`. `init` never resets an existing campaign. These helper paths are checkout-relative; after installation, resolve them inside the installed skill folder.

## Boundaries

- Public business sources; no guessed emails or mail-server probes.
- Drafts for review; no sending, scheduling, or campaign operation.
- No required paid enrichment integrations or credit purchases.
- Real campaign data stays outside the public repository. Helpers make no network requests or uploads.
- Structural validation does not verify a source, prove buyer intent, or predict results.

## Develop and contribute

```sh
python -m unittest discover -s tests -v
```

CI checks helpers and skill packaging on Linux/Python 3.10 and Windows/Python 3.13. Read [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md). Only synthetic fixtures belong in public contributions.

## Roadmap

- [x] Self-contained installable skill with four modes and an AI visibility workflow
- [x] Public-source contact guidance and evidence-linked outreach
- [x] Local JSON, CSV/Markdown, suppression, deduplication, checkpoints
- [x] Standard-library helpers, synthetic example, automated checks
- [ ] More industry examples based on demonstrated user needs
- [ ] Optional source integrations with explicit access and cost requirements

## PerceptCore

**[PerceptCore — AI Brand Intelligence](https://perceptcore.com/)**

*Shape how AI sees your brand.*

[MIT](LICENSE) — Copyright (c) 2026 PerceptCore.
