*Edition #3. Window: roughly 7 to 14 October 2026; two items (eBay and Amazon, both submitted 6 Oct) are a day older and labelled as such. Every number below comes from the linked source.*

This week's theme: **the label contract matters as much as the model.** Preply replaces a prompted frontier annotator with a 0.8B fine-tune once its teacher data is cleaned and its output is made checkable; eBay finds that the right student (encoder or small generator) depends on the text and on how fast the taxonomy grows; Consultant gets its biggest win by splitting extraction from decision before distilling to 350M; Amazon shows that serving settings alone can change a classifier's predictions; and Enterpret shows generated taxonomies that pass every node-level check and still fail as trees. Five items made the cut.

## 1. Grammar Concept Annotation at Scale: Deployed Fine-Tuned Small Language Models Outperform Prompted Frontier Models

**Marjan Celikik, Ana Peleteiro Ramallo, Javier Morales (Preply)** · arXiv, 7 Oct 2026 (v2 11 Oct) · [arXiv:2610.10827](https://arxiv.org/abs/2610.10827)

**What they did.** A grammar-mastery tracker for every English learner on the platform. For each learner utterance (plus an upstream corrected sentence) the model emits, in one pass, every curricular grammar concept used (34 in this version), the exact evidence span, a correct/incorrect judgment and a short explanation for errors, as pipe-delimited lines. The product pilot prompted GPT-5.4 with a 3,810-token prompt, which was far over the serving budget at full scale.

**Method.** Completion-only LoRA on Qwen3.5 (deployed: 0.8B; 4B as a reference comparator). Training data (~187k utterance groups) comes from a curation pipeline: GPT-5.4 fully re-reviews pilot annotations using spaCy-derived linguistic anchors and edit differences, a deterministic validator rejects non-substring spans and invalid labels, and synthetic examples are generated from "structural backbones" (concept and correctness sequences) sampled to boost rare concepts and planted errors. Fine-tuning lets the 0.8B model use a compact 375-token prompt (−90.2%).

**Evaluation.** Two human-adjudicated benchmarks: Golden (689 utterances, production distribution) and Golden2 (2,977 utterances, error-enriched). Nested criteria: concept (L1), plus exact span (L2), plus correctness (L3); paired bootstrap CIs and randomization tests; raw-supervision controls at matched budgets.

**Key results.**
- Golden, L3 precision / recall: prompted GPT-5.4 67.81 / 62.87, GPT-5.6 Sol 74.37 / 76.04, **fine-tuned 0.8B 82.74 / 85.16**. Untuned 0.8B was unusable (75.3 to 92.0% parse failures).
- The data pipeline vs raw teacher labels raised L3 recall by **36.9 to 40.7 points** at matched size, and Rare-9 recall on Golden2 by about 45 points.
- An LLM judge rated GPT-5.4's explanations higher (99.06% vs 93.88% for 0.8B), but after human audit all three systems were similar (about 95%): the judge favored its sibling.
- Served with vLLM on autoscaled single-GPU g6.2xlarge instances, failures fall back to GPT-5.4; recurring cost is 6.2% of the GPT-5.4 baseline (**~16× cheaper**); p95 latency 4.3 s.
- 35-day A/B test of the whole feature: engagement with progress +15.80%, scheduled hours +2.06%, GMV from new lessons +13.20%.

**Why it matters.** A full recipe for retiring a frontier annotator: clean the teacher's labels before distilling, make spans checkable by string identity, let fine-tuning absorb the long prompt, and keep the frontier model as a fallback. Also a clean example of why LLM judges need human calibration.

## 2. Multi-Label Topic Assignment via LLM Distillation: A Comparative Analysis of Generative vs. Discriminative Student Models

**Sourabh Kasliwal, Shubhranshu Singh (eBay)** · arXiv, 6 Oct 2026 *(one day before the window)* · [arXiv:2610.09063](https://arxiv.org/abs/2610.09063)

**What they did.** GPT-4o labels user-generated content against a taxonomy (iterative prompt tuning with expert audits), and students are trained on those labels for two production uses: buyer-seller conversation topics (112 topics; ~25k training conversations) and category-specific product-review topics (e.g. tread wear for tires; ~39k reviews).

**Method.** Compare discriminative encoders (DeBERTa-V3, ModernBERT; sigmoid heads, BCE) with LoRA-tuned generative SLMs at 1B, 4B and 8B that write the label list. Conversation examples use progressive context (each turn classified given the earlier turns); 10k extra conversations rich in rare topics were mined by embedding similarity.

**Evaluation.** Macro-F1 against the distilled oracle labels (so this measures fidelity to GPT-4o), by data type, per-label support, label-set size and latency.

**Key results.**
- Reviews: DeBERTa-V3 0.7047 vs SLM-1B 0.6502, SLM-8B 0.8031. Conversations: DeBERTa-V3 0.4062 vs **SLM-1B 0.4501**, SLM-8B 0.5404.
- Growing the conversation label set from 10 to 112 topics: DeBERTa-V3 0.5435 → 0.3504 (**−35.5%**), SLM-8B 0.4739 → 0.4728. At 10 labels the encoder was ahead.
- Latency: DeBERTa-V3 58 ms, ModernBERT 79 ms, SLM-1B 163 ms, SLM-8B 241 ms.
- Generators produced out-of-taxonomy labels (e.g. "shipping-issue") on 0.11 to 0.26% of samples; production maps them to the nearest valid label or drops them.
- SLM-8B deployed for both uses (conversations: ~250 requests/s on 9 H100s, P99 under 500 ms). In a 20% ramp A/B test, reviews meeting the quality threshold for approval rose **60%**.

**Why it matters.** A useful decision rule for the student: encoders for short, single-author text with a stable label set; small generators for noisy multi-turn text and taxonomies that keep growing, with a normalization step to enforce the schema.

## 3. Distilling a job title model to 350M parameters for CPU inference

**Consultant (engineering blog)** · 10 Oct 2026 · [consultant.dev](https://consultant.dev/blog/job-title-model-on-a-cpu-2026)

**What they did.** Normalize messy multilingual contract-assignment titles ("Systemutvecklare nivå 3, ref 4411") into one clean English job title, on hardware they already rent.

**Method.** Output contract first: the model returns JSON with `role`, a verbatim `evidence` quote and a verbatim `level_quote`; it never assigns seniority. Deterministic rules check the quotes exist, read the level word, reject company names, IDs and URLs, and retry once on invalid output. Gemma 4 E2B was LoRA-tuned on 2,083 labelled postings and then labelled 19,990 postings; LFM2.5-350M was trained on those plus the originals (LoRA rank 64, 1 epoch).

**Evaluation.** 200 postings from sources held out by hash (provider-disjoint), answers written under a fixed rubric before any model ran, Wilson 95% intervals.

**Key results.**
- Role matches (of 197): **distilled 350M 174 (88.3%)**, fine-tuned 2B teacher 173 (87.8%), 350M trained on 2,083 rows only 163 (82.7%). Hard failures 25 / 27 / 38 of 200.
- On earlier holdouts, switching a general 9B model from writing whole titles to the split output took role matches from 57% to 85% and seniority errors from 65 to 4 of 200.
- On a 4-vCPU Hetzner CX33 (EUR 5.49/month) with llama.cpp and a Q8_0 GGUF: about 1,700 postings/hour (~1.2M/month), under EUR 0.0044 per 1,000 titles. The 1B and 1.2B models were slower and no better; a mixture-of-experts model was slow because the task is mostly prompt reading.
- Caveats stated plainly: labels were written by an AI reviewer, one run on 200 items, overlapping intervals; the student copies its teacher's mistakes.

**Why it matters.** Two transferable lessons: split extraction (quote it) from decision (rules decide it) to kill a whole class of hallucinations, and when a tiny student lags, give it more teacher labels before giving it more parameters. Model published on Hugging Face (`bytelope/consultant-title-lfm350m-distilled`).

## 4. Same Text, Different Prediction: Serving-Context Nondeterminism in Text Classifiers

**Santhosh Kumar Kasa, Siva Rajesh Kasa, Sumit Negi (Amazon)** · arXiv, 6 Oct 2026 *(one day before the window)*; NeurIPS 2026 workshops · [arXiv:2610.09111](https://arxiv.org/abs/2610.09111)

**What they did.** Measured whether serving settings, not the model or the input, change text-classifier outputs: 180 classifiers (discriminative, pseudo-generative and fully generative; three sizes; five public datasets; three seeds), each evaluated across 3,960 serving contexts (padded length, batch size and composition, precision, quantization, device, backend).

**Key results.**
- Identical contexts reproduce logits bitwise, so every change is caused by the setting varied.
- **Changing padded length alone changes about 10% of predicted labels**, more than any other factor: with learned absolute positions and left padding, every real token moves to a new position. Assigning positions by order among real tokens removes the effect without hurting accuracy.
- Batch shape changes no labels in fp32 comparisons, but in bf16 it moves up to **56.7 percentage points** of probability mass; label changes concentrate at small margins.
- Fully generative classifiers change more labels than discriminative ones under the same serving changes.

**Why it matters.** Aggregate accuracy and F1 can't see which examples flip, while thresholds, ranking and filters consume the scores. Their recommendation: fix the serving settings, monitor class probabilities rather than labels, and recompute inputs on which fixed settings disagree.

## 5. From Plausible Hierarchies to Useful Taxonomies: Evaluating Agentic Harnesses on Customer Feedback

**Prabhath Chellingi, Raviraja G, Viraj Bagal (Enterpret)** · arXiv, 7 Oct 2026 · [arXiv:2610.09377](https://arxiv.org/abs/2610.09377)

**What they did.** Six taxonomies over two proprietary customer-feedback corpora (1,940 and 5,000 records): per corpus, a production reference and two runs of the same off-the-shelf agentic construction harness.

**Key results.**
- All six pass every generic LLM-judge check (description completeness 1.00, name-description match 0.97 to 1.00), and a product-coverage check even prefers the generated trees.
- Yet **97.7 to 100%** of generated leaf names restate an ancestor's name verbatim (references: 13.9% and 2.9%); in one tree all 158 parents at one level have exactly one child.
- Routing real records through the trees, a third to three quarters land under more than one top-level product area (references: about a fifth); trees rated equally correct differ by 27 points in cross-branch leakage, and one does worse than a random partition.
- Proposed fix: deterministic, judge-free whole-tree metrics (structural discriminators and team partitionability).

**Why it matters.** If small models tag content against a taxonomy, the taxonomy is part of the system. Node-by-node judging can't catch templated labels or leaky branches; measure the whole tree and the records routed through it.

## Also noted

- **GPT-5.6 Luna vs a fine-tuned model for ticket and intent classification** (ILLATE, a vendor; measured 5 to 8 Oct, updated 9 Oct 2026) — pre-registered test after OpenAI named Luna as the replacement for fine-tuned gpt-4.1-nano: Luna with the 20 most similar examples tied a small fine-tuned model on Banking77 (93.8% vs 94.0%) and CLINC150 (94.6% vs 95.1%) and trailed by 2.0 points on long CFPB complaints; the retrieved examples, not the model, made the difference (+6.6 points on Banking77). [illate.dev](https://illate.dev/luna-vs-fine-tuned-model)
- **When Do We Need On-Policy Distillation? Distilling on Offline Student Rollouts Is Often Better** (Zhao et al.; arXiv, 8 Oct 2026) — across 17 teacher-student pairs (1.5B to 235B), distilling on offline rollouts from the initial student beat on-policy distillation in 14, with up to +13.6% accuracy and 11.4× faster training. [arXiv:2610.11291](https://arxiv.org/abs/2610.11291)
- **FinVector-Market-4B: A Controlled Study of LoRA Adaptation for Structured Financial Tasks** (Khaybullina; arXiv, 6 Oct 2026) — supplying the JSON schema alone took base Qwen3.5-4B validity from 0% to 91.3%; rank-16 LoRA then added large task gains under matched prompting (e.g. branch-label agreement 20.1% → 89.5%). [arXiv:2610.08882](https://arxiv.org/abs/2610.08882)
- **Not Every Call Needs a Frontier Model** (Kasnesis et al.; arXiv, 6 Oct 2026) — per-call-site evaluation of 9 models in a deployed home-automation agent: the best local model was statistically indistinguishable from hosted ones at four of five call sites; routing each site to its best local model reached 91.8% vs 95.4%. [arXiv:2610.09021](https://arxiv.org/abs/2610.09021)

## Patterns this week

**Clean, checkable labels beat bigger students.** Preply's curation pipeline was worth about 40 points of strict recall; Consultant's 350M student caught its teacher with ten times more teacher labels, not more parameters. **Make outputs verifiable**: exact substring spans (Preply), verbatim quotes plus rules (Consultant), normalization back to the taxonomy (eBay). **Pick the student by the data**: encoders for short, stable label sets; small generators for noisy dialogue and growing taxonomies. **And the system around the model counts**: serving settings can flip labels and move scores (Amazon), and a plausible taxonomy can quietly break every count built on it (Enterpret).
