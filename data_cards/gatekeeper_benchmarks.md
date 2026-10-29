# Data card: research-idea gatekeeper training and benchmark data

**Source:** Gong, Li, and Zhou (2026), arXiv:2603.16659. Public files: [FutureTech-OB/ai-taste](https://github.com/FutureTech-OB/ai-taste) (commit `3e6637c7b8faec0977185185c0bd315c58a9eba2`) and the Hugging Face collection [K1mG0ng/ai-taste-scientific](https://huggingface.co/collections/K1mG0ng/ai-taste-scientific). Data CC BY 4.0; code MIT.

**Unit.** A research pitch: one paragraph (about 120 to 150 words in the paper's protocol; the 120 management benchmark pitches range from 107 to 179 words, median 144) giving the phenomenon, the gap, the research question, a brief approach, and the contribution. Empirical results, author names, affiliations, and journal identity are removed.

**Label.** The four-tier standing (exceptional, strong, fair, limited) of the journal in which the source article was published. Tiers were assigned by field experts before any model was trained. In management, subject experts on the author team placed 19 journals into tiers; in the other fields, expert nominations were cross-checked against citation metrics and recognized journal-quality lists. The label is an institutional trace of where work was published. It is not a record of editorial decisions on submissions, and it is not a measure of objective quality. In the public management files the tiers are coded `top`, `top-`, `good`, `fair`, which map to exceptional, strong, fair, limited.

**Fields and sizes.** Eight fields: psychology, economics, communication, sociology, management, political science, business and finance, public administration. Training sets: 4,479 pitch-tier pairs in management; 2,094 to 5,593 in each other field. Held-out benchmarks: 120 pitches in management (30 per tier) and 200 in each other field (50 per tier), 1,520 in total, drawn from articles published after 30 June 2025. Training sets are disjoint from benchmarks.

**Known limits.** Pitches can retain field vocabulary that covaries with tier. Earlier versions of some benchmark papers may have circulated as working papers before the cutoff. Only published articles are included, so the label inherits the selectivity of past publication. Of the 120 archived management prediction records, 24 keep log-probabilities for all four tiers; the other 96 keep only the top class.

**Not included.** Full article texts (publisher copyright).
