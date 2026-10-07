*Edition #2. Window: roughly 30 September – 7 October 2026; two items (RWS Language Weaver, first posted 29 Sep; Billennium, 24 Sep) are slightly older and labelled as such. Every number below comes from the linked source.*

This week's theme: **the large model moves offline — as a labeler, a teacher or a relevance judge — and a genuinely small student serves production.** Walmart scores a 220M T5's own generations with a relevance classifier and trains on the preferences; a recruiting platform retires its online LLM for a CPU-served 0.6B bi-encoder; a privacy tagger learns from frontier annotations into an encoder; AWS shows a moderation fine-tune gated by two macro-F1 targets; and a Polish safety-classifier paper is a masterclass in not fooling yourself with metrics. Five items made the cut.

## 1. Query Generation with Direct Preference Optimization for Document Expansion in E-commerce Search

**Kaihao Li, Feng Liu, Juexin Lin, Xunfan Cai, Zhen Yang, Tony Lee, Ciya Liao (Walmart Global Tech)** · arXiv, 3 Oct 2026 · [arXiv:2610.04352](https://arxiv.org/abs/2610.04352)

**What they did.** Search enrichment via document expansion (Doc2Query): a sequence-to-sequence model generates the queries a shopper might type for a product, and those are appended to the product before lexical indexing (an extra Solr text-matching field), to bridge vocabulary mismatch (e.g. "smart watch for kid" vs brand-named listings).

**Method (QGDPO).** (1) SFT of **T5-base (220M)** on 64M product–query pairs for 16M products (two years of engagement data, filtered to exact-match pairs, pairs already fully covered by the title removed, price/promo phrases stripped). (2) Run the SFT model over the training products and score each generated query with Walmart's in-house three-class relevance model (exact / substitute / irrelevant, ESCI-style). (3) Build (product, winning query, losing query) triplets — winners labelled exact, losers irrelevant — and train with **DPO** (10M triplets, learning rate 1e-6, β = 0.1). (4) At inference, a relevance filter keeps only queries whose exact-class probability clears a threshold set at 95% recall. Only tokens not already in the product information are indexed; inference runs offline daily on K80 GPUs.

**Evaluation.** A 1,000-product set judged by humans (top-5 beam-search queries), a 1.6M-product set judged by the relevance model, novel-token counts, and a two-week online A/B test plus human relevance assessment of top-ranked results.

**Key results.**
- Top-5 queries on the 1,000-product set, vs the production Doc2Query: QGDPO +8.07% exact-match predictions and −49.87% irrelevant; with the relevance filter, **+9.63% exact and −64.48% irrelevant**. Novel tokens per product stayed roughly stable (6.0 baseline → 4.9 with filtering).
- A second DPO round (QGDPO²) overfit: −50.40% irrelevant but slightly lower exact-match lift (+7.78%).
- Higher β increased hallucination; beam search beat top-k and top-k/top-p sampling (92.43% exact vs 87.73% / 89.15%).
- Online: NDCG@5 +0.93%, NDCG@10 +0.86%, **search-session add-to-cart rate +0.36%** (all significant); GMV +0.17% (not significant). Deployed on Walmart.com for full traffic.
- Side experiment: LoRA-tuned Mistral-7B (rank 256) beat SFT T5-base by +2.00% exact and −22.84% irrelevant on the large set, at much higher compute.

**Why it matters.** A clean template for preference-tuning a *generator* of metadata with an existing *classifier* as the judge — no human preference labels, a tiny model, and the filter and the DPO gains turned out to be complementary. The honest negative results (second DPO round, high β, sampling) are as useful as the headline.

## 2. Building Interpretable Feature Representations for Resume–Vacancy Matching by Distilling Production LLM Signals

**Ilya Chekin, Vyacheslav Malyugin, Vladimir Chirkov (BroutonLab), Mikhail Yurushkin (Curately)** · arXiv, 2 Oct 2026 · EMNLP 2026 · [arXiv:2610.03112](https://arxiv.org/abs/2610.03112)

**What they did.** Instead of a single fit score, the system extracts **eight named matching dimensions** per candidate–vacancy pair (job title match, industry experience, certifications, hard-skill experience, skill proficiency, experience recency, seniority alignment, skill context; seven ordinal, one binary) — essentially structured attribute extraction over document pairs.

**Method.** An LLM labeler (OpenAI GPT-5.2 mini) whose prompts were refined from recruiter feedback while it served an earlier production stage is now used **only offline**. Its labels (168,772 vacancy–resume pairs) train a **Qwen3-4B reranker as a cross-encoder teacher**, whose soft per-class outputs are distilled into a **Qwen3-Embedding-0.6B bi-encoder with LoRA (r = 32)** plus eight small MLP heads (proportional-odds ordinal outputs) and a vacancy-only "applicability" head that masks certification when the vacancy doesn't require one. Hybrid loss: KD + label-smoothed hard labels + monotonicity + margin. Label stability was checked with five repeated LLM runs on 5,000 pairs; two less stable dimensions use adaptive majority voting.

**Evaluation.** Student-to-teacher fidelity on a vacancy-disjoint split; ablations of the pair representation and loss terms; operational agreement with recruiter-recorded decisions; efficiency.

**Key results.**
- Fidelity to LLM labels (accuracy / macro-F1): majority 0.606 / 0.268; frozen encoder + MLP 0.760 / 0.669; cross-encoder teacher 0.934 / 0.897; **production bi-encoder 0.886 / 0.849**. KD gave the largest single gain over hard-label cross-entropy (0.825 → 0.840).
- Deployed student matches **888 of 927 (95.79%)** recruiter-recorded values (non-blinded — recruiters saw the prediction first); the LLM labeler matched 924/927. Seniority alignment is the weak dimension (86/120, 71.7%).
- ~5,500 resumes/s on a single CPU with cached embeddings, ~$4.7×10⁻⁵ per resume including offline precompute; training ~4.5 hours on one A100.

**Why it matters.** The clearest write-up this week of a full "LLM labeler → cross-encoder teacher → cacheable student" ladder, with the prompt-refinement loop and retraining lifecycle spelled out — and with unusually candid framing of what the agreement number does and doesn't prove. The applicability head is a neat trick for any attribute that only exists for some items.

## 3. Strong Multilingual Privacy Tagging at Encoder Speed

**Jonathan Graehl (RWS Language Weaver)** · arXiv, v1 29 Sep 2026, v2 6 Oct 2026 *(first posted slightly before the window)* · [arXiv:2609.38630](https://arxiv.org/abs/2609.38630)

**What they did.** A fine-grained multilingual named-entity tagger for privacy redaction (31 types in its "Ont3" ontology, 35 languages), built by distilling prompted frontier-model annotations into an encoder.

**Method.** Fine-tune **XLM-R-large** with a single affine BIOES token-classification head. Two training tricks: **replay human-gold corpora labelled under other schemas** via label mappings, with *coverage-aware masking* so entity types a corpus never annotated aren't treated as negatives; and a learned **±1-character boundary adjustment** to repair subword span errors. Also studied: how to weight unmarked tokens from incomplete teacher annotations.

**Evaluation.** 1,283 human-gold test segments in seven languages (redaction F1), plus a 1,201-segment frontier-annotated development set (exact typed-span F1), against published systems, local LLM annotators and alternative encoders.

**Key results.**
- **Redaction F1 88.8** vs 69.1 for published GLiNER2 (68.8 without exempting its 11 unrepresentable types), 67.8 for GLiNER2 adapted to the same new data, 57.3 for Microsoft Presidio and 35.8 for the best published OpenAI Privacy Filter fine-tune.
- Mapped-gold replay raised human-gold F1 by ten points in a matched precursor experiment without loss on frontier-annotated text; boundary adjustment adds 1.7 exact typed-span F1; ~50K more annotated sentences moved exact typed-span F1 from 74.5 to 76.3.
- XLM-R-XL (3.5B) did *not* beat XLM-R-large. Local LLMs on a single 96 GB GPU were weaker annotators, with prompted annotation roughly 180–1,100× slower.
- CPU throughput 4.9× GLiNER2 (675 vs 138 input tokens/s). One full fit ≈ 2.3 GPU-hours (~$5); re-pricing the recorded annotation calls gives ~$53.

**Why it matters.** For extraction tasks with a fixed label inventory, "frontier model annotates, encoder serves" still wins on both quality and cost — and the coverage-aware masking trick applies to anyone merging datasets with different label schemes. Code, prompts and recipes are released; weights and training data are not.

## 4. How uniopen customized Amazon Nova to their retail moderation policies for production deployment

**Felix Chin, Jia-You Lin, Ray Wang, Linpo Guo, David Hung (AWS / uniopen)** · AWS Machine Learning Blog, 1 Oct 2026 · [aws.amazon.com](https://aws.amazon.com/blogs/machine-learning/how-uniopen-customized-amazon-nova-to-their-retail-moderation-policies-for-production-deployment/)

**What they did.** uniopen, a membership and e-commerce platform from Taiwan's Uni-President Enterprises Group, classifies each conversation window on two axes: **behavior** (nine categories) and **subject** (brand, other, forbidden). Note: Amazon Nova 2 Lite's parameter count isn't disclosed, so treat "small" loosely here.

**Method.** LoRA SFT of Amazon Nova 2 Lite in SageMaker AI on 3,391 training windows; Nova 2 Pro drafts candidate corrections for user-reported errors, but **a human must verify every correction** before it enters training. Promotion runs through hard gates (must-pass regressions) and soft gates (warnings such as a per-class drop, which require admin approval), orchestrated with Argo on EKS and tracked in DynamoDB.

**Evaluation.** A fixed held-out set of 737 conversation windows; per-behavior macro-F1 and subject-type macro-F1, each with a production target.

**Key results.**

| Metric | Baseline | Fine-tuned (JSON) | + line-format output | Target |
|---|---|---|---|---|
| Per Behavior Macro F1 | 0.5852 | 0.8364 | 0.8550 | ≥ 0.8500 |
| Subject Type Macro F1 | 0.4162 | 0.8302 | 0.8491 | ≥ 0.8200 |

**Why it matters.** Two practical lessons: fine-tuning does the heavy lifting on a business-specific taxonomy, and a **zero-training output-format change (JSON → line-based)** was what pushed both metrics over target. Using two macro-F1 release gates stops an improvement on one axis from hiding a regression on the other.

## 5. Baszta: Data-Centric Fine-Tuning of a Polish Multi-Label Safety Classifier

**Adam Górski, Mateusz Jąkalak, Rafał Jakubowski (Billennium S.A.)** · arXiv, 24 Sep 2026 *(slightly older than the window)* · [arXiv:2609.29266](https://arxiv.org/abs/2609.29266)

**What they did.** A five-category Polish content-safety classifier (hate, vulgarity, sexual content, crime, self-harm) from **HerBERT-base (124M)** with a Focal + R-Drop objective, compared with Bielik Guard ("Sójka") on the shared out-of-distribution Gadzi Język benchmark.

**Evaluation (the point of the paper).** Both systems get per-category threshold tuning on the same calibration split, paired bootstrap tests, a degenerate baseline, calibration metrics, and two operating points reported rather than the flattering one.

**Key results.**
- Both-tuned: micro F1 **0.929 vs 0.903** (diff +0.026, 95% CI [+0.004, +0.049], p = 0.011); macro F1 0.712 vs 0.782 — the earlier macro "lead" was an artifact of comparing a tuned model with an untuned one.
- The benchmark is 97% crime-positive (322 of 333 test rows): **always predicting "crime" scores 0.910 micro F1** (0.197 macro), so micro barely separates either model from a degenerate strategy.
- The OOD gap is calibration, not discrimination: per-category temperature scaling recovers it where Platt scaling and isotonic regression don't — but only if the calibration set contains safe text.
- Per-class cost-sensitive weighting and mean pooling each raised in-distribution macro F1 while *lowering* the OOD figure.

**Why it matters.** A reusable checklist for anyone shipping small moderation or tagging classifiers: always report the always-majority baseline, tune thresholds symmetrically before claiming wins, separate calibration from ranking, and select for robustness directly.

## Also noted

- **Search-Aware Reinforcement Learning for Multi-Component Query Understanding in Roblox Game Search** (Choi et al., Roblox / Emory; arXiv, 24 Sep 2026, older) — distill a frontier teacher into Qwen3.5 2B/4B students (zero-shot format validity of 0.1%/0.8% rises to 98.9%/99.3% after SFT), then GRPO with per-component rewards from the live search engine: NDCG@20 +8.9 over the SFT policy and +3.5 over a single end-to-end reward. [arXiv:2609.30177](https://arxiv.org/abs/2609.30177)
- **Guard Models Are Overconfident Where Base Models Are Uncertain** (Hong, Jung, Kim; arXiv, 29 Sep 2026; EMNLP 2026 Findings) — adversarial attacks degrade guard-model calibration by an order of magnitude, while the base model often still signals uncertainty on the same inputs. [arXiv:2609.36477](https://arxiv.org/abs/2609.36477)
- **Autonomous Structuring of Radiology Reports Across Modalities at Archive Scale** (Puttkammer et al.; arXiv, 3 Oct 2026) — not a small model (gpt-oss-120B, constrained decoding, one local GPU), but a strong archive-scale document-structuring case: 96.5% of 2,186,982 reports structured at 1,258 reports/hour; residents left 88.7% of 24,638 fields unchanged. [arXiv:2610.04541](https://arxiv.org/abs/2610.04541)

## Patterns this week

**The big model goes offline.** Walmart's relevance classifier judges its generator's outputs; BroutonLab's LLM labeler and RWS's frontier annotators never see production traffic; Roblox's teacher only initializes the policy. **Students got genuinely small** — a 220M T5, a 0.6B embedding model, XLM-R-large, a 124M HerBERT — and two papers found the next size up didn't help (XLM-R-XL) or wasn't worth the compute (Mistral-7B). **Preference and feedback loops replace manual labels**: classifier-scored DPO pairs, recruiter-refined prompts, human-verified moderation corrections. **Output format is a lever**: uniopen's JSON → line-format switch cleared both production targets without retraining. And **evaluation honesty is a production skill**: matched threshold tuning, degenerate baselines, non-blinded caveats stated plainly, and release gates on per-class macro metrics rather than one headline number.
