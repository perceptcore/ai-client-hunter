"""Schema-v2 contact evidence and ranking. No network or model calls."""
from urllib.parse import urlsplit

GENERIC = {'info', 'hello', 'contact', 'support', 'sales', 'team', 'admin', 'office',
           'help', 'enquiries', 'inquiries', 'press', 'marketing', 'careers', 'jobs'}
SYSTEM = {'noreply', 'no-reply', 'donotreply', 'notifications', 'notify', 'privacy',
          'legal', 'security', 'billing', 'abuse', 'postmaster', 'webmaster'}
CHANNELS = {'email', 'professional_profile', 'work_contact_page', 'company_form'}


def email_kind(address):
    local = (address or '').split('@')[0].casefold().split('+')[0]
    return 'system_address' if local in SYSTEM else 'generic_inbox' if local in GENERIC else 'person'


def compact(value):
    import unicodedata
    return ' '.join(unicodedata.normalize('NFKC', value).casefold().split())


def person_route(contact):
    """A company-level form/inbox is never a named-person success."""
    if contact.get('contact_kind') != 'person' or contact.get('identity_status') != 'supported':
        return None
    candidates = [c for c in contact.get('channels', []) if c.get('status') == 'observed'
                  and c.get('attribution') == 'person' and c['type'] != 'company_form'
                  and (c['type'] != 'email' or email_kind(c['value']) == 'person')]
    order = {'email': 0, 'professional_profile': 1, 'work_contact_page': 2}
    return min(candidates, key=lambda c: order[c['type']], default=None)


def validate_contacts(data, require, text, web_url, domain, email, dated):
    companies = {c['id']: c for c in data['companies']}
    for contact in data['contacts']:
        company = companies[contact['company_id']]
        kind = contact.get('contact_kind', 'legacy_unverified')
        identity = contact.get('identity_status', 'legacy_unverified')
        fit = contact.get('role_fit', 'unknown')
        require(kind in ('person', 'generic_inbox', 'system_address', 'legacy_unverified'), 'Invalid contact_kind')
        require(identity in ('candidate', 'supported', 'historical', 'conflicting', 'legacy_unverified'), 'Invalid identity_status')
        require(fit in ('primary', 'fallback', 'unmatched', 'unknown'), 'Invalid role_fit')
        contact.update(contact_kind=kind, identity_status=identity, role_fit=fit)
        contact['selection_reason'] = text(contact.get('selection_reason', ''), 'selection_reason', optional=True)
        sources = contact.setdefault('role_evidence', [])
        channels = contact.setdefault('channels', [])
        require(isinstance(sources, list) and all(isinstance(s, dict) for s in sources), 'role_evidence must be an object array')
        require(isinstance(channels, list) and all(isinstance(c, dict) for c in channels), 'channels must be an object array')
        current = []
        for source in sources:
            source['url'] = web_url(source.get('url'), 'role evidence URL')
            source['excerpt'] = text(source.get('excerpt'), 'role evidence excerpt')
            dated(source.get('observed_at'), 'role evidence observed_at')
            require(source.get('source_type') in ('official_company', 'external'), 'Invalid role source_type')
            require(type(source.get('is_current')) is bool, 'Role evidence must explicitly label is_current')
            if source['source_type'] == 'official_company':
                host, base = domain(source['url']), company['domain']
                require(host == base or host.endswith('.' + base), 'Official role evidence must be on the company domain')
            if source['is_current']:
                current.append(source)
        if identity == 'supported':
            require(kind == 'person' and contact['name'] and contact['role'], 'Supported identity requires a named person and role')
            supported = [s for s in current if compact(contact['name']) in compact(s['excerpt'])
                         and compact(contact['role']) in compact(s['excerpt'])]
            official = any(s['source_type'] == 'official_company' for s in supported)
            hosts = {domain(s['url']) for s in supported}
            require(official or len(hosts) >= 2, 'Supported identity requires an official named-role source or two distinct corroborating source hosts')
            require(contact['selection_reason'] and fit != 'unknown', 'Supported contacts require a role-fit decision and reason')
        for channel in channels:
            require(channel.get('type') in CHANNELS, 'Invalid channel type')
            channel['source_url'] = web_url(channel.get('source_url'), 'channel source_url')
            channel['excerpt'] = text(channel.get('excerpt'), 'channel excerpt')
            dated(channel.get('observed_at'), 'channel observed_at')
            require(channel.get('status') in ('observed', 'unconfirmed'), 'Invalid channel status')
            require(channel.get('attribution') in ('person', 'company'), 'Invalid channel attribution')
            channel['value'] = email(channel.get('value')) if channel['type'] == 'email' else web_url(channel.get('value'), 'channel value')
            if channel['type'] == 'company_form':
                require(channel['attribution'] == 'company', 'A company form is not a personal route')
            if channel['status'] == 'observed' and channel['type'] == 'email':
                require(channel['value'].casefold() in channel['excerpt'].casefold(), 'Email must appear verbatim in its source excerpt')
            if channel['status'] == 'observed' and channel['attribution'] == 'person':
                require(kind == 'person' and contact['name'] and compact(contact['name']) in compact(channel['excerpt']),
                        'A personal channel requires the named person in its source excerpt')
                if channel['type'] == 'professional_profile':
                    parts = urlsplit(channel['value'])
                    require(parts.path.strip('/'), 'A professional profile needs a person-specific path')
                    require(domain(channel['value']) != company['domain'] or parts.path.strip('/'), 'Company homepage is not a personal profile')
        if kind == 'person' and contact.get('email'):
            require(email_kind(contact['email']) == 'person', 'Generic/system email cannot be a named-person email')
            require(any(c['type'] == 'email' and c['status'] == 'observed' and c['attribution'] == 'person'
                        and c['value'].casefold() == contact['email'].casefold() for c in channels),
                    'Person email requires an observed, person-attributed channel')


def selected_contacts(data, is_suppressed):
    result = []
    for company in data['companies']:
        if company['qualification'] != 'qualified':
            continue
        candidates = [c for c in data['contacts'] if c['company_id'] == company['id']
                      and c.get('role_fit') in ('primary', 'fallback') and person_route(c)
                      and not is_suppressed(data, c)]
        order = {'email': 0, 'professional_profile': 1, 'work_contact_page': 2}
        candidates.sort(key=lambda c: (c['role_fit'] != 'primary', order[person_route(c)['type']], c['id']))
        result.extend(candidates[:3])
    return result


def migrate_v1(raw):
    import copy
    data = copy.deepcopy(raw)
    if data.get('schema_version') != 1:
        raise ValueError('Migration accepts schema_version 1 only')
    data['schema_version'] = 2
    for c in data.get('contacts', []):
        kind = email_kind(c.get('email')) if c.get('email') else 'legacy_unverified'
        if kind == 'person':
            kind = 'legacy_unverified'
        c.update(contact_kind=kind, identity_status='legacy_unverified', role_fit='unknown',
                 selection_reason='Imported from v1; identity and role evidence need review',
                 role_evidence=[], channels=[])
        if c.get('email'):
            c['channels'].append({'type': 'email', 'value': c['email'], 'source_url': c['source_url'],
                                  'excerpt': 'Legacy public email record: ' + c['email'],
                                  'observed_at': c['observed_at'], 'status': 'unconfirmed', 'attribution': 'company'})
    return data
