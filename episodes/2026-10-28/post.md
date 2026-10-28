*Edition #5. Window: 21 to 28 October 2026. Every number below comes from the linked source.*

This week's theme: **score each decision instead of generating a list, check what your schema quietly asks for, and judge the action rather than the label.** LinkedIn turns a fine-tuned labeler into a per-candidate scorer; a preregistered study shows that a minimum count in a JSON schema makes open models pad their extraction lists; a cost-aware evaluation of IT ticket routing shows when to defer to a human; a controlled study separates LoRA from full fine-tuning for prompt-safety classifiers; and Atos fine-tunes small models for German hate-speech feature extraction. Five items made the cut.

## 1. From Generation to Scoring: Scaling LLM-Based Semantic Labeling at LinkedIn

**Jian Sheng, Sriram Vasudevan, Sundara Raman Ramachandran, Yang Hu, Junyu Zhou, Xiaojing Ma, Haolan Qin, Tiffany Zhou, Vedant Vipul Jhaveri, Ashwini Bhingare, Chinmay Kini, Qing Lan, Xiaoqing Wang, Suleyman Cetintas, Fedor Borisyuk (LinkedIn)** · arXiv, 26 Oct 2026 · [arXiv:2610.36383](https://arxiv.org/abs/2610.36383)

**What they did.** LinkedIn labels member profiles against a catalog of qualifications (skills, experience, education, licenses): retrieve candidates from the catalog, then label them in rounds. The deployed labeler used *packed generation*: many candidates in one prompt, and a fine-tuned LLM generates a comma-separated yes/no list. That couples independent decisions, spends decoding on the list and depends on the list being well-formed.

**Method.** *Semantic scoring*: fine-tune on single-candidate prompts and read each decision as one answer-token score from a prefill-only pass. *Multiple-Item Scoring (MIS)* packs hundreds of candidates into one sequence with attention masked between them, so the profile is encoded once without cross-candidate interaction. All methods use internally fine-tuned 1.5B decoder-only models. Offline inference runs as a model-agnostic Ray Data API (proposed upstream); serving uses MIS support contributed to SGLang.

**Key results.**
- Order sensitivity: reordering candidates changes at most **0.01%** of semantic-scoring labels at every training size (floating-point noise); packed generation changes **24.8%** at the smallest training size and still 0.86% at the largest.
- Data efficiency: semantic scoring reaches **86.3%** agreement with reference labels at 45K training pairs; packed generation reaches 50.8% at 45K and needs about **210K** pairs (~4.7x) to match.
- Throughput (stack-level, so engine, checkpoint and tuning also differ): offline **6.3K vs 5.1K labels/s per GPU (1.24x)** on H100; in serving at a one-second p99 target, **4.8K vs 2.5K labels/s per GPU (1.9x)** on H200.
- Exploratory: a fine-tuned 0.6B labeler had label quality comparable to the 1.5B in their runs; the authors report only its throughput and make no general size claim.

**Why it matters.** If each label depends only on the item and one candidate, make the model answer one candidate at a time and read a score. You get order invariance by construction, calibrated thresholds, and far less training data for the same quality.

## 2. Padding to k: A Minimum Count in the Schema Makes Open-Weight Models Pad Their Extraction Lists

**Abhishek Barali, Aayush Paudel** · arXiv, 22 Oct 2026 · [arXiv:2610.30997](https://arxiv.org/abs/2610.30997) · [code and run records](https://github.com/AbhishekBarali/padding-to-k)

**What they did.** A preregistered test of what happens when a JSON schema sets a minimum list length (`minItems`) but the document holds fewer items. Eight open-weight models on one GPU (plus six hosted models as reference), 558 real documents from nine annotated datasets (emails, meetings, receipts, job ads, clinical notes, reviews and more) holding 0 to 6 checked items. Counts of 1, 3 or 5, stated in prose, in a schema shown in the prompt, or in a schema the decoder enforces.

**Key results.**
- Models treat the count as a target: a minimum shown in the schema but not enforced raises the share of lists longer than the true count from **34.5% to 55.4%**. On documents a model gets exactly right with no count, a shown minimum still makes about a third of its lists pad (35.2%, post hoc).
- Padding is hard to catch: most added entries are real text from the document, and about **half pass a source-occurrence check**.
- Fixes only partly work: "fewer is fine" removes the effect on average but misses more true items; "up to k" in prose raises over-counting from 34.5% to 42.7%; an "N/A" option under an enforced minimum lowers padding only from 90.1% to 51.0%.
- Re-asking with the bare validation error, as schema-validating libraries do, made padding far more common in every run tested: **10.0% → 69.0%** for Qwen3.5-9B (exploratory).

**Why it matters.** Schema constraints are instructions. Audit your extraction schemas for `minItems` and "top k" wording, and don't rely on "is this span in the source?" as your hallucination check for list fields.

## 3. Cost-Aware Abstention for LLM-Based IT Ticket Classification

**Sachin Gupta** · arXiv, 22 Oct 2026 · [arXiv:2610.31657](https://arxiv.org/abs/2610.31657)

**What they did.** Treats ticket routing as a cost decision: choose a route-or-defer policy on calibration data under explicit costs (correct 0, human triage 1, wrong route 5), then evaluate that frozen policy once on held-out data. Public corpus of 47,837 tickets in eight classes; four trained non-LLM classifiers vs four LLMs, zero- and few-shot.

**Key results.**
- TF-IDF + logistic regression with a calibration-selected threshold of 0.60 cuts test cost from **0.763 to 0.472 (−38.1%, 95% CI 35.7–40.4%)** and wrong routes from **15.3% to 3.5%**.
- Frozen calibration-selected policies beat both always-route and always-defer in 14 of 16 cost settings (post hoc).
- On a stratified 1,000-ticket subset, the best prompted configuration reaches **0.477 accuracy vs 0.879 for fine-tuned DistilBERT**.
- Calibration is not discrimination: isotonic recalibration lowers expected calibration error without reliably improving ranking; GPT-4o-mini few-shot emits a single confidence value (correctness AUROC 0.500). At the break-even probability 0.80, seven prompted configurations defer every ticket; Haiku few-shot routes 19 of 1,000.
- Scope stated: one dataset, one prompt design, illustrative costs.

**Why it matters.** For routing and triage, the metric is cost per decision, including deferrals. Report correctness AUROC and risk-coverage next to calibration error, and choose thresholds from costs, not 0.5.

## 4. Task Format as a Factor in Adaptation: A Controlled Comparison of LoRA and Full Fine-Tuning for Prompt-Safety Classification

**John Alderete, Srirakshith Betageri, Jennifer Flynn, Alex Greenhalgh, Josh Rubin, Yoshita Varma Annam** · arXiv, 24 Oct 2026 · [arXiv:2610.33813](https://arxiv.org/abs/2610.33813)

**What they did.** Low-rank adaptation (LoRA) vs full fine-tuning for prompt-safety classification on a matched 400M encoder-decoder pair (Ettin), across three task formats, with up to 15 seeds per cell and pre-specified analyses.

**Key results.**
- At pre-specified learning rates, full fine-tuning leads LoRA by **2–3 points** in every architecture and format trained on the label alone. On the encoder, the gap **closes when both get the same learning-rate search**.
- Training LoRA to write a reason after its verdict adds **4.0 points** and closes the gap; a content-free sentence of equal length does not.
- Robustness: tuned models beat a prompted 8B model in domain but trail it by **8–23 points on adversarial jailbreaks** and flag **27–66% of benign but harmful-looking prompts** as unsafe, against the 8B's 2–3%.

**Why it matters.** Tune the learning rate and the training target before arguing about LoRA vs full fine-tuning. And for safety classifiers, in-domain accuracy hides over-flagging; keep a benign-but-scary test set.

## 5. Smaller model, sharper insights: How Atos approached structured outputs

**Aditi Saluja, Mustafa Eyceoz, Marius Kiskemper (Red Hat Developer)** · 27 Oct 2026 · [developers.redhat.com](https://developers.redhat.com/articles/2026/10/27/smaller-model-sharper-insights-how-atos-approached-structured-outputs)

**What they did.** A proof of value by Atos for a German public-sector customer that could only self-host. Task: extract 14 features from German social media comments (persons, locations, groups, slurs, tonality, vulgarity, spelling errors, violence triggers and more) into strict JSON, and detect calls to violence. GPT-4.1 (by API) generated synthetic training data; Phi-4 Mini 3.8B, Qwen2.5 1.5B and Qwen2.5 7B were tuned with supervised fine-tuning and orthogonal subspace fine-tuning (OSFT) on 3 NVIDIA L40 GPUs.

**Evaluation.** A custom 34-point rubric (28 for the 14 features, 3 for valid JSON, 3 for violence detection against a human-validated gold standard) on custom generated eval data; 39 runs (27 fine-tuned variants, 12 baselines including NuExtract 2B/8B and GPT-4.1).

**Key results.**
- Phi-4 Mini base produced valid JSON **1%** of the time; **92%** after one epoch, about **99%** with more training (GPT-4.1: 96%).
- Rubric: GPT-4.1 short prompt ~29, fine-tuned Phi-4 Mini ~30, GPT-4.1 detailed prompt 30.5, **fine-tuned Qwen2.5 7B 30.8**; all fine-tuned variants 29–30.8.
- Interpretive fields (tonality, summary) were the hardest for every model; NuExtract did well on concrete entities and dropped on those.

**Caveats.** A vendor post: the margins are small, the eval data was generated, and the headline mentions a 1B model while the best score came from the 7B.

**Why it matters.** When data can't leave the building, teacher-generated data plus a small fine-tune gets structured extraction to frontier level on the concrete fields. The interpretive fields are where you still need care.

## Also noted

- **Joint or Per-Option? Compact Encoders for Closed-Set Decisions from 17 Million to 1 Billion Parameters** (Tardelli Ronan Coelho Stekel; arXiv, 22 Oct 2026): per-option scoring beats joint scoring by 5.8 points of chance-corrected skill at 32M parameters (matched steps), but needs 5–13x more encoder passes; reordering options changes 12–23% of the joint models' answers; the 68M and 150M joint encoders beat a 435M DeBERTa-v3 zero-shot classifier by 4.9 and 5.9 points. [arXiv:2610.30970](https://arxiv.org/abs/2610.30970)
- **Measure Before You Train: Typed Decision Models vs. a Classical Baseline vs. a Generative LLM for Routing a Personal Multilingual Inbox** (Federico Lucca; arXiv, 23 Oct 2026): on 739 owner-labelled Italian/English emails, the production keyword rules scored 28% on message type against a 58% majority class; with ~200 labels logistic regression was most accurate on every field, but composed into actions it most often ignored emails needing action (18% vs 4% for the best LLM) until a cost-chosen threshold halved that. [arXiv:2610.32955](https://arxiv.org/abs/2610.32955)
- **Two Uncertainties Are Not One: Disagreement versus Decision-Risk in Cheap Structured Content Moderation** (Karan Yadav; arXiv, 23 Oct 2026): an audit on 142,658 human-labelled comments: a cheap typed-decision model's AUROC (0.83) was not statistically separable from 13 of 14 frontier models on a 56-item probe set, and annotator disagreement and decision risk call for different escalation signals. [arXiv:2610.33258](https://arxiv.org/abs/2610.33258)
- **Bug Severity Classification with Fine-Tuned Open LLMs** (Kanatov, Bayan, Boranbayev; arXiv, 25 Oct 2026): on 2,000 held-out Eclipse reports, QLoRA-tuned Llama 3 8B (macro-F1 0.526) showed no detectable difference from fine-tuned CodeBERT (0.518); zero-shot LLMs (0.305, 0.321) were below every TF-IDF model (0.430–0.489); 8% of test reports duplicated a training report. [arXiv:2610.34127](https://arxiv.org/abs/2610.34127)
- **RubriX: A Fast, Fine-Tunable Non-Autoregressive Rubric Judge** (Paramasivam, Rajkumar, CobuildX; arXiv, 26 Oct 2026): a LoRA-adapted encoder scores rubric levels by cosine similarity: 75.4% exact accuracy on held-out rubrics vs 49.8% for a Qwen3-8B judge, about 28 ms per judgment with level embeddings cached, from 10 to 3,000 tokens per level. [arXiv:2610.34875](https://arxiv.org/abs/2610.34875)

## Patterns this week

**One decision at a time, read as a score.** LinkedIn's per-candidate scoring and the per-option encoder study both remove order sensitivity that list-style or joint answers carry. **Your schema and prompt are part of the model.** A `minItems` turns into a target, and re-asking with validation errors makes it worse. **Judge the action, not the label.** Cost-aware thresholds and deferral (IT tickets, the inbox study) and benign out-of-domain tests (prompt safety) tell you more about production behaviour than in-domain accuracy.
