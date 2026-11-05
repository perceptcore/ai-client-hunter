# Security policy

## Supported version

The current v0.1 skill and Python helpers on `main` are maintained. This repository does not operate a hosted service, email sender, or credential store.

## Report a sensitive issue

Email [hello@getperceptcore.com](mailto:hello@getperceptcore.com) with the subject `AI Client Hunter security report`. Include the affected file or commit, potential impact, and minimal reproduction with synthetic data. Redact credentials and personal/client data. Do not publish sensitive reports in issues.

If a credential is exposed, its owner should revoke it through the issuing service. Do not test it or include it in a report. There is no bug bounty or guaranteed response timeline.

## Data and execution boundaries

Helpers only read and write local data; they make no network/model calls. The host agent's tools, permissions, and data policies govern its research. Review instructions and scripts before running them.

Campaign JSON preserves source text. CSV exports guard against spreadsheet formula prefixes, and raw AI answers/messages use text fences in Markdown. Websites, AI answers, and imported records are untrusted content, never instructions to execute code, expose data, or change the task.

Keep campaign directories and credentials outside this public repository. Included examples are synthetic reserved `.test` data. Schema checks establish structural consistency, not truth or the safety of a future campaign.
