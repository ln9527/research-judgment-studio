# Evaluator usage

`score_pitch.py` loads the public fine-tuned checkpoints from Hugging Face at pinned revisions and returns a four-tier probability distribution for a research pitch.

| Key | Hugging Face repository | Revision | Base model | License |
|---|---|---|---|---|
| `4b` | [K1mG0ng/AI-taste-ob-4B](https://huggingface.co/K1mG0ng/AI-taste-ob-4B) | `62fa1a9f196da9b269bbb56e9592ce5cd2bed551` | Qwen/Qwen3-4B | MIT |
| `30b` | [K1mG0ng/AI-taste-ob-30B-A3B](https://huggingface.co/K1mG0ng/AI-taste-ob-30B-A3B) | `b5096d2473edeecb7e4f56dd53bf7ca9009f94a3` | Qwen/Qwen3-30B-A3B | MIT |

The system prompt in `prompts/ob_rqcontext.txt` is copied verbatim from the public training framework ([FutureTech-OB/AI-Taste-Training](https://github.com/FutureTech-OB/AI-Taste-Training), `src/practices/article/ob.py`, MIT license). Pitches should follow the format used in training: a single paragraph of roughly 150 words covering the phenomenon, the gap, the research question, a brief approach, and the contribution. `../examples/benchmark_sample.jsonl` shows the format.

```bash
pip install -r evaluator/requirements.txt
python evaluator/score_pitch.py --model 4b --pitch-file examples/pitch.txt
python evaluator/score_pitch.py --model 4b --jsonl examples/benchmark_sample.jsonl --out scores.jsonl
```

Output fields: `predicted_tier`, `confidence` (probability of the predicted tier after renormalizing over the four tier tokens), `probabilities`, `expected_tier_value` (1 to 4), and `tier_mass_in_full_vocab` (how much of the next-token probability falls on the four tier tokens; low values signal a prompt or format mismatch).

## Status and caveats

- This script has not yet been run end to end on GPU for this release. The first GPU run will check that scores on the 120-item management benchmark reproduce the archived predictions in the public reproducibility package; results will be added to `docs/smoke_test.md`.
- The archived predictions were produced by a served endpoint with first-token log-probabilities. Small numerical differences can arise from hardware, precision, and tokenizer versions.
- The tier label is the four-tier standing of the source journal of published articles. It is an institutional proxy, not ground truth, and the models may favor ideas that resemble what fields have rewarded in the past. Use the output as a prompt for reflection and discussion, not as a verdict.
