#!/usr/bin/env python3
"""Return unanswered intake questions or deterministic design targets. No file writes."""
import argparse
import json

ORDER = ('size', 'detail', 'experience')
DEFAULTS = dict(size='small', detail='balanced', experience='beginner')
SIZE_CM = {'small': [8, 15], 'medium': [15, 25], 'large': [25, 40]}
PART_RANGES = {
    'small': {'minimal': [40, 80], 'balanced': [80, 160], 'detailed': [160, 280]},
    'medium': {'minimal': [120, 220], 'balanced': [220, 450], 'detailed': [450, 700]},
    'large': {'minimal': [300, 500], 'balanced': [500, 900], 'detailed': [900, 1400]},
}
DETAIL_GUIDANCE = {
    'minimal': 'Prioritize the silhouette and the few features that identify the subject.',
    'balanced': 'Preserve the silhouette and add the main recognizable features.',
    'detailed': 'Add secondary features and surface accents within the supported part catalog.',
}
STEP_LIMITS = {'beginner': 4, 'familiar': 6, 'experienced': 8}
CHOICES = {
    'size': tuple(SIZE_CM),
    'detail': tuple(DETAIL_GUIDANCE),
    'experience': tuple(STEP_LIMITS),
}
COPY = {
    'de': {
        'size': ('Wie groß soll dein Modell ungefähr werden?', [
            ('Klein', 'Ungefähr handgroß; längste Seite etwa 8–15 cm.'),
            ('Mittel', 'Ein Modell fürs Regal; längste Seite etwa 15–25 cm.'),
            ('Groß', 'Ein größeres Schaustück; längste Seite etwa 25–40 cm.'),
        ]),
        'detail': ('Wie detailreich möchtest du es haben?', [
            ('Schlicht', 'Wenige Formen, auf das Wesentliche reduziert.'),
            ('Ausgewogen', 'Gut erkennbar, mit den wichtigsten Details.'),
            ('Viele Details', 'Mehr kleine Merkmale und mehr Teile zum Bauen.'),
        ]),
        'experience': ('Wie viel Erfahrung hast du mit Klemmbausteinen?', [
            ('Kaum oder keine', 'Besonders übersichtliche, kleine Bauschritte.'),
            ('Schon etwas', 'Normale Schrittgrößen mit gezielten Hilfen.'),
            ('Viel Erfahrung', 'Kompaktere Schritte sind für mich in Ordnung.'),
        ]),
    },
    'en': {
        'size': ('Roughly how big would you like your model to be?', [
            ('Small', 'About hand-sized; longest dimension around 8–15 cm.'),
            ('Medium', 'A shelf model; longest dimension around 15–25 cm.'),
            ('Large', 'A larger display piece; longest dimension around 25–40 cm.'),
        ]),
        'detail': ('How much detail would you like?', [
            ('Minimal', 'A few simple shapes capturing the essentials.'),
            ('Balanced', 'Recognizable, with the main distinctive details.'),
            ('Lots of detail', 'More small features and more pieces to assemble.'),
        ]),
        'experience': ('How much experience do you have with building bricks?', [
            ('Little or none', 'Especially clear, small building steps.'),
            ('Some experience', 'Regular steps with help where it matters.'),
            ('Experienced', 'I am comfortable with more compact steps.'),
        ]),
    },
}


def resolve(answers, language='en', use_defaults=False):
    if language not in COPY:
        raise ValueError('Unsupported question language')
    if set(answers) - set(ORDER):
        raise ValueError('Unknown intake field')
    selected = {key: value for key, value in answers.items() if value is not None}
    for key, value in selected.items():
        if value not in CHOICES[key]:
            raise ValueError(f'Unknown choice for {key}')
    assumed = {}
    if use_defaults:
        assumed = {key: DEFAULTS[key] for key in ORDER if key not in selected}
        selected.update(assumed)
    questions = []
    for key in ORDER:
        if key in selected:
            continue
        title, labels = COPY[language][key]
        questions.append(dict(id=key, question=title, options=[
            dict(id=choice, label=label, description=description)
            for choice, (label, description) in zip(CHOICES[key], labels)
        ]))
    result = dict(schema_version='1.0', status='needs_answers' if questions else 'ready',
                  answers=selected, assumptions=assumed, questions=questions)
    if not questions:
        size, detail, experience = (selected[key] for key in ORDER)
        result['targets'] = dict(
            longest_dimension_cm=SIZE_CM[size][:],
            suggested_part_count=PART_RANGES[size][detail][:],
            max_new_parts_per_step=STEP_LIMITS[experience],
            detail_guidance=DETAIL_GUIDANCE[detail],
            dimensions_and_part_count_are_estimates=True,
        )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--language', choices=tuple(COPY), default='en')
    for key in ORDER:
        parser.add_argument('--' + key, choices=CHOICES[key])
    parser.add_argument('--defaults', action='store_true', help='Only after the user delegates unanswered choices')
    args = parser.parse_args()
    print(json.dumps(resolve({key: getattr(args, key) for key in ORDER}, args.language, args.defaults),
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
