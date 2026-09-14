#!/usr/bin/env python3
"""Resolve host-provided model evidence; this helper cannot inspect the host itself."""
import argparse
import json


def check_model(active_model=None, confirmed_astra=False, accept_other=False):
    known = (active_model or '').strip().lower()
    astra = known in ('gpt-6-astra', 'gpt-6 astra', 'astra')
    if astra or confirmed_astra:
        return {'status': 'ready', 'evidence': 'host' if astra else 'user', 'questions': []}
    if accept_other:
        return {'status': 'ready_with_override', 'evidence': 'user_override', 'questions': []}
    question = (
        'This session uses another model. Please switch to GPT-6 Astra before we design the model. Have you switched?'
        if known else
        'This skill is designed for GPT-6 Astra. I cannot reliably identify the active model here. Is GPT-6 Astra selected?'
    )
    return {'status': 'needs_model_confirmation', 'evidence': 'host' if known else 'unknown',
            'questions': [{'id': 'astra_selected', 'question': question,
                           'options': [{'id': 'yes', 'label': 'Astra is selected'},
                                       {'id': 'switch', 'label': 'I will switch first'}]}]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--active-model', help='Exact current model ID from trusted host session metadata only')
    parser.add_argument('--confirmed-astra', action='store_true', help='Use only after an explicit user answer')
    parser.add_argument('--accept-other', action='store_true', help='Use only when the user explicitly chooses to continue without Astra')
    args = parser.parse_args()
    print(json.dumps(check_model(args.active_model, args.confirmed_astra, args.accept_other), indent=2))


if __name__ == '__main__':
    main()
