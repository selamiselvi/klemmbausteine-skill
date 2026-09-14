import copy
import hashlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'skills/brick-models/scripts'))
from preflight import check_model
from runtime import find_blender
from setup_runtime import download, package, setup
from guide_language import replace_model_text, translated_model, translation_template
from test_pipeline import small


class FirstRunTests(unittest.TestCase):
    def test_unknown_and_other_model_need_answer(self):
        for name in (None, 'gpt-6', 'gpt-5.6-sol', 'not-astra'):
            self.assertEqual(check_model(name)['status'], 'needs_model_confirmation')
        self.assertEqual(check_model('gpt-6-astra')['status'], 'ready')
        self.assertEqual(check_model(confirmed_astra=True)['evidence'], 'user')
        self.assertEqual(check_model(accept_other=True)['status'], 'ready_with_override')

    def test_portable_discovery_ignores_existing_system_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.dict(os.environ, {'BLENDER_BIN': sys.executable}):
                with self.assertRaises(ValueError):
                    find_blender(root=root, system=False)
                p = root/'blender/blender';p.parent.mkdir();p.touch()
                self.assertEqual(find_blender(root=root, system=False), str(p.resolve()))

    def test_bad_explicit_blender_never_falls_back(self):
        with self.assertRaises(ValueError):
            find_blender('/no-such-brick-models-binary')

    def test_package_platform_mapping_and_unsupported_platform(self):
        self.assertIn('windows-x64.zip', package('Windows','AMD64')[0])
        self.assertIn('windows-arm64.zip', package('Windows','ARM64')[0])
        self.assertIn('macos-arm64.dmg', package('Darwin','arm64')[0])
        self.assertIn('linux-x64.tar.xz', package('Linux','x86_64')[0])
        with self.assertRaises(ValueError):package('Darwin','x86_64')

    def test_download_checksum_rejects_wrong_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)/'source';source.write_bytes(b'archive')
            dest = Path(tmp)/'download'
            download(source.as_uri(),dest,hashlib.sha256(b'archive').hexdigest())
            with self.assertRaisesRegex(ValueError,'checksum'):
                download(source.as_uri(),dest,'0'*64)

    def test_setup_refuses_repository_runtime_before_installing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'.git').mkdir()
            with self.assertRaisesRegex(ValueError,'outside'):
                setup(root/'runtime')


class LanguageTests(unittest.TestCase):
    def test_translation_does_not_mutate_model_or_construction(self):
        m=small();before=copy.deepcopy(m);t=translation_template(m)
        t.update(language='de',title='Turm',description='Ein Turm')
        t['steps'][0]['title']='Grundplatte'
        out=translated_model(m,t)
        self.assertEqual(m,before)
        self.assertEqual(out['parts'],m['parts'])
        self.assertEqual(out['steps'][0]['parts'],m['steps'][0]['parts'])
        self.assertEqual(out['steps'][0]['title'],'Grundplatte')

    def test_partial_translation_never_falls_back_to_english(self):
        for section in ('labels','part_names','color_names'):
            m=small();t=translation_template(m);t[section].pop(next(iter(t[section])))
            with self.assertRaises(ValueError):translated_model(m,t)
        t=translation_template(small());t['steps'].pop()
        with self.assertRaises(ValueError):translated_model(small(),t)

    def test_counts_and_required_notes_cannot_be_lost(self):
        m=small();m['steps'][0]['note']='Keep flat'
        t=translation_template(m);t['steps'][0]['note']=''
        with self.assertRaises(ValueError):translated_model(m,t)
        t=translation_template(m);t['labels']['counts']='Parts only'
        with self.assertRaises(ValueError):translated_model(m,t)

    def test_text_refresh_rejects_geometry_and_camera_changes(self):
        m=small();candidate=copy.deepcopy(m);candidate['title']='New title'
        candidate['steps'][0]['title']='Place the base'
        self.assertEqual(replace_model_text(m,candidate),candidate)
        candidate['parts'][0]['x']=1
        with self.assertRaises(ValueError):replace_model_text(m,candidate)
        candidate=copy.deepcopy(m);candidate['steps'][0]['view']='back-left'
        with self.assertRaises(ValueError):replace_model_text(m,candidate)


if __name__=='__main__':unittest.main()
