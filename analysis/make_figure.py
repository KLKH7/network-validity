"""Draw the README figure: the friend effect split into shared background and beyond.

    python analysis/make_figure.py

Reads site/results.js and writes figures/friend_effect_split.svg.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INK, MUTED, GRID, BACKGROUND, REF = '#0b0b0b', '#52514e', '#e4e2dc', '#fcfcfb', '#b9b7b0'
SERIES = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100']


def main():
    data = json.loads((ROOT / 'site' / 'results.js').read_text().split('=', 1)[1].rstrip().rstrip(';'))
    conditions, names = data['conditions'], data['questions']
    base = conditions[0]['items']
    order = sorted(base, key=lambda k: -base[k]['real_friend_effect'])
    runs = [('Real students', INK, lambda k: (base[k]['real_profile_part'], base[k]['real_beyond_profile']))]
    for i, c in enumerate(conditions):
        label = c['label'] + (' (' + c['model'][0] + ')' if c.get('model') else '')
        runs.append((label, SERIES[i], lambda k, c=c: (c['items'][k]['sim_profile_part'], c['items'][k]['sim_beyond_profile'])))
    width, left, right, bar, gap = 860, 190, 90, 14, 6
    group = len(runs) * (bar + gap) + 26
    top = 96 + 22 * ((len(runs) + 1) // 2)
    height = top + group * len(order) + 44
    peak = max(max(0, a) + max(0, b) for k in order for _, _, get in runs for a, b in [get(k)])
    hi = (int(peak * 100 / 5) + 1) * 5 / 100
    x = lambda v: left + v / hi * (width - left - right)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" font-family="Helvetica, Arial, sans-serif">',
           f'<rect width="{width}" height="{height}" fill="{BACKGROUND}"/>',
           f'<text x="24" y="36" font-size="19" font-weight="600" fill="{INK}">Real friends agree beyond their background. Simulated friends don’t.</text>',
           f'<text x="24" y="60" font-size="13" fill="{MUTED}">Extra agreement between friends, in percentage points above random pairs. {data["friend_pairs_total"]:,} friend pairs, NetHealth wave 2.</text>']
    legend = [('Explained by shared gender, race and region', REF)] + [(label + ': beyond background', color) for label, color, _ in runs]
    for i, (label, color) in enumerate(legend):
        lx, ly = 24 + (i % 2) * 400, 86 + (i // 2) * 22
        out.append(f'<rect x="{lx}" y="{ly - 10}" width="12" height="12" rx="3" fill="{color}"/><text x="{lx + 18}" y="{ly}" font-size="12" fill="{MUTED}">{label}</text>')
    t = 0.0
    while t <= hi + 1e-9:
        out.append(f'<line x1="{x(t):.1f}" x2="{x(t):.1f}" y1="{top}" y2="{height - 34}" stroke="{GRID}"/>')
        out.append(f'<text x="{x(t):.1f}" y="{height - 14}" font-size="12" fill="{MUTED}" text-anchor="middle">{round(t * 100)} pts</text>')
        t += 0.05
    for i, k in enumerate(order):
        y0 = top + group * i + 10
        out.append(f'<text x="24" y="{y0 + bar - 2}" font-size="14" fill="{INK}">{names[k]}</text>')
        for j, (label, color, get) in enumerate(runs):
            background, beyond = get(k)
            y = y0 + j * (bar + gap)
            w1, w2 = x(max(0, background)) - x(0), x(max(0, beyond)) - x(0)
            if w1 > 0:
                out.append(f'<rect x="{x(0):.1f}" y="{y}" width="{w1:.1f}" height="{bar}" fill="{REF}"/>')
            x2 = x(0) + w1 + (2 if w1 > 0 else 0)
            if w2 > 0:
                out.append(f'<rect x="{x2:.1f}" y="{y}" width="{w2:.1f}" height="{bar}" rx="3" fill="{color}"/>')
            out.append(f'<text x="{x2 + w2 + 6:.1f}" y="{y + bar - 2}" font-size="12" fill="{MUTED}">{100 * (background + beyond):.1f}</text>')
    out.append('</svg>')
    (ROOT / 'figures' / 'friend_effect_split.svg').write_text('\n'.join(out))
    print('written figures/friend_effect_split.svg')


if __name__ == '__main__':
    main()
