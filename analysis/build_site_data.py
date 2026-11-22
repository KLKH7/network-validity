"""Collect the per-condition score files into one file the results page reads.

    python analysis/build_site_data.py

Reads results/<condition>.json (written by score.py) and writes site/results.js.
Only aggregate figures are included: no student-level answers leave the machine.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONDITIONS = [
    ('baseline', 'One student at a time', 'Each simulated student is described by gender, race and home region, and answers alone.'),
    ('friends_r1', 'Shown friends’ answers, round 1', 'Each simulated student also sees what their friends answered in the baseline run.'),
    ('friends_r2', 'Shown friends’ answers, round 2', 'The same again, using the answers from round 1.'),
]
QUESTIONS = {
    'usewine_2': 'Drank wine or liquor',
    'usebeer_2': 'Drank beer',
    'polparty_1_2': 'Political party',
    'gaymarriage_2': 'Same-sex marriage',
    'marijuana_2': 'Legalising marijuana',
}


def main():
    conditions = []
    for key, label, note in CONDITIONS:
        path = ROOT / 'results' / f'{key}.json'
        if not path.exists():
            continue
        data = json.loads(path.read_text())
        conditions.append({'key': key, 'label': label, 'note': note, 'model': data['model'],
                           'items': {row['item']: row for row in data['items']}})
    if not conditions:
        raise SystemExit('No score files in results/')
    out = {'questions': QUESTIONS, 'conditions': conditions,
           'friend_pairs_total': json.loads((ROOT / 'results' / 'baseline.json').read_text())['friend_pairs_total']}
    (ROOT / 'site' / 'results.js').write_text('window.RESULTS = ' + json.dumps(out, indent=1) + ';\n')
    print('conditions:', [c['key'] for c in conditions])


if __name__ == '__main__':
    main()
