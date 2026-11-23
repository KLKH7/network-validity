"""Score the control runs that test what "showing friends' answers" actually does.

    python analysis/score_controls.py DATA_FOLDER ANSWERS_FOLDER results/controls.json

ANSWERS_FOLDER holds the answer files written by simulate_claude.py:
the one-at-a-time run, the friends run, and the three --control runs.
Only aggregate figures are written.
"""
import collections
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from simulate_claude import ITEMS, PROFILE, roster

STEM = 'answers_claude-haiku-5-5'
FILES = {'alone': '', 'friends': '_friends-r1', 'strangers': '_control-strangers',
         'anchor': '_control-anchor', 'dose': '_control-dose'}


def load(folder, suffix):
    rows = [json.loads(line) for line in (Path(folder) / f'{STEM}{suffix}.jsonl').read_text().splitlines()]
    rows = [r for r in rows if r['answer']]
    return {(r['egoid'], r['item']): r for r in rows}


def plurality(answers):
    """The most common answer, or None when there is a tie for first place."""
    counts = collections.Counter(answers).most_common()
    if not counts or (len(counts) > 1 and counts[0][1] == counts[1][1]):
        return None
    return counts[0][0]


def any_two(answers):
    counts = collections.Counter(answers).values()
    n = sum(counts)
    return sum(c * (c - 1) for c in counts) / (n * (n - 1))


def main():
    data, folder, out = sys.argv[1:4]
    basic, students, ties = roster(data)
    students = [int(s) for s in students]
    runs = {name: load(folder, suffix) for name, suffix in FILES.items()}
    alone = {key: row['answer'] for key, row in runs['alone'].items()}
    profile = basic.loc[students, [c for c, _ in PROFILE]].astype(str).agg('|'.join, axis=1)
    profile = dict(zip(students, profile))
    cell = collections.defaultdict(list)
    for student, p in profile.items():
        cell[p].append(student)
    pairs = sorted({(min(a, b), max(a, b)) for a in ties for b in ties[a]})

    def fresh(student, item, option):
        """Chance that a no-friends answer for this profile equals `option`."""
        others = [alone[(o, item)] for o in cell[profile[student]] if o != student and (o, item) in alone]
        return np.mean([a == option for a in others]) if len(others) >= 5 else None

    result = {'model': 'claude-haiku-5-5', 'exposure': {}, 'dose': []}
    for name in ['alone', 'friends', 'strangers', 'anchor']:
        answer = {key: row['answer'] for key, row in runs[name].items()}
        everyone, friends = [], []
        for item in ITEMS:
            everyone.append(any_two([answer[(s, item)] for s in students if (s, item) in answer]))
            both = [(a, b) for a, b in pairs if (a, item) in answer and (b, item) in answer]
            friends.append(np.mean([answer[(a, item)] == answer[(b, item)] for a, b in both]))
        row = {'any_two_agree': np.mean(everyone), 'friend_pairs_agree': np.mean(friends),
               'friend_excess': np.mean(friends) - np.mean(everyone)}
        if name != 'alone':
            tally = collections.defaultdict(list)
            for (student, item), record in runs[name].items():
                if (student, item) not in alone:
                    continue
                shown = plurality(record.get('shown') or
                                  [alone[(f, item)] for f in ties[student] if (f, item) in alone])
                real_friends = plurality([alone[(f, item)] for f in ties[student] if (f, item) in alone])
                earlier = alone[(student, item)]
                if shown:
                    expected = fresh(student, item, shown)
                    if expected is not None:
                        tally['matched_shown'].append(record['answer'] == shown)
                        tally['matched_shown_if_fresh'].append(expected)
                    if earlier != shown:
                        tally['differed_moved_to_shown'].append(record['answer'] == shown)
                        tally['differed_kept_earlier'].append(record['answer'] == earlier)
                if real_friends:
                    tally['matched_real_friends'].append(record['answer'] == real_friends)
            row.update({k: float(np.mean(v)) for k, v in tally.items()})
            row['cases_where_earlier_differed'] = len(tally['differed_moved_to_shown'])
        result['exposure'][name] = {k: round(float(v), 4) if not isinstance(v, int) else v for k, v in row.items()}

    for k in [0, 2, 4]:
        rows = [r for r in runs['dose'].values() if r['disagreeing'] == k]
        expected = [fresh(r['egoid'], r['item'], r['target']) for r in rows]
        expected = [e for e in expected if e is not None]
        result['dose'].append({
            'friends_disagreeing_of_4': k, 'answers': len(rows),
            'chose_shown_alternative': round(float(np.mean([r['answer'] == r['target'] for r in rows])), 4),
            'kept_earlier_answer': round(float(np.mean([r['answer'] == r['earlier'] for r in rows])), 4),
            'alternative_if_fresh': round(float(np.mean(expected)), 4)})
    Path(out).write_text(json.dumps(result, indent=1) + '\n')
    print(json.dumps(result, indent=1))


if __name__ == '__main__':
    main()
