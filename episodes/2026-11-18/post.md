*Edition #8. Window: 11 to 18 November 2026. Every number below comes from the linked source.*

This week's theme: **distill the probabilities, send only the hard cases to a big model, and find out where your small model stops being reliable.** Perplexity distills a 27B decision model into a 4B one by matching its output distribution; a swap test across 24 ACL-venue papers shows when a zero-shot decision model can replace a fine-tuned classifier and what 500 labels buy you; an ICD-10 coder calls a frontier model on about a third of cases and beats calling it on all of them; decision models extract pathology fields fast and with calibrated probabilities, but not for numbers or unreported fields; and a Japanese clinical NER study shows how output-token limits can decide a BERT-versus-LLM comparison. Five items made the cut.

## 1. Perplexity Decider v1.3: Training, eval, and use cases

**Perplexity** · Perplexity blog, 12 Nov 2026 · [perplexity.ai](https://www.perplexity.ai/hub/blog/perplexity-decider) · model card: [perplexity-ai/pplx-decider-flash-v1.3](https://huggingface.co/perplexity-ai/pplx-decider-flash-v1.3) · coverage: [Unite.AI](https://www.unite.ai/perplexity-releases-decider-v1-3-models-with-text-span-extraction/)

**What they did.** Released Decider v1.3 and the smaller Decider Flash v1.3, decision models that return a probability for every option of a typed question (binary, multi-class, ordered score) instead of generating text. Intended uses: judging outputs, routing, moderation and security, filtering and tagging, retrieval and reranking. v1.3 adds Locate, which returns verbatim text spans with character offsets (for NER, PII detection, extractive QA).

**Method.** The large model is built on Qwen3.8-27B; Flash on Qwen3.5-4B (about 8.5 GiB of BF16 weights). Training: generalist full fine-tuning on hundreds of public datasets converted to one state/question/options format (benchmark training splits excluded), then targeted LoRA stages for domains and tasks, to avoid drifting from the generalist model. Flash is then trained with the large model as teacher: the teacher's predicted output distribution replaces the gold labels, and the student minimises KL divergence to it. The decision head is read at a marker token, and a temperature fitted on held-out data is stored with the checkpoint.

**Key results.**
- Perplexity reports that KL distillation **outperformed cross-entropy on the same training data** on held-out data; cross-entropy did better only on benchmarks with dedicated training data. Their hypothesis: distillation transfers the teacher's confidence over non-gold alternatives.
- On a sample of one million deduplicated production API requests (2,318,887 questions), v1.3 agreed with frontier LLM judges on **93.98%** (v1.2: 93.68%). Cost for that sample: **$26.47** (v1.3) vs **$13.24** (Flash).
- Model card: the fast path was about 1.7-1.9x faster than default batching with 99.6-99.7% top-answer agreement.

**Caveats.** Vendor-reported numbers; production agreement is against LLM judges, not ground truth. The card itself advises calibrating thresholds on your own traffic, since one temperature cannot be right for every task. (The blog blocked direct fetching from our side; the method and cost figures above were cross-checked against the model card and Unite.AI's coverage.)

**Why it matters.** A clear production recipe for distilling a classifier: train the student on the teacher's full probability distribution, not just its top label, and you keep more of the teacher's generalisation at half the cost.

## 2. Do We Still Need Fine-Tuned Classifiers? Swapping Typed Decision Models into 24 ACL-Venue Papers

**Marek Šuppa (Comenius University in Bratislava, Cisco), Jaroslav Kopčan (Kempelen Institute of Intelligent Technologies)** · arXiv, 15 Nov 2026 · [arXiv:2611.20191](https://arxiv.org/abs/2611.20191)

**What they did.** Took 24 ACL-venue papers that fine-tune a task-specific classifier and swapped each predictor for a zero-shot Typed Decision Model (TypeSafe's Jev), keeping each paper's splits, label definitions and metric. Results were checked with Cloudflare's Clef, Microsoft-Decision-1 and OpenAI's GPT-6 Luna Decisions. The 46 English test sets, with questions and published scores, are released as the TDM-Gauntlet benchmark.

**Key results.**
- Zero-shot, Jev directly replaced the paper's predictor on **12 of 46** test sets, mostly single judgments with plain labels, rarely where the paper's method was trained on its labels.
- Where Jev scored lower, the most common cause was **an annotation convention that the label name does not state**.
- With **500 training labels** plus validation and no user-managed GPU, calibration plus GEPA-style prompt optimisation closed a **median 72%** of the gap to the paper's method (about twice what off-the-shelf GEPA closed), for a median **$1.66 per search**.
- On the same labels, fine-tuned encoders such as RoBERTa and DeBERTa closed **59%**; LoRA fine-tuning of Qwen3.8-27B closed **97%**.

**Caveats.** English only; academic benchmarks rather than production traffic.

**Why it matters.** A practical decision ladder: try zero-shot for plain labels, spend 500 labels on calibration and prompt search next, and fine-tune when you need the last points. And read your annotation guide: the rules hidden behind label names are what zero-shot models miss.

## 3. Call-Efficient ICD-10 Code Prediction via Supervised Candidate Generation and Selective LLM Invocation

**Ilia Kopanichuk, Daniil Kartashev, Yuri Bolkonsky, Petr Anokhin, Vladimir Makharev, Iaroslav Bespalov, Dmitry V. Dylov (AIRI, MIPT, Skoltech, Innopolis University, Lomonosov Moscow State University)** · arXiv, 16 Nov 2026 · [arXiv:2611.21891](https://arxiv.org/abs/2611.21891)

**What they did.** Assign ICD-10 codes from short, noisy clinical diagnosis text: a hierarchical, strongly imbalanced label space. The pipeline combines transformer embeddings, tree-based supervised candidate generation, candidate-level reranking, and an LLM that is called only when a gate says so.

**Method.** Leakage-safe evaluation: model and threshold selection on out-of-fold cross-validation predictions; final numbers on a locked test set with zero shared source-file groups between train and test.

**Key results.**
- Supervised parent-code candidate generator: **74.32%** Top-1 and **93.05%** Top-10 coverage on the locked test set.
- Zero-shot GPT-5.6-Sol on every diagnosis: **81.01%** Top-1.
- Final deployable system (Pre-LLM fusion): **83.19%** locked-test accuracy (81.24% out-of-fold) while calling the LLM on only **31.97%** of cases. Error rate falls from 25.68% to 16.81%, a **34.5%** relative reduction.

**Caveats.** One dataset of short diagnosis phrases; accuracy at parent-code level.

**Why it matters.** The big model is most useful as a controlled reranker over the small model's candidates on uncertain cases, not as a coder for every row. Fewer calls and better accuracy at the same time.

## 4. Can decision models extract clinical data from cancer pathology reports? An evaluation of accuracy, calibration, and failure modes

**Indranil Mallick, Paromita Roy (Tata Medical Center, Kolkata)** · arXiv, 15 Nov 2026 · [arXiv:2611.20129](https://arxiv.org/abs/2611.20129)

**What they did.** Used two open-weight decision models, Nimble 9B and Tev1 4B, to extract **25 fields** from **1,113** oral cavity cancer pathology reports at a single centre, against a prospectively maintained clinical database. Compared with Qwen3.5 9B run locally and GLM-5.3-flash via a cloud API.

**Key results.**
- Tev1 mean field accuracy **0.917** (95% CI 0.913-0.920), the same as Qwen3.5 9B (0.918; p = 0.26), and **four times faster** (15 s vs 61 s per report). Nimble 0.862; GLM-5.3-flash 0.986.
- Both decision models matched GLM-5.3-flash on simple yes/no categories, but were weak on **measurements binned into categories**, on **fields whose answer was not reported**, and on some complex decisions such as involved margins.
- Nimble's main problem was **asking 25 questions in one request**; with two questions per request its accuracy improved.
- Pooled probabilities were well calibrated (expected calibration error 0.022 and 0.026), but **did not flag systematic errors within single fields**.
- Simulated escalation: sending Tev1 answers with probability below 0.94 to GLM-5.3-flash raised accuracy to **0.982**, with **38%** of answers escalated.

**Caveats.** One centre, one cancer type; escalation result is simulated.

**Why it matters.** Validate a small extractor in the exact configuration you will run (questions per request included), restrict it to the fields where it is reliable, and don't trust good pooled calibration to catch a field that is consistently wrong.

## 5. Fine-Grained Japanese Clinical Named Entity Recognition: A Controlled Comparison of BERT and Open-Weight Large Language Models

**Feng Han, Ayako Yagahara, Kenji Hirata, Atsushi Yoshida, Kohsuke Kudo (Hokkaido University, Hokkaido University of Science)** · arXiv, 17 Nov 2026 · [arXiv:2611.22219](https://arxiv.org/abs/2611.22219)

**What they did.** Compared two fine-tuned BERT-CRF baselines with nine open-weight LLMs on iCorpus (113 entity categories): 1,672 training sentences, 433 test sentences from 36 documents. LLMs ran zero-shot with and without JSON Schema constraints, and with three-seed QLoRA fine-tuning under different output-token limits (900, and model-specific 2,600 or 4,096).

**Key results.**
- Best zero-shot relaxed F1 **0.337**, against **0.836-0.841** for the BERT baselines.
- At the larger output limits, all eight fine-tuned LLMs with at least 13B total parameters beat both BERT baselines: relaxed F1 **0.882-0.914**, exact-surface F1 0.840-0.880.
- Raising the output limit improved relaxed F1 by **0.052-0.085** (three-seed means), with higher recall and fewer length-limited outputs.
- JSON Schema constraints changed relaxed F1 by only -0.014 to +0.008 for seven models; medical-specialised models showed no consistent advantage over their general counterparts.

**Caveats.** One historical case-report corpus; the LLMs that beat BERT are 13B and up, so the small fine-tuned encoder remains the cheap, strong baseline.

**Why it matters.** Dense extraction needs output room. A tight generation limit truncates answers and can make a fine-tuned model look worse than it is, and a schema does not fix a model that has not learned the task.

## Also noted

- **Can Decision Models Replace LLMs in Real-World Contact Center Classification and Judging Tasks?** (Md Tahmid Rahman Laskar, Xue-Yong Fu, Shashi Bhushan TN; Dialpad; arXiv, 17 Nov 2026): nine decision models vs thirteen generative LLMs, zero-shot, on eight contact-center tasks. Many decision models match frontier LLMs on classification and their confident predictions are more accurate, but most rarely choose the no-answer option, which accounts for most of their gap; judging quality drops sharply for smaller models, which are also more prone to position bias. [arXiv:2611.22949](https://arxiv.org/abs/2611.22949)
- **AdaMenu: Query-Adaptive Menus for Decision Models over Large Label Spaces** (Jiangze Yan and colleagues; arXiv, 13 Nov 2026): build a compact candidate menu from retrieved labelled examples and make one decision-model call; on label sets up to 1,016 labels it beats a beam-search baseline by 16.6-34.3 points on all 16 model and label-set pairs, and cuts input tokens 3.2-22.9x versus the full menu. [arXiv:2611.19005](https://arxiv.org/abs/2611.19005)
- **Train After You Measure: a Pre-Registered Learning Curve for Fine-Tuning Typed Decision Models on One User's Labels** (Federico Lucca; arXiv, 16 Nov 2026): LoRA on Tev1-0.8B and Tev1-4B with 50-587 email labels on a free T4; four of five pre-registered hypotheses refuted. A TF-IDF logistic regression stays ahead on the three action switches (0.931 vs 0.904 and 0.899) at under a millisecond per question against 306 and 1,681 ms. [arXiv:2611.21393](https://arxiv.org/abs/2611.21393)
- **UltraBERT-JEV: Encoder models for System One Applications** (Astarag Mohapatra; arXiv, 13 Nov 2026): a 380M encoder scoring options in one pass reaches 69.7-72.1% test accuracy against 67.6% for Qwen3-0.6B trained on the same data; scoring "yes" minus "no" gives the larger gain; 29 ms vs 68 ms per decision on an A100, but more peak memory (2.8 vs 2.2 GiB). [arXiv:2611.17867](https://arxiv.org/abs/2611.17867)
- **Small Models in AI Memory: What We Learned Making Entity Extraction LLM-Free** (Lazar Obradovic; cognee blog, 11 Nov 2026): GLiNER extracts entities and relations locally after two production fixes, a "document sketch" that picks entity types per document and dropping relations with ambiguous endpoints; roughly 30x faster per chunk than an estimated LLM baseline in their internal evaluation. [cognee.ai](https://www.cognee.ai/small-models-in-ai-memory)

## Patterns this week

**Small model on the common path, big model on the uncertain rest.** A supervised coder plus a gated LLM beats the LLM alone (ICD-10); escalating low-confidence answers recovers most of the gap (pathology). **Distill the distribution.** Matching the teacher's probabilities generalised better than gold labels (Perplexity). **Find where the small model stops.** Unstated annotation rules (TDM-Gauntlet), abstention (contact center), binned numbers and unreported fields (pathology), and output-token limits (Japanese NER). **Test the configuration you ship.** Questions per request, output limits and thresholds all move the numbers.
