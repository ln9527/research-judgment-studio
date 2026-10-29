# Human-guided auto-research loop: specification and results summary

This folder documents the evaluator-guided idea-generation loop reported in Li (2026c, working paper, "Auto-research in low-verifiability domains: Learned evaluators as search objectives for idea generation"). It is a specification and a results summary. The full generation logs are not part of this release.

## Division of labor

- **Investigator.** Set the research brief and domain scope (organizational behavior, human resource management, general management), chose the seven theorizing logics, fixed the scoring rules and the feasibility threshold (3.0 on a 1 to 5 scale) in advance, required one-element-at-a-time changes, and decided when to open each branch. These choices were issued as 15 written directives to the agent. A summary is given below; the verbatim directives are not released here.
- **Agent (Claude Code).** Wrote concrete prompt variants, ran generation, computed scores, and applied the pre-set keep-or-discard rule, logging the reason for each decision.

## Search space

Seven theorizing logics, each built from modular prompt elements:

| Code | Logic | Grounding |
|---|---|---|
| M0 | Naive prompt | none |
| M1 | Gap-spotting | Corley and Gioia (2011) |
| M2 | Problematization | Alvesson and Sandberg (2011) |
| M3 | Analogical import | Cornelissen (2005) |
| M4 | Phenomenon-based theorizing | |
| M5 | Theory integration | Okhuysen and Bonardi (2011) |
| M6 | Disciplined imagination | Weick (1989) |

Default generator: GLM-5. Generator substitutions tested: Kimi K2.5, Qwen 3.6 Plus, Claude Opus 4.7, GPT-5.4.

## Objectives and constraint

- **Quality:** expected tier value (ETV, 1 to 4) averaged over three fine-tuned evaluators: GPT-4.1 SFT, GPT-4.1-nano SFT (both proprietary API fine-tunes), and the open-weight OB-30B (Qwen3-30B-A3B SFT).
- **Novelty:** mean cosine distance to the five nearest neighbors (KNN-5) in a frozen corpus of 4,108 published management pitches (text-embedding-3-large).
- **Feasibility:** 1 to 5 rating by GLM-5, with Gemini 3.1 Pro as a check; admissibility threshold 3.0 in the constrained branch.
- **Keep rule:** the AR-01 ledger records a one-element change as kept only if it improves both quality and novelty; configurations are ranked by the composite ETV + 10 x KNN-5; AR-03 also requires mean feasibility of at least 3.0.
- **External check:** 1,200 blinded pitches from 12 management journals (100 per journal, three journals per tier) plus 100 *Academy of Management Review* pitches; an independent pairwise judge (Gemini 3.1 Pro, 840 pair records).

## Branches

| Branch | What changed | Outcome |
|---|---|---|
| AR-01 | One element at a time from M3 | 14 variants, 5 kept, 9 discarded; winner M3v06 (ETV 3.813, KNN-5 0.394) |
| AR-02 | Scaffold transfer, critique-and-revise operator (E9v2), generator substitution | GPT-5.4 x M3v06_E9v2: ETV 3.919, KNN-5 0.411, feasibility 2.44 (below threshold) |
| AR-03 | Feasibility-gated search from M6, M2, M5 | Admissible winners M6v05 (ETV 3.390, KNN-5 0.379, feasibility 3.380) and M6v04 (ETV 3.472, KNN-5 0.341, feasibility 3.375) |

`results_summary.csv` lists every point in Figure 2b.

## Known limits

No blinded human validation of generated ideas yet; item-level agreement between the fine-tuned committee and the independent judge is low (Cohen's kappa 0.149); feasibility was rated by language models; one domain; two of the three evaluators are proprietary. The planned open release replaces them with the open-weight OB-30B and OB-4B checkpoints.
