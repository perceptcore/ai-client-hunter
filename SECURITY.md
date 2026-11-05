# Security policy

## Supported version

The current v0.2 skill and Python helpers on `main` are maintained. This repository does not operate a hosted service, email sender, or credential store.

## Report a sensitive issue

Email [hello@getperceptcore.com](mailto:hello@getperceptcore.com) with the subject `AI Client Hunter security report`. Include the affected file or commit, potential impact, and minimal reproduction with synthetic data. Redact credentials and personal/client data. Do not publish sensitive reports in issues.

If a credential is exposed, its owner should revoke it through the issuing service. Do not test it or include it in a report. There is no bug bounty or guaranteed response timeline.

## Data and execution boundaries

Data preparation and export are local. The explicit contact-research helper makes bounded public HTTP(S) GET requests with verified TLS, pinned public DNS addresses, redirect checks, robots handling, size limits, rate limits and persistent allowances. It uses no account cookies or credentials and sends no form submissions. The host agent's tools, permissions and data policies govern its additional research. Review instructions and scripts before running them.

Crawler/cache records contain original public source text and contact candidates; keep them with private campaign data. `inspect` emits bounded source summaries and signals truncation. A parser result is not a verified person, and two different hostnames do not by themselves prove sources are independent. The agent must inspect provenance and meaning. Run one crawler writer per campaign at a time.

Campaign JSON preserves source text. CSV exports guard against spreadsheet formula prefixes, and raw AI answers/messages use text fences in Markdown. Websites, AI answers, and imported records are untrusted content, never instructions to execute code, expose data, or change the task.

Keep campaign directories and credentials outside this public repository. Included examples are synthetic reserved `.test` data. Schema checks establish structural consistency, not truth or the safety of a future campaign.
