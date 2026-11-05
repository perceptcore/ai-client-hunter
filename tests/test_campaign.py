import copy
import csv
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills' / 'ai-client-hunter'
sys.path.insert(0, str(SKILL / 'scripts'))
from prepare_campaign import (company_suppressed, contact_suppressed, domain,
                              draft_state, normalize, save_campaign, web_url)
from export_campaign import csv_safe, render


class CampaignTests(unittest.TestCase):
    def setUp(self):
        self.raw = json.loads((SKILL / 'assets/synthetic-campaign/data.json').read_text(encoding='utf-8'))
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)

    def run_cli(self, script, *args):
        return subprocess.run([sys.executable, str(SKILL / 'scripts' / script), *map(str, args)],
                              capture_output=True, encoding='utf-8')

    def test_all_four_artifacts_and_review_status(self):
        d = normalize(self.raw)
        out = render(d)
        self.assertEqual(set(out), {'prospects.csv', 'contacts.csv', 'account-briefs.md', 'outreach.md'})
        self.assertEqual(draft_state(d, d['drafts'][0])[0], 'review_ready')
        self.assertIn('Human review required', out['outreach.md'])
        self.assertIn('unverified', out['contacts.csv'])

    def test_normalization_is_idempotent_and_preserves_input(self):
        original = copy.deepcopy(self.raw)
        d = normalize(self.raw)
        self.assertEqual(normalize(d), d)
        self.assertEqual(self.raw, original)

    def test_domain_variants_and_idna(self):
        self.assertEqual(domain('HTTPS://WWW.Example.test/pricing?x=1'), 'example.test')
        self.assertEqual(domain('bücher.test'), 'xn--bcher-kva.test')
        for invalid in ('http://127.0.0.1/', 'https://user:password@example.test/',
                        'file:///etc/passwd', 'https://example.test:8080/'):
            with self.assertRaises(ValueError):
                web_url(invalid)

    def test_domain_dedup_remaps_evidence_and_contacts(self):
        duplicate = copy.deepcopy(self.raw['companies'][0])
        duplicate['id'] = 'northstar-alias'
        duplicate['website'] = 'https://www.northstar-scheduling.test/pricing'
        self.raw['companies'].append(duplicate)
        self.raw['contacts'][0]['company_id'] = 'northstar-alias'
        d = normalize(self.raw)
        self.assertEqual(len(d['companies']), 3)
        self.assertEqual(d['contacts'][0]['company_id'], 'northstar')

    def test_conflicting_duplicate_does_not_discard_research(self):
        duplicate = copy.deepcopy(self.raw['companies'][0])
        duplicate.update(id='alias', qualification='excluded')
        self.raw['companies'].append(duplicate)
        with self.assertRaisesRegex(ValueError, 'Conflicting duplicate domain'):
            normalize(self.raw)

    def test_email_dedup_remaps_draft_and_preserves_original_spelling(self):
        duplicate = copy.deepcopy(self.raw['contacts'][0])
        duplicate.update(id='duplicate', email='HELLO@NORTHSTAR-SCHEDULING.TEST')
        self.raw['contacts'].append(duplicate)
        self.raw['drafts'][0]['contact_id'] = 'duplicate'
        d = normalize(self.raw)
        self.assertEqual(len(d['contacts']), 1)
        self.assertEqual(d['drafts'][0]['contact_id'], 'northstar-inbox')
        self.assertEqual(d['contacts'][0]['email'], 'hello@northstar-scheduling.test')

    def test_conflicting_email_association_fails(self):
        duplicate = copy.deepcopy(self.raw['contacts'][0])
        duplicate.update(id='other', company_id='harbor')
        self.raw['contacts'].append(duplicate)
        with self.assertRaisesRegex(ValueError, 'Conflicting duplicate email'):
            normalize(self.raw)

    def test_domain_suppression_withholds_recipient_and_message(self):
        self.raw['suppression']['domains'] = ['northstar-scheduling.test']
        d = normalize(self.raw)
        self.assertTrue(company_suppressed(d, d['companies'][0]))
        out = render(d)
        self.assertNotIn('hello@northstar', out['contacts.csv'])
        self.assertNotIn(self.raw['drafts'][0]['body'], out['outreach.md'])
        self.assertIn('suppressed', out['outreach.md'])

    def test_email_and_email_domain_suppression(self):
        for suppression in ({'domains': [], 'emails': ['HELLO@NORTHSTAR-SCHEDULING.TEST']},
                            {'domains': ['northstar-scheduling.test'], 'emails': []}):
            self.raw['suppression'] = suppression
            self.raw['companies'][0]['website'] = 'https://other-brand.test/'
            d = normalize(self.raw)
            self.assertTrue(contact_suppressed(d, d['contacts'][0]))
            self.assertEqual(draft_state(d, d['drafts'][0])[0], 'suppressed')

    def test_subdomain_suppression_does_not_match_lookalike(self):
        self.raw['suppression']['domains'] = ['scheduling.test']
        self.raw['companies'][0]['website'] = 'https://team.scheduling.test/'
        d = normalize(self.raw)
        self.assertTrue(company_suppressed(d, d['companies'][0]))
        d['companies'][0]['domain'] = 'notscheduling.test'
        self.assertFalse(company_suppressed(d, d['companies'][0]))

    def test_missing_email_keeps_review_draft_without_inference(self):
        self.raw['contacts'][0].update(email=None, email_status='not_found')
        d = normalize(self.raw)
        self.assertEqual(draft_state(d, d['drafts'][0])[0], 'needs_contact')
        self.assertIn('Recipient: Not found', render(d)['outreach.md'])
        self.assertNotIn('hello@northstar', render(d)['contacts.csv'])

    def test_unqualified_or_conflicting_outreach_is_held(self):
        for qualification in ('review', 'excluded'):
            self.raw['companies'][0]['qualification'] = qualification
            d = normalize(self.raw)
            self.assertEqual(draft_state(d, d['drafts'][0])[0], 'held')
            self.assertNotIn(self.raw['drafts'][0]['body'], render(d)['outreach.md'])
        self.raw['companies'][0]['qualification'] = 'qualified'
        self.raw['evidence'][0]['status'] = 'conflicting'
        d = normalize(self.raw)
        self.assertEqual(draft_state(d, d['drafts'][0])[0], 'held')

    def test_missing_source_and_cross_account_links_fail(self):
        for mutation in ('missing', 'cross'):
            raw = copy.deepcopy(self.raw)
            if mutation == 'missing':
                raw['evidence'][0].pop('url')
            else:
                raw['drafts'][0]['evidence_ids'] = ['harbor-product']
            with self.assertRaises(ValueError):
                normalize(raw)

    def test_unrelated_conflict_does_not_block_website_based_draft(self):
        self.raw['evidence'].append({'id': 'unrelated', 'company_id': 'northstar',
                                    'kind': 'business', 'finding': 'Separate unresolved question',
                                    'url': 'https://northstar-scheduling.test/other',
                                    'observed_at': '2026-11-06', 'status': 'conflicting'})
        self.raw['companies'][0]['evidence_ids'].append('unrelated')
        self.raw['contacts'][0].update(email=None, email_status='not_found')
        d = normalize(self.raw)
        self.assertEqual(draft_state(d, d['drafts'][0])[0], 'needs_contact')
        self.assertIn(self.raw['drafts'][0]['body'], render(d)['outreach.md'])

    def test_contact_export_shows_qualification_for_excluded_account(self):
        self.raw['contacts'][0]['company_id'] = 'birch'
        self.raw['drafts'] = []
        rows = list(csv.DictReader(io.StringIO(render(normalize(self.raw))['contacts.csv'])))
        self.assertEqual(rows[0]['qualification'], 'excluded')

    def test_ai_metadata_unknown_is_preserved_and_holds_outreach(self):
        self.raw['ai_observations'] = [{'id': 'ai-one', 'company_id': 'northstar',
                                      'prompt': 'Which product fits this buyer?',
                                      'response': 'Original supplied answer.', 'origin': 'user_provided'}]
        self.raw['evidence'].append({'id': 'ai-finding', 'company_id': 'northstar',
                                    'kind': 'ai_answer', 'finding': 'One supplied observation.',
                                    'ai_observation_id': 'ai-one'})
        self.raw['drafts'][0]['evidence_ids'].append('ai-finding')
        d = normalize(self.raw)
        self.assertIsNone(d['ai_observations'][0]['provider'])
        self.assertEqual(draft_state(d, d['drafts'][0])[0], 'held')
        self.assertIn('provider: unknown', render(d)['account-briefs.md'])
        self.raw['ai_observations'][0].update(provider='Test provider', model='Test model', collected_at='2026-11-06')
        d = normalize(self.raw)
        self.assertEqual(draft_state(d, d['drafts'][0])[0], 'review_ready')

    def test_ai_evidence_requires_original_answer(self):
        self.raw['evidence'][0].update(kind='ai_answer', ai_observation_id='invented')
        with self.assertRaisesRegex(ValueError, 'matching raw AI observation'):
            normalize(self.raw)

    def test_csv_formula_neutralization_and_quoted_unicode(self):
        for value in ('=1+1', ' +SUM(A1:A2)', '-1+2', '@cmd', '\t=1', '\n=1', '\r=1'):
            self.assertTrue(csv_safe(value).startswith("'"))
        self.raw['companies'][0]['name'] = '=HYPERLINK("https://example.test"), Tiếng Việt'
        d = normalize(self.raw)
        rows = list(csv.DictReader(io.StringIO(render(d)['prospects.csv'])))
        self.assertTrue(rows[0]['name'].startswith("'="))
        self.assertIn('Tiếng Việt', rows[0]['name'])
        self.assertTrue(d['companies'][0]['name'].startswith('='))

    def test_markdown_answer_and_draft_cannot_break_text_fence(self):
        self.raw['drafts'][0]['body'] = '```\n<script>alert(1)</script>\n![x](https://tracker.test)'
        out = render(normalize(self.raw))['outreach.md']
        self.assertIn('````text\n```', out)
        self.assertIn('![x]', out)  # Preserved inside the longer text fence.

    def test_initialize_import_resume_and_no_clobber(self):
        campaign = self.work / 'campaign'
        result = self.run_cli('prepare_campaign.py', 'init', '--campaign', campaign,
                              '--brief', SKILL/'assets/brief.json', '--websites', SKILL/'assets/websites.csv')
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads((campaign/'data.json').read_text())
        data['companies'][0].update(research_status='complete', reason='No supported contact found')
        save_campaign(campaign, normalize(data))
        before = (campaign/'data.json').read_bytes()
        result = self.run_cli('prepare_campaign.py', 'init', '--campaign', campaign, '--brief', SKILL/'assets/brief.json')
        self.assertEqual(result.returncode, 2)
        self.assertEqual(before, (campaign/'data.json').read_bytes())
        seeds = self.work/'more.csv'
        seeds.write_text('name,website\nNorthstar Scheduling,https://www.northstar-scheduling.test/a\nNew Account,new-account.test\n', encoding='utf-8')
        result = self.run_cli('prepare_campaign.py', 'import', '--campaign', campaign, '--websites', seeds)
        self.assertEqual(result.returncode, 0, result.stderr)
        state = json.loads((campaign/'data.json').read_text())
        self.assertEqual(len(state['companies']), 4)
        self.assertEqual(state['companies'][0]['reason'], 'No supported contact found')
        checkpoint = json.loads((campaign/'checkpoint.json').read_text())
        self.assertEqual(checkpoint['completed_company_ids'], [state['companies'][0]['id']])
        self.assertEqual(len(checkpoint['remaining_company_ids']), 3)
        (campaign/'checkpoint.json').unlink()
        result = self.run_cli('prepare_campaign.py', 'check', '--campaign', campaign)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((campaign/'checkpoint.json').exists())

    def test_invalid_data_does_not_overwrite_campaign_or_exports(self):
        campaign = self.work/'campaign'
        save_campaign(campaign, normalize(self.raw))
        result = self.run_cli('export_campaign.py', '--campaign', campaign)
        self.assertEqual(result.returncode, 0, result.stderr)
        before_export = (campaign/'exports/outreach.md').read_bytes()
        self.raw['evidence'][0]['url'] = 'not a source'
        (campaign/'data.json').write_text(json.dumps(self.raw), encoding='utf-8')
        before_data = (campaign/'data.json').read_bytes()
        for script, args in [('prepare_campaign.py', ['check']), ('export_campaign.py', [])]:
            result = self.run_cli(script, *args, '--campaign', campaign)
            self.assertEqual(result.returncode, 2)
        self.assertEqual(before_data, (campaign/'data.json').read_bytes())
        self.assertEqual(before_export, (campaign/'exports/outreach.md').read_bytes())

    def test_check_only_does_not_write_and_suppression_csv_merges(self):
        campaign = self.work/'campaign'
        save_campaign(campaign, normalize(self.raw))
        before = {p.name: p.read_bytes() for p in campaign.iterdir()}
        result = self.run_cli('prepare_campaign.py', 'check', '--campaign', campaign, '--check-only')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(before, {p.name: p.read_bytes() for p in campaign.iterdir()})
        suppression = self.work/'suppression.csv'
        suppression.write_text('domain,email\n,HELLO@NORTHSTAR-SCHEDULING.TEST\nharbor-operations.test,\n', encoding='utf-8')
        result = self.run_cli('prepare_campaign.py', 'check', '--campaign', campaign, '--suppression', suppression)
        self.assertEqual(result.returncode, 0, result.stderr)
        d = normalize(json.loads((campaign/'data.json').read_text()))
        self.assertEqual(draft_state(d, d['drafts'][0])[0], 'suppressed')
        self.assertTrue(company_suppressed(d, d['companies'][1]))

    def test_isolated_skill_copy_runs_without_checkout_dependencies(self):
        import shutil
        isolated = self.work/'installed-skill'
        shutil.copytree(SKILL, isolated, ignore=shutil.ignore_patterns('__pycache__'))
        result = subprocess.run([sys.executable, str(isolated/'scripts/export_campaign.py'),
                                 '--campaign', str(isolated/'assets/synthetic-campaign'),
                                 '--out', str(self.work/'isolated-exports')],
                                capture_output=True, encoding='utf-8', cwd=self.work)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(list((self.work/'isolated-exports').iterdir())), 4)

    def test_unicode_campaign_directory_and_saved_records(self):
        campaign = self.work/'Tiếng Việt'
        self.raw['companies'][0]['name'] = 'Lịch Việt'
        save_campaign(campaign, normalize(self.raw))
        result = self.run_cli('export_campaign.py', '--campaign', campaign)
        self.assertEqual(result.returncode, 0, result.stderr)
        with (campaign/'exports/prospects.csv').open(encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(rows[0]['name'], 'Lịch Việt')


if __name__ == '__main__':
    unittest.main()
