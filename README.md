# Network validity

A proposed twelfth test for the [Artificial Societies Benchmark](https://github.com/artificial-societies/artificial-societies-benchmark). The benchmark checks internal, construct and external validity, one respondent at a time. This asks one more question, about the ties between respondents.

**When two real students are friends, are their simulated versions as alike as the real ones were?**

This is a first pass. Its limits are listed at the end.

## The question

The Artificial Societies Benchmark asks whether a model answering as a specific survey respondent gives valid answers. Its eleven tests score each simulated respondent against the real person. One of its sources, the NetHealth study, also recorded who each student named as a friend, which makes it possible to compare pairs.

## What the real data shows

Data: 1,031 friend pairs among 639 University of Notre Dame students (NetHealth, second survey round, 2016).

Extra agreement between friends, in percentage points above randomly paired students:

| Question | Explained by gender, race and region | Beyond those three facts |
| --- | ---: | ---: |
| Drank wine or liquor | 1.1 | 13.2 |
| Drank beer | 2.4 | 10.2 |
| Same-sex marriage | -0.4 | 8.1 |
| Political party | 1.1 | 6.5 |
| Legalising marijuana | 1.1 | 5.8 |
| **Average** | **1.0** | **8.8** |

Real friends agree well beyond what those three profile fields explain. "Beyond" here means only that: not explained by gender, race and home region. It could still come from religion, school, dorm or earlier habits.

### Were friends alike before they met?

NetHealth's first survey was taken the summer before the students arrived. For pairs who became friends at university, agreement above random pairs:

| Question | Pairs | Before arrival | After one semester |
| --- | ---: | ---: | ---: |
| Drank beer | 264 | 11.1 | 9.6 |
| Drank wine or liquor | 264 | 5.7 | 13.2 |
| Political party | 254 | 2.4 | 6.0 |
| Legalising marijuana | 184 | 8.3 | 6.6 |

On beer and marijuana the agreement was already there: students chose friends who were like them. On wine or liquor and political party it grew after they met. With a few hundred pairs the growth is suggestive, not firm. Same-sex marriage was not asked in the first survey.

## What simulation shows

Each student was simulated alone from gender, race and home region, using the benchmark's persona prompt.

| Run | Friend agreement beyond the profile (points) | Any two students give the same answer |
| --- | ---: | ---: |
| Real students | 8.8 | 27% |
| `claude-haiku-5-5`, one student at a time | 1.7 | 46% |
| `Qwen3-8B` (4-bit, run on a laptop), one student at a time | 0.4 | 83% |
| `claude-haiku-5-5`, each student shown their friends' simulated answers | 7.0 | 66% |

How to read this:

- **The near-zero figures for students simulated alone are true by construction.** Any simulator that answers one student at a time, given a profile, cannot produce friend agreement beyond that profile. They say nothing about either model. What they show is how much a three-fact profile leaves out.
- **A richer persona should recover the part that was there before the friendship.** If a persona carried what a student said before arriving, the likeness between friends-to-be would come with it and no network would be needed. This is not tested here yet.
- **Showing friends' answers is a rough probe, not a model of friendship.** The 7.0 should not be set beside the real 8.8, because its size depends on how the answers are shown. The clear effect is conformity: any two simulated students then agree 66% of the time, against 27% for real students.
- **Both small models give far less varied answers than real students**, which the benchmark already measures.

![Friend effect split into shared background and beyond](figures/friend_effect_split.svg)

## How it works

1. **Friend pairs.** Take every friend a student named in the wave 2 network survey, keep pairs where both students took part, and treat ties as undirected.
2. **Questions.** Five wave 2 questions where real friends agree far more than chance. Wording and options come from the study's questionnaire.
3. **Simulation.** One request per student per question, using the benchmark's persona prompt.
4. **Agreement.** The share of friend pairs giving the same answer.
5. **Background and beyond.** Shuffle answers among students with the same gender, race and region, 2,000 times. Agreement that survives the shuffle is explained by shared background. The rest is beyond it.

## Reproduce

Download `BasicSurvey(3-6-20).csv` and `NetWorkSurvey(2-28-20).csv` from the [NetHealth release on Zenodo](https://zenodo.org/records/21904040) into a folder, saved as `BasicSurvey.csv` and `NetWorkSurvey.csv`.

```sh
pip install pandas numpy

# human side only, no model needed
python analysis/check_ties.py DATA_FOLDER
python analysis/profile_ceiling.py DATA_FOLDER
python analysis/selection_vs_influence.py DATA_FOLDER

# simulate (needs the `claude` command line tool), then score
python analysis/simulate_claude.py DATA_FOLDER answers.jsonl
python analysis/score.py DATA_FOLDER answers.jsonl results/baseline.json

# network-aware round: each student sees their friends' answers from the previous run
python analysis/simulate_claude.py DATA_FOLDER answers_r1.jsonl --friends-from answers.jsonl
python analysis/score.py DATA_FOLDER answers_r1.jsonl results/friends_r1.json

# local open model on Apple silicon
pip install mlx-lm
python analysis/simulate_mlx.py DATA_FOLDER answers_qwen.jsonl --model mlx-community/Qwen3-8B-4bit

# rebuild the page data and the figure
python analysis/build_site_data.py
python analysis/make_figure.py
```

## Limits

- The five questions were chosen because real friends agree on them, which flatters the size of the effect. A fairer version would use every attitude question, or choose on half the students and measure on the other half.
- Agreement means giving exactly the same answer, so near misses count as disagreement.
- One university. The before-and-after comparison rests on a few hundred pairs.
- Two small models and a three-fact profile.
- Friend ties are self-reported and only counted when both students are in the study.

## What is and is not in this repository

Included: code, aggregate results and the figure. Not included: the NetHealth data, populated prompts and student-level model answers, following the benchmark's own practice.

## Credits

- NetHealth Project, University of Notre Dame, [CC BY 4.0](https://zenodo.org/records/21904040).
- Artificial Societies Benchmark (Chidichimo, Jung, Wallis and He, 2026), whose persona prompt template (after Gordon et al., 2026, CC BY 4.0) and NetHealth profile fields this test reuses.

Code in this repository is MIT licensed.
