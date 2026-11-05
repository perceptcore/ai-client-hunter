from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT/'skills/ai-client-hunter'


class SkillPackageTests(unittest.TestCase):
    def test_entrypoint_and_local_resource_links(self):
        entrypoint = (SKILL/'SKILL.md').read_text(encoding='utf-8')
        frontmatter = re.match(r'^---\n(.*?)\n---\n', entrypoint, re.S)
        self.assertIsNotNone(frontmatter)
        self.assertIn('name: ' + SKILL.name, frontmatter[1])
        self.assertRegex(frontmatter[1], r'(?m)^description: .+')
        for file in [SKILL/'SKILL.md', *SKILL.glob('references/*.md')]:
            for target in re.findall(r'\]\(([^)]+)\)', file.read_text(encoding='utf-8')):
                if not re.match(r'^(https?://|mailto:|#)', target):
                    resolved = (file.parent/target.split('#')[0]).resolve()
                    self.assertTrue(resolved.is_relative_to(SKILL.resolve()), (file, target))
                    self.assertTrue(resolved.is_file(), (file, target))

    def test_no_absolute_private_paths_or_runtime_external_dependencies(self):
        for script in SKILL.glob('scripts/*.py'):
            code = script.read_text(encoding='utf-8')
            self.assertNotIn('C:\\Users\\', code)
            self.assertNotIn('/root/projects/', code)
        names = [p.parent.name for p in ROOT.rglob('SKILL.md')]
        self.assertEqual(names, ['ai-client-hunter'])


if __name__ == '__main__':
    unittest.main()
