#!/usr/bin/env python3
"""Return unanswered intake questions or deterministic design targets. No file writes."""
import argparse
import json

ORDER = ('size', 'detail', 'experience')
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
        'mode': ('Wie möchtest du starten?', [
            ('Direkt loslegen', 'Du entscheidest passend zu meinem Motiv.'),
            ('Gemeinsam festlegen', 'Ich wähle Größe, Details und Bauschritte selbst.'),
        ]),
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
        'mode': ('How would you like to start?', [
            ('Start right away', 'Choose what suits my subject.'),
            ('Choose together', 'Let me choose size, detail and building steps.'),
        ]),
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


def resolve(answers, language='en', mode=None, decisions=None):
    if language not in COPY:
        raise ValueError('Unsupported question language')
    if mode not in (None, 'auto', 'guided'):
        raise ValueError('Unknown intake mode')
    decisions = {} if decisions is None else decisions
    if decisions and mode != 'auto':
        raise ValueError('Agent choices require auto mode')
    for values in (answers, decisions):
        if set(values) - set(ORDER):
            raise ValueError('Unknown intake field')
        for key, value in values.items():
            if value is not None and value not in CHOICES[key]:
                raise ValueError(f'Unknown choice for {key}')
    selected = {key: value for key, value in answers.items() if value is not None}
    assumed = {}
    if mode == 'auto':
        assumed = {key: value for key, value in decisions.items() if value is not None and key not in selected}
        # Clear instructions are a presentation choice, not a claim about the user's experience.
        if 'experience' not in selected and 'experience' not in assumed:
            assumed['experience'] = 'beginner'
        selected.update(assumed)
    missing = [key for key in ORDER if key not in selected]
    questions = []
    question_keys = ['mode'] if missing and mode is None else (missing if mode == 'guided' else [])
    for key in question_keys:
        title, labels = COPY[language][key]
        questions.append(dict(id=key, question=title, options=[
            dict(id=choice, label=label, description=description)
            for choice, (label, description) in zip(('auto', 'guided') if key == 'mode' else CHOICES[key], labels)
        ]))
    status = 'needs_answers' if questions else ('needs_agent_choices' if missing else 'ready')
    result = dict(schema_version='1.1', mode=mode, status=status,
                  answers=selected, assumptions=assumed, questions=questions)
    if mode == 'auto' and missing:
        result['missing_choices'] = missing
    if not missing:
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
    parser.add_argument('--mode', choices=('auto', 'guided'))
    for key in ORDER:
        parser.add_argument('--' + key, choices=CHOICES[key])
        parser.add_argument('--choose-' + key, choices=CHOICES[key], help='Agent decision in auto mode')
    args = parser.parse_args()
    try:
        result = resolve({key: getattr(args, key) for key in ORDER}, args.language, args.mode,
                         {key: getattr(args, 'choose_' + key) for key in ORDER if getattr(args, 'choose_' + key) is not None})
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
