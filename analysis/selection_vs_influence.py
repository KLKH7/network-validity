"""Were friends already alike before they met, or did they grow alike?

NetHealth's first survey was taken in the summer before the students arrived at
university; the second after their first semester. For the friend pairs named in the
second survey, compare agreement on the same question before arrival and after.

    python analysis/selection_vs_influence.py DATA_FOLDER
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ITEMS = {'Drank beer': ('usebeer_1', 'usebeer_2'), 'Drank wine or liquor': ('usewine_1', 'usewine_2'),
         'Political party': ('polparty_1_1', 'polparty_1_2'), 'Legalising marijuana': ('marijuana_1', 'marijuana_2'),
         'Same-sex marriage': ('gaymarriage_1', 'gaymarriage_2')}
REPS = 2000


def effect(values, left, right, rng):
    observed = float((values[left] == values[right]).mean())
    null = np.array([(p[left] == p[right]).mean() for p in (rng.permutation(values) for _ in range(REPS))])
    return observed, null.mean(), observed - null.mean(), float((np.sum(null >= observed) + 1) / (REPS + 1)), null.std()


def main(folder):
    rng = np.random.default_rng(20261122)
    net = pd.read_csv(folder + '/NetWorkSurvey.csv', low_memory=False)
    basic = pd.read_csv(folder + '/BasicSurvey.csv', low_memory=False).set_index('egoid')
    e = net[(net.wave == 'Wave2') & net.alterid.isin(basic.index) & (net.friend == True)][['egoid', 'alterid']]
    e = e[e.egoid != e.alterid]
    dyads = pd.DataFrame(np.sort(e.to_numpy(), axis=1)).drop_duplicates().to_numpy()
    w1 = net[(net.wave == 'Wave1') & (net.friend == True)][['egoid', 'alterid']]
    known = set(map(tuple, np.sort(w1.to_numpy(), axis=1)))
    already = np.array([tuple(d) in known for d in dyads])
    print(f'wave-2 friend pairs: {len(dyads)}; already named as friends before arrival: {already.sum()}')
    rows = []
    for name, (before, after) in ITEMS.items():
        if before not in basic or after not in basic:
            print(f'\n{name}: not asked in both waves'); continue
        b, a = basic[before], basic[after]
        if name == 'Legalising marijuana':
            a = a.where(a != 'Not sure')  # the first survey had no "Not sure" option
        ok = lambda x: b.reindex(x).notna().to_numpy() & a.reindex(x).notna().to_numpy()
        keep = ok(dyads[:, 0]) & ok(dyads[:, 1]) & ~already
        d = dyads[keep]
        nodes = np.unique(d); idx = {n: i for i, n in enumerate(nodes)}
        left = np.array([idx[x] for x in d[:, 0]]); right = np.array([idx[x] for x in d[:, 1]])
        eb = effect(b.reindex(nodes).to_numpy(), left, right, rng)
        ea = effect(a.reindex(nodes).to_numpy(), left, right, rng)
        print(f'\n{name}: {len(d)} pairs who were not yet friends at the first survey, both answered both times')
        print(f'  before arrival: friends-to-be agree {eb[0]:.3f}, random {eb[1]:.3f}, effect {100*eb[2]:+.1f} pts (p={eb[3]:.4f}, null sd {100*eb[4]:.1f})')
        print(f'  after a semester: friends agree     {ea[0]:.3f}, random {ea[1]:.3f}, effect {100*ea[2]:+.1f} pts (p={ea[3]:.4f}, null sd {100*ea[4]:.1f})')
        rows.append({'question': name, 'pairs': int(len(d)), 'before': eb[2], 'before_p': eb[3], 'before_sd': float(eb[4]), 'after': ea[2], 'after_p': ea[3], 'after_sd': float(ea[4])})
    out = Path(__file__).resolve().parents[1] / 'results' / 'before_after.json'
    out.write_text(json.dumps({'new_friend_pairs_excluded_as_prior_friends': int(already.sum()), 'items': rows}, indent=1))
    print('written', out)


if __name__ == '__main__':
    main(sys.argv[1])
