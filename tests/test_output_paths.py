import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/brick-models/scripts'))
import brick
from runtime import output_path


class OutputPathTests(unittest.TestCase):
    def test_external_output_is_allowed_without_creating_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'results/model'
            self.assertEqual(output_path(target), target.resolve())
            self.assertFalse(target.exists())

    def test_repositories_and_worktrees_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name, worktree in [('repo', False), ('worktree', True)]:
                repo = Path(tmp) / name
                repo.mkdir()
                if worktree:
                    (repo / '.git').write_text('gitdir: elsewhere')
                else:
                    (repo / '.git').mkdir()
                with self.assertRaisesRegex(ValueError, 'outside'):
                    output_path(repo / 'nested/new/output.zip')

    def test_installed_skill_is_rejected_without_git(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / 'installed-skill'
            script = skill / 'scripts/runtime.py'
            with patch('runtime.__file__', str(script)):
                with self.assertRaisesRegex(ValueError, 'outside'):
                    output_path(skill / 'outputs/model')

    def test_symlink_cannot_bypass_repository_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / 'repo'
            repo.mkdir()
            (repo / '.git').mkdir()
            link = root / 'alias'
            try:
                link.symlink_to(repo, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('Symlink creation unavailable')
            with self.assertRaisesRegex(ValueError, 'outside'):
                output_path(link / 'new/model')

    def test_all_export_commands_fail_before_reading_or_rendering(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / '.git').mkdir()
            args = SimpleNamespace(out=repo / 'output', zip=repo / 'output.zip')
            with patch.object(brick, 'checked_model') as model, patch.object(brick, 'inspect_bundle') as bundle, patch.object(brick, 'blender_path') as blender:
                for command in (brick.build, brick.refresh_guide, brick.localize_guide, brick.pack):
                    with self.subTest(command=command.__name__), self.assertRaisesRegex(ValueError, 'outside'):
                        command(args)
                model.assert_not_called()
                bundle.assert_not_called()
                blender.assert_not_called()


if __name__ == '__main__':
    unittest.main()
