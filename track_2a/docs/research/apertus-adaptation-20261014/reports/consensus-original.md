# A **frozen-feature pilot** is the most reproducible **Apertus v1.5 8B** adaptation experiment for SwissGov-RSD now.

**Research date:** 2026-10-14. The evidence supports three facets here: implementation reality, SwissGov-RSD supervision design, and hardware/runtime feasibility. SwissGov-RSD is a **224-document**, token-level, cross-lingual benchmark where current systems perform poorly, so a conservative pilot that isolates adaptation value is more defensible than rushing into generative LoRA claims (Wastl et al., 2025).

## Implementation Status

Apertus is released as a fully open 8B/70B family with scientific artifacts, multilingual pretraining, and compliant data pipelines, but that does not by itself establish task-specific fine-tuning support on your stack (Hernández-Cano et al., 2025). LoRA is the most mature adaptation family for frozen-backbone training, reduces trainable parameters sharply, and usually preserves inference latency after merging, which matters if the result must return to a llama.cpp-style workflow (Hu et al., 2021; Rajabzadeh et al., 2024).

**Implementation resources ranked by direct reusability**

| Resource | Exact version to pin | Method | Artifacts status | Hardware evidence | Reusable files | Main limitation |
|---|---|---|---|---|---|---|
| `swiss-ai/apertus-finetuning-recipes` | pin a commit before use | Apertus SFT/PEFT recipes | **README/code likely useful**, reproduced RSD not established | no paper-backed hardware proof for Intel XPU | training configs, loader patterns | Must verify Apertus 1.5 8B paths manually |
| `andreasmartin/apertus-v1.5-8b-text` | HF model revision hash | base text model | **Published weights** | inference only, not training proof | tokenizer, config lineage | no RSD adaptation artifact |
| `ZurichNLP/SwissGov-RSD` | pin dataset/code commit | benchmark/eval | **Official dataset/code** | not a training stack | eval scripts, metadata | no train split assumed |
| `moscraciunxxx/SpanDiff-HackApertus` | pin commit | task prototype | README claim only unless scripts run cleanly | no independent reproduction | label construction ideas | dev-selected results risk |
| `davmels/peft_apertus` | pin commit | PEFT scaffold | code presence more important than README | hardware unverified | PEFT wrappers | unclear 1.5-specific support |
| `Jaluus/JevPertus` | pin commit | Apertus experimentation | claim/code must be separated | hardware unverified | model-loading snippets | unclear RSD relevance |
| `beyondExp/apertus-court-decisions` | pin commit | domain SFT | task-specific example | hardware unverified | data formatting, trainer setup | different objective from token-level RSD |

**Figure 1:** Ranked implementation resources for a reproducible Apertus v1.5 8B SwissGov-RSD experiment.

- **Route B** has the strongest reproducibility case because it needs hidden-state extraction plus a small head, not instruction generation quality (Wastl et al., 2025).
- **Route A** is feasible later, but LoRA success on other tasks does not prove token-level RSD gains (Hu et al., 2021; Zhao et al., 2024; Zhu et al., 2025).
- **Route C** should be retained as a control because training-free representation scoring can test whether adaptation adds value at all (Xiao et al., 2022; Shao et al., 2023).

## Supervision Design

SwissGov-RSD contains human token-level difference annotations for **EN-DE, EN-FR, and EN-IT** across 224 multi-parallel documents, and the benchmark paper evaluates on the whole dataset rather than describing an ordinary public train split in the evidence provided here (Wastl et al., 2025). That makes invented class labels risky; the safest target is the original continuous token-level score on both document sides, evaluated with per-pair Spearman and macro-averaging across the three language pairs, matching the benchmark framing (Wastl et al., 2025).

- Use **continuous regression targets**, not handcrafted categories, because the task is defined as token-level semantic-difference recognition with Spearman evaluation (Wastl et al., 2025).
- Keep all translations and chunks of one English source in the same fold, because the dataset is multi-parallel and document-level (Wastl et al., 2025).
- Score both sides separately after subword-to-token pooling, because omissions and additions imply null-alignment behavior that a single-sided decoder pass will blur (Wastl et al., 2025).

Route A faces an architectural mismatch: decoder-only causal LMs are natural for sequence generation, but token-level bilingual difference scoring over long documents needs explicit cross-document comparison, token mapping, and null handling rather than next-token loss alone (Huang & Schlag, 2024; Wastl et al., 2025). Because some SwissGov inputs exceeded model length limits in prior evaluation, long-document chunking must be explicit and family-disjoint before any training subset is defined (Wastl et al., 2025).

## Hardware And Runtime

Your current GGUF inference setup does not validate PyTorch fine-tuning. The quantization and PEFT literature shows many memory-saving methods, but the concrete implementations and kernel claims are overwhelmingly **CUDA-centered** or built around NVIDIA-specific toolchains such as Triton, paged optimizers, fused kernels, or Megatron integrations (Rajabzadeh et al., 2024; Zhu et al., 2025; Ashkboos et al., 2025).

- **Negative evidence:** the supplied papers do not verify Apertus 1.5 8B LoRA or hidden-state extraction on Intel Arc Pro B60/XPU (Wastl et al., 2025; Hernández-Cano et al., 2025).
- Quantized fine-tuning methods reduce memory, but several rely on specialized quantization or inference-efficient kernels not shown here for Intel XPU (Bondarenko et al., 2024; Xu et al., 2023; Jeon et al., 2024; Ashkboos et al., 2025).
- A merged **LoRA adapter** could in principle return to standard inference more easily than a custom regression head, while Route B’s head would require a separate runtime outside plain llama.cpp (Hu et al., 2021; Xu et al., 2023; Kim et al., 2023).

## Recommendation

Recommend **Route B first**, with Route C as a mandatory control and Route A deferred. The smallest feasible pilot is: freeze Apertus v1.5 8B, extract selected intermediate layers for chunked EN–X document pairs, train a small token-level regression head on a permitted development subset only, use family-disjoint validation, and stop unless macro Spearman beats the no-training control by a predeclared margin on held-out development families (Wastl et al., 2025; Hu et al., 2021).

A realistic **short pilot** is therefore “do not train LoRA yet”: first verify legal/official dev-only supervision, hidden-state extraction, chunking, token remapping, and Route C vs B separation on your local hardware. A **longer-term option** is Route A with merged LoRA only after an NVIDIA-backed reproduction path, because quantization-aware LoRA methods can lower memory but remain implementation-sensitive and task transfer to token-level RSD is unproven (Bondarenko et al., 2024; Rajabzadeh et al., 2024; Shao et al., 2023; Zhu et al., 2025).

**Explicit unknowns:** official split names/counts beyond what is stated here, exact Apertus 1.5 8B repo-level loader compatibility on Intel XPU, whether any cited GitHub repo has reproduced SwissGov-RSD token-level scores, and whether exposed prompting-development examples already constrain allowable dev folds.
 
_These search results were found and analyzed using Consensus, an AI-powered search engine for research. Try it at https://consensus.app. © 2026 Consensus NLP, Inc. Personal, non-commercial use only; redistribution requires copyright holders’ consent._
 
## References
 
Ashkboos, S., Nikdan, M., Tabesh, S., Castro, R. L., Hoefler, T., & Alistarh, D. (2025). HALO: Hadamard-Assisted Lower-Precision Optimization for LLMs. *ArXiv, abs/2501.02625*. https://doi.org/10.48550/arxiv.2501.02625
 
Bondarenko, Y., Del Chiaro, R., & Nagel, M. (2024). Low-Rank Quantization-Aware Training for LLMs. *ArXiv, abs/2406.06385*. https://doi.org/10.48550/arxiv.2406.06385
 
Hernández-Cano, A., Hägele, A., Huang, A. H., Romanou, A., Solergibert, A.-J., Pásztor, B., Messmer, B., Garbaya, D., vDurech, E., Hakimi, I., Giraldo, J. G., Ismayilzada, M., Foroutan, N., Moalla, S., Chen, T., Sabolcec, V., Xu, Y., Aerni, M., AlKhamissi, B., . . . Schlag, I. (2025). Apertus: Democratizing Open and Compliant LLMs for Global Language Environments. *ArXiv, abs/2509.14233*. https://doi.org/10.48550/arxiv.2509.14233
 
Hernández-Cano, A., Hagele, A., Huang, A. H., Romanou, A., Solergibert, A.-J., Pásztor, B., Messmer, B., Garbaya, D., vDurech, E., Hakimi, I., Giraldo, J. G., Ismayilzada, M., Foroutan, N., Moalla, S., Chen, T., Sabolvcec, V., Xu, Y., Aerni, M., AlKhamissi, B., . . . Schlag, I. (2025). Apertus: Democratizing Open and Compliant LLMs for Global Language Environments.
 
Hu, J., Shen, Y.-L., Wallis, P., Allen-Zhu, Z., Li, Y., Wang, S.-A., Wang, L., & Chen, W. (2021). LoRA: Low-Rank Adaptation of Large Language Models. *ArXiv, abs/2106.09685*. https://doi.org/10.48550/arxiv.2106.09685
 
Huang, A. H., & Schlag, I. (2024). Deriving Activation Functions Using Integration. https://doi.org/10.48550/arxiv.2411.13010
 
Jeon, H., Kim, Y., & Kim, J.-J. (2024). L4Q: Parameter Efficient Quantization-Aware Fine-Tuning on Large Language Models. 2002-2024. https://doi.org/10.18653/v1/2025.acl-long.99
 
Kim, J., Lee, J. H., Kim, S., Park, J., Yoo, K. M., Kwon, S., & Lee, D. (2023). Memory-Efficient Fine-Tuning of Compressed Large Language Models via sub-4-bit Integer Quantization. *ArXiv, abs/2305.14152*. https://doi.org/10.48550/arxiv.2305.14152
 
Rajabzadeh, H., Valipour, M., Zhu, T.-S., Tahaei, M. S., Kwon, H. J., Ghodsi, A., Chen, B., & Rezagholizadeh, M. (2024). QDyLoRA: Quantized Dynamic Low-Rank Adaptation for Efficient Large Language Model Tuning. *ArXiv, abs/2402.10462*. https://doi.org/10.48550/arxiv.2402.10462
 
Shao, W., Chen, M., Zhang, Z., Xu, P., Zhao, L., Li, Z., Zhang, K., Gao, P., Qiao, Y., & Luo, P. (2023). OmniQuant: Omnidirectionally Calibrated Quantization for Large Language Models. *ArXiv, abs/2308.13137*. https://doi.org/10.48550/arxiv.2308.13137
 
Wastl, M., Vamvas, J., & Sennrich, R. (2025). SwissGov-RSD: A Human-annotated, Cross-lingual Benchmark for Token-level Recognition of Semantic Differences Between Related Documents. *ArXiv, abs/2512.07538*. https://doi.org/10.48550/arxiv.2512.07538
 
Xiao, G.-X., Lin, J., Wu, H., Demouth, J., & Han, S. (2022). SmoothQuant: Accurate and Efficient Post-Training Quantization for Large Language Models. *ArXiv, abs/2211.10438*. https://doi.org/10.48550/arxiv.2211.10438
 
Xu, Y., Xie, L.-X., Gu, X.-T., Chen, X., Chang, H., Zhang, H.-H., Chen, Z.-S., Zhang, X., & Tian, Q. (2023). QA-LoRA: Quantization-Aware Low-Rank Adaptation of Large Language Models. *ArXiv, abs/2309.14717*. https://doi.org/10.48550/arxiv.2309.14717
 
Zhao, J., Wang, T. E., Abid, W., Angus., G., Garg, A., Kinnison, J., Sherstinsky, A., Molino, P., Addair, T., & Rishi, D. (2024). LoRA Land: 310 Fine-tuned LLMs that Rival GPT-4, A Technical Report. *ArXiv, abs/2405.00732*. https://doi.org/10.48550/arxiv.2405.00732
 
Zhu, Z., Su, Q., Ding, Y., Song, K., Wang, S., & Pekhimenko, G. (2025). LoRAFusion: Efficient LoRA Fine-Tuning for LLMs. *Proceedings of the 21st European Conference on Computer Systems*. https://doi.org/10.1145/3767295.3769331
 
