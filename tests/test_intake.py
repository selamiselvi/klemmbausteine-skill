import itertools
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/brick-models/scripts'))
from intake import CHOICES, ORDER, resolve


class IntakeTests(unittest.TestCase):
    def test_no_silent_defaults_or_plan_before_answers(self):
        result = resolve({})
        self.assertEqual(result['status'], 'needs_answers')
        self.assertEqual([q['id'] for q in result['questions']], ['mode'])
        self.assertEqual([o['id'] for o in result['questions'][0]['options']], ['auto', 'guided'])
        self.assertEqual(result['answers'], {})
        self.assertEqual(result['assumptions'], {})
        self.assertNotIn('targets', result)

    def test_partial_answers_are_preserved_and_not_asked_again(self):
        result = resolve({'size': 'large', 'experience': 'beginner'}, mode='guided')
        self.assertEqual([q['id'] for q in result['questions']], ['detail'])
        self.assertNotIn('targets', result)
        self.assertEqual(result['answers']['size'], 'large')

    def test_auto_decisions_never_override_explicit_choices(self):
        result = resolve({'size': 'large', 'detail': 'detailed'}, mode='auto', decisions={'size': 'small'})
        self.assertEqual(result['assumptions'], {'experience': 'beginner'})
        self.assertEqual(result['targets']['suggested_part_count'], [900, 1400])
        self.assertEqual(result['targets']['max_new_parts_per_step'], 4)

    def test_all_profiles_fit_engine_limits_and_are_repeatable(self):
        for choices in itertools.product(*(CHOICES[key] for key in ORDER)):
            answers = dict(zip(ORDER, choices))
            a = resolve(answers); b = resolve(answers)
            self.assertEqual(a, b)
            self.assertEqual(a['status'], 'ready')
            self.assertEqual(a['questions'], [])
            self.assertLessEqual(a['targets']['suggested_part_count'][1], 2000)
            self.assertLessEqual(a['targets']['max_new_parts_per_step'], 8)

    def test_experience_does_not_reduce_size_or_detail(self):
        base = {'size': 'large', 'detail': 'detailed'}
        a = resolve(dict(base, experience='beginner'))['targets']
        b = resolve(dict(base, experience='experienced'))['targets']
        self.assertEqual(a['longest_dimension_cm'], b['longest_dimension_cm'])
        self.assertEqual(a['suggested_part_count'], b['suggested_part_count'])
        self.assertLess(a['max_new_parts_per_step'], b['max_new_parts_per_step'])

    def test_question_ids_are_stable_for_agent_translation(self):
        questions = resolve({}, mode='guided')['questions']
        self.assertEqual([q['id'] for q in questions], list(ORDER))
        for q in questions:
            self.assertEqual([o['id'] for o in q['options']], list(CHOICES[q['id']]))

    def test_unknown_choices_are_rejected(self):
        for answers in ({'size': 'huge'}, {'unexpected': 'value'}, {'detail': ''}):
            with self.assertRaises(ValueError):
                resolve(answers)

    def test_auto_mode_waits_for_agent_decisions_not_user_answers(self):
        result = resolve({}, mode='auto')
        self.assertEqual(result['status'], 'needs_agent_choices')
        self.assertEqual(result['questions'], [])
        self.assertEqual(result['missing_choices'], ['size', 'detail'])
        self.assertNotIn('targets', result)

    def test_auto_mode_supports_subject_specific_choices(self):
        result = resolve({}, mode='auto', decisions={'size': 'medium', 'detail': 'balanced'})
        self.assertEqual(result['status'], 'ready')
        self.assertEqual(result['targets']['longest_dimension_cm'], [15, 25])
        self.assertEqual(result['targets']['suggested_part_count'], [220, 450])
        self.assertEqual(result['questions'], [])

    def test_switch_to_auto_preserves_partial_guided_answers(self):
        result = resolve({'size': 'small'}, mode='auto', decisions={'size': 'medium', 'detail': 'detailed'})
        self.assertEqual(result['answers']['size'], 'small')
        self.assertEqual(result['answers']['detail'], 'detailed')
        self.assertNotIn('size', result['assumptions'])
        self.assertEqual(result['status'], 'ready')

    def test_complete_brief_skips_mode_question(self):
        result = resolve(dict(size='small', detail='minimal', experience='experienced'))
        self.assertEqual(result['questions'], [])
        self.assertEqual(result['status'], 'ready')

    def test_agent_decisions_require_auto_mode(self):
        for mode in (None, 'guided', 'unknown'):
            with self.assertRaises(ValueError):
                resolve({}, mode=mode, decisions={'size': 'medium'})


if __name__ == '__main__':
    unittest.main()
