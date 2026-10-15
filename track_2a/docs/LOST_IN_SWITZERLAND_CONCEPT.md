# Lost in Switzerland — concept and product direction

Updated 13 October 2026 · **Federal-first field research, city transfer later**.

## Thesis

**Same country. Different language. Same information?**

People should be able to rely on multilingual government information. Different published language versions may diverge through translation, omission or asynchronous updates. We investigate correspondence and uncertainty with provenance; we do **not** assume any administration has made a mistake or publish unreviewed model outputs as errors.

Our core product is an **evidence-first multilingual government-content observatory**, not only a benchmark algorithm or a marketing campaign.

```
DISCOVER official public webpages
  → PAIR actual language counterparts
  → CAPTURE versioned source evidence
  → ANALYZE with explicitly versioned methods
  → VERIFY candidate semantic observations against originals
  → TRIAGE and REVIEW unknown / accepted / rejected claims
  → EXPLORE bilingual source-linked evidence
  → WATCH comparable future revisions (later)
```

## Three complementary lanes

### 1. UZH scientific engine

SwissGov-RSD is a multilingual **federal** source-based challenge evaluated with official token-level Spearman. B0/B2/B3/B4/B5 experiments are immutable records of hypotheses and results, not five interchangeable production models.

As recorded in B4 PR #17, the published Qwen3-Embedding-4B DiffAlign score vectors achieved 0.187117 macro across the frozen 30 dev pairs with full token output coverage, **without Apertus calls**. As recorded in B5 PR #19, the tested reciprocal, NULL-aware and affine-gap matching variants did not outperform that baseline; B5 was **NOT SUPPORTED**, and its Apertus contrastive stage was not run.

**Important:** DiffAlign alone has no demonstrated meaningful Apertus contribution. The eventual Hack Apertus submission must meet the challenge's actual model-use requirements, judge interface, licensing and owner publication decisions. Avoid treating support-model performance as Apertus performance.

### 2. Live government pilot

Start with a **federal** government website profile closely related to the benchmark's source domain, with deliberately small seeds and verified cross-language partners. First candidate: BFE energy-label pages (DE/FR). A language version from a similar topic is merely a pairing candidate until supported by page metadata or human review.

Then try `ch.ch` for practical citizen services (registration, permits, insurance). Retain `www.stadt-zuerich.ch` as a **municipal transfer test** using the previously implemented Zürich-only Scout.

Keep source snapshots separate from train/dev/test data. No use of held-out test content or metadata for discovery.

### 3. Public experience and narrative

**Lost in Switzerland** explains *why understanding the wording is not the same as receiving equivalent information*. The visitor can inspect a small number of real, source-linked multilingual pairs; see what the system observed, what it cannot establish, and what a human verified.

Use precise, restrained visual design and avoid sensationalized “government caught making mistakes” claims. The useful public result may be demonstrated equivalence, a verifiable difference, or an explicit unknown.

## Provenance and authority

- The original government webpage remains authoritative; the model generates candidate analyses only.
- Authority differs by publisher and language. Federal DE/FR/IT can have different legal status from English; Zürich's translated content follows its own stated rules. Do not make a universal claim that DE is always the legally binding version.
- Record URL, locale, capture time, content/extract digest, exact original spans, pairing rationale, detector revision, reviewer decision and rights/reuse status.
- No uncontrolled crawling, automatic outreach or public findings before validation.

## Development ownership

The [federal-first build plan](ZURICH_PILOT_BUILD_PLAN.md) supersedes the Zürich-first ordering. PR #13 contains the initial safe Python Scout and source material; retain and refactor rather than discarding it. Independent experimental and submission branches remain draft and unmerged unless separately authorized.

The minimum public demonstration is **one actual federal page pair captured, processed and displayed with source evidence**, plus honest method/provenance metadata. Do not require a positive discrepancy to have a legitimate demonstration.
