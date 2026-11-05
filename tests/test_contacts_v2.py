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
SKILL = ROOT/'skills/ai-client-hunter'
sys.path.insert(0, str(SKILL/'scripts'))
from contact_models import migrate_v1, person_route, selected_contacts
from prepare_campaign import contact_suppressed, normalize, save_campaign
from export_campaign import render


class ContactV2Tests(unittest.TestCase):
    def setUp(self):
        self.raw = json.loads((SKILL/'assets/decision-maker-campaign/data.json').read_text(encoding='utf-8'))
        self.person = self.raw['contacts'][1]
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)

    def test_profile_is_a_person_route_without_an_email(self):
        d = normalize(self.raw)
        contact = d['contacts'][1]
        self.assertIsNone(contact['email'])
        self.assertEqual(person_route(contact)['type'], 'professional_profile')
        result = render(d)
        self.assertEqual(len(result), 6)
        rows = list(csv.DictReader(io.StringIO(result['decision-makers.csv'])))
        self.assertEqual([r['name'] for r in rows], ['Jo Ellis'])
        self.assertIn('https://profiles.test/jo-ellis', result['outreach.md'])
        self.assertNotIn('Other record: Jo Ellis', result['contact-research.md'])

    def test_historical_and_generic_records_do_not_count(self):
        d = normalize(self.raw)
        self.assertIsNone(person_route(d['contacts'][0]))
        self.assertIsNone(person_route(d['contacts'][2]))
        self.assertEqual(len(selected_contacts(d, contact_suppressed)), 1)
        self.person['identity_status'] = 'candidate'
        d = normalize(self.raw)
        self.assertFalse(selected_contacts(d, contact_suppressed))

    def test_current_identity_needs_role_and_person_in_excerpt(self):
        for field in ('name', 'role'):
            raw = copy.deepcopy(self.raw)
            raw['contacts'][1]['role_evidence'][0]['excerpt'] = 'Jo Ellis leads the team' if field == 'role' else 'The Head of Marketing leads the team'
            with self.assertRaisesRegex(ValueError, 'official named-role source'):
                normalize(raw)

    def test_old_role_cannot_be_promoted_to_supported(self):
        self.person['role_evidence'][0]['is_current'] = False
        with self.assertRaises(ValueError):
            normalize(self.raw)

    def test_unrelated_domain_is_not_an_official_source(self):
        self.person['role_evidence'][0]['url'] = 'https://parent-brand.test/team'
        with self.assertRaisesRegex(ValueError, 'company domain'):
            normalize(self.raw)

    def test_two_external_hosts_corroborate_but_two_same_host_pages_do_not(self):
        first = self.person['role_evidence'][0]
        first.update(source_type='external', url='https://profile.test/jo')
        second = copy.deepcopy(first)
        second['url'] = 'https://conference.test/speakers/jo'
        self.person['role_evidence'].append(second)
        self.assertEqual(normalize(self.raw)['contacts'][1]['identity_status'], 'supported')
        second['url'] = 'https://profile.test/jo/about'
        with self.assertRaises(ValueError):
            normalize(self.raw)

    def test_channel_requires_explicit_person_and_email_attribution(self):
        self.person['channels'][0]['excerpt'] = 'Visit our company profile'
        with self.assertRaisesRegex(ValueError, 'named person'):
            normalize(self.raw)
        self.person['channels'] = [{'type': 'email', 'value': 'jo@northstar-scheduling.test',
                                   'source_url': self.person['source_url'],
                                   'excerpt': 'Jo Ellis is Head of Marketing.', 'observed_at': '2026-11-06',
                                   'status': 'observed', 'attribution': 'person'}]
        with self.assertRaisesRegex(ValueError, 'verbatim'):
            normalize(self.raw)

    def test_generic_email_and_company_form_cannot_be_person_success(self):
        self.person.update(email='support@northstar-scheduling.test', email_status='publicly_listed')
        with self.assertRaisesRegex(ValueError, 'Generic/system'):
            normalize(self.raw)
        self.person.update(email=None, email_status='not_found')
        self.person['channels'][0].update(type='company_form', attribution='company', value='https://northstar-scheduling.test/contact')
        d = normalize(self.raw)
        self.assertIsNone(person_route(d['contacts'][1]))
        self.assertFalse(selected_contacts(d, contact_suppressed))

    def test_unknown_profile_root_and_unmatched_role_not_selected(self):
        self.person['channels'][0]['value'] = 'https://profiles.test/'
        with self.assertRaisesRegex(ValueError, 'person-specific'):
            normalize(self.raw)
        self.person['channels'][0]['value'] = 'https://profiles.test/jo'
        self.person['role_fit'] = 'unmatched'
        d = normalize(self.raw)
        self.assertFalse(selected_contacts(d, contact_suppressed))

    def test_suppression_applies_to_secondary_person_email(self):
        self.person['channels'].append({'type': 'email', 'value': 'jo@northstar-scheduling.test',
                                       'source_url': self.person['source_url'],
                                       'excerpt': 'Jo Ellis: jo@northstar-scheduling.test', 'observed_at': '2026-11-06',
                                       'status': 'observed', 'attribution': 'person'})
        self.raw['suppression']['emails'] = ['JO@NORTHSTAR-SCHEDULING.TEST']
        d = normalize(self.raw)
        self.assertTrue(contact_suppressed(d, d['contacts'][1]))
        self.assertFalse(selected_contacts(d, contact_suppressed))
        self.assertNotIn('Jo Ellis', render(d)['decision-makers.csv'])

    def test_top_three_explained_contacts_only(self):
        for number in range(4):
            c = copy.deepcopy(self.person)
            c['id'] = f'person-{number}'
            c['name'] = f'Person {number}'
            c['role_evidence'][0]['excerpt'] = f'Person {number} is Head of Marketing.'
            c['channels'][0]['excerpt'] = f'Person {number} professional profile'
            c['channels'][0]['value'] = f'https://profiles.test/person-{number}'
            self.raw['contacts'].append(c)
        d = normalize(self.raw)
        self.assertEqual(len(selected_contacts(d, contact_suppressed)), 3)

    def test_v1_migration_preserves_data_and_backups_exact_bytes(self):
        old = json.loads((SKILL/'assets/synthetic-campaign/data.json').read_text(encoding='utf-8'))
        original = ('\ufeff' + json.dumps(old, ensure_ascii=False, indent=1)).encode('utf-8')
        (self.folder/'data.json').write_bytes(original)
        command = [sys.executable, str(SKILL/'scripts/prepare_campaign.py'), 'migrate', '--campaign', str(self.folder)]
        result = subprocess.run(command, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.folder/'data.v1.backup.json').read_bytes(), original)
        migrated = normalize(json.loads((self.folder/'data.json').read_text(encoding='utf-8')))
        self.assertEqual(migrated['companies'], normalize(old)['companies'])
        self.assertEqual(migrated['drafts'], old['drafts'])
        self.assertEqual(migrated['suppression'], old['suppression'])
        self.assertEqual(migrated['contacts'][0]['identity_status'], 'legacy_unverified')
        self.assertFalse(selected_contacts(migrated, contact_suppressed))
        result = subprocess.run(command, capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual((self.folder/'data.v1.backup.json').read_bytes(), original)

    def test_v1_still_exports_four_files_and_v2_six(self):
        old = json.loads((SKILL/'assets/synthetic-campaign/data.json').read_text(encoding='utf-8'))
        self.assertEqual(len(render(normalize(old))), 4)
        self.assertEqual(len(render(normalize(migrate_v1(old)))), 6)
        self.assertEqual(save_campaign(self.folder, normalize(old))['schema_version'], 1)
        self.assertEqual(save_campaign(self.folder, normalize(migrate_v1(old)))['schema_version'], 2)


if __name__ == '__main__':
    unittest.main()
