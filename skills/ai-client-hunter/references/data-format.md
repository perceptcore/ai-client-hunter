# Campaign files — schema versions 1 and 2

The helper commands are relative to the installed skill directory. Campaign paths are user-owned output folders, never this skill directory. JSON is UTF-8; dates use `YYYY-MM-DD`. IDs are stable strings unique within each collection.

## Brief and seed input

`brief.json` requires nonempty `icp` and `offer` strings. Optional fields:

| Field | Type | Default |
| --- | --- | --- |
| markets | string array | [] |
| contact_roles | string array | [] |
| target_count | positive integer | 25 |
| batch_size | positive integer | 10 |
| outreach_language | string | English |

The seed CSV has a required `website` column and optional `name`. Absolute HTTP(S) URLs or bare hostnames are accepted in the CSV. Company IDs are generated from the canonical domain. Blank rows are skipped. `import` adds new domains without resetting prior research.

Suppression CSV headers are `domain,email`; either column can be omitted. Supply at least one nonempty field per useful row. Pass `--suppression` on `init` or `check`; additional entries are merged into the stored lists.

## Stored data.json

The root is an object with `schema_version` (1 or 2), `brief`, `suppression: {domains: [], emails: []}`, and these five arrays. New campaigns use v2; v1 remains readable/exportable without an implicit upgrade.

| Collection | Required record fields |
| --- | --- |
| companies | id, name, website, qualification (`qualified`/`review`/`excluded`), reason, evidence_ids, research_status (`pending`/`complete`) |
| evidence | id, company_id, kind (`business`/`contact`/`ai_answer`), finding, status (`observed`/`conflicting`); business/contact evidence also requires url and observed_at |
| contacts | id, company_id, name and role (empty strings allowed), email (string or null), email_status (`publicly_listed`/`not_found`), source_url, observed_at |
| drafts | id, company_id, contact_id (string or null), evidence_ids (nonempty), subject, body, followups (exactly two nonempty strings) |
| ai_observations | id, company_id, prompt, response, origin (`host_tool`/`user_provided`), provider, model, collected_at, source_url |

AI observation metadata may be null. `ai_answer` evidence requires `ai_observation_id` pointing to an observation for the same company; its url/date may be absent. URLs must be absolute HTTP(S), without credentials. Data validation/export helpers do not fetch URLs; only the explicit contact-research crawler does.

### Additional v2 contact fields

- `contact_kind`: `person`, `generic_inbox`, `system_address`, or `legacy_unverified`.
- `identity_status`: `candidate`, `supported`, `historical`, `conflicting`, or `legacy_unverified`.
- `role_fit`: `primary`, `fallback`, `unmatched`, or `unknown`; `selection_reason` explains the offer-specific decision.
- `role_evidence`: objects with `url`, exact `excerpt`, `observed_at`, `source_type` (`official_company`/`external`), and boolean `is_current`.
- `channels`: objects with `type` (`email`/`professional_profile`/`work_contact_page`/`company_form`), `value`, `source_url`, exact `excerpt`, `observed_at`, `status` (`observed`/`unconfirmed`), and `attribution` (`person`/`company`).

Supported identities require a current official company source or two corroborating current source hosts naming the person and actual role. The agent still reviews ownership, independence and meaning. A person email must also be represented by an observed personal channel. A generic/system address cannot be a named-person email. The [v2 example](../assets/decision-maker-campaign/data.json) shows these fields. Read [contact-discovery.md](contact-discovery.md) for research and budget mechanics.

`migrate --campaign <folder>` validates v1, creates a non-overwriting `data.v1.backup.json`, retains IDs and existing research/drafts/suppression, and upgrades to v2. It does not turn old contacts into verified people. Migration is explicit and one-time; an existing backup is never replaced. If interrupted, inspect the intact data/backup before resuming. Keep v1 when an older tool still requires it.

Only reference evidence belonging to the same company. A qualified company must have completed research, a reason, and at least one evidence ID. A draft's contact must belong to the same company. Email syntax validation does not establish that an address is published or deliverable; the agent must inspect the source.

Do not rewrite original AI answers when labeling them. The full worked [synthetic campaign](../assets/synthetic-campaign/data.json) demonstrates each record shape and includes qualified, review, and excluded accounts.

## Commands

```text
python scripts/prepare_campaign.py init --campaign <output> --brief <brief.json> [--websites <websites.csv>] [--suppression <suppression.csv>]
python scripts/prepare_campaign.py import --campaign <output> --websites <more-websites.csv>
python scripts/prepare_campaign.py migrate --campaign <output>
python scripts/prepare_campaign.py check --campaign <output> [--suppression <suppression.csv>] [--check-only]
python scripts/export_campaign.py --campaign <output> [--out <export-directory>]
```

`init` refuses an existing `data.json`. `check` normalizes and validates the entire state before saving. `--check-only` writes nothing. Exit code 0 means structural success; 2 means invalid data or a file error. Fix the reported issue without discarding other records.

`checkpoint.json` is rebuilt from `data.json`, recording completed/pending company IDs and the update time. If a run stops between saving the two files, rerun `check` to rebuild the derived checkpoint. Do not use the checkpoint as a substitute for reading the research data.

Duplicate company domains with compatible decisions are combined and references remapped. Conflicting company decisions or duplicate emails associated with different people/accounts stop validation for review. Exact duplicate email contacts are collapsed and draft references remapped. Domain canonicalization folds case, removes `www.`, and ignores path/query; it does not merge arbitrary subdomains.

## Exports

- `prospects.csv`: every researched/seeded account, qualification, reason, evidence IDs, and suppression flag.
- `contacts.csv`: nonsuppressed contacts, company qualification, public-source metadata, and deliverability explicitly unverified. Contacts from review/excluded accounts are research records, not a qualified send list.
- `account-briefs.md`: account decisions, cited findings, and original AI observations with unknown metadata visible.
- `outreach.md`: review drafts plus status; bodies withheld for suppressed/held records. `needs_contact` drafts have no usable public recipient yet.

V2 adds `decision-makers.csv` (up to three supported, role-matched people with personal routes per qualified company) and `contact-research.md` (proof, alternatives, unresolved states and ledger statistics). The existing contact CSV keeps its v1 columns and appends identity/channel fields. V1 exports keep their four-file contract. On v2, a generic inbox never upgrades a draft to `review_ready`.

Exports revalidate the data and reapply suppression. CSV cells that could execute spreadsheet formulas are prefixed with an apostrophe. Original text is retained in JSON. Markdown messages and raw AI answers are fenced as text so embedded markup is not treated as instructions or active content.
