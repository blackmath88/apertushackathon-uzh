# Apertus 1.5 RSD Adaptation Plan

**Research date: 14 October 2026, 09:32 CEST.** With roughly 50 hours until the submission deadline, the defensible outcome is **do not start LoRA/QLoRA yet**. Freeze the running prompting baseline, establish a clean family-disjoint development protocol, attempt Route C only after a PyTorch/XPU capability gate, and train the smallest Route B head only if that gate passes.

## Evidence standard

This report distinguishes four evidence levels:

- **Implemented code:** the relevant loader or training path exists in inspected source.
- **Published artifact:** weights, adapters, predictions, or checkpoints are publicly referenced.
- **README claim:** an author reports hardware or results, but they were not independently reproduced here.
- **Reproduced result:** none of the Apertus 1.5 SwissGov-RSD results below were independently rerun during this research.

No SwissGov-RSD test documents, test annotations, or test predictions were used in the analysis. Test-set discussion below is limited to split metadata and evaluation-code structure.

## Data reality

[SwissGov-RSD](https://huggingface.co/datasets/ZurichNLP/SwissGov-RSD) exposes **672 rows**, split into `validation` with 504 rows and `test` with 168 rows. Because every source family appears for EN–DE, EN–FR, and EN–IT, this corresponds to **168 development source families and 56 test source families**, with **no training split**.

Each row contains whitespace-tokenized and untokenized text for both sides, continuous `labels_a` and `labels_b`, source-page identifiers, `chunk_id`, an ID, annotator tag, and language subset. Gold labels are 0, 0.2, 0.4, 0.6, 0.8, or 1.0; punctuation is marked `-1` and excluded from scoring—not converted into a semantic category.

The official evaluator concatenates predictions and gold labels across **both sides** of every document for each language, removes positions whose gold label is `-1`, and computes one global token-level Spearman per language. It does not print the three-language macro average, so the submission metric should explicitly calculate the unweighted mean of the EN–DE, EN–FR, and EN–IT Spearmans.

A concerning detail is that the evaluator can pad or truncate predictions whose lengths do not match gold. The experiment should instead reject every mismatch: successful token mapping means exact equality for both sides of every document, with no repair by padding or truncation.

## Ranked resources

| Rank | Resource and revision | Actual method/support | Artifacts and licence | Hardware evidence | Exact reusable files | Limitations |
|---:|---|---|---|---|---|---|
| 1 | [SwissGov-RSD](https://github.com/ZurichNLP/SwissGov-RSD), [`1807a421`](https://github.com/ZurichNLP/SwissGov-RSD/commit/1807a42100e742ed03d337c54c4b9ea86995f565) | Official dataset, encoder regressor, evaluation code and paper implementation; no Apertus integration | Dataset labels declared CC-BY-4.0; source-text rights remain with the Swiss authorities. No repository-level code licence was visible | Paper experiments include Llama QLoRA and encoder training, but no Apertus or Intel XPU evidence | `scripts/evaluate_predictions_admin.py`, `encoders/utils.py`, `encoders/modeling_modernbert.py`, `encoders/finetuning/train_modernbert.py` | Official data helper supervises only `text_b`; it is not symmetric enough for this experiment without modification. |
| 2 | [SpanDiff](https://github.com/moscraciunxxx/SpanDiff-HackApertus), [`0822d470`](https://github.com/moscraciunxxx/SpanDiff-HackApertus/commit/0822d47001b1edb3c0145ab5639bea81ae7456eb) | Genuine Apertus v1.5 8B hidden-state extraction through the Swiss AI Transformers fork; two-sided, no-training scoring | Code Apache-2.0; no learned weights required; repository references committed predictions, which were not inspected | README claims about 16 GB and 280.2 seconds for 564,349 tokens on Apple GPU; code has CUDA and MPS branches, **not XPU** | `track_2a/src/spandiff/score.py`, `align.py`, `schema.py`, `requirements.txt` | README reports 0.3340 development macro Spearman, but this is unverified, based on development-selected layer/constants, and not a clean external reproduction. |
| 3 | [JevPertus](https://github.com/Jaluus/JevPertus), [`b7a25d65`](https://github.com/Jaluus/JevPertus/commit/b7a25d65ff4ab609d04d18af21ffa465e797c4fa) | Genuine custom loader for official Apertus 1.5 text weights, PEFT LoRA injection, hidden-state access and a custom pointer head | README links a Hugging Face model collection; code MIT, bundled data Apache-2.0 | CUDA uses BF16; every non-CUDA device defaults to FP32. No Intel run or VRAM measurement | `modeling/apertus/loading.py`, `modeling/jev.py`, `modeling/pointerhead.py`, `train_jevpertus.py` | Multiple-choice head, not RSD. Its custom `jev.pt` head cannot run in ordinary llama.cpp, and its dependency file is unpinned. |
| 4 | [Official Apertus 1.5 8B weights](https://huggingface.co/swiss-ai/Apertus-v1.5-8B) plus Transformers [`3797303d`](https://github.com/swiss-ai/transformers/commit/3797303dda74844e3d1f8977ff5518bb91f818b4) | Canonical multimodal checkpoint and loader lineage; decoder-only xIELU model | Published gated weights, Apache-2.0 plus AUP; immutable model-weight revision was not captured | Official examples cover generic device mapping and CUDA-oriented vLLM, not Intel XPU training | `AutoModelForMultimodalLM`, `AutoProcessor`; pin the exact Transformers commit | Transformers 1.5 integration was still not in a released upstream version; the model card says a technical report and detailed evaluation were forthcoming. |
| 5 | [Official fine-tuning recipes](https://github.com/swiss-ai/apertus-finetuning-recipes), [`fe94ada7`](https://github.com/swiss-ai/apertus-finetuning-recipes/commit/fe94ada7eb220bb8831728237a65d550901683bd) | Generic TRL SFT and LoRA implementation; README claims all Apertus versions | Code under Apache-2.0; produces PEFT adapters, no task-specific weights or results | Examples are CPU installation or modern GPU; default config uses BF16 and FlashAttention3 | `sft_train.py`, `configs/sft_lora.yaml`, `requirements.txt` | Current config defaults to Apertus 1.1 4B, while code loads `AutoModelForCausalLM`; this does not by itself prove that the official multimodal 1.5 checkpoint works. It is LoRA, not QLoRA. |
| 6 | [Andreas Martin text-only model](https://huggingface.co/andreasmartin/apertus-v1.5-8b-text) and [Kaggle SFT template](https://www.kaggle.com/code/andreasmartinch/sft-apertus-v1-5-8b-hack-apertus-template) | Community text-backbone repackaging intended for standard Transformers, plus an SFT notebook | Published text-only weights and GGUF derivatives are linked; exact Hub revisions and notebook source were not captured | Index reports testing on Kaggle and CSCS JupyterLab; no Intel XPU evidence | Potential Route A base and conversion lineage | Useful lead, but not sufficiently inspected here to treat the notebook as a reproducible recipe. Training against this derivative must merge back into the exact same derivative, not the official multimodal base. |
| 7 | [peft_apertus](https://github.com/davmels/peft_apertus), [`46d7ad35`](https://github.com/davmels/peft_apertus/commit/46d7ad358d4a1749270ed9ed4c2a7182acf6f9b2) | TRL/PEFT recipes for Apertus 1.0 `Apertus-8B-Instruct-2509`, not 1.5 | Training scripts and configs; no published adapted RSD weights found; no root licence found | README claims 8B LoRA on a single 40 GB GPU and shows four-GPU examples | `sft_train.py`, `configs/sft_lora.yaml`, `slurm.sbatch`, Dockerfiles | Cannot be cited as Apertus 1.5 support. One “8B full” example even names the 70B checkpoint, so commands require auditing. |
| 8 | [awesome-apertus](https://github.com/rnckp/awesome-apertus), [`8b5e4245`](https://github.com/rnckp/awesome-apertus/commit/8b5e424545ce3ccfebce3a752312f325285730d8) | Discovery index, not an implementation | CC0 list of official and community resources | No execution evidence | `README.md`, `RESEARCH.md` | Explicitly says Hack Apertus projects and reported results were not independently tested. Use it to find sources, never as proof that code works. |

## Route choice

| Route | Strength | Main failure mode | Deadline suitability | llama.cpp return |
|---|---|---|---|---|
| **A. LoRA/SFT generation** | Only route likely to produce a mergeable generative adapter and exact-text evidence in the existing inference style | Tiny in-domain development set; generated arrays/spans can be incomplete; cross-entropy does not directly optimize token-level Spearman; 1.5/XPU and conversion lineage remain unverified | **No** | Possible only for a pure causal LoRA trained and merged against the exact unquantized text-only base |
| **B. Frozen features + head** | Direct continuous supervision, exact output length, inexpensive head training, and clean comparison with C | Requires working PyTorch hidden-state extraction; causal embeddings and long documents need deliberate handling; separate runtime | **Conditional pilot** | No ordinary GGUF runtime support for the head |
| **C. Frozen representation score** | No training, easiest scientific control, two-sided outputs and no generative formatting failures | Layer choice and alignment heuristics can overfit development; current GGUF path does not expose the required intermediate states | **Recommended immediate control** | Not with the current unmodified llama.cpp workflow |

**Recommendation:** use C as the locked control and B as the only near-term adaptation candidate. Do not attempt A before the deadline; the available evidence does not establish Apertus 1.5 QLoRA on Intel XPU, nor a verified merge-and-convert path from the official multimodal checkpoint.

## Genuine 1.5 support

Two inspected implementations genuinely recognize the Apertus 1.5 checkpoint structure:

- **SpanDiff** imports `AutoModelForMultimodalLM` and Apertus 1.5 model classes from the Swiss AI Transformers fork at commit `3797303…`, requires 33 hidden states for the 32-layer text model, and explicitly refuses another model ID.
- **JevPertus** recognizes top-level `model_type="apertus1p5"`, requires `text_config.model_type="apertus1p5_text"`, maps official `model.language_model.*` weight names, loads xIELU parameters, and checks tensor shapes.

The official recipes are less conclusive. Their README now recommends 1.5, but the current training script uses `AutoModelForCausalLM`, while the authored 1.5 instructions use `AutoModelForMultimodalLM`; their checked-in LoRA configuration targets the 1.1 4B checkpoint and FlashAttention3.

## Supervision design

Do not invent “minor,” “major,” “addition,” or “omission” classes. Such categories may help qualitative analysis, but the training target should remain the released continuous score in `[0,1]`, and punctuation or special tokens should use an ignore index.

For every whitespace gold token:

1. Locate its exact character span in the untokenized source.
2. Tokenize with a fast tokenizer and request offsets.
3. Assign every subword whose character interval overlaps that gold-token span.
4. Apply the same gold target to all assigned subwords during direct token training, or compute similarity at subword level and pool back to the whitespace token.
5. Reject zero-subword, duplicated, dropped, or length-mismatched mappings.
6. Produce predictions for `labels_a` and `labels_b` separately.

The existing SwissGov helper maps labels only to `text_b`, changes punctuation from `-1` to `-100`, and trains with `BCEWithLogitsLoss` on continuous labels. Its loss can be reused, but its one-sided mapping cannot.

### Causal limitations

Apertus is decoder-only. In a sequence formatted as `A [SEP] B`, tokens in A cannot attend to B, whereas tokens in B can attend to A and prior B tokens; a single token-regression pass therefore creates structural asymmetry.

Three defensible alternatives are:

- Run `A [SEP] B` and supervise only B, then `B [SEP] A` and supervise only A.
- Encode both documents separately and let a bidirectional external head compare all frozen representations.
- Use paired chunks and an explicit cross-attention head outside Apertus.

The proposed pilot uses the second option because it guarantees symmetric access in the head and avoids pretending that causal hidden states are bidirectional.

### Null alignments

An omission or addition may have no counterpart. Do not force a token-to-token match and then label that arbitrary match as evidence.

For Route B, add either a learned null representation or explicit match-quality features such as:

- Top cosine similarity.
- Difference between top-1 and top-5 similarity.
- Whether the best match is outside the best matching sentence or chunk.
- Ratio between the best match and document-level similarity distribution.

A low-confidence token can then score highly without claiming a false aligned counterpart.

### Long documents

The paper reports documents up to roughly 2,500–2,800 whitespace tokens, so some examples exceed a conservative 512-token extraction window. SpanDiff’s reusable contribution is its exact chunk–encode–stitch discipline; its code verifies that stitched outputs equal the original whitespace-token count.

For the pilot:

- Split each side independently at sentence boundaries into at most 512 model tokens.
- Preserve every token and stitch representations into original document order.
- Compare stitched tokens against the entire other document, not just the same-numbered chunk.
- Cache the English document once per family instead of encoding it three times.
- Keep all chunks from a page family in the same data partition.

## Clean development use

Create a **source-family key** from the canonical English page URL, falling back to the language-independent numeric component of IDs such as `admin_de_N`, `admin_fr_N`, and `admin_it_N`. Group all language pairs, translations, chunks, tokenized forms, and annotation variants carrying that source key.

Maintain a prompt-exposure ledger containing every development family that was:

- Included as an in-context example.
- Used for prompt construction or prompt debugging.
- Viewed during qualitative error analysis.
- Used to choose output parsing or post-processing.

Those families must not enter reported validation. If exposure records cannot be reconstructed, treat all potentially viewed development families as exposed and report that no clean adaptation estimate is available.

## Intel XPU gate

The local Q8_0 GGUF result establishes only that llama.cpp’s SYCL backend can execute that quantized conversion. It does **not** establish PyTorch loading, BF16 xIELU execution, `output_hidden_states`, PEFT back-propagation, 4-bit training kernels, or the custom head.

Negative evidence is stronger than positive evidence here:

- SpanDiff implements CUDA and MPS branches and rejects other paths.
- JevPertus selects BF16 only when `device.type == "cuda"`; every other device receives FP32 weights.
- The official LoRA config defaults to `kernels-community/vllm-flash-attn3`, which is not an Intel attention path.
- None of the inspected repositories provides an Intel Arc, PyTorch XPU, oneAPI, or IPEX training log.

PEFT’s Python-level adapter injection is not the likely blocker; model loading, xIELU, attention, BF16 and quantization kernels are. In particular, CUDA or Unsloth/bitsandbytes QLoRA claims must not be transferred to XPU.

### Memory check

Do not infer VRAM from the product name. Before any authorization to run, record:

```bash
xpu-smi discovery
xpu-smi stats -d 0
```

If the installed PyTorch build exposes XPU, also record:

```python
import torch
print(torch.__version__)
print(torch.xpu.is_available())
print(torch.xpu.get_device_properties(0))
print(torch.xpu.mem_get_info())
```

The official Hub card describes the full checkpoint as approximately 9B parameters with BF16 and FP32 tensors. That implies a **weight-only BF16 floor near 18 GB** before temporary loader copies, multimodal components, allocator overhead, hidden states or activations; FP32 is near 36 GB and therefore unsuitable for a 32 GB system-memory machine. SpanDiff independently reports an approximately 16 GB text-focused path and notes that its FP32 load was killed, but that is an author claim and its MPS implementation loads only the layers needed to reach hidden state 15.

A reasonable go/no-go threshold for the unmodified full BF16 checkpoint is therefore **at least 22–24 GB actually free device memory**, measured immediately before loading. This is an engineering allowance, not a verified B60 requirement.

### Capability test

The first authorized operation should be a one-family, inference-only gate:

- Pin Transformers to `3797303dda74844e3d1f8977ff5518bb91f818b4`.
- Use the official unquantized checkpoint, BF16, `attn_implementation="sdpa"` or eager—not FlashAttention3.
- Load on `xpu:0` without CPU offload.
- Request hidden states for a sequence of 512 tokens with `use_cache=False`.
- Confirm 33 states, expected width, finite values and deterministic repeated output.
- Record peak allocated/reserved memory.
- Do not proceed to PEFT until this passes.

Failure means **no local B or C experiment before the deadline**. CPU fallback is not a responsible assumption with only 32 GB RAM.

## Smallest pilot

### Research question

> Does a family-disjoint linear token-difference head trained over frozen Apertus v1.5 representations improve macro token-level Spearman over the same representations scored by untrained cosine alignment?

### Data

Use exactly **96 clean development source families**, provided that at least 96 remain after prompt-exposure exclusions:

- 72 source families for training.
- 24 source families for validation.
- Each family contributes EN–DE, EN–FR and EN–IT.
- Split by a fixed SHA-256 hash of the canonical English-page key.
- Never split on row ID or `chunk_id`.

If fewer than 96 clean families remain—or fewer than 24 can be reserved for validation—stop and report **insufficient clean data**.

### Fixed baselines

- **Prompt baseline:** the currently running local prompting system, frozen before seeing pilot results.
- **C-final:** independent document encoding, final text hidden state, token score `1 - max cosine`.
- **C-mid:** identical scoring using hidden state 15, treated only as an externally suggested hypothesis.

Do not add SpanDiff’s development-tuned centering, CSLS, sentence blend or smoothing constants to the pilot.

### Trainable target

For token \(i\), find its frozen best match \(j^*\) in the other document. Construct:

\[
z_i = [h_i,\ h_{j^*},\ |h_i-h_{j^*}|,\ h_i \odot h_{j^*},\ s_1,\ s_1-s_5]
\]

Train one shared linear sigmoid head on continuous gold scores using soft-target BCE and L2 regularization. Apply the same head to both directions and all three languages.

### Configuration budget

Cap the pilot at four predefined configurations:

| Config | Layer | Learning rate | Epoch cap |
|---|---:|---:|---:|
| B1 | 15 | 0.0003 | 10 |
| B2 | 15 | 0.001 | 10 |
| B3 | Final | 0.0003 | 10 |
| B4 | Final | 0.001 | 10 |

Use batch size 4,096 cached token features, AdamW, weight decay 0.01, one fixed seed, and early stopping with patience two on the three-language validation macro. Do not tune smoothing, thresholds, class weights, layer mixtures or language-specific heads.

### Resources

Assuming the XPU capability gate passes:

- Frozen extraction dominates compute; head training should fit comfortably on CPU.
- For 96 source families, two layers of FP16 token representations will likely require several GB of temporary storage; stream per family or cache only match features.
- Peak accelerator memory is governed by the BF16 backbone, not the head.
- Wall time on Intel is unknown. SpanDiff’s reported 280.2 seconds for the full development pass on an Apple GPU is not transferable to Arc hardware.

Optional NVIDIA engineering estimates, **not assumed access**:

| Operation | Estimated memory |
|---|---:|
| Frozen BF16 extraction, 512-token windows | 20–24 GB |
| BF16 LoRA, gradient checkpointing, batch 1 | 24–32 GB |
| 4-bit QLoRA, batch 1, 512–1,024 tokens | 14–22 GB |
| Comfortable experimental margin | 40 GB |

The QLoRA estimate presumes a CUDA stack with working Apertus 1.5 quantized loading; none of the inspected code establishes the equivalent on Intel.

### Evaluation

Run the official evaluator logic locally against the 24-family validation subset:

- One global Spearman for EN–DE over both sides.
- One global Spearman for EN–FR over both sides.
- One global Spearman for EN–IT over both sides.
- Unweighted macro of the three.
- Secondary family-bootstrap confidence interval, resampling source families rather than tokens.
- Report exact token-mapping failures and refuse to score a repaired output.

### Stop criteria

Stop immediately if:

- Any test file, annotation, prediction, or copied test artifact would be required.
- The exposure ledger cannot establish 24 clean validation families.
- XPU BF16 loading or hidden extraction fails.
- Any prediction length differs from the gold whitespace-token length.
- Any model configuration requires CPU offload or starts paging system RAM.

Do not promote B over C unless it:

- Improves validation macro Spearman by at least **0.02 absolute** over the better fixed C baseline.
- Improves at least two of three language pairs.
- Does not reduce the remaining language by more than 0.01.
- Shows the gain under source-family bootstrap rather than only at token level.

Even if those criteria pass, describe the result as a **development pilot**, not a reproduced benchmark or expected test result.

## SpanDiff lessons

SpanDiff provides useful implementation discipline:

- Pin the exact Transformers fork.
- Verify the hidden-state tuple length and index convention.
- Tokenize with offsets.
- Stitch long-document chunks exactly.
- Score both document directions.
- Reject rather than repair token-count mismatches.
- Set `use_cache=False` and avoid generation.

Do **not** automatically reuse hidden state 15, `beta=0.5`, `alpha=0.5`, `k=5`, sentence blend 0.35, or window-two smoothing. Its README reports that these choices were evaluated on the development set and reports a development macro of 0.3340; that is valuable hypothesis generation, but it is not an independent validation result and may include development selection.

The committed SpanDiff test and full-set predictions are unnecessary for this research and should remain untouched.

## Returning to llama.cpp

### Route A

A pure LoRA adapter can potentially return to llama.cpp, but only through a strict lineage:

1. Start from the exact unquantized text-only Hugging Face base corresponding to the current GGUF.
2. Train PEFT LoRA against that base.
3. Merge with `merge_and_unload`.
4. Save merged safetensors with the same tokenizer and language-model head.
5. Convert that merged checkpoint with a v1.5-compatible `convert_hf_to_gguf.py`.
6. Quantize the resulting GGUF to Q8_0.
7. Regression-test logits or generations before and after conversion.

The official recipe demonstrates PEFT merging conceptually, but it does not prove this complete 1.5 GGUF conversion chain. Do not merge an adapter trained on the official multimodal checkpoint into the Andreas Martin text-only conversion, or vice versa.

The full 1.5 model has a larger multimodal vocabulary while only text-token logits are selectable. A text-only conversion may prune or reshape this interface, making tokenizer IDs and output-head lineage critical.

### Routes B and C

A custom regression head requires:

- Intermediate hidden states.
- Cross-document matching.
- External head execution.
- Exact subword-to-whitespace pooling.

Ordinary llama.cpp text generation does not provide that pipeline. B and C therefore require a separate PyTorch runtime unless llama.cpp is modified to export the selected layer and an external scorer is built around it.

## Longer-term option

The strongest longer-term design is a **tied two-tower Apertus adapter with an explicit cross-document head**, not generative SFT:

- Encode each side separately with the same Apertus text backbone and a small LoRA adapter.
- Chunk and stitch long documents before cross-document comparison.
- Project tokens to a lower-dimensional match space.
- Add a learned null key for additions and omissions.
- Use bidirectional cross-attention or differentiable top-k matching.
- Predict a continuous score for every token on both sides.
- Train with soft-target BCE or Huber loss plus a small pairwise-ranking term aligned with Spearman.
- Evaluate through five-fold source-family cross-validation on development, with all exposed prompting families isolated.
- Lock architecture and hyperparameters before a single test submission.

This route sacrifices direct llama.cpp deployment but properly addresses the task. Route A should remain a secondary deployment experiment after B establishes whether Apertus adaptation actually improves RSD.

## Unknowns and negatives

- No inspected repository demonstrates **Apertus v1.5 8B QLoRA on Intel Arc/XPU**.
- No inspected repository demonstrates Apertus xIELU training or hidden-state extraction on the Arc Pro B60.
- No current evidence establishes that the available B60 has sufficient free VRAM; it must be measured.
- No SwissGov-RSD training split exists.
- No Apertus 1.5 RSD LoRA weights or independently reproduced RSD results were found.
- The official generic recipes claim 1.5 support but do not check in a 1.5 configuration or use the official multimodal loader.
- The Kaggle notebook and Andreas Martin text-only model were identified, but exact notebook code and immutable Hub revisions were not verified.
- [Apertus Evidence Lab](https://github.com/hallzyx/apertus) and [Apertus Court Decisions](https://github.com/beyondExp/apertus-court-decisions) are described by the curated index as frozen-1.5 custom-head projects, but their loaders, checkpoints and results were not directly inspected; those remain README/index leads, not evidence.
- JevPertus proves that a custom 1.5 text loader plus PEFT and a head can be implemented, not that its classification results transfer to token-level RSD.
- Better translation, multiple-choice, legal classification or embedding performance is not evidence of better token-level semantic-difference Spearman.
- The identities of development examples already exposed during prompting are currently unknown. Without that ledger, a clean adaptation claim is impossible.
- Direct deployment of Routes B or C through the current llama.cpp SYCL workflow is unsupported.
- The authored Apertus 1.5 model card still described the detailed technical report and benchmark publication as forthcoming at the research date.