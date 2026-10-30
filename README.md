# Learning to Judge Research Ideas: a human-guided auto-research studio for doctoral training

Research artifact for a Stage 1 submission to the *Organization Science* special issue "AI-Enabled Frontiers in Organizational Science".

Authors: Ziqin Gong, Ning Li, and Huaikang Zhou.

Public repository: https://github.com/ln9527/research-judgment-studio

The project has three parts that already exist and one that is proposed:

1. **The research-idea gatekeeper** (Gong, Li, and Zhou 2026, [arXiv:2603.16659](https://arxiv.org/abs/2603.16659)). Small language models fine-tuned on the source-journal tier of published articles learn to sort research pitches by tier across eight social science fields (best four-tier accuracy from 55.0% in public administration to 85.5% in psychology; 59.2% in management against 41.6% for an expert majority vote and 25% chance).
2. **Open evaluators and a live platform.** Two open-weight management evaluators on Hugging Face and the public platform [Idea Gatekeeper](https://gatekeeper.spansurvey.net) (1,417 registered users and 3,455 evaluations as of 28 October 2026).
3. **A human-guided auto-research loop** (Li 2026c, working paper) that uses the evaluators as a search objective for idea generation in management, under written investigator direction and a feasibility constraint.
4. **Proposed:** a training studio in which doctoral students direct the loop, commit to their own judgments before seeing model scores, and keep a reviewable record of why they kept or dropped each idea.

## What you can run here

| Folder | What it does | Needs |
|---|---|---|
| `reproduce_pilot.py`, `pilot/` | Downloads four hash-pinned public files from FutureTech-OB/ai-taste and recomputes the eight-row model-versus-human disagreement table exactly | Python 3.9+, internet; no GPU, no API key |
| `learning-ledger/` | Standard-library prototype of the study ledger (fixed-pool selection, blinded review export, unaided transfer records) with synthetic fixtures and tests | Python 3.9+ |
| `evaluator/` | Scores a pitch with the public open-weight evaluators at pinned revisions; returns tier probabilities and expected tier value | GPU, `pip install -r evaluator/requirements.txt` |
| `figures/` | Rebuilds all submission figures; plotted values are also listed in `figures/source_data/` | matplotlib, numpy, pillow |
| `autoresearch/` | Loop specification and results summary for branches AR-01 to AR-03 | none |
| `data_cards/` | Data cards for the benchmarks, human ratings, and platform counts | none |
| `platform/screenshots/` | Screenshots of the live platform taken on 28 October 2026 | none |

```bash
python3 reproduce_pilot.py
python3 -m unittest discover -s learning-ledger/tests -v
python3 figures/make_figures.py            # writes PDFs and PNGs into figures/
python3 evaluator/score_pitch.py --model 4b --pitch-file examples/pitch.txt   # GPU
```

`reproduce_pilot.py` reproduces archived model outputs. It does not rerun model inference. The evaluator script is the path to fresh inference; see `evaluator/README.md` for its status.

## Models

| Model | Revision | Base |
|---|---|---|
| [K1mG0ng/AI-taste-ob-4B](https://huggingface.co/K1mG0ng/AI-taste-ob-4B) | `62fa1a9f196da9b269bbb56e9592ce5cd2bed551` | Qwen/Qwen3-4B |
| [K1mG0ng/AI-taste-ob-30B-A3B](https://huggingface.co/K1mG0ng/AI-taste-ob-30B-A3B) | `b5096d2473edeecb7e4f56dd53bf7ca9009f94a3` | Qwen/Qwen3-30B-A3B |

Training code: [FutureTech-OB/AI-Taste-Training](https://github.com/FutureTech-OB/AI-Taste-Training). Benchmarks, predictions, and human ratings: [FutureTech-OB/ai-taste](https://github.com/FutureTech-OB/ai-taste).

## What the label means

The evaluators predict the four-tier standing of the journal where a published article appeared. That is an institutional trace of past sorting. It is not an editorial decision on a submission and not a measure of whether an idea is right or valuable. The models can favor ideas that look like what fields have rewarded before. We treat their output as one signal for a researcher to argue with, and the proposed studio is built around that use.

## What is not here

Full article texts (publisher copyright), rater identities, platform user data and submitted ideas, and the verbatim investigator directives and generation logs of the auto-research loop.

## License

Code: MIT. Figures, screenshots, data cards, and CSV files: CC BY 4.0. See `LICENSE`.

## Citation

Gong Z, Li N, Zhou H (2026) LLMs learn scientific taste from institutional traces across the social sciences. Preprint, arXiv:2603.16659. See `CITATION.cff`.
