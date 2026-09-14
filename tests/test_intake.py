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
        self.assertEqual([q['id'] for q in result['questions']], list(ORDER))
        self.assertEqual(result['answers'], {})
        self.assertEqual(result['assumptions'], {})
        self.assertNotIn('targets', result)

    def test_partial_answers_are_preserved_and_not_asked_again(self):
        result = resolve({'size': 'large', 'experience': 'beginner'})
        self.assertEqual([q['id'] for q in result['questions']], ['detail'])
        self.assertNotIn('targets', result)
        self.assertEqual(result['answers']['size'], 'large')

    def test_delegated_defaults_never_override_explicit_choices(self):
        result = resolve({'size': 'large', 'detail': 'detailed'}, use_defaults=True)
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

    def test_languages_preserve_question_and_option_meanings(self):
        for language in ('de', 'en'):
            questions = resolve({}, language)['questions']
            for q in questions:
                self.assertEqual([o['id'] for o in q['options']], list(CHOICES[q['id']]))
        answers = dict(size='small', detail='minimal', experience='beginner')
        self.assertEqual(resolve(answers, 'de')['targets'], resolve(answers, 'en')['targets'])

    def test_unknown_choices_are_rejected(self):
        for answers in ({'size': 'huge'}, {'unexpected': 'value'}, {'detail': ''}):
            with self.assertRaises(ValueError):
                resolve(answers)


if __name__ == '__main__':
    unittest.main()
