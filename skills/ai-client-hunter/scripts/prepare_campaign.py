#!/usr/bin/env python3
"""Local campaign storage, normalization and validation. Python 3.10+, no network."""
import argparse
import copy
import csv
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from datetime import date, datetime, timezone
from urllib.parse import urlsplit, urlunsplit

VERSION = 1
COLLECTIONS = ('companies', 'evidence', 'contacts', 'drafts', 'ai_observations')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def text(value, label, optional=False):
    require(isinstance(value, str), f'{label}: expected a string')
    value = value.strip()
    require(optional or bool(value), f'{label}: must not be empty')
    return value


def web_url(value, label='URL'):
    value = text(value, label)
    require(not any(c.isspace() for c in value), f'{label}: whitespace is invalid')
    parts = urlsplit(value)
    require(parts.scheme.lower() in ('http', 'https') and bool(parts.hostname),
            f'{label}: use an absolute http(s) URL')
    require(not parts.username and not parts.password, f'{label}: credentials are not allowed')
    host = parts.hostname.rstrip('.').encode('idna').decode('ascii').lower()
    require('.' in host and not host.endswith(('.local', '.localhost')),
            f'{label}: expected a public website hostname')
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError(f'{label}: use a website hostname, not an IP address')
    port = parts.port
    require(port in (None, 80 if parts.scheme.lower() == 'http' else 443),
            f'{label}: nonstandard ports are not supported')
    return urlunsplit((parts.scheme.lower(), host, parts.path or '/', parts.query, ''))


def domain(value):
    value = text(value, 'domain/website')
    if '://' not in value:
        value = 'https://' + value
    host = urlsplit(web_url(value)).hostname
    return host[4:] if host.startswith('www.') else host


def email(value):
    value = text(value, 'email')
    require(bool(re.fullmatch(r'[^\s@,;]+@[^\s@,;]+\.[^\s@,;]+', value)),
            f'Invalid email syntax: {value!r}; syntax does not prove deliverability')
    return value


def dated(value, label):
    value = text(value, label)
    date.fromisoformat(value)
    return value


def string_list(value, label):
    require(isinstance(value, list), f'{label}: expected an array')
    return list(dict.fromkeys(text(v, label) for v in value))


def brief_config(brief):
    require(isinstance(brief, dict), 'brief: expected an object')
    b = copy.deepcopy(brief)
    for key in ('icp', 'offer'):
        b[key] = text(b.get(key), 'brief.' + key)
    for key in ('markets', 'contact_roles'):
        b[key] = string_list(b.get(key, []), 'brief.' + key)
    b['outreach_language'] = text(b.get('outreach_language', 'English'), 'outreach_language')
    for key, default in (('target_count', 25), ('batch_size', 10)):
        b[key] = b.get(key, default)
        require(type(b[key]) is int and b[key] > 0, f'brief.{key}: positive integer required')
    return b


def load_json(path):
    with Path(path).open(encoding='utf-8-sig') as f:
        return json.load(f)


def atomic_text(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='',
                                         dir=path.parent, delete=False) as f:
            tmp = Path(f.name)
            f.write(content)
        os.replace(tmp, path)
    finally:
        if tmp and tmp.exists():
            tmp.unlink()


def atomic_json(path, data):
    atomic_text(path, json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def suppression_csv(path):
    result = {'domains': [], 'emails': []}
    if not path:
        return result
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        require(bool(set(reader.fieldnames or []) & {'domain', 'email'}),
                'Suppression CSV requires domain and/or email headers')
        for row in reader:
            if row.get('domain', '').strip():
                result['domains'].append(domain(row['domain']))
            if row.get('email', '').strip():
                result['emails'].append(email(row['email']).casefold())
    return result


def seed_companies(path):
    if not path:
        return []
    result = []
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        require('website' in (reader.fieldnames or []), 'Website CSV requires a website header')
        for line, row in enumerate(reader, 2):
            if not any((v or '').strip() for v in row.values() if isinstance(v, str)):
                continue
            website = (row.get('website') or '').strip()
            host = domain(website)
            result.append({'id': 'co-' + hashlib.sha256(host.encode()).hexdigest()[:12],
                           'name': (row.get('name') or host).strip(),
                           'website': web_url(website if '://' in website else 'https://' + website),
                           'qualification': 'review', 'reason': '', 'evidence_ids': [],
                           'research_status': 'pending'})
    return result


def normalize(raw):
    require(isinstance(raw, dict), 'Campaign data must be an object')
    d = copy.deepcopy(raw)
    require(type(d.get('schema_version')) is int and d['schema_version'] == VERSION,
            'Unsupported schema_version; expected 1')
    d['brief'] = brief_config(d.get('brief'))
    for key in COLLECTIONS:
        require(isinstance(d.get(key), list), f'{key}: expected an array')
        require(all(isinstance(r, dict) for r in d[key]), f'{key}: records must be objects')
    suppression = d.setdefault('suppression', {'domains': [], 'emails': []})
    require(isinstance(suppression, dict), 'suppression: expected an object')
    suppression['domains'] = sorted({domain(v) for v in string_list(suppression.get('domains', []), 'suppression.domains')})
    suppression['emails'] = sorted({email(v).casefold() for v in string_list(suppression.get('emails', []), 'suppression.emails')})

    # Collapse duplicate company domains while retaining IDs referenced by other records.
    by_domain, aliases, companies = {}, {}, []
    for company in d['companies']:
        company['id'] = text(company.get('id'), 'company.id')
        company['name'] = text(company.get('name'), 'company.name')
        company['website'] = web_url(company.get('website'), 'company.website')
        company['domain'] = domain(company['website'])
        company.setdefault('qualification', 'review')
        company.setdefault('research_status', 'pending')
        company['reason'] = text(company.get('reason', ''), 'company.reason', optional=True)
        company['evidence_ids'] = string_list(company.get('evidence_ids', []), 'company.evidence_ids')
        require(company['qualification'] in ('qualified', 'review', 'excluded'), 'Invalid company qualification')
        require(company['research_status'] in ('pending', 'complete'), 'Invalid research_status')
        require(company['research_status'] != 'complete' or company['reason'], 'Completed research requires a reason')
        previous = by_domain.get(company['domain'])
        if previous:
            fields = ('name', 'qualification', 'reason', 'research_status')
            require(all(previous[k] == company[k] for k in fields),
                    f'Conflicting duplicate domain {company["domain"]}; resolve before saving')
            aliases[company['id']] = previous['id']
            previous['evidence_ids'] = list(dict.fromkeys(previous['evidence_ids'] + company['evidence_ids']))
        else:
            by_domain[company['domain']] = company
            companies.append(company)
    d['companies'] = companies
    for key in COLLECTIONS[1:]:
        for r in d[key]:
            r['company_id'] = aliases.get(r.get('company_id'), r.get('company_id'))

    ids = {}
    for key in COLLECTIONS:
        ids[key] = {}
        for r in d[key]:
            rid = text(r.get('id'), key + '.id')
            require(rid not in ids[key], f'Duplicate ID in {key}: {rid}')
            ids[key][rid] = r
            if key != 'companies':
                require(r.get('company_id') in ids['companies'], f'{key}.{rid}: unknown company_id')

    for r in d['ai_observations']:
        for key in ('prompt', 'response'):
            text(r.get(key), 'ai_observation.' + key)
        require(r.get('origin') in ('host_tool', 'user_provided'), 'Invalid AI observation origin')
        for key in ('provider', 'model', 'collected_at', 'source_url'):
            r.setdefault(key, None)
            if r[key] is not None:
                text(r[key], 'ai_observation.' + key)
        if r['collected_at']:
            dated(r['collected_at'], 'AI collected_at')
        if r['source_url']:
            r['source_url'] = web_url(r['source_url'])

    for r in d['evidence']:
        require(r.get('kind') in ('business', 'contact', 'ai_answer'), 'Invalid evidence kind')
        text(r.get('finding'), 'evidence.finding')
        r.setdefault('status', 'observed')
        require(r['status'] in ('observed', 'conflicting'), 'Invalid evidence status')
        if r['kind'] == 'ai_answer':
            observation = ids['ai_observations'].get(r.get('ai_observation_id'))
            require(observation and observation['company_id'] == r['company_id'], 'AI evidence requires a matching raw AI observation')
            if r.get('url'):
                r['url'] = web_url(r['url'])
            if r.get('observed_at'):
                dated(r['observed_at'], 'evidence.observed_at')
        else:
            r['url'] = web_url(r.get('url'), 'evidence.url')
            dated(r.get('observed_at'), 'evidence.observed_at')

    def evidence_links(r, key='evidence_ids'):
        links = string_list(r.get(key, []), key)
        for eid in links:
            e = ids['evidence'].get(eid)
            require(e and e['company_id'] == r.get('company_id', r['id']), f'{key}: missing or cross-company evidence {eid}')
        r[key] = links
        return links

    for company in d['companies']:
        evidence_links(company)
        require(company['qualification'] != 'qualified' or
                (company['research_status'] == 'complete' and company['evidence_ids']),
                'Qualified companies require completed research and evidence')

    contacts, by_email, contact_aliases = [], {}, {}
    for r in d['contacts']:
        r['source_url'] = web_url(r.get('source_url'), 'contact.source_url')
        dated(r.get('observed_at'), 'contact.observed_at')
        for key in ('name', 'role'):
            r[key] = text(r.get(key, ''), 'contact.' + key, optional=True)
        if r.get('email'):
            r['email'] = email(r['email'])
            require(r.get('email_status') == 'publicly_listed', 'Email requires email_status publicly_listed; never infer an address')
            address = r['email'].casefold()
            if address in by_email:
                previous = by_email[address]
                require(previous['company_id'] == r['company_id'] and previous['name'] == r['name']
                        and previous['role'] == r['role'], 'Conflicting duplicate email; resolve the account/person association')
                contact_aliases[r['id']] = previous['id']
                continue
            by_email[address] = r
        else:
            r['email'] = None
            require(r.get('email_status') == 'not_found', 'Missing email requires email_status not_found')
        contacts.append(r)
    d['contacts'] = contacts
    ids['contacts'] = {r['id']: r for r in contacts}
    for r in d['drafts']:
        text(r.get('subject'), 'draft.subject')
        text(r.get('body'), 'draft.body')
        require(evidence_links(r), 'Drafts require evidence_ids')
        followups = r.get('followups')
        require(isinstance(followups, list) and len(followups) == 2, 'Draft requires exactly two followups')
        for followup in followups:
            text(followup, 'followup')
        cid = r.get('contact_id')
        r['contact_id'] = contact_aliases.get(cid, cid)
        if r['contact_id'] is not None:
            contact = ids['contacts'].get(r['contact_id'])
            require(contact and contact['company_id'] == r['company_id'], 'Draft contact must belong to the same company')
    return d


def company_suppressed(d, company):
    return any(company['domain'] == host or company['domain'].endswith('.' + host)
               for host in d['suppression']['domains'])


def contact_suppressed(d, contact):
    company = next(c for c in d['companies'] if c['id'] == contact['company_id'])
    address = contact.get('email')
    if company_suppressed(d, company):
        return True
    if not address:
        return False
    email_domain = domain(address.rsplit('@', 1)[1])
    return (address.casefold() in d['suppression']['emails'] or
            any(email_domain == host or email_domain.endswith('.' + host)
                for host in d['suppression']['domains']))


def draft_state(d, draft):
    company = next(c for c in d['companies'] if c['id'] == draft['company_id'])
    contact = next((c for c in d['contacts'] if c['id'] == draft.get('contact_id')), None)
    if company_suppressed(d, company) or (contact and contact_suppressed(d, contact)):
        return 'suppressed', 'Suppression match; message withheld'
    if company['qualification'] != 'qualified':
        return 'held', 'Company is not qualified'
    evidence = {e['id']: e for e in d['evidence']}
    if any(evidence[eid]['status'] == 'conflicting' for eid in draft['evidence_ids']):
        return 'held', 'Conflicting evidence requires resolution'
    for eid in draft['evidence_ids']:
        e = evidence[eid]
        if e['kind'] == 'ai_answer':
            obs = next(o for o in d['ai_observations'] if o['id'] == e['ai_observation_id'])
            if not all(obs.get(k) for k in ('provider', 'model', 'collected_at')):
                return 'held', 'AI finding lacks provider, model or collection date'
    if not contact or not contact.get('email'):
        return 'needs_contact', 'No publicly listed recipient email; review draft only'
    return 'review_ready', 'Human review required; address deliverability is unverified'


def save_campaign(folder, data):
    folder = Path(folder)
    atomic_json(folder / 'data.json', data)
    checkpoint = {'schema_version': VERSION, 'updated_at': datetime.now(timezone.utc).isoformat(),
                  'completed_company_ids': [c['id'] for c in data['companies'] if c['research_status'] == 'complete'],
                  'remaining_company_ids': [c['id'] for c in data['companies'] if c['research_status'] == 'pending']}
    atomic_json(folder / 'checkpoint.json', checkpoint)
    return checkpoint


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init', help='Create a campaign without overwriting an existing one')
    init.add_argument('--campaign', required=True)
    init.add_argument('--brief', required=True)
    init.add_argument('--websites')
    init.add_argument('--suppression')
    check = sub.add_parser('check', help='Normalize data and rebuild the checkpoint')
    check.add_argument('--campaign', required=True)
    check.add_argument('--suppression')
    check.add_argument('--check-only', action='store_true')
    imp = sub.add_parser('import', help='Add seed websites while preserving researched records')
    imp.add_argument('--campaign', required=True)
    imp.add_argument('--websites', required=True)
    args = parser.parse_args(argv)
    folder = Path(args.campaign)
    try:
        if args.command == 'init':
            require(not (folder / 'data.json').exists(), 'Campaign already exists; use check or import to resume')
            d = {'schema_version': VERSION, 'brief': load_json(args.brief),
                 'suppression': suppression_csv(args.suppression), **{k: [] for k in COLLECTIONS}}
            d['companies'] = seed_companies(args.websites)
        else:
            d = normalize(load_json(folder / 'data.json'))
            if args.command == 'import':
                known = {c['domain'] for c in d['companies']}
                d['companies'].extend(c for c in seed_companies(args.websites) if domain(c['website']) not in known)
            elif args.suppression:
                extra = suppression_csv(args.suppression)
                for key in extra:
                    d['suppression'][key].extend(extra[key])
        d = normalize(d)
        if not getattr(args, 'check_only', False):
            save_campaign(folder, d)
        print(json.dumps({'valid': True, 'companies': len(d['companies']),
                          'contacts': len(d['contacts']), 'drafts': len(d['drafts']),
                          'check_only': getattr(args, 'check_only', False)}))
        return 0
    except (ValueError, OSError, TypeError, KeyError) as exc:
        print(f'Campaign error: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
