# Contributing to AI Client Hunter

Help agencies find stronger reasons to start a business conversation.

## Project shape

v0.1 is a host-run Agent Skill with local Python helpers. The agent performs public-source research and drafting; scripts validate and export local data. Keep the installed skill self-contained. Changes must work when only `skills/ai-client-hunter` is installed, without sibling skills or checkout-specific paths.

## Propose a change

Open an issue explaining the user, decision, input, expected result, and evidence needed. Discuss substantial integrations or schema changes before implementation. State host-tool, account, cost, and compatibility requirements. Keep scope and permissions under the user's control.

## Submit a pull request

1. Make a focused change on a branch in your fork.
2. Explain the problem, resulting behavior, and relevant validation.
3. Run `python -m unittest discover -s tests -v` with Python 3.10+.
4. Check links and installed resource paths. Exercise changed helpers on synthetic data and inspect actual exports.
5. For behavior changes, test missing sources, unknown contacts, suppression, and interrupted/resumed work. Do not rely on matching generated wording.

Keep documentation in English and runtime helpers standard-library-only unless a dependency has a clear, agreed benefit. Document versioning and compatibility for data-format changes.

## Evidence standard

- Separate observations from interpretations and recommendations.
- Include source URLs and collection dates for external findings and contacts.
- Preserve original AI context and record missing metadata explicitly.
- Do not equate public email listing, SMTP acceptance, or sent mail with inbox placement.
- Do not invent buyer intent, contacts, business problems, or campaign results.

Do not submit live prospect lists, private client data, real messages, credentials, or account information. Use reserved `.test` domains and synthetic fixtures. Follow [SECURITY.md](SECURITY.md) for sensitive reports.

By contributing, you confirm the right to share the material and agree to the repository's [MIT license](LICENSE).
