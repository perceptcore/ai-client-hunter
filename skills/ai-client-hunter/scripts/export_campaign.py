#!/usr/bin/env python3
"""Export validated local campaign data; does not fetch sources or send messages."""
import argparse
import csv
import html
import io
import json
import re
import sys
from pathlib import Path
from prepare_campaign import (atomic_text, company_suppressed, contact_suppressed,
                              draft_state, load_json, normalize)


def csv_safe(value):
    value = '' if value is None else str(value)
    if value.startswith(('\t', '\r', '\n')) or value.lstrip().startswith(('=', '+', '-', '@')):
        return "'" + value
    return value


def csv_text(fields, rows):
    out = io.StringIO(newline='')
    writer = csv.DictWriter(out, fieldnames=fields, extrasaction='ignore', lineterminator='\n')
    writer.writeheader()
    for row in rows:
        writer.writerow({k: csv_safe(row.get(k)) for k in fields})
    return out.getvalue()


def md(value):
    value = html.escape(str(value), quote=False)
    return re.sub(r'([\\`*\[\]#!_|])', r'\\\1', value)


def fenced(value):
    runs = [len(s) for s in re.findall(r'`+', value)]
    fence = '`' * max(3, max(runs, default=0) + 1)
    return f'{fence}text\n{value}\n{fence}'


def render(d):
    companies = {c['id']: c for c in d['companies']}
    evidence = {e['id']: e for e in d['evidence']}
    prospects = [dict(c, evidence_ids=';'.join(c['evidence_ids']),
                      suppressed=company_suppressed(d, c)) for c in d['companies']]
    contacts = [dict(c, company=companies[c['company_id']]['name'],
                     qualification=companies[c['company_id']]['qualification'],
                     deliverability='unverified') for c in d['contacts'] if not contact_suppressed(d, c)]
    briefs = ['# Account briefs', '', 'Research findings require source review. Script validation checks structure, not truth.', '']
    for c in d['companies']:
        briefs += [f'## {md(c["name"])}', '', f'- Website: {c["website"]}',
                   f'- Qualification: {c["qualification"]}',
                   f'- Research: {c["research_status"]}',
                   f'- Suppressed: {company_suppressed(d, c)}',
                   f'- Reason: {md(c["reason"] or "Not researched")}', '']
        for eid in c['evidence_ids']:
            e = evidence[eid]
            briefs += [f'- [{md(eid)}] {md(e["finding"])}',
                       f'  Source: {e.get("url") or "No source URL supplied"}; date: {md(e.get("observed_at") or "unknown")}; status: {e["status"]}']
        for o in d['ai_observations']:
            if o['company_id'] == c['id']:
                briefs += ['', f'### AI observation {md(o["id"])}',
                           f'Origin: {o["origin"]}; provider: {md(o.get("provider") or "unknown")}; model: {md(o.get("model") or "unknown")}; date: {md(o.get("collected_at") or "unknown")}',
                           '', 'Prompt:', fenced(o['prompt']), '', 'Original answer:', fenced(o['response'])]
        briefs += ['']
    outreach = ['# Outreach drafts', '', 'Human review required. No messages have been sent. Publicly listed emails have not been verified for deliverability.', '']
    for draft in d['drafts']:
        c = companies[draft['company_id']]
        status, reason = draft_state(d, draft)
        outreach += [f'## {md(c["name"])} — {md(draft["id"])}', '', f'Status: {status}. {reason}', '']
        if status in ('held', 'suppressed'):
            continue
        contact = next((r for r in contacts if r['id'] == draft.get('contact_id')), None)
        outreach += [f'Recipient: {md(contact.get("email") if contact and contact.get("email") else "Not found")}',
                     f'Subject: {md(draft["subject"])}', '', fenced(draft['body']), '']
        for n, followup in enumerate(draft['followups'], 1):
            outreach += [f'### Follow-up {n}', '', fenced(followup), '']
        outreach += ['Evidence:']
        for eid in draft['evidence_ids']:
            e = evidence[eid]
            outreach += [f'- {md(eid)}: {md(e["finding"])} — {e.get("url") or "user/tool-provided AI answer"}']
        outreach += ['']
    return {'prospects.csv': csv_text(['id', 'name', 'domain', 'website', 'qualification', 'reason', 'research_status', 'evidence_ids', 'suppressed'], prospects),
            'contacts.csv': csv_text(['id', 'company_id', 'company', 'qualification', 'name', 'role', 'email', 'email_status', 'source_url', 'observed_at', 'deliverability'], contacts),
            'account-briefs.md': '\n'.join(briefs).rstrip() + '\n',
            'outreach.md': '\n'.join(outreach).rstrip() + '\n'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign', required=True)
    parser.add_argument('--out', help='Defaults to CAMPAIGN/exports')
    args = parser.parse_args(argv)
    try:
        d = normalize(load_json(Path(args.campaign) / 'data.json'))
        outputs = render(d)  # Validate and render everything before writing any artifact.
        destination = Path(args.out) if args.out else Path(args.campaign) / 'exports'
        for filename, content in outputs.items():
            atomic_text(destination / filename, content)
        print(json.dumps({'exported': len(outputs), 'directory': str(destination)}))
        return 0
    except (ValueError, OSError, TypeError, KeyError) as exc:
        print(f'Export error: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
