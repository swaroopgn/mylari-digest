*Edition #9. Window: 18 to 25 November 2026. Every number below comes from the linked source.*

This week's theme: **the probabilities are the useful part.** A 150M encoder trained only on a rented decision model's labels lands within a point of its teacher, mistakes included; Comet trains a 1.7B LoRA judge on 600 of its own labelled turns and finds where it wins and where it doesn't; Barclays reads per-field confidence from token log-probabilities in document extraction and uses the uncertain fields as a training curriculum; Sheffield shows that reading label probabilities beats asking a zero-shot classifier how confident it is; and Intel counts how many decisions compression quietly flips. Five items made the cut.

## 1. No Labels? Borrow Them: Distilling a Classifier Locally

**Damien Riquet (Hornetsecurity)** · driquet.info, 21 Nov 2026 · [driquet.info](https://driquet.info/distilling-a-classifier/) · part 3 of his "Classifying Text Locally" series

**What he did.** A classification task with no gold labels: file 2026 arXiv papers into one of eight computer science categories from title and abstract. Six decision models from 2B to 27B (Base Labs Joey, Elephant and Mammoth; Perplexity Decider Flash v1.2 and Decider v1.2, rented through OpenRouter; OneJev1.6-4B run locally) labelled a 9,000-paper pool once. An Ettin-150M encoder was then fine-tuned on each teacher's answers (hard top label, or soft probabilities at temperature 2) on an Apple M5 laptop. Gold labels were used only to grade on a 2,000-paper test set, plus a "ceiling" Ettin and a TF-IDF baseline trained on 8,000 gold labels.

**Key results.**
- Every student lands on its teacher: **79.4 vs 79.8** macro-F1 for Decider 27B, 78.9 vs 79.3 for Mammoth 27B, 77.3 vs 76.5 for Elephant 9B; no student more than 0.8 points away.
- Mistakes carry over: on the 418 test papers Decider 27B got wrong, its student copied **67%**, fixed 27% and made a different mistake on 6%; overall agreement with the teacher 87.5%.
- Soft labels beat hard ones by 1.6 points (OneJev) and 1.0 (Mammoth), and tied for Decider: they cost nothing extra and never hurt.
- A better teacher makes a better student point for point; the Decision Index leaderboard did not pick the best teacher for this task, but a 100-paper pilot (2 cents for five rented teachers) nearly did.
- Labelling 9,000 papers with Decider 27B cost **$0.08**. The student answers in **32 ms** on the laptop's GPU vs 316 ms through the API. Ettin on gold labels scores **84.7**, 5.3 points above the best student, and TF-IDF on gold labels scores 83.9.

**Caveats.** A weekend project: one task, one student size, one to three seeds; arXiv categories are noisy author choices, and the teachers could in principle have seen some of the papers.

**Why it matters.** A clean, cheap recipe for when you have no labels: rent the best teacher once, keep its probabilities, serve a small student. But check a few hundred teacher labels by hand, because the student learns the teacher's systematic errors.

## 2. Build Your Own Judge: When a Fine-Tuned 1.7B Model Beats Jev and LLM-as-a-Judge (and When It Doesn't)

**Aswin Thiyagarajan (Comet)** · Comet blog, 19 Nov 2026 · [comet.com](https://www.comet.com/site/blog/finetune-judge-vs-jev/)

**What they did.** Took 1,000 real conversations with Ollie, the assistant inside Opik, and had gpt-5.5 answer three yes/no questions per turn (on topic, declined, answer sound). Split 600/100/300 and trained a LoRA adapter (6.4M trainable parameters) on Qwen3-1.7B, reading Yes/No option probabilities in both option orders to reduce position bias. Thresholds for every judge were set on validation. Compared with Jev 1.13 and a gpt-4o-mini LLM-as-a-Judge.

**Key results.**
- "Did Ollie decline?" on 300 held-out turns: accuracy **0.933** (fine-tuned) vs **0.857** (Jev) vs **0.883** (gpt-4o-mini); AUC 0.982 vs 0.914.
- Training took about **37 minutes on a MacBook**, one epoch, 450 optimizer steps.
- On attempted answers only (213 turns), Jev stayed ahead on soundness: AUC **0.724 vs 0.681**. The authors call it a knowledge problem, not a training problem.
- Before fine-tuning, Qwen3-1.7B said "yes" to 97% of turns (κ 0.05). A first fine-tune on CommonsenseQA improved that benchmark (0.597 to 0.784) and did nothing for judging.

**Caveats.** Labels come from a stronger model, not humans; one run on a 300-turn test set (±0.03 accuracy is noise); the fine-tuned model's raw probabilities are poorly calibrated until recalibrated on validation data.

**Why it matters.** A practical split: train a small judge for pattern decisions you ask often (declines, scope, format, policy), keep a general judge for decisions that need world or domain knowledge. And train on your task, not a proxy benchmark.

## 3. Could This BE Any More Wrong? Teaching VLMs to Know What They Don't Know in Document Extraction

**Varad Srivastava, Victor Casas Hernandez (AI Lab, Barclays Investment Bank)** · arXiv, 23 Nov 2026 · [arXiv:2611.30119](https://arxiv.org/abs/2611.30119)

**What they did.** Mapped the token log-probabilities a vision-language model already produces onto each value in its JSON output, giving a per-field confidence. Tested on CORD v2 receipts and Kleister NDA contracts with Qwen3-VL-8B, Granite-2.9B and Gemma 4-5.1B, routing fields into green/amber/red bins. Then used the uncertain fields as a training curriculum for rank-16 QLoRA fine-tuning with GRPO (and SFT for comparison).

**Key results.**
- Minimum token probability per field detects errors with AUROC **0.74-0.91**; verbalized confidence scores **0.53-0.56**.
- GRPO on **67** automatically selected CORD examples lifts accuracy from **78.5% to 87.5%**; 857 of 914 aligned fields route straight to green, cutting human review by **80%**. SFT on the same examples reached 82.4% with higher green precision (0.980).
- On multi-page NDA contracts (259 examples): accuracy 70.7% to 75.1%, error-detection AUROC 0.70 to 0.85.
- A frontier model as pseudo-label judge agreed with ground-truth rewards about 92% of the time.

**Caveats.** Two benchmarks; the main fine-tuning results are on one model (Qwen3-VL-8B), and the base model is overconfident (ECE 0.165 on CORD) before training. Sampling degraded calibration compared with greedy decoding.

**Why it matters.** Per-field confidence is nearly free if you keep the logprobs, and it tells you both what to send to a human and what to train on next.

## 4. LLMs Are Already Confidence-Aware Zero-Shot Classifiers

**Owen Cook, Xingyi Song (University of Sheffield)** · arXiv, 18 Nov 2026 · [arXiv:2611.25289](https://arxiv.org/abs/2611.25289)

**What they did.** Compared black-box confidence (verbalised confidence, sampling) with white-box methods that read token probabilities (P(True) and several logit-scoring methods with constrained generation) for eleven open-weight LLMs (1B-32B) on five classification datasets with 3 to 151 labels.

**Key results.**
- The confidence method rarely changes accuracy, but logit-based scoring discriminates right from wrong much better: AUROC **0.74-0.77** vs **0.57-0.66** for black-box methods.
- Replacing labels with single-token identifiers keeps discrimination but costs **3-6 accuracy points** on average.
- "Decision-only scoring", which scores only where labels diverge in a prefix tree, cuts decode steps by **88-96%** on the three largest label sets with comparable results.
- The best open-weight configurations (Gemma 4 31B, Qwen 3.5 9B) are competitive with the commercial Jev 1.13.0 classifier.

**Caveats.** Zero-shot only; five datasets.

**Why it matters.** If you already run an open model as a classifier, you have a usable confidence score in the logits. Don't ask the model how sure it is, and keep real label names.

## 5. Sirius-Tiamat: How Small Can a One-Pass Decision Encoder Get Before Its Decisions Change?

**Mohammed Nayeem Khan, Vrishank Tiwari (Intel Corporation)** · arXiv, 19 Nov 2026 · [arXiv:2611.26339](https://arxiv.org/abs/2611.26339)

**What they did.** Compressed Laya, a 421M-parameter one-pass decision encoder, with lower precision, weight rounding, layer deletion, early exit, distillation and vocabulary trimming. Counted decisions that differ from the full-precision model and tracked calibration (ECE) on 1,221 in-family synthetic items, 273 with an unseen schema, and 800 out-of-family questions from ARC, MMLU and HellaSwag.

**Key results.**
- bf16 flips **0.2%** of in-family decisions but **2.2%** out of family; 6-bit grouped rounding 1.3% and 5.9%; 4-bit grouped rounding 4.3% and 21.4%.
- Deleting 6 layers flips 0.9% in family and **9.1%** out of family, while ECE rises from **5.9% to 39.2%**. One fitted temperature, needing no labels, brings it back to **3.6%**.
- CPU dynamic int8 changes **30%** of decisions, nearly all through one layer. One scale per tensor fails below six bits.
- Distilling a 16-layer student cuts in-family flips from 44% to 9% (45% out of family). At equal stored size, rounding flips fewer decisions than deleting layers.

**Caveats.** Synthetic, LLM-labelled data and one architecture.

**Why it matters.** Compression checks on in-family data understate the damage. Count flipped decisions on held-out data, recheck calibration, and refit a temperature after you compress.

## Also noted

- **Fill in the Blanks: Non-Autoregressive Schema-Parallel Key Information Extraction with CTC Decoding** (Shaked Perek, Avihu Dekel, Ben Wiesel, Sivan Harary, Eli Schwartz; IBM Research; arXiv, 22 Nov 2026): the schema fixes the JSON structure, so a 4B extractor writes it from the schema and predicts all values in parallel in 4-6 passes; 3.5x faster than diffusion-VLM competitors on average and more accurate zero-shot on VAREX, CORD and FUNSD. [arXiv:2611.29460](https://arxiv.org/abs/2611.29460)
- **Decision Models for Multilingual Emotion Classification: A Comparative Study Against LLMs and Encoders** (Alessandro Piccolo, Francesco De Nicolò, Francesco Manco, Eufemia Lella; arXiv, 20 Nov 2026): across 10 social-media datasets in five languages, the best zero-shot systems sit about one macro-F1 point below an encoder fine-tuned on the target dataset and beat encoders fine-tuned on another dataset by 8-15 points; fine-tuning won by a wide margin only on GoEmotions. [arXiv:2611.27721](https://arxiv.org/abs/2611.27721)
- **WeMM-Ecom: Advancing Multimodal Content Understanding for WeChat E-Commerce** (Binhui Xie and colleagues; arXiv, 23 Nov 2026): a 0.8B to 35B-A3B multimodal family trained with e-commerce continued pre-training, on-policy distillation and RL; the authors say it powers catalog management, multimodal product search and livestream commerce in WeChat. [arXiv:2611.30662](https://arxiv.org/abs/2611.30662)
- **Meddies-PII: A Multilingual Framework for Personally Identifiable Information Extraction in Clinical De-identification** (Le Linh Uyen and colleagues; arXiv, 22 Nov 2026): a 350M BIOES token classifier trained on a synthetic 17-language dataset reaches mean exact-match F1 0.827 vs 0.672 for the strongest public system across 15 benchmarks. [arXiv:2611.29491](https://arxiv.org/abs/2611.29491)

## Patterns this week

**Keep the probabilities.** Soft labels from the teacher never hurt (Riquet); token logprobs flag wrong fields (Barclays) and wrong labels (Sheffield) far better than asked-for confidence. **Labels set the ceiling.** A student copies its teacher's systematic errors, and a small judge learns patterns, not knowledge (Comet). **Recheck after you compress.** Held-out flips and calibration move much more than in-family tests suggest, and one temperature fixes most of the calibration (Intel).
