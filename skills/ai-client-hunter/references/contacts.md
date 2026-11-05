# Find the right public business contact

This reference describes the schema v1 email workflow. For new schema v2 campaigns and decision-maker discovery, read [contact-discovery.md](contact-discovery.md), which defines current-role evidence, professional routes, crawler budgets, and migration.

Check suppression first. Identify the role responsible for the offer: a founder for a small business, or the appropriate marketing, growth, brand, communications, or commercial lead for a larger one. Do not assume job title, seniority, or ownership from a name alone.

Inspect contact/about/team pages, public professional profiles, and named business directories when relevant. Verify that the person and source refer to the same business. Keep the source URL and collection date for each contact record.

Record the exact published address. Mark it `publicly_listed`; do not call it verified or deliverable. Do not construct likely addresses from company naming patterns, generate permutations, contact a mail server, or purchase enrichment credits.

If a named decision maker has no public email, record the supported name and role with `email: null`, `email_status: not_found`, and the public profile/team-page source. A generic business inbox may be recorded as a separate contact with an explicit role such as `General business inbox`; do not present it as the person's address. A contact form can be noted in account evidence without fabricating an email.

When no appropriate public contact is found, leave `contacts` empty and explain the gap in the company reason. Do not keep searching unrelated sources indefinitely just to fill a cell. Do not copy personal contact details that are unrelated to the person's professional role.

The suppression CSV accepts `domain,email` columns. Either field may be empty per row. Domain suppression covers that company domain and its subdomains. Email suppression matches the full address case-insensitively. Imports preserve suppression, and exports recheck it.
