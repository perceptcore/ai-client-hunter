# AI Client Hunter

**Find the person who can act. Keep the proof and the public route.**

AI Client Hunter is an open-source skill for agencies and consultants researching B2B prospects. It builds a decision-maker map: relevant people, evidence for their company roles, reasons to select them, and attributable public professional routes.

**v0.2 is a host-run skill with a bounded public HTML crawler.** Python collects and caches source pages, extracts candidates, records research allowances, validates data and exports reports. Your Codex, Claude Code, or compatible agent resolves identity, role fit and source meaning using its available tools. No model API keys are required by this repository.

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
| Contacts | Named decision makers, current role evidence, exact published emails or public professional routes |
| Drafting | One initial message and two follow-ups based on cited findings |
| Review | Local CSV and Markdown exports with unresolved gaps visible |

The default batch is 10 companies and the default outreach language is English. Checkpoints let later runs continue completed research. The target count is a goal; the skill does not pad the list with unsupported accounts.

### Decision-maker discovery

Find a person through company/team/author pages, corroborate their current role, then find a route attributable to them. Email, public professional profiles and person-specific work contact pages are accepted. Generic inboxes, company forms, former employees and unresolved namesakes remain separate research records.

Each qualified company can have up to three supported, role-matched people with selection reasons and source excerpts. A current official company source is sufficient; otherwise the agent checks two independent corroborating sources. Validation checks the record structure and stated evidence conditions, not the truth of the web.

The crawler reads small batches, follows relevant discovered links, exposes compact candidates, and caches source bodies locally. It never promotes extracted names or addresses to supported people by itself. Start with 20 page attempts and six host searches per company; stop early when a supported person and route are found. Resume preserves allowances. Host searches/readers must be logged by the agent—the helper cannot intercept unrelated host-tool calls.

Read the [20-company discovery check](BENCHMARK.md) for measured counts and limitations. This release does not claim higher accuracy or lower token cost than AI alone.

```sh
python skills/ai-client-hunter/scripts/contact_research.py crawl --campaign campaigns/my-campaign --company-id COMPANY_ID
python skills/ai-client-hunter/scripts/contact_research.py inspect --campaign campaigns/my-campaign --company-id COMPANY_ID
```

See the [full discovery workflow](skills/ai-client-hunter/references/contact-discovery.md), including external-source seeds, search/page logging, cache refresh and stopping conditions. Source text remains untrusted input. Research is local and read-only; no messages or forms are submitted.

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
| `decision-makers.csv` | Up to three supported role-matched people and personal routes per qualified company (v2) |
| `contact-research.md` | Role/channel evidence, alternatives, unresolved states, budgets and cache statistics (v2) |

Public listings do not establish deliverability or buying intent. Generic/system inboxes are labelled and cannot stand in for a named-person success. Suppressed/excluded accounts do not receive exported message bodies. Conflicting cited evidence stays held. CSV exports neutralize spreadsheet formula prefixes. Contacts from review/excluded accounts remain research records, not a send list.

## Run the synthetic example

These companies, addresses, and findings are fictional reserved `.test` fixtures. No live research or sending is involved. From this repository root:

```sh
python skills/ai-client-hunter/scripts/prepare_campaign.py check --campaign skills/ai-client-hunter/assets/decision-maker-campaign --check-only
python skills/ai-client-hunter/scripts/export_campaign.py --campaign skills/ai-client-hunter/assets/decision-maker-campaign --out outputs/synthetic
```

Inspect the committed [decision makers](examples/decision-maker-outputs/decision-makers.csv), [contact research](examples/decision-maker-outputs/contact-research.md), [prospects](examples/decision-maker-outputs/prospects.csv), [contacts](examples/decision-maker-outputs/contacts.csv), [account briefs](examples/decision-maker-outputs/account-briefs.md), and [outreach](examples/decision-maker-outputs/outreach.md). The example separates a supported marketing contact and public profile from a historical founder and a generic inbox.

To initialize a campaign, adapt the packaged [brief](skills/ai-client-hunter/assets/brief.json) and optional [website CSV](skills/ai-client-hunter/assets/websites.csv):

```sh
python skills/ai-client-hunter/scripts/prepare_campaign.py init --campaign campaigns/my-campaign --brief my-brief.json --websites my-websites.csv
```

The agent updates `data.json` using the [record format](skills/ai-client-hunter/references/data-format.md). Resume with `check`; add seeds with `import`. `init` never resets an existing campaign. These helper paths are checkout-relative; after installation, resolve them inside the installed skill folder.

### Existing v0.1 campaigns

V1 data remains readable and keeps its four-export contract. To add decision-maker research, explicitly upgrade:

```sh
python skills/ai-client-hunter/scripts/prepare_campaign.py migrate --campaign campaigns/my-campaign
```

Migration backs up the original data, preserves IDs, evidence, suppression and drafts, and marks old contact identities unverified. Existing backups are never overwritten. New campaigns use v2 and produce six exports.

## Boundaries

- Public business sources; no guessed emails or mail-server probes.
- Drafts for review; no sending, scheduling, or campaign operation.
- No required paid enrichment integrations or credit purchases.
- Real campaign data and caches stay outside the public repository. Only the explicit contact crawler makes bounded public GET requests; no helper calls a model or uploads campaign data.
- Structural validation does not verify a source, prove buyer intent, or predict results.

## Develop and contribute

```sh
python -m unittest discover -s tests -v
```

CI checks helpers, contact attribution, migration, crawler/cache/redirect/robots behavior and skill packaging on Linux/Python 3.10 and Windows/Python 3.13. Network tests use controlled transports; CI does not crawl real businesses. Read [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md). Only synthetic fixtures belong in public contributions.

## Roadmap

- [x] Self-contained installable skill with four modes and an AI visibility workflow
- [x] Public-source contact guidance and evidence-linked outreach
- [x] Local JSON, CSV/Markdown, suppression, deduplication, checkpoints
- [x] Standard-library helpers, synthetic example, automated checks
- [x] Bounded public crawler, compact source inspection, persistent cache and research ledger
- [x] Current-role evidence, personal route attribution and decision-maker exports
- [x] Explicit v1 backup/migration with legacy contacts kept unverified
- [ ] More industry examples based on demonstrated user needs
- [ ] Optional source integrations with explicit access and cost requirements

## PerceptCore

**[PerceptCore — AI Brand Intelligence](https://perceptcore.com/)**

*Shape how AI sees your brand.*

[MIT](LICENSE) — Copyright (c) 2026 PerceptCore.
