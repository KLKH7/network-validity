"""Simulate NetHealth wave-2 students with an open model running locally on Apple silicon.

Same prompts, questions and parsing as simulate_claude.py; only the model call differs.
Decoding follows the benchmark's local-model regime: temperature 1.0, top-p 0.95, no reasoning.

    python analysis/simulate_mlx.py DATA_FOLDER OUT.jsonl --model mlx-community/Qwen3-8B-4bit [--limit N]
    python analysis/simulate_mlx.py DATA_FOLDER OUT.jsonl --model ... --friends-from PREVIOUS.jsonl
"""
import argparse
import json
import time
from pathlib import Path

import numpy as np
from mlx_lm import batch_generate, generate, load
from mlx_lm.sample_utils import make_sampler

from simulate_claude import ITEMS, SYSTEM, parse, prompt, roster


def main():
    a = argparse.ArgumentParser()
    a.add_argument('folder')
    a.add_argument('out')
    a.add_argument('--model', required=True)
    a.add_argument('--limit', type=int)
    a.add_argument('--friends-from')
    a.add_argument('--seed', type=int, default=20261122)
    a.add_argument('--batch', type=int, default=16)
    args = a.parse_args()

    import mlx.core as mx
    mx.random.seed(args.seed)
    basic, students, ties = roster(args.folder)
    if args.limit:
        students = np.random.default_rng(7).choice(students, args.limit, replace=False)
    previous = {}
    if args.friends_from:
        for r in map(json.loads, Path(args.friends_from).read_text().splitlines()):
            if r['answer']:
                previous[(r['egoid'], r['item'])] = r['answer']
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out.exists():
        done = {(r['egoid'], r['item']) for r in map(json.loads, out.read_text().splitlines()) if r['answer']}
    todo = [(int(s), item) for s in students for item in ITEMS if (int(s), item) not in done]
    print(f'students={len(students)} requests to send={len(todo)} already done={len(done)}', flush=True)

    model, tokenizer = load(args.model)
    sampler = make_sampler(temp=1.0, top_p=0.95)
    counts = {'ok': 0, 'unparsed': 0}
    started = time.time()
    def render(student, item):
        shown = [previous[(x, item)] for x in sorted(ties.get(student, [])) if (x, item) in previous] if previous else None
        messages = [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': prompt(basic.loc[student], item, shown)}]
        try:
            text = tokenizer.apply_chat_template(messages, add_generation_prompt=True, tokenize=False, enable_thinking=False)
        except TypeError:
            text = tokenizer.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
        return text, len(shown) if shown else 0

    with out.open('a') as f:
        for start in range(0, len(todo), args.batch):
            jobs = todo[start:start + args.batch]
            rendered = [render(*job) for job in jobs]
            texts = batch_generate(model, tokenizer, prompts=[tokenizer.encode(t) for t, _ in rendered], max_tokens=24, sampler=sampler).texts
            for (student, item), (text, shown), raw in zip(jobs, rendered, texts):
                answer = parse(raw.split('</think>')[-1], ITEMS[item][1])
                if not answer:
                    raw = generate(model, tokenizer, prompt=text, max_tokens=24, sampler=sampler, verbose=False)
                    answer = parse(raw.split('</think>')[-1], ITEMS[item][1])
                counts['ok' if answer else 'unparsed'] += 1
                f.write(json.dumps({'egoid': student, 'item': item, 'answer': answer, 'raw': raw, 'model': args.model.split('/')[-1],
                                    'friends_shown': shown}) + '\n')
            f.flush()
            n = start + len(jobs)
            if (start // args.batch) % 10 == 0:
                rate = n / (time.time() - started)
                print(n, counts, f'{rate:.2f} requests/s, about {(len(todo) - n) / rate / 60:.0f} min left', flush=True)
    print('finished', counts, flush=True)


if __name__ == '__main__':
    main()
