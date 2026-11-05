# AI Client Hunter

**Your AI writes code. Your pipeline is still empty.**

Put Claude or Codex on prospecting duty.

AI Client Hunter takes your offer, researches companies worth approaching, finds the people responsible, and drafts an opening backed by sources.

Built for founders, agencies and consultants who need a concrete answer to: who should I contact, and why would they care?

## Why use it

- **Spend tokens on new evidence.** Reuse saved findings, search for missing facts, and stop once the person's role and contact route are supported. Keep the next session focused on unfinished work.
- **Qualify before you pitch.** Filter companies against your ICP and offer. Every shortlisted company needs a specific reason it fits, with sources you can inspect.
- **Find the role that matters.** Look for the person responsible for your offer, check their current role, and keep generic inboxes separate from personal contacts.
- **Give every message a reason.** Turn an observed company finding into a relevant opening, a concrete offer and a clear next step. Get a first email and two follow-ups together.
- **Keep the workflow ready.** Install once and reuse the research, qualification and drafting instructions across campaigns. Bring an existing company list or continue prior work.
- **Use the AI you already have.** Run through your agent's search and browser tools, with no required enrichment subscription or separate prospecting server.

## Install

```sh
npx skills add perceptcore/ai-client-hunter --skill ai-client-hunter
```

For Codex and Claude Code explicitly:

```sh
npx skills add perceptcore/ai-client-hunter --skill ai-client-hunter --agent codex claude-code
```

The installer needs Node.js/npm. You can also copy the complete [skill folder](skills/ai-client-hunter) into your agent's skills directory. The skill requires no Python runtime, API keys or paid enrichment service. Live research uses your agent's existing tools and normal usage allowance.

## Give it a job

```text
Use $ai-client-hunter to find 10 UK B2B SaaS companies I could pitch.
I research and write comparison pages for software buyers.
Find the founder or marketing owner, a public contact route,
and one source-backed reason my offer fits.
Draft a short first email and two follow-ups in English.
Save the shortlist and drafts under campaigns/uk-software.
```

Already have a company list? Hand it over. You can run research, contact discovery or drafting separately and continue earlier work.

## Open the shortlist

| What you get | The question it answers |
| --- | --- |
| Company fit and reason | Is this business relevant to the offer? |
| A specific finding with sources | Why approach this company? |
| Named person, role and public route | Who owns the decision, and where can I find them? |
| First email and two follow-ups | How do I open the conversation? |
| Missing or conflicting evidence | What still needs checking? |

Save the shortlist as CSV and the drafts as Markdown, or request a table for a small run. A public profile can be the route when no email is found. Generic support inboxes are labelled separately. Drafts stay open for human review.

## What runs

The [skill](skills/ai-client-hunter/SKILL.md) is a Markdown workflow. Your agent does the research with its existing search and browser tools. You keep the files. There is no separate server or enrichment account to set up.

It researches and drafts; it does not guess addresses, probe mail servers or send messages. Published contacts still need review. Research quality depends on the host agent, available tools and public evidence.

## Contribute

Improve the [instructions](skills/ai-client-hunter/SKILL.md) with a concrete research problem and a concise correction. Read [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md). Use synthetic examples in public issues and contributions.

[MIT](LICENSE)
