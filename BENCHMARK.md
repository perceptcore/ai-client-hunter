# Discovery check: AI alone and v0.2

**This check does not establish higher accuracy, lower token cost, or faster research than AI alone.** It tests what each workflow records and where it stops. A populated contact row is not a verified buyer.

## Setup

Two independent host-agent runs received the same brief and convenience sample of 20 B2B software companies. The offer was positioning and comparison-content research; requested contacts were founders or marketing leaders. Both runs could use public search and reading tools, with a ceiling of six search queries and 20 page attempts per company. No paid enrichment, login, guessed addresses, SMTP probes, messages or form submissions were used.

The baseline used ordinary AI research without reading this skill or its outputs. The v0.2 run used the skill, crawler, cached source inspection, contact evidence model and exports. Research occurred on 5 November 2026 UTC. Raw contacts, source bodies and research logs remain private; only aggregates are published.

## Observations

| Measure | AI-only baseline | v0.2 workflow |
| --- | --- | --- |
| Companies examined | 20 | 20 |
| Contact records produced | 20 candidate selections | 17 supported selections; 2 historical/advisor alternatives; 1 unresolved candidate |
| Routes among selected records | 6 published emails, 13 professional profiles, 1 work contact page | 2 published emails, 14 professional profiles, 1 work contact page |
| Host search queries | 44 | 37 |
| Page attempts, including failed/repeated reads | 48 | 85 |
| Elapsed run interval | 5 minutes 2 seconds | 15 minutes 17 seconds |
| Exact tokens and model cost | Not exposed | Not exposed |

The v0.2 crawler made 130 network requests across the sample, including robots checks and redirects. Its ledger recorded zero page-cache hits during collection. Later inspection reused local bodies; those local inspections are not network reads or measured token savings. Each company remained inside its page/search allowance.

The 17 supported selections passed v2 structural validation. Review also matched all 34 selected role/channel excerpts to retained source text. That checks traceability, not independent ground truth about employment, authority, deliverability or response rates.

Baseline review found strong directly read primary-source role and route support for 11 selections. Other rows relied on indexed profiles or carried role-currency, parent-company ownership, old-route, or full-identity uncertainty. These are evidence qualifications, not proven wrong people. The workflows used different evidence gates, so **17 versus 20, or 17 versus 11, is not an accuracy comparison**.

## What the check exposed

- Live biographies can contradict older leadership pages. The v2 run retained two advisor/former-role records without promoting them to operating decision makers.
- A linked public profile can remain an attributable route when its destination blocks direct reading. It does not prove that messaging is enabled.
- Strict full-name-and-role evidence rules left one strongly triangulated identity unresolved. Multiple official pages with partial names are not yet modeled as one supported identity proof.
- Old published routes remain age-qualified evidence. Neither workflow established current mailbox delivery or social-handle ownership for every route.
- Compact extraction initially missed role context and late profile links. It was corrected during the v2 run, using the saved bodies. Repeated host reads also exposed a ledger bug; the helper was fixed and the actual attempts reconciled.

## Limits and next measurement

This was one nonrandom sample, one run per workflow, without blind ground-truth adjudication or a recorded provider/model version. The v2 code changed during the run. Research intervals include agent reasoning, tool latency, review and integration friction; they are not controlled speed measurements. No confidence interval or efficacy claim follows from these numbers.

The demonstrated difference is a persistent, inspectable workflow: source bodies and excerpts, explicit current-role/channel decisions, held alternatives, bounded attempts, resumable state and reproducible exports. AI-only research also found useful contacts and more email routes in this run.

A future comparison should freeze the release, record the host model/tools, randomize company order, apply the same blind evidence rubric to both outputs, repeat runs and collect actual token/tool charges when exposed. Measure correct current person plus attributable route, identity errors, human review time and total cost separately. Outreach outcomes require a separately authorized experiment; they were not measured here.
