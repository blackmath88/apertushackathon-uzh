# S1 test fixtures — SYNTHETIC

Everything in this directory is handcrafted for unit tests. It is **not**
SwissGov-RSD data, carries no official labels and must never be reported as
benchmark evidence or used in prompts.

- `synthetic_dev_de.jsonl` — four records in the SwissGov-RSD dev schema
  (`id`, `text_a`, `text_b`, `labels_a`, `labels_b`, `page_*`, `subset`),
  covering a numeric change, a modality change, an omission with a repeated
  phrase, and Unicode/NBSP/thin-space/tab/newline tokenisation.
