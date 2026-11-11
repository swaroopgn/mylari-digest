*Edition #7. Window: 4 to 11 November 2026. Every number below comes from the linked source.*

This week's theme: **let the small model take the first pass, check the exact artifact you ship, and keep your examples in line with your definitions.** Atlassian fine-tunes a 4B model with reasoning traces and puts it in front of a 20B safety model; a one-person jobs API distills a 400M extractor and keeps a salary only if its digits are in the posting; Mobile AI Factory builds a fine-tuned small model per phone and shows that quantized files must be scored as shipped; an 11 MB Russian embedder drops the transformer at serving time; and an audit finds that LLM annotators, fine-tuned or not, follow old labels more than new definitions. Five items made the cut.

## 1. Teaching a 4B Model to Think Like a Policy Expert

**Shusen Liu, Ke Wang, Tony Chen, Xiaojiang Huang, Kai Zhang, Rohan Shah, Puyang Xu, Kang Li (Atlassian, with NVIDIA)** · Inside Atlassian blog, 4 Nov 2026 · [atlassian.com](https://www.atlassian.com/blog/how-we-build/teaching-a-4b-model-to-think-like-a-policy-expert)

**What they did.** Atlassian checks every message, prompt and query in Rovo Chat and Rovo Search against its Acceptable Use Policy (AUP) before answering. Its filter was gpt-oss-safeguard-20B (21B total, 3.6B active), which reasons at inference; after months of prompt work, recall plateaued at 50.9% on their internal set. They fine-tuned NVIDIA Nemotron 3 Nano 4B to take the first pass.

**Method.** Real AUP violations are well under 1% of traffic, so training data was synthetic: violation and benign examples plus adversarial variants (typos, paraphrases, jailbreaks). Stage 1: full supervised fine-tuning on 20k+ `<prompt, label, reasoning>` triples. Stage 2: DPO on 2k+ pairs of correct versus wrong reasoning traces. Built with NVIDIA Megatron Bridge. AI agents ran 300+ experiments in about a week (about 5 hours per run on one H200, about 20 in parallel). Eval: a balanced 2k set plus a 3k adversarial set.

**Key results.**
- Evaluation sets: base Nemotron 4B F1 **0.66** (P 78.9%, R 56.7%); fine-tuned **0.81** (P 87.0%, R 75.5%); the 20B baseline 0.66 (P 94.0%, R 50.9%).
- End-to-end in production, with the 4B model first and the 20B model on suspicious cases: precision **94.0% → 98.1%**, recall 50.9% → 56.6%, latency **740 ms → 350 ms** (53% faster), throughput +42%.

**Caveats.** Internal, synthetic-heavy evaluation sets that are not published; no per-category or false-positive-rate breakdown; production recall is still 56.6%.

**Why it matters.** Train with reasoning, serve without it. A small fine-tuned model in front of a bigger one cut latency and raised both precision and recall, after prompt engineering had stalled.

## 2. We distilled a job posting extractor into a 400M model that runs on an 8 GB GPU

**Loukas Tzekos (founder, Job Opportunities API)** · DEV Community, 6 Nov 2026 · [dev.to](https://dev.to/lucagiftzek/we-distilled-a-job-posting-extractor-into-a-400m-model-that-runs-on-an-8-gb-gpu-1bnk) · model: `JobOpportunitiesAPI/joa-job-extractor-400m-gguf` (Apache 2.0)

**What he did.** His rule-based salary parser was precise when it fired, but in an audit of 886 hand-checked postings it found pay in only 59% of postings that stated one. He distilled a 13-field extractor small enough for one GTX 1070 (8 GB).

**Method.** One "evidence bundle" per posting (rendered page, JSON-LD JobPosting, the employer's applicant tracking record, liveness signals, stored text; typically 4,000-5,000 tokens). GLM-5.3-Flash labelled about **47,300** bundles into one flat JSON schema; a grounding filter removed or corrected values the text did not support. Student: IBM Granite 3.1 1B-A400M (mixture of experts, about 400M active), LoRA rank 64 on attention projections only, one epoch, merged and exported to GGUF (Q4_K_M 0.82 GB, Q8_0 1.42 GB, f16 2.67 GB). Compute on the EuroHPC Discoverer+ H200 cluster.

**Key results.**
- Bake-off on 100 postings: GLM-5.3 Flash and DeepSeek V4.1 Flash about 0.93, Qwen 3.8 27B 0.926; the reference model agreed with itself 96.1% of the time across two runs.
- 400M student: strict F1 **0.926** on 100 held-out postings (matching the 27B model); Q4_K_M on the GTX 1070 0.923.
- Salary on postings that state one: recall/precision/F1 **86/94/90** for the model vs 59/97/74 for the rule parser. Valid JSON on all 1,084 audited postings.
- A fine-tuned 3B dropped from 0.888 to 0.520 when allowed to browse.
- Speed: about 2 s per posting on the GTX 1070; about 62,900 postings per hour on one H200 with 32 parallel requests.

**Caveats.** About 3% of salary amounts (8 of 271) were not in the posting. Country (F1 91 vs 99) and seniority (64 vs 88) are worse than rules. Only works with its exact training prompt. Small test sets, and a vendor writing about its own model.

**Why it matters.** The deployment is the lesson: rules first, the model only where rules found nothing, and every number checked against the source text before it is stored.

## 3. Mobile AI Factory: Building Specialized Language Models for Your Mobile Device

**Evan Li, Krishna Deshpande, Wen Cheng, Shyamnath Gollakota (University of Washington)** · arXiv, 10 Nov 2026 · [arXiv:2611.13509](https://arxiv.org/abs/2611.13509) · [code](https://github.com/evanly-gh/SLM_Factory)

**What they did.** An agentic system that, given a task spec and a target phone, builds a fine-tuned, quantized small model that meets the app's speed, memory and energy limits on that phone.

**Method.** Orchestrator: Claude Sonnet 5; teacher for synthetic data: Qwen3.6-35B-A3B. Pool of 9 base models (135M to 4B; SmolLM2, Gemma 3, Qwen3, Qwen3.5) at 4, 8 and 16 bits = 27 variants, grouped into five size tiers and searched from small to large. Each iteration the orchestrator picks one intervention (LoRA hyperparameters, mine real data, or generate targeted synthetic data); fixed rules roll back anything that lowers accuracy and decide when to move up a tier. Four contamination firewalls protect a frozen held-out set. Four Android phones profiled once (364 configurations across llama.cpp and MNN, CPU and GPU). Ten tasks, including biomedical and fine-grained entity extraction, calendar event extraction, 151-way intent classification, spam and emotion detection.

**Key results.**
- On unseen test sets, the phone models beat Claude Sonnet 5 and DeepSeek v4 Flash (five-shot) on **5 of 10** tasks by 0.024 to 0.342, and match them on 3 more.
- Biomedical entity extraction: a **517 MB** model scores **0.828** vs 0.652 for Claude with five examples.
- Bucketed search comes within 3 points of training all 27 variants at **1/19** of the GPU time.
- In the longest run (109 evaluations), **88%** of the orchestrator's interventions made the model worse and were rolled back.
- Same weights, different 4-bit export: MNN's default drops a fine-tuned SmolLM2-360M on CLINC150 from **0.767 to 0.659** macro-F1 (llama.cpp Q4_K_M); HQQ-32 brings most cells back within noise.
- Of 364 configurations, 76 did not run, and weight size predicted only 35 of those. Without measurements, Claude Opus 5.5 given full specs missed the app's limits in 25% of easy and moderate cases and 60% of hard ones.

**Caveats.** The held-out set guides every search decision, so its scores can read slightly high (the headline uses unseen test sets). Four Android phones, ten tasks.

**Why it matters.** Score the artifact you ship. Quantization recipe, engine and backend change accuracy and speed per device, and a spec sheet does not tell you which.

## 4. StaRSE: Compact Russian Sentence Embeddings with a Sign-Coded Static Encoder

**Boris Malashenko, Ivan Jarsky, Egor Soldatov, Vladislav Luzhnov, Sviatoslav Stumpf, Vladislav Shmatkov, Viacheslav Shalamov, Andrey Stankevich, Valeria Efimova (ITMO University)** · arXiv, 10 Nov 2026 · [arXiv:2611.14236](https://arxiv.org/abs/2611.14236)

**What they did.** A Russian static sentence encoder: no transformer at serving time. Each token's direction is stored as sign bits with a separate scalar norm; a sentence embedding is the mean of norm-scaled sign directions.

**Method.** Initialized from ruBERT-base (WordPiece vocabulary of 120,138 tokens), fine-tuned on adjacent-sentence pairs from documents and task-shaped pairs, then post-trained with a contrastive loss computed directly through the sign-projected token table.

**Key results.**
- RuMTEB (23 tasks) mean **51.16**, **7.98** points above the strongest static baseline and 2.60 below ruBERT-tiny-turbo, the closest contextual encoder.
- Package **11.3 MiB** vs an estimated 55.7 MiB for ruBERT-tiny-turbo; mean CPU latency **0.08 ms** vs 1.43 ms per sentence (about 18x).
- Russian MLDR long documents (8,192 tokens kept): 51.66 nDCG@10, 17.35 above the next static baseline and 0.03 below USER2-small.

**Caveats.** Mean pooling cannot model word order or context; pair classification (TERRa entailment) is effectively tied with other static models, and larger contextual encoders remain much stronger on retrieval-heavy tasks.

**Why it matters.** For CPU-bound or frequently refreshed embeddings, a fine-tuned lookup table can get close to a small transformer at a fraction of the size and latency.

## 5. Definitions, Label Names, or Demonstrations? Auditing What Governs LLM Annotation

**Viraj Mishra, Shubham Gupta, Dhruv Gupta, Yuehong Cassandra Tai, Qunhua Li (Pennsylvania State University)** · arXiv, 6 Nov 2026 · [arXiv:2611.09457](https://arxiv.org/abs/2611.09457)

**What they did.** A counterfactual audit of LLM annotators: reassign codebook definitions among output labels and see whether predictions follow the new definitions or the dataset's original mapping. Three political-text datasets: CCC (US protest events, 8 categories), BFRS (political violence in Pakistan, 12), Manifesto (party-platform sentences, 49).

**Method.** Zero-shot audit over ten rearrangements on 1,000 documents per dataset; repeated after LoRA fine-tuning (one adapter per dataset) of Mistral-7B-Instruct-v0.2 and Llama-3.1-8B-Instruct. Retrieval analyses also use Llama-3.3-70B, with all-mpnet-base-v2 retrieval and a direct k-nearest-neighbour baseline over the same neighbours.

**Key results.**
- Under reassignment (Mistral-7B), original-label agreement beats definition adherence on all three: **55.80% vs 10.75%** (CCC), 20.93% vs 12.87% (BFRS), 30.25% vs 3.24% (Manifesto).
- Fine-tuning raises original-label agreement in all six model-dataset pairs (**4.63 to 29.44** points). Definition adherence falls on CCC for both models and rises only for Llama on Manifesto (+1.96).
- Global retrieval lifts Mistral's weighted F1 on BFRS from .548 to .774 (test), but direct kNN on the same examples recovers **74-93%** of the gain on Manifesto and BFRS.
- Relabeling demonstrations to match the swapped definitions raises reassigned-target F1 by .114 to .401.

**Caveats.** Political-text codebooks only; the audit shows which mapping predictions match, not why.

**Why it matters.** Higher accuracy can mean the model reproduces old labels better, not that it follows your codebook. When you change a taxonomy, update definitions, examples and training data together, and test the new mapping.

## Also noted

- **Zuse: A Decision Model for European Languages** (Umair Mehmood Imam; arXiv, 4 Nov 2026): LoRA plus a pointer head on frozen 4B, 9B and 27B bases for 27 European languages; the 27B reaches 87.5% accuracy with pooled calibration error 0.016 on held-out sources, miscalibration follows task rather than language, and languages outside the base model's list trail by 23 to 28 points. [arXiv:2611.06238](https://arxiv.org/abs/2611.06238)
- **Label-Wording Augmentation in a Typed-Decision Encoder** (Vladimir Beskorovainyi; arXiv, 5 Nov 2026): a 307M Russian cross-encoder trained with labels shown in several surface forms is more accurate on unfamiliar jargon and slang labels in all 14 cells (up to +0.24), but gains nothing on abbreviations or opaque codes. [arXiv:2611.08439](https://arxiv.org/abs/2611.08439)
- **Escalate or Close: How Fast-Tier Models Handle Held-Out Web Attack Families in Two-Tier Triage** (Kisielewicz, Kędziora, Nguyen; arXiv, 5 Nov 2026): a ModernBERT detector trained on the other families gave 37-60% of held-out path traversal requests a probability below 0.05 and escalated only 50-81% of them within a 5% benign budget (over 10 training runs), against nearly all when traversal was in training. [arXiv:2611.08229](https://arxiv.org/abs/2611.08229)
- **Beyond Ranking: Are Decision Models Calibrated Relevance Scorers?** (Zhuang, Ma, Petri, Lin; arXiv, 8 Nov 2026): of DL21 pairs Jev scores above 0.9, only 66% are relevant; a two-parameter calibration fitted on 2,257 DL19 pairs fixes much of it and transfers. [arXiv:2611.11480](https://arxiv.org/abs/2611.11480)
- **Yuanbao-Reranker: Document-Grounded Synthesis and Preference Distillation for Text Reranking** (Hongyuan Xu and colleagues; arXiv, 7 Nov 2026): Qwen3-based rerankers trained on 2.75M synthetic ranking groups; the 4B student averages 73.63 across five benchmarks, above its 8B teacher at 72.68. [arXiv:2611.10405](https://arxiv.org/abs/2611.10405)

## Patterns this week

**Small model first, safety net behind.** A fine-tuned 4B in front of a 20B model (Atlassian); rules first and the model only for gaps (job extractor). **Check outputs against the source.** Keep a number only if its digits are in the text. **Score the artifact you ship.** Quantization recipe, engine and phone change accuracy (Mobile AI Factory). **Accuracy is not adherence.** Fine-tuning and retrieval can teach old labels better without teaching new definitions (annotation audit).
