# Taste-as-learning-signal ledger harness

A small local Python standard-library CLI for keeping three proposed study components analytically separate. This is a technical harness, not a deployed study, validated measure, preregistration, or academic proposal. It makes no network or model calls. The organizational research vignettes in the synthetic fixture are invented test content.

The bundled `fixtures/study.synthetic.json` and `fixtures/ratings.synthetic.csv` contain invented content, labels, and ratings only. They are for software checks and demonstrations, never empirical evidence. No participant data is included.

## Study components

1. **Fixed-pool selection.** Arms must contain the same candidate IDs and exact text hashes, and each must select the same preregistered `k`. The synthetic fixture demonstrates taste-guided, baseline, and random selection conditions. Taste judgments use ordinal labels (`exceptional`, `strong`, `fair`, `limited`), not probabilities. Independent external ratings are collected on a blinded review file. The file given to reviewers contains one row per unique candidate and omits arm, condition, and taste labels. `export-blind` writes the separate key map; keep that file private. A pool fingerprint binds the review export and key map to the current fixed-pool design. The descriptive summary joins external ratings to arm selections only when explicitly given a key map that exactly matches the current ledger.
2. **Iterative search.** Each revision records parent/revision IDs, model-call and token usage, ordinal taste label (where applicable), and provenance such as model, prompt, and scorer versions. Arm-wide values are checked against declared **ceilings**. The harness never asserts strict budget equality; actual calls and tokens can differ below the ceilings.
3. **Unaided transfer.** Separate transfer tasks are explicitly marked unaided. `import-transfer` records pseudonymous subject codes, response text, timestamp, and import provenance in a new output ledger. For human collection, first record an approved or formally determined protocol reference in the ledger's `governance` object. The synthetic fixture has no such determination because its response is fictional.

The harness does not use source-journal tier labels as rewards or proof that taste labels are valid. The only allowed rating dimensions are novelty, value, and feasibility, each rated 1–7 by the independent rubric. Summaries first average ratings within each candidate, then average candidate means equally; they report `n_items`, `n_ratings`, and a separate `pooled_rating_mean` so unequal rater counts do not silently change the primary descriptive mean's item weighting. These are descriptive only: no significance tests, causal estimates, or learning claims. A real study still needs a designed assignment, frozen prompts/rubrics, a blinded rating protocol, power and missingness plans, consent/privacy decisions, and independent analysis.

## Run

From this directory:

```sh
python3 ledger.py validate fixtures/study.synthetic.json
python3 ledger.py export-blind fixtures/study.synthetic.json \
  --review /tmp/reviewer.csv --key-map /tmp/private-key-map.csv
python3 ledger.py import-ratings fixtures/study.synthetic.json \
  --blind-export /tmp/reviewer.csv --ratings fixtures/ratings.synthetic.csv \
  --out /tmp/study-with-ratings.json
python3 ledger.py summarize /tmp/study-with-ratings.json \
  --key-map /tmp/private-key-map.csv --csv /tmp/descriptive-summary.csv
python3 ledger.py import-transfer fixtures/study.synthetic.json \
  --responses fixtures/transfer-responses.synthetic.csv --out /tmp/study-with-transfer.json
```

`import-ratings` rejects unknown blind IDs, duplicate reviewer × candidate × dimension rows, missing candidate/dimension coverage, invalid dimensions, and ratings outside integer range 1–7. Reviewers use study-issued pseudonymous codes, not names or email addresses. It appends normalized rows plus a provenance event to a new output file; it does not overwrite the input ledger. `import-transfer` likewise writes a new ledger and rejects unknown tasks, missing values, and duplicate task/subject responses. `validate` reports the ledger's recorded `fixture_status`; structural validity does not prove study approval or data validity.

The generated reviewer CSV and private key map should be stored separately. Do not send the key map to reviewers. Avoid putting direct identifiers, confidential text, credentials, or production data in this local research artifact. The JSON Schema is a portable structural reference; the executable validator additionally checks cross-arm hashes, fixed selection counts, budget ceilings, revision ancestry and hashes, deterministic blind IDs, pool fingerprints, key-map equality, and event provenance.

## Validation

```sh
python3 -m unittest discover -s tests -v
```

All bundled records, taste labels, and external ratings are synthetic. The event history is an ordinary editable JSON record, not a tamper-proof audit trail. The script is implementation scaffolding only; its passing tests do not establish construct validity, inter-rater reliability, treatment effectiveness, or research approval.
