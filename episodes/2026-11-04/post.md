*Edition #6. Window: 28 October to 4 November 2026. Every number below comes from the linked source.*

This week's theme: **read the task before you pick the model, check that your thresholds travel, and judge a second opinion on what it actually fixes.** A laptop benchmark shows when a fine-tuned encoder beats a prompted LLM and when it only ties; XDecideBench finds that English model picks and English-fitted confidence thresholds don't hold across languages; BERT students distilled from an LLM beat their teacher on the sentences that carry sentiment, while a constant "neutral" wins the headline metric; a study of selective escalation shows that uncertainty finds errors but other models rarely fix them; and a 560M Tajik embedder is fine-tuned in under an hour. Five items made the cut.

## 1. Do You Need an LLM for That? Classifying Text Locally

**Damien Riquet (Lead Research Engineer, Hornetsecurity, a Proofpoint company)** · blog, 1 Nov 2026 · [driquet.info](https://driquet.info/do-you-need-an-llm/) · [code](https://github.com/driquet/local-classification)

**What he did.** A weekend benchmark on one Apple M5 laptop (24 GB) comparing four ways to classify text: TF-IDF plus logistic regression, a fine-tuned Ettin-150M encoder, Qwen3.5-4B prompted zero-shot and few-shot (BF16, MLX, reading label probabilities), and OneJev1.6-4B, a decision model built on Qwen. Three tasks chosen to differ in kind: CLINC150 intents (words give the answer away), VAST stance (the answer is in the relation between comment and topic) and DynaSent round 2 (sentences written by crowdworkers to fool sentiment models).

**Evaluation.** Official train and test splits, macro-F1, labels used, training time, median latency per text at batch size 1, peak RAM while predicting. Learning curves average three draws up to 100 per class.

**Key results.**
- Full CLINC150 plus out-of-scope: TF-IDF **87.8** F1 (16 s training, 0.37 ms, 0.5 GB); Ettin **93.2** (16 min, 7.6 ms, 1.5 GB); Qwen zero-shot **79.7** (1.1 s, 17.6 GB); few-shot 79.0 (1.7 s); OneJev **95.7** (1.3 s, 17.7 GB).
- More intents hurt the generic prompt, not the trained model: from 50 intents the prompt falls behind because more intents share the same words.
- VAST: TF-IDF is at chance; Ettin 75.8; OneJev 80.6 but ten times slower; zero-shot far behind the encoder.
- DynaSent: four of the five approaches are within 2.7 points (a tie on a 720-sentence test set). Zero-shot Qwen with a two-line prompt does as well as an encoder trained on all **13,065** sentences.
- Labels needed for the encoder to beat both prompts: **25 per intent** on CLINC, **333 per class** (about 1,000) on VAST, never on DynaSent.

**Caveats.** One seed, one prompt, no tuning. The datasets are public and Qwen has likely seen them; OneJev's training data includes 206 CLINC150 training examples. One 4B LLM stands in for "an LLM".

**Why it matters.** The right answer depends on whether the words give the label away. If they do, a small fine-tuned encoder wins on quality, latency and memory with very few labels. If the words lie, labels buy little and a prompt is a fair choice.

## 2. XDecideBench: Evaluating Typed Decision Models and Confidence Policies Across Languages

**Marek Šuppa (Comenius University in Bratislava; Cisco Systems), Jaroslav Kopčan (Kempelen Institute of Intelligent Technologies)** · arXiv, 1 Nov 2026 · [arXiv:2611.01370](https://arxiv.org/abs/2611.01370)

**What they did.** A multilingual benchmark for Typed Decision Models, which return a probability for each declared option of a typed question (the kind used for routing, moderation and labeling). 9 suites, 122 languages, 88,425 texts and 153,875 typed questions, with a common scoring contract for valid answers, refusals and resampling.

**Method.** Scores eleven Typed Decision Models from ten developers, the Qwen backbones of three open heads, and a supervised mmBERT-base comparator fine-tuned on MASSIVE, SIB-200 and English MultiNLI. Tests confidence policies fitted on English (5% error threshold, conformal sets) unchanged on the other Core12 languages.

**Key results.**
- The best model in English loses significantly in **56 of 232** suite-language cells. On Burmese Belebele, Brier skill is .336 for Microsoft's Decision-1 against .814 for Jev.
- Three open fine-tuned heads beat their Qwen backbones in **all 12** development languages, with larger gains in low-web-share languages, but they remove a similar share of backbone errors in both groups, so the larger gain may reflect weaker base models.
- An English-fitted 5% error threshold lets through **7.8 to 12.4%** errors on German and French XNLI. Jev admits 10.8% of Swahili decisions against 46.8% of English ones.
- On the three datasets it was trained for, the supervised mmBERT comparator reaches **.673** Brier skill; Laya, a decision model on the same encoder, reaches .274.
- RTP-LX: the local gold toxicity label differs from the English one for 54% (4,016 of 7,400) of pairs.
- Rankings move: GPT-6 Luna is 8th of 10 on Core12 but 1st on the native INCLUDE exams (.600 vs .536). Kendall correlation with the Core12 ranking is .33 to .64 on other suites.

**Caveats.** Hosted and local readouts can differ; several models could only be scored through APIs.

**Why it matters.** If you ship a classifier or router in several languages, re-fit thresholds and re-check model choice per language. English results don't transfer, and a task-specific fine-tuned encoder is still a strong baseline.

## 3. Distilling Literary Sentiment from LLM Annotations into an Ordinal BERT Model

**Artem Suslov (Hokkai-Gakuen University), Takehiro Hashimoto (Chuo University)** · arXiv, 2 Nov 2026 · [arXiv:2611.02985](https://arxiv.org/abs/2611.02985) · [models](https://github.com/susurofu)

**What they did.** Gemma 4 31B labeled 10,889 literary sentences on a 10-point sentiment scale. Five BERT models (Large, Base, Medium, Small, Mini) were trained on those labels with ordinal regression (8,711 train, 1,089 validation, 1,089 test).

**Evaluation.** 1,923 sentences from Hemingway's *The Old Man and the Sea*, scored by two human annotators. Compared with the teacher, two general-domain RoBERTa sentiment classifiers and a constant-neutral baseline. MAE, Kendall's tau, and tolerance-based precision and accuracy (±1); separately on 305 non-neutral sentences (scores below 4 or above 6).

**Key results.**
- Rank correlation: teacher **0.604**, BERT-large **0.589**, BERT-base 0.580.
- All five BERT students had lower MAE than the general-domain classifiers.
- **84.1%** of human scores fell between 4 and 6, so the constant-neutral predictor had the lowest overall MAE (**0.597**), below every model.
- On non-neutral sentences, BERT-base beat the teacher: MAE **0.726 vs 1.116**, accuracy (±1) 0.803 vs 0.600. The constant-neutral baseline scored MAE 1.962 and 0 accuracy there.

**Caveats.** One literary work, no comparison against nominal three-class training, and no variation across random seeds, so the contribution of ordinal modeling is not isolated.

**Why it matters.** A small encoder distilled from LLM labels can match or beat its teacher where it counts. On skewed label distributions, report metrics on the classes you care about; the overall MAE crowned a model that always says neutral.

## 4. Finding Errors Is Not Enough: Selective Model Escalation for Entity-Targeted Sentiment Analysis

**Nishan Chatterjee, Matthew Purver, Antoine Doucet, Senja Pollak (Jožef Stefan Institute; Queen Mary University of London; University of La Rochelle; University of Ljubljana)** · arXiv, 2 Nov 2026 · [arXiv:2611.02989](https://arxiv.org/abs/2611.02989)

**What they did.** Entity-level sentiment analysis on long South Slavic news (AspectBench) plus two external datasets (SentiCoref, Slovenian; NewsMTSC, English). After training a primary encoder, they ask which uncertainty signals find errors, whether a second encoder or a local LLM (Gemma 3 27B, 4-bit, prompts optimised with DSPy) improves the selected predictions, and whether development data can pick the policy before test labels are seen.

**Method.** 80 candidate policies (signal, share routed, action) chosen on a discovery split with a confirmation veto, then frozen and tested. Paired source-group bootstrap intervals (10,000 resamples) and an accounting of extra GPU-minutes.

**Key results.**
- On SentiCoref, the least confident 10% (216 predictions) held 90 of the encoder's errors. A perfect fixer would add **9.14** macro-F1 points; the best evaluated action adds only **0.90**.
- Replacing with a second encoder corrected 24 of those errors but damaged **59** correct predictions; averaging corrected 20 and harmed 42.
- Encoder averaging helps on NewsMTSC (+1.51) but hurts SentiCoref.
- Development-selected policies route **30%** of records to encoder-assisted Gemma: **+1.02** on SentiCoref (interval includes zero) and **+1.71** on NewsMTSC.
- Sending more records is not consistently better: going from 10% to 20% helped only 7 of 18 dataset-prompt curves.
- Chronological data collection is risky: at 20% of the data, HBS reaches 49.46 macro-F1 vs 75.42 for random order.

**Caveats.** One second-encoder type per external dataset, one LLM, and cost estimates partly from historical timings and assumed prices.

**Why it matters.** Confidence tells you where to look, not who can fix it. Evaluate a fallback model on the exact predictions it would touch, counting the correct answers it breaks.

## 5. Saidzoda-Tajik-E5-Large: Fine-Tuning a 560M Embedder for Tajik Retrieval

**Tohir Saidzoda, Nekruz Maxudov, Bedil Karimov, Abubakr Abdullozoda, Amin Jalilov, Jonibek Kishvarov, Rahmonali Sharipov, Mariyamkhon Shodyeva (Saidzoda AI Lab, Dushanbe)** · arXiv, 31 Oct 2026 · [arXiv:2611.00592](https://arxiv.org/abs/2611.00592)

**What they did.** Fine-tuned multilingual-e5-large-instruct (560M) for Tajik question-to-passage retrieval, with the full recipe published.

**Method.** 235,140 pairs from questions written by their own Tajik LLM for passages from laws, tax documents, Wikipedia and web text; 36% of pairs are English and Russian replay so the model keeps those languages. Hard negatives mined with another embedder and filtered with a positive-aware margin (71% of in-domain pairs got one). Cached multiple-negatives loss, global batch 512, one epoch (466 steps, about **56 minutes** on one H100), fp32 with TF32.

**Key results.**
- Recall@10 on held-out laws **80.2 → 93.6%**; tax **82.6 → 94.5%**.
- Belebele Tajik (human-written, the only test not from their generator): 92.2 → 95.2%, intervals touching, so not confirmed.
- Russian and English unchanged (97.9 → 98.6, 98.9 → 98.9).
- Tied with Giga-Embeddings-3B (five times larger) on in-style law and tax questions; Qwen3-Embedding-8B reaches 76.3 on law.
- The same recipe on BGE-M3: +14.0 law, +13.8 tax, +8.4 Belebele Tajik.
- What failed: bfloat16 training (loss dropped to exactly zero at step 8), replacing Tajik letters with Russian ones, and merging trained weights back with the originals.

**Caveats.** Test questions for law, tax and Wikipedia come from the same generator as the training data, so the authors treat those scores as an upper limit. No run without replay.

**Why it matters.** For a low-resource language, an hour of contrastive fine-tuning on synthetic pairs gets a mid-size embedder level with models several times larger, as long as you keep replay data and check on a human-written set.

## Also noted

- **To Jev or Not to Jev: When Can System-1 Decision Models Replace LLM Judges?** (Shreyas Subramanian; arXiv, 31 Oct 2026): of 14 decision models, five were statistically indistinguishable from GPT-5.6 without reasoning on all five pairwise and best-of-4 benchmarks; with a reference answer, eleven reach 90.3–93.4% on JudgeBench; an injected note to the evaluator reverses 0–5% of correct verdicts for five models but 17–49% for the other nine. [arXiv:2611.00505](https://arxiv.org/abs/2611.00505)
- **Predicting What Answer Engines Cite** (Elisha Bajemon, Andre-Louis Rochet, TW3 Partners; arXiv, 28 Oct 2026): a LoRA-tuned Qwen3-Reranker-4B student trained on teacher labels (released as GEO Citation Ranker 4B) reaches Spearman 0.542–0.549 over three seeds, not distinguishable on 229 queries from Jev and 27B models at 0.575–0.578. [arXiv:2610.38090](https://arxiv.org/abs/2610.38090)
- **Grading the Unannotated: Insights from the WorkRB Skill Extraction Challenge at RecSys-HR 2026** (Warre Veys, Luis Gasco, Jens-Joris Decorte; arXiv, 2 Nov 2026): graded relevance over ESCO's 13,939 skills shows that top retrieve-and-rerank gains came from clearing nonsense out of the ranking window, and every sized submission used at least 42x the parameters of the baselines it beat. [arXiv:2611.03525](https://arxiv.org/abs/2611.03525)
- **Honest Small Decision Models for Finance** (Ajitabh Kumar; arXiv, 2 Nov 2026): one frozen LoRA recipe from 0.8B to 32B; narrow fine-tuning cost 9–45 points of general decision competence; best calibration at 2B (ECE 0.026); one mixed-corpus adapter matches or slightly exceeds the generalist on the public benchmark. [arXiv:2611.03755](https://arxiv.org/abs/2611.03755)
- **CST: Lightweight Risk Triage with Source-Grounded Evidence for Web Discussions** (Zhihua Wang and colleagues; arXiv, 1 Nov 2026): a CPU-only moderation triage that ranks harmful messages better than a fully fine-tuned multilingual model on six tasks; reviewers needed at least 27% less time with decision accuracy above 94%. [arXiv:2611.01710](https://arxiv.org/abs/2611.01710)

## Patterns this week

**Read the task first.** Whether the words give the label away decides between a cheap encoder and a prompt (Riquet). **Thresholds and model picks are per language.** English-fitted policies let through more errors elsewhere (XDecideBench). **Pick metrics that see the classes you care about.** A constant neutral can win overall MAE (literary sentiment). **Judge a fallback on what it touches.** Second opinions break correct answers as well as fix wrong ones (selective escalation).
