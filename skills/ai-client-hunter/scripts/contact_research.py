#!/usr/bin/env python3
"""Bounded public HTML collection and resumable contact research. Python 3.10+."""
import argparse
from datetime import datetime, timezone
import hashlib
import html
from html.parser import HTMLParser
import http.client
import ipaddress
import json
from pathlib import Path
import re
import socket
import ssl
import sys
import time
from urllib.parse import urljoin, urlsplit, unquote, quote
from urllib.robotparser import RobotFileParser

from prepare_campaign import atomic_json, domain, email, load_json, normalize, web_url, company_suppressed
from contact_models import email_kind

AGENT = 'PerceptCore-AIClientHunter/0.2'
MAX_BYTES = 2 * 1024 * 1024
PAGE_LIMIT = 20
QUERY_LIMIT = 6
ROLES = re.compile(r'founder|chief|head of|director|marketing|growth|leadership|\bCEO\b|\bCMO\b', re.I)
LINK_WORDS = {'contact': 100, 'leadership': 95, 'team': 90, 'about': 85, 'people': 80,
              'founder': 80, 'staff': 75, 'author': 70, 'company': 60, 'press': 50}
EMAIL_RE = re.compile(r'[A-Z0-9.!#$%&\x27*+/=?^_`{|}~-]+@[A-Z0-9](?:[A-Z0-9.-]*[A-Z0-9])?\.[A-Z]{2,}', re.I)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def fingerprint(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


class PageParser(HTMLParser):
    def __init__(self, url):
        super().__init__(convert_charrefs=True)
        self.url, self.parts, self.links, self.jsonld = url, [], [], []
        self.hidden = []
        self.anchor = None
        self.ld = None
        self.text_offset = 0

    def append_text(self, value):
        self.parts.append(value)
        self.text_offset += len(value)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        hide = tag in ('script', 'style', 'noscript', 'svg', 'template') or 'hidden' in attrs or attrs.get('aria-hidden') == 'true'
        if tag == 'script' and attrs.get('type', '').lower() == 'application/ld+json' and not self.hidden:
            self.ld = []
        if hide or self.hidden:
            if tag not in ('br', 'img', 'input', 'meta', 'link', 'hr', 'source', 'wbr'):
                self.hidden.append(tag)
            return
        if tag in ('p', 'div', 'li', 'h1', 'h2', 'h3', 'h4', 'section', 'article', 'br'):
            self.append_text('\n')
        if tag == 'a' and attrs.get('href'):
            self.anchor = {'url': urljoin(self.url, attrs['href']), 'parts': [attrs.get('aria-label') or attrs.get('title') or ''], 'offset': self.text_offset}

    def handle_endtag(self, tag):
        if self.hidden:
            if tag == self.hidden[-1]:
                self.hidden.pop()
            if tag == 'script' and self.ld is not None:
                try:
                    self.jsonld.append(json.loads(''.join(self.ld)))
                except (ValueError, TypeError, RecursionError):
                    pass
                self.ld = None
            return
        if tag == 'a' and self.anchor:
            self.links.append({'url': self.anchor['url'], 'label': ' '.join(self.anchor['parts']).strip(), 'offset': self.anchor['offset']})
            self.anchor = None
        if tag in ('p', 'div', 'li', 'section', 'article'):
            self.append_text('\n')

    def handle_data(self, value):
        if self.ld is not None:
            self.ld.append(value)
        if self.hidden:
            return
        self.append_text(value + ' ')
        if self.anchor:
            self.anchor['parts'].append(value)


def extract_page(body, url):
    parser = PageParser(url)
    parser.feed(body)
    raw_text = ''.join(parser.parts)
    lines = [' '.join(s.split()) for s in raw_text.splitlines()]
    lines = list(dict.fromkeys(s for s in lines if s))
    visible = '\n'.join(lines)
    emails = {}
    for match in EMAIL_RE.finditer(visible):
        address = match.group().strip('.;,')
        if address.rsplit('.', 1)[-1].lower() in ('png', 'jpg', 'jpeg', 'svg', 'webp', 'woff'):
            continue
        emails[address.casefold()] = {'value': address, 'kind': email_kind(address),
                                      'excerpt': visible[max(0, match.start()-150):match.end()+150], 'source': 'visible_text'}
    links = []
    for link in parser.links:
        if link['url'].lower().startswith('mailto:'):
            value = unquote(link['url'][7:].split('?', 1)[0])
            try:
                email(value)
            except ValueError:
                continue
            emails.setdefault(value.casefold(), {'value': value, 'kind': email_kind(value),
                                                'excerpt': f'{link["label"]} <{value}>', 'source': 'mailto'})
        else:
            try:
                target = web_url(link['url'])
            except (ValueError, UnicodeError):
                continue
            score = max((weight for word, weight in LINK_WORDS.items() if word in (target + ' ' + link['label']).casefold()), default=0)
            parts = urlsplit(target)
            profile = ((parts.hostname == 'linkedin.com' or parts.hostname.endswith('.linkedin.com')) and parts.path.startswith('/in/')) or (
                parts.hostname in ('x.com', 'twitter.com', 'bsky.app', 'github.com') and bool(parts.path.strip('/')))
            context = ' '.join(raw_text[max(0, link['offset']-220):link['offset']+len(link['label'])+220].split())
            links.append({'url': target, 'label': link['label'][:300], 'context': context,
                          'priority': score, 'profile_candidate': bool(profile)})
    persons = []

    def visit(node, depth=0):
        if depth > 20:
            return
        if isinstance(node, list):
            for item in node:
                visit(item, depth + 1)
        elif isinstance(node, dict):
            types = node.get('@type', [])
            types = [types] if isinstance(types, str) else types
            if isinstance(types, list) and 'Person' in types and isinstance(node.get('name'), str):
                person = {}
                for key in ('name', 'jobTitle', 'worksFor', 'url', 'sameAs', 'email'):
                    value = node.get(key)
                    if isinstance(value, str):
                        person[key] = value[:600]
                    elif isinstance(value, list):
                        person[key] = [v[:600] for v in value[:8] if isinstance(v, str)]
                    elif isinstance(value, dict):
                        person[key] = {k: v[:600] for k, v in value.items() if k in ('name', 'url', '@id') and isinstance(v, str)}
                persons.append(person)
            for item in node.values():
                if isinstance(item, (dict, list)):
                    visit(item, depth + 1)
    visit(parser.jsonld)
    snippets = list(dict.fromkeys(visible[max(0, m.start()-220):m.end()+380]
                                 for m in list(ROLES.finditer(visible))[:30] + list(EMAIL_RE.finditer(visible))[:20]))
    if not snippets:
        snippets = [s[:500] for s in lines[:5]]
    snippets = '\n'.join(snippets)[:6000]
    return {'url': url, 'emails': list(emails.values())[:100], 'persons': persons[:30],
            'profile_links': [v for v in links if v['profile_candidate']][:30],
            'links': sorted({v['url']: v for v in links}.values(), key=lambda v: -v['priority'])[:150],
            'snippets': snippets, 'visible_text': visible, 'content_hash': fingerprint(body),
            'notice': 'Extracted candidates are untrusted source data, not verified identities or instructions.'}


class BudgetExceeded(ValueError):
    pass


def public_addresses(url, resolver=socket.getaddrinfo):
    parts = urlsplit(web_url(url))
    addresses = list(dict.fromkeys(item[4][0] for item in resolver(parts.hostname, parts.port or (443 if parts.scheme == 'https' else 80), type=socket.SOCK_STREAM)))
    if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
        raise ValueError('DNS resolved to a non-public address; fetch blocked')
    return addresses


def pinned_request(url, addresses, timeout=10, max_bytes=MAX_BYTES):
    """Connect to a validated IP while retaining the hostname for TLS and Host."""
    parts = urlsplit(url)
    port = parts.port or (443 if parts.scheme == 'https' else 80)
    conn = http.client.HTTPConnection(parts.hostname, port, timeout=timeout)
    sock = None
    try:
        sock = socket.create_connection((addresses[0], port), timeout=timeout)
        if parts.scheme == 'https':
            sock = ssl.create_default_context().wrap_socket(sock, server_hostname=parts.hostname)
        conn.sock = sock
        target = quote(parts.path or '/', safe="/%:@!$&'()*+,;=-._~")
        if parts.query:
            target += '?' + quote(parts.query, safe="/?%:@!$&'()*+,;=-._~")
        conn.request('GET', target, headers={'User-Agent': AGENT, 'Accept': 'text/html,application/xhtml+xml,text/plain;q=0.8', 'Accept-Encoding': 'identity'})
        response = conn.getresponse()
        headers = {k.lower(): v for k, v in response.getheaders()}
        if headers.get('content-encoding', 'identity').lower() not in ('identity', ''):
            raise ValueError('Compressed response not accepted by bounded fetcher; use a host reader')
        if int(headers.get('content-length', '0')) > max_bytes:
            raise ValueError('Response exceeds size limit')
        body = response.read(max_bytes + 1)
        if len(body) > max_bytes:
            raise ValueError('Response exceeds size limit')
        return response.status, headers, body
    finally:
        conn.close()
        if sock:
            sock.close()


class Fetcher:
    def __init__(self, cache, request_hook=lambda: None, refresh=False, resolver=socket.getaddrinfo,
                 transport=pinned_request, clock=time.time, sleeper=time.sleep):
        self.cache = Path(cache)
        self.request_hook, self.refresh = request_hook, refresh
        self.resolver, self.transport, self.clock, self.sleeper = resolver, transport, clock, sleeper
        self.last_request, self.robots = {}, {}
        rate_file = self.cache / 'host-requests.json'
        if rate_file.is_file():
            try:
                self.last_request = {k: float(v) for k, v in load_json(rate_file).items() if isinstance(v, (int, float))}
            except (ValueError, OSError, TypeError, AttributeError):
                pass
        self.cache_hits = 0

    def _cached(self, url):
        path = self.cache / (fingerprint(url) + '.json')
        if self.refresh or not path.exists():
            return None
        try:
            value = load_json(path)
            ttl = 7*86400 if value['status'] == 'ok' else 86400
            if value['requested_url'] == url and 0 <= self.clock() - value['cached_at'] < ttl:
                self.cache_hits += 1
                return value
        except (ValueError, OSError, KeyError, TypeError):
            pass
        return None

    def _save(self, original, value):
        value.update(requested_url=original, cached_at=self.clock())
        atomic_json(self.cache / (fingerprint(original) + '.json'), value)
        return value

    def _robots(self, url):
        parts = urlsplit(url)
        origin = f'{parts.scheme}://{parts.netloc}'
        if origin in self.robots:
            return self.robots[origin]
        result = self.fetch(origin + '/robots.txt', respect_robots=False)
        parser = RobotFileParser()
        code = result.get('http_status')
        if code == 404:
            parser.parse(['User-agent: *', 'Allow: /'])
        elif result['status'] == 'ok':
            parser.parse(result.get('body', '').splitlines())
        else:
            parser.parse(['User-agent: *', 'Disallow: /'])
        self.robots[origin] = parser
        return parser

    def fetch(self, url, respect_robots=True):
        original = web_url(url)
        cached = self._cached(original)
        if cached is not None:
            return dict(cached, cache_hit=True)
        current = original
        try:
            for hop in range(6):
                current = web_url(current)
                delay = 1
                if respect_robots:
                    robot = self._robots(current)
                    if not robot.can_fetch(AGENT, current):
                        return self._save(original, {'url': current, 'status': 'robots_denied', 'http_status': None, 'fetched_at': utc_now()})
                    delay = max(1, robot.crawl_delay(AGENT) or 0)
                    if delay > 10:
                        raise ValueError('robots crawl-delay exceeds interactive budget; deferred')
                addresses = public_addresses(current, self.resolver)
                self.request_hook()
                host = urlsplit(current).netloc
                pause = max(0, delay - (self.clock() - self.last_request.get(host, 0)))
                if pause:
                    self.sleeper(pause)
                self.last_request[host] = self.clock()
                atomic_json(self.cache / 'host-requests.json', self.last_request)
                status, headers, body = self.transport(current, addresses)
                if len(body) > MAX_BYTES:
                    raise ValueError('Response exceeds size limit')
                if status in (301, 302, 303, 307, 308):
                    if hop == 5 or not headers.get('location'):
                        raise ValueError('Redirect limit or missing redirect target')
                    current = urljoin(current, headers['location'])
                    continue
                mime = headers.get('content-type', '').split(';', 1)[0].lower()
                result = {'url': current, 'http_status': status, 'fetched_at': utc_now(), 'content_type': mime}
                if status != 200:
                    result.update(status='http_error', retry_after=headers.get('retry-after'))
                elif mime not in ('text/html', 'application/xhtml+xml', 'text/plain'):
                    result.update(status='unsupported_type', error='Use a host tool for PDFs, dynamic pages or non-HTML sources')
                else:
                    charset = re.search(r'charset=([^;\s]+)', headers.get('content-type', ''), re.I)
                    encoding = charset.group(1).strip('"\x27') if charset else 'utf-8'
                    try:
                        decoded = body.decode(encoding, errors='replace')
                    except LookupError:
                        decoded = body.decode('utf-8', errors='replace')
                    result.update(status='ok', body=decoded, content_hash=fingerprint(decoded))
                return self._save(original, result)
        except BudgetExceeded:
            raise
        except (OSError, ValueError, http.client.HTTPException) as exc:
            return self._save(original, {'url': current, 'status': 'fetch_error', 'http_status': None, 'fetched_at': utc_now(), 'error': str(exc)})


def job_path(folder, company_id):
    return Path(folder) / 'contact-research' / (fingerprint(company_id) + '.json')


def get_job(folder, company):
    path = job_path(folder, company['id'])
    if path.exists():
        job = load_json(path)
        if job.get('company_id') != company['id']:
            raise ValueError('Research job/company mismatch')
        return job
    return {'company_id': company['id'], 'page_limit': PAGE_LIMIT, 'query_limit': QUERY_LIMIT,
            'network_limit': 60, 'network_requests': 0, 'cache_hits': 0, 'queries': [], 'pages': [],
            'queue': [company['website']], 'stop_reason': 'not_started', 'created_at': utc_now()}


def compact_page(page):
    return {key: page[key] for key in ('url', 'content_hash', 'snippets', 'emails', 'persons', 'profile_links', 'notice')}


def crawl(folder, company, seeds=(), refresh=False, new_attempt=False, batch_pages=3):
    job = get_job(folder, company)
    if not 1 <= batch_pages <= PAGE_LIMIT:
        raise ValueError('batch_pages must be between 1 and 20')
    if refresh and job['pages'] and not new_attempt:
        raise ValueError('Refreshing a completed/partial frontier requires --new-attempt to retain its prior ledger')
    if new_attempt:
        history = Path(folder) / 'contact-research' / 'history' / (fingerprint(company['id'] + utc_now()) + '.json')
        atomic_json(history, job)
        job = {'company_id': company['id'], 'page_limit': PAGE_LIMIT, 'query_limit': QUERY_LIMIT,
               'network_limit': 60, 'network_requests': 0, 'cache_hits': 0, 'queries': [], 'pages': [],
               'queue': [company['website']], 'stop_reason': 'not_started', 'created_at': utc_now()}
    allowed = set(job.get('allowed_domains', [domain(company['website'])]))
    cleaned_seeds = [web_url(url) for url in seeds]
    allowed.update(domain(url) for url in cleaned_seeds)
    job['allowed_domains'] = sorted(allowed)
    visited = {p['requested_url'] for p in job['pages']}
    job['queue'] = list(dict.fromkeys(cleaned_seeds + job['queue']))

    def charge():
        if job['network_requests'] >= job['network_limit']:
            raise BudgetExceeded('network_budget_exhausted')
        job['network_requests'] += 1
        atomic_json(job_path(folder, company['id']), job)
    fetcher = Fetcher(Path(folder) / 'cache' / 'contact-pages', charge, refresh=refresh)
    job['stop_reason'] = 'running'
    started_with = len(job['pages'])
    try:
        while job['queue'] and len(job['pages']) < job['page_limit'] and len(job['pages']) - started_with < batch_pages:
            url = job['queue'][0]
            if url in visited:
                job['queue'].pop(0)
                continue
            # Reserve before network I/O so a killed process cannot erase an attempt.
            position = len(job['pages'])
            job['pages'].append({'requested_url': url, 'url': url, 'status': 'started', 'fetched_at': utc_now()})
            atomic_json(job_path(folder, company['id']), job)
            result = fetcher.fetch(url)
            record = {k: v for k, v in result.items() if k not in ('body', 'cached_at')}
            if result['status'] == 'ok':
                page = extract_page(result['body'], result['url'])
                record['extracted'] = compact_page(page)
                internal = [link['url'] for link in page['links'] if link['priority'] > 0
                            and domain(link['url']) in allowed and link['url'] not in visited]
                job['queue'].extend(internal[:8])
                record['candidate_links'] = page['links']
            job['pages'][position] = record
            visited.add(url)
            job['queue'].pop(0)
            job['queue'] = list(dict.fromkeys(job['queue']))[:80]
            job['cache_hits'] += int(result.get('cache_hit', False))
            atomic_json(job_path(folder, company['id']), job)
        job['stop_reason'] = ('page_budget_exhausted' if len(job['pages']) >= job['page_limit'] else
                              'paused_for_review' if job['queue'] else 'frontier_exhausted')
    except BudgetExceeded as exc:
        job['stop_reason'] = str(exc)
    finally:
        job['updated_at'] = utc_now()
        job['fetch_cache_hits_including_robots'] = fetcher.cache_hits
        atomic_json(job_path(folder, company['id']), job)
    return job


def query_plan(company, roles, contacts):
    name = company['name']
    role = roles[0] if roles else 'founder marketing leader'
    found = [c for c in contacts if c['company_id'] == company['id'] and c.get('contact_kind') == 'person']
    if found:
        person = found[0]['name']
        return [f'"{person}" "{name}" contact', f'"{person}" "{name}" profile', f'"{person}" business website']
    return [f'site:{company["domain"]} team founder marketing', f'"{name}" "{role}"',
            f'"{name}" leadership company', f'"{name}" "{role}" contact']


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for command in ('crawl', 'status', 'inspect', 'log-search', 'log-page', 'finish'):
        p = sub.add_parser(command)
        p.add_argument('--campaign', required=True)
        p.add_argument('--company-id', required=True)
        if command == 'crawl':
            p.add_argument('--seed-url', action='append', default=[])
            p.add_argument('--refresh', action='store_true')
            p.add_argument('--new-attempt', action='store_true', help='Explicitly start another bounded attempt, archiving the prior ledger')
            p.add_argument('--batch-pages', type=int, default=3, help='Pause for AI review after this many new pages (1-20)')
        elif command == 'inspect':
            p.add_argument('--url', help='Inspect a single saved page instead of the company summary')
        elif command == 'log-page':
            p.add_argument('--url', required=True)
            p.add_argument('--text-file', help='UTF-8 text actually read through a host tool; never fabricated source text')
            p.add_argument('--notes', default='')
        elif command == 'log-search':
            p.add_argument('--query', required=True)
            p.add_argument('--url', action='append', default=[])
            p.add_argument('--notes', default='')
        elif command == 'finish':
            p.add_argument('--reason', choices=['verified_route_found', 'no_supported_person', 'no_person_route', 'access_blocked', 'budget_exhausted'], required=True)
    args = parser.parse_args(argv)
    try:
        data = normalize(load_json(Path(args.campaign) / 'data.json'))
        if data['schema_version'] != 2:
            raise ValueError('Run prepare_campaign.py migrate before v2 contact research')
        company = next((c for c in data['companies'] if c['id'] == args.company_id), None)
        if company is None:
            raise ValueError('Unknown company ID')
        if company_suppressed(data, company):
            raise ValueError('Company is suppressed; research skipped')
        job = get_job(args.campaign, company)
        if args.command == 'crawl':
            from contact_models import selected_contacts
            from prepare_campaign import contact_suppressed
            if not args.new_attempt and any(c['company_id'] == company['id'] for c in selected_contacts(data, contact_suppressed)):
                job['stop_reason'] = 'verified_route_found'
                atomic_json(job_path(args.campaign, company['id']), job)
            else:
                job = crawl(args.campaign, company, args.seed_url, args.refresh, args.new_attempt, args.batch_pages)
        elif args.command == 'log-page':
            url = web_url(args.url)
            # A second host-tool read is another attempt, even for a crawled URL.
            if len(job['pages']) >= job['page_limit']:
                raise ValueError('Page budget exhausted; do not open another host page')
            record = {'requested_url': url, 'url': url, 'status': 'host_read', 'fetched_at': utc_now(),
                      'origin': 'host_tool_report', 'notes': args.notes}
            if args.text_file:
                with Path(args.text_file).open('rb') as f:
                    content_bytes = f.read(MAX_BYTES + 1)
                if len(content_bytes) > MAX_BYTES:
                    raise ValueError('Host source text exceeds size limit')
                content = content_bytes.decode('utf-8-sig')
                parsed = extract_page('<p>' + html.escape(content).replace('\n', '</p><p>') + '</p>', url)
                record['extracted'] = compact_page(parsed)
                source_path = Path(args.campaign)/'cache'/'host-sources'/(fingerprint(company['id'] + url + str(len(job['pages'])))+'.json')
                record['source_cache'] = str(source_path)
                atomic_json(source_path,
                            {'url': url, 'origin': 'host_tool_report', 'text': content, 'observed_at': utc_now()})
            job['pages'].append(record)
            job['queue'] = [u for u in job['queue'] if u != url]
            atomic_json(job_path(args.campaign, company['id']), job)
        elif args.command == 'log-search':
            if len(job['queries']) >= job['query_limit']:
                raise ValueError('Search budget exhausted; do not run another host search')
            query = args.query.strip()
            if not query:
                raise ValueError('Search query must not be empty')
            job['queries'].append({'query': query, 'urls': [web_url(u) for u in args.url], 'notes': args.notes, 'logged_at': utc_now()})
            atomic_json(job_path(args.campaign, company['id']), job)
        elif args.command == 'finish':
            if args.reason == 'verified_route_found':
                from contact_models import selected_contacts
                from prepare_campaign import contact_suppressed
                if not any(c['company_id'] == company['id'] for c in selected_contacts(data, contact_suppressed)):
                    raise ValueError('Cannot finish as verified_route_found without a supported person/route')
            job['stop_reason'] = args.reason
            job['updated_at'] = utc_now()
            atomic_json(job_path(args.campaign, company['id']), job)
        output = {'company_id': company['id'], 'stop_reason': job['stop_reason'],
                  'pages_read': sum(p['status'] in ('ok', 'host_read') for p in job['pages']),
                  'pages_used': len(job['pages']), 'page_limit': job['page_limit'],
                  'queries_used': len(job['queries']), 'query_limit': job['query_limit'],
                  'network_requests': job['network_requests'], 'cache_hits': job['cache_hits'],
                  'suggested_queries': query_plan(company, data['brief']['contact_roles'], data['contacts']),
                  'ledger': str(job_path(args.campaign, company['id'])),
                  'notice': 'Search plans are suggestions; log each host search and every host-read URL. No model or search API is called by this helper.'}
        if args.command == 'inspect':
            selected = [p for p in job['pages'] if not args.url or p['requested_url'] == web_url(args.url)]
            output['source_summaries'] = []
            output['summary_truncated'] = False
            for page in selected:
                excerpt = page.get('extracted', {})
                candidate_links = page.get('candidate_links', [])
                cache_file = Path(args.campaign)/'cache'/'contact-pages'/(fingerprint(page['requested_url'])+'.json')
                if cache_file.is_file():
                    cached = load_json(cache_file)
                    if cached.get('body') and cached.get('fetched_at') == page['fetched_at']:
                        reparsed = extract_page(cached['body'], page['url'])
                        excerpt = compact_page(reparsed)
                        candidate_links = reparsed['links']
                entry = {'url': page['url'], 'status': page['status'], 'fetched_at': page['fetched_at'],
                         'snippets': excerpt.get('snippets', '')[:6000 if args.url else 1600],
                         'emails': excerpt.get('emails', [])[:10], 'persons': excerpt.get('persons', [])[:5],
                         'profile_candidates': excerpt.get('profile_links', [link for link in candidate_links if link.get('profile_candidate')])[:12],
                         'candidate_links': candidate_links[:8], 'source_cache': page.get('source_cache', str(cache_file) if cache_file.is_file() else None)}
                if len(json.dumps(output)) + len(json.dumps(entry)) > 18000:
                    output['summary_truncated'] = True
                    break
                output['source_summaries'].append(entry)
        print(json.dumps(output))
        return 0
    except (ValueError, OSError, TypeError, KeyError, http.client.HTTPException) as exc:
        print(f'Contact research error: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
