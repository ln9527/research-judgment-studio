#!/usr/bin/env python3
"""Score a research pitch with the public open-weight institutional-taste evaluators.

The evaluator returns a probability distribution over four source-journal tiers
(Exceptional, Strong, Fair, Limited), read from the first generated token after the
public evaluation prompt. Tiers are an institutional proxy learned from where
published work appeared; they are not a measure of objective merit.

Usage:
  python evaluator/score_pitch.py --model 4b --pitch-file my_pitch.txt
  python evaluator/score_pitch.py --model 30b --jsonl pitches.jsonl --field rq_with_context --out scores.jsonl

Requirements: see evaluator/requirements.txt. The 4B model needs roughly 9 GB of GPU
memory in bfloat16; the 30B-A3B model needs a large-memory GPU or multi-GPU setup.
"""
import argparse, json, math, sys
from pathlib import Path

MODELS = {
    "4b":  {"repo": "K1mG0ng/AI-taste-ob-4B",      "revision": "62fa1a9f196da9b269bbb56e9592ce5cd2bed551"},
    "30b": {"repo": "K1mG0ng/AI-taste-ob-30B-A3B", "revision": "b5096d2473edeecb7e4f56dd53bf7ca9009f94a3"},
}
TIERS = ["Exceptional", "Strong", "Fair", "Limited"]
TIER_VALUE = {"Exceptional": 4, "Strong": 3, "Fair": 2, "Limited": 1}
HERE = Path(__file__).resolve().parent


def load(model_key, device):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    spec = MODELS[model_key]
    tok = AutoTokenizer.from_pretrained(spec["repo"], revision=spec["revision"])
    model = AutoModelForCausalLM.from_pretrained(spec["repo"], revision=spec["revision"],
                                                 torch_dtype=torch.bfloat16, device_map=device)
    model.eval()
    return tok, model


def first_token_ids(tok):
    ids = {}
    for t in TIERS:
        enc = tok.encode(t, add_special_tokens=False)
        ids[t] = enc[0]
    if len(set(ids.values())) != len(ids):
        raise RuntimeError("Tier labels share a first token; use full-sequence scoring instead.")
    return ids


def build_inputs(tok, system_prompt, pitch):
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": pitch}]
    kwargs = dict(tokenize=False, add_generation_prompt=True)
    try:
        text = tok.apply_chat_template(messages, enable_thinking=False, **kwargs)
    except TypeError:
        text = tok.apply_chat_template(messages, **kwargs)
    return tok(text, return_tensors="pt")


def score(tok, model, ids, system_prompt, pitch):
    import torch
    enc = build_inputs(tok, system_prompt, pitch).to(model.device)
    with torch.no_grad():
        logits = model(**enc).logits[0, -1].float()
    logp = torch.log_softmax(logits, dim=-1)
    raw = {t: float(logp[i]) for t, i in ids.items()}
    z = math.log(sum(math.exp(v) for v in raw.values()))
    probs = {t: math.exp(v - z) for t, v in raw.items()}  # renormalized over the four tiers
    top = max(probs, key=probs.get)
    return {
        "predicted_tier": top,
        "confidence": round(probs[top], 4),
        "probabilities": {t: round(p, 4) for t, p in probs.items()},
        "expected_tier_value": round(sum(TIER_VALUE[t] * p for t, p in probs.items()), 4),
        "tier_mass_in_full_vocab": round(sum(math.exp(v) for v in raw.values()), 4),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", choices=MODELS, default="4b")
    ap.add_argument("--prompt", default=str(HERE / "prompts" / "ob_rqcontext.txt"))
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--pitch-file")
    src.add_argument("--jsonl")
    ap.add_argument("--field", default="rq_with_context")
    ap.add_argument("--out")
    ap.add_argument("--device", default="auto")
    a = ap.parse_args()
    system_prompt = Path(a.prompt).read_text()
    tok, model = load(a.model, a.device)
    ids = first_token_ids(tok)
    meta = {"model": MODELS[a.model], "prompt_file": Path(a.prompt).name}
    if a.pitch_file:
        res = score(tok, model, ids, system_prompt, Path(a.pitch_file).read_text().strip())
        print(json.dumps({**res, **meta}, indent=2))
        return
    out = open(a.out, "w") if a.out else sys.stdout
    for line in open(a.jsonl):
        row = json.loads(line)
        res = score(tok, model, ids, system_prompt, row[a.field])
        out.write(json.dumps({**{k: row[k] for k in row if k != a.field}, **res, **meta}) + "\n")


if __name__ == "__main__":
    main()
