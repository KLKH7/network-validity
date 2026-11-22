"""Friend agreement in NetHealth versus the most any per-respondent simulator can reproduce.

A simulator that answers for each student separately, given only that student's profile,
produces answers that are independent across students once the profile is fixed. Its friend
agreement therefore cannot exceed, in expectation, what you get by shuffling the real answers
among students who share a profile. That shuffle is the ceiling computed here.
"""
import sys
import numpy as np
import pandas as pd

ITEMS = ['usebeer_2', 'usewine_2', 'usetobacco_2', 'usedrugs_2', 'polparty_1_2', 'polorientation_2',
         'gaymarriage_2', 'marijuana_2', 'deathpenalty_2']
PROFILES = {
    'benchmark profile (gender, race, region)': ['gender_1', 'race_1', 'RegionUS'],
    'richer profile (+ religion, parent income, school type)': ['gender_1', 'race_1', 'RegionUS', 'yourelig_1', 'parentincome_1', 'hs_1'],
}
REPS = 2000


def friend_dyads(net, roster, wave='Wave2'):
    e = net[(net.wave == wave) & net.alterid.isin(roster) & (net.friend == True)][['egoid', 'alterid']]
    e = e[e.egoid != e.alterid]
    return pd.DataFrame(np.sort(e.to_numpy(), axis=1)).drop_duplicates().to_numpy()


def agreement(a, b):
    return float((a == b).mean())


def main(folder):
    rng = np.random.default_rng(20261122)
    net = pd.read_csv(folder + '/NetWorkSurvey.csv', low_memory=False)
    basic = pd.read_csv(folder + '/BasicSurvey.csv', low_memory=False).set_index('egoid')
    dyads = friend_dyads(net, basic.index)
    print(f'friend pairs: {len(dyads)}, students: {len(np.unique(dyads))}')
    for item in ITEMS:
        answers = basic[item]
        keep = answers.reindex(dyads[:, 0]).notna().to_numpy() & answers.reindex(dyads[:, 1]).notna().to_numpy()
        d = dyads[keep]
        nodes = np.unique(d)
        idx = {n: i for i, n in enumerate(nodes)}
        left = np.array([idx[x] for x in d[:, 0]])
        right = np.array([idx[x] for x in d[:, 1]])
        values = answers.reindex(nodes).to_numpy()
        observed = agreement(values[left], values[right])
        chance = np.array([agreement(p[left], p[right]) for p in (rng.permutation(values) for _ in range(REPS))])
        print(f'\n{item}: pairs={len(d)} real friends agree {observed:.3f} | random pairing {chance.mean():.3f}')
        for name, cols in PROFILES.items():
            cell = basic[cols].reindex(nodes).fillna('missing').astype(str).agg('|'.join, axis=1).to_numpy()
            groups = [np.flatnonzero(cell == c) for c in np.unique(cell)]
            sims = np.empty(REPS)
            for r in range(REPS):
                shuffled = values.copy()
                for g in groups:
                    shuffled[g] = values[rng.permutation(g)]
                sims[r] = agreement(shuffled[left], shuffled[right])
            lo, hi = np.quantile(sims, [0.025, 0.975])
            explained = (sims.mean() - chance.mean()) / (observed - chance.mean())
            p = (np.sum(sims >= observed) + 1) / (REPS + 1)
            singles = sum(len(g) == 1 for g in groups)
            print(f'  ceiling, {name}: {sims.mean():.3f} [{lo:.3f}, {hi:.3f}] '
                  f'share of friend effect reachable {explained:.0%}, p(ceiling >= real)={p:.4f}, '
                  f'profile groups={len(groups)} (single-student groups={singles})')


if __name__ == '__main__':
    main(sys.argv[1])
