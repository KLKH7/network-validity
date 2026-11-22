"""Simulate NetHealth wave-2 students one at a time and record their answers.

Each request describes one student with the same three recorded characteristics the
benchmark's NetHealth tasks use (gender, race, home region) and asks one question with the
wording and options of the wave-2 questionnaire. Requests go through the `claude` command
line tool in print mode with no tools, no settings and no session history.

    python analysis/simulate_claude.py DATA_FOLDER OUT.jsonl [--limit N]
"""
import argparse
import json
import subprocess
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ACTIVITY = 'For the items below, indicate how often you did each item during the Fall 2015 semester?\n\n'
FREQUENCY = ['Three times a week or more', '1-2 times a week', '1-2 times a month', 'Less than 1-2 times a month', 'Not at all']
ITEMS = {
    'usebeer_2': (ACTIVITY + 'Drank beer', FREQUENCY),
    'usewine_2': (ACTIVITY + 'Drank wine or liquor', FREQUENCY),
    'polparty_1_2': ('Generally speaking, do you usually think of yourself as a Republican, a Democrat, an Independent, or what?',
                     ['Republican', 'Democrat', 'Independent', 'Other', 'No preference']),
    'marijuana_2': ('Do you favor or oppose the legalization of the use of marijuana?',
                    ['Strongly favor', 'Favor', 'Oppose', 'Strongly oppose', 'Not sure']),
    'gaymarriage_2': ('Do you agree that homosexual couples should have the right to marry one another?',
                      ['Strongly agree', 'Agree', 'Neither agree nor disagree', 'Disagree', 'Strongly disagree', 'Not sure']),
}
PROFILE = [('gender_1', 'Gender recorded at entry'), ('race_1', 'Source race or student-origin category'),
           ('RegionUS', 'US home-address region recorded at entry')]
SYSTEM = 'You answer survey questions in character. Reply with only the selected option. No commentary.'
TEMPLATE = '''You are being asked to role-play as a specific individual with the following characteristics:

Country: United States
Date: February 2016

Demographics:
{demographics}
{friends}
Please answer the following survey question AS THIS PERSON, considering how their demographics, values, and life circumstances would shape their response. Think carefully about how someone with these characteristics would authentically respond.

Question: {question}

Options:
{options}

Please respond with ONLY your selected answer from the options above. Choose exactly one option and use the exact text as it appears.

Your answer:'''


FRIENDS = '''
Friends:
The students this person named as friends at university answered this same question as follows:
{answers}
'''


def roster(folder):
    net = pd.read_csv(folder + '/NetWorkSurvey.csv', low_memory=False)
    basic = pd.read_csv(folder + '/BasicSurvey.csv', low_memory=False).set_index('egoid')
    e = net[(net.wave == 'Wave2') & net.alterid.isin(basic.index) & (net.friend == True)][['egoid', 'alterid']]
    e = e[e.egoid != e.alterid]
    ties = {}
    for a, b in pd.DataFrame(np.sort(e.to_numpy(), axis=1)).drop_duplicates().to_numpy():
        ties.setdefault(int(a), []).append(int(b))
        ties.setdefault(int(b), []).append(int(a))
    return basic, np.unique(e.to_numpy()), ties


def prompt(row, item, friend_answers=None):
    lines = ['- University cohort: Entered the University of Notre Dame in fall 2015']
    lines += [f'- {label}: {row[col]}' for col, label in PROFILE if pd.notna(row[col])]
    question, options = ITEMS[item]
    friends = ''
    if friend_answers:
        friends = FRIENDS.format(answers='\n'.join(f'- Friend {i}: {a}' for i, a in enumerate(friend_answers, 1)))
    return TEMPLATE.format(demographics='\n'.join(lines), friends=friends, question=question,
                           options='\n'.join('  - ' + o for o in options))


def parse(text, options):
    cleaned = text.strip().strip('"\'.*- ').casefold()
    exact = [o for o in options if o.casefold() == cleaned]
    if exact:
        return exact[0]
    inside = [o for o in options if o.casefold() in cleaned]
    return max(inside, key=len) if inside else None


def ask(text, model, workdir):
    out = subprocess.run(
        ['claude', '-p', '--model', model, '--tools', '', '--strict-mcp-config', '--setting-sources', '',
         '--no-session-persistence', '--system-prompt', SYSTEM, '--output-format', 'json'],
        input=text, capture_output=True, text=True, cwd=workdir, timeout=120)
    reply = json.loads(out.stdout)
    if reply.get('is_error'):
        raise RuntimeError(str(reply.get('result'))[:200])
    return reply['result'], next(iter(reply.get('modelUsage', {})), model)


def main():
    a = argparse.ArgumentParser()
    a.add_argument('folder')
    a.add_argument('out')
    a.add_argument('--model', default='haiku')
    a.add_argument('--limit', type=int)
    a.add_argument('--workers', type=int, default=8)
    a.add_argument('--friends-from', help='answers file from the previous round; each student is shown what their friends answered in it')
    args = a.parse_args()
    basic, students, ties = roster(args.folder)
    previous = {}
    if args.friends_from:
        for r in map(json.loads, Path(args.friends_from).read_text().splitlines()):
            if r['answer']:
                previous[(r['egoid'], r['item'])] = r['answer']
    if args.limit:
        students = np.random.default_rng(7).choice(students, args.limit, replace=False)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out.exists():
        done = {(r['egoid'], r['item']) for r in map(json.loads, out.read_text().splitlines()) if r['answer']}
    todo = [(int(s), item) for s in students for item in ITEMS if (int(s), item) not in done]
    print(f'students={len(students)} requests to send={len(todo)} already done={len(done)}', flush=True)
    lock = threading.Lock()
    workdir = tempfile.mkdtemp(prefix='nh_claude_')
    counts = {'ok': 0, 'unparsed': 0, 'error': 0}

    def run(job):
        student, item = job
        shown = [previous[(f, item)] for f in sorted(ties.get(student, [])) if (f, item) in previous] if previous else None
        text = prompt(basic.loc[student], item, shown)
        record = {'egoid': student, 'item': item, 'answer': None, 'raw': None, 'model': None, 'friends_shown': len(shown) if shown else 0}
        for _ in range(2):
            try:
                record['raw'], record['model'] = ask(text, args.model, workdir)
            except Exception as error:
                record['raw'] = 'ERROR ' + str(error)[:200]
                continue
            record['answer'] = parse(record['raw'], ITEMS[item][1])
            if record['answer']:
                break
        key = 'ok' if record['answer'] else ('error' if str(record['raw']).startswith('ERROR') else 'unparsed')
        with lock:
            counts[key] += 1
            with out.open('a') as f:
                f.write(json.dumps(record) + '\n')
            total = sum(counts.values())
            if total % 200 == 0:
                print(total, counts, flush=True)

    with ThreadPoolExecutor(args.workers) as pool:
        list(pool.map(run, todo))
    print('finished', counts, flush=True)


if __name__ == '__main__':
    main()
