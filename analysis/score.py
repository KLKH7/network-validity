"""Compare friend agreement among real students with friend agreement among simulated ones.

    python analysis/score.py DATA_FOLDER ANSWERS.jsonl [OUT.json]
"""
import json
import sys

import numpy as np
import pandas as pd

PROFILE = ['gender_1', 'race_1', 'RegionUS']
REPS = 2000


def agreement(values, left, right):
    return float((values[left] == values[right]).mean())


def shuffled(values, left, right, rng, groups=None):
    out = np.empty(REPS)
    for r in range(REPS):
        if groups is None:
            v = rng.permutation(values)
        else:
            v = values.copy()
            for g in groups:
                v[g] = values[rng.permutation(g)]
        out[r] = agreement(v, left, right)
    return out


def distribution_gap(real, sim):
    labels = sorted(set(real) | set(sim))
    p = np.array([(real == l).mean() for l in labels])
    q = np.array([(sim == l).mean() for l in labels])
    return 0.5 * np.abs(p - q).sum()


def main(folder, answers_path):
    rng = np.random.default_rng(20261122)
    net = pd.read_csv(folder + '/NetWorkSurvey.csv', low_memory=False)
    basic = pd.read_csv(folder + '/BasicSurvey.csv', low_memory=False).set_index('egoid')
    e = net[(net.wave == 'Wave2') & net.alterid.isin(basic.index) & (net.friend == True)][['egoid', 'alterid']]
    e = e[e.egoid != e.alterid]
    dyads = pd.DataFrame(np.sort(e.to_numpy(), axis=1)).drop_duplicates().to_numpy()
    rows = [json.loads(line) for line in open(answers_path)]
    sim = pd.DataFrame([r for r in rows if r['answer']]).drop_duplicates(['egoid', 'item'], keep='last')
    print('model:', sorted(sim.model.dropna().unique()), '| simulated answers:', len(sim))
    summary = []
    for item in sorted(sim.item.unique()):
        s = sim[sim.item == item].set_index('egoid').answer
        h = basic[item]
        ok = lambda x: h.reindex(x).notna().to_numpy() & s.reindex(x).notna().to_numpy()
        d = dyads[ok(dyads[:, 0]) & ok(dyads[:, 1])]
        nodes = np.unique(d)
        index = {n: i for i, n in enumerate(nodes)}
        left = np.array([index[x] for x in d[:, 0]])
        right = np.array([index[x] for x in d[:, 1]])
        real = h.reindex(nodes).to_numpy()
        model = s.reindex(nodes).to_numpy()
        cell = basic[PROFILE].reindex(nodes).fillna('missing').astype(str).agg('|'.join, axis=1).to_numpy()
        groups = [np.flatnonzero(cell == c) for c in np.unique(cell)]
        real_friends = agreement(real, left, right)
        real_random = shuffled(real, left, right, rng)
        ceiling = shuffled(real, left, right, rng, groups)
        sim_friends = agreement(model, left, right)
        sim_random = shuffled(model, left, right, rng)
        # how often the simulator gives two same-profile students the same answer
        within = shuffled(model, left, right, rng, groups)
        result = {
            'item': item, 'pairs': len(d), 'students': len(nodes),
            'real_friends_agree': real_friends, 'real_random_pairs': real_random.mean(),
            'real_friend_effect': real_friends - real_random.mean(),
            'ceiling_one_at_a_time': ceiling.mean(),
            'sim_friends_agree': sim_friends, 'sim_random_pairs': sim_random.mean(),
            'sim_friend_effect': sim_friends - sim_random.mean(),
            'sim_friend_effect_p': float((np.sum(sim_random >= sim_friends) + 1) / (REPS + 1)),
            'sim_same_profile_reshuffle': within.mean(),
            'share_of_real_effect_reproduced': (sim_friends - sim_random.mean()) / (real_friends - real_random.mean()),
            'answer_distribution_gap_tvd': distribution_gap(real, model),
            'individual_accuracy': float((real == model).mean()),
            'distinct_sim_answers': int(len(set(model))),
            # split each friend effect into the part explained by shared profile and the part beyond it
            'real_profile_part': float(ceiling.mean() - real_random.mean()),
            'real_beyond_profile': float(real_friends - ceiling.mean()),
            'real_beyond_profile_p': float((np.sum(ceiling >= real_friends) + 1) / (REPS + 1)),
            'sim_profile_part': float(within.mean() - sim_random.mean()),
            'sim_beyond_profile': float(sim_friends - within.mean()),
            'sim_beyond_profile_p': float((np.sum(within >= sim_friends) + 1) / (REPS + 1)),
            'sim_beyond_low': float(sim_friends - np.quantile(within, 0.975)), 'sim_beyond_high': float(sim_friends - np.quantile(within, 0.025)),
            'ceiling_low': float(np.quantile(ceiling, 0.025)), 'ceiling_high': float(np.quantile(ceiling, 0.975)),
            'real_shares': {str(k): float(v) for k, v in pd.Series(real).value_counts(normalize=True).items()},
            'sim_shares': {str(k): float(v) for k, v in pd.Series(model).value_counts(normalize=True).items()},
        }
        summary.append(result)
    table = pd.DataFrame(summary).drop(columns=['real_shares', 'sim_shares']).set_index('item')
    pd.set_option('display.width', 250, 'display.max_columns', 30, 'display.float_format', '{:.3f}'.format)
    print(table.T)
    out = sys.argv[3] if len(sys.argv) > 3 else answers_path.replace('.jsonl', '.scores.json')
    json.dump({'model': sorted(sim.model.dropna().unique()), 'friend_pairs_total': int(len(dyads)), 'items': summary}, open(out, 'w'), indent=1)
    print('written', out)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
