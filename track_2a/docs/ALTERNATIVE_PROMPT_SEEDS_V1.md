# Alternative-prompt seed specifications v1

Companion: ALTERNATIVE_PROMPT_EXPERIMENTS_2026-10-14.md.
Status: authored candidates, unmeasured. Synthetic examples below are invented for this experiment, not benchmark quotations or independently human-verified cases.

## Composition

P0 is exact B2_TEMPLATE from the pinned implementation commit.
P1/P2/P3 each insert ONLY their respective block immediately before "Version A (English):".
Do not combine blocks in the initial experiment. Preserve every other prompt byte, model setting, output cap, parser and projector.
Record source template hash, block hash and fully rendered request hash. If the exact insertion marker is absent or repeated, refuse composition.
Insert literal text after formatting the original B2 prompt; JSON braces in the block must not be interpreted as template placeholders.

## P1 — semantic commitments

Additional comparison guidance:
Different words can convey the same information. Compare the actor, action, affected object, permission or obligation, negation, conditions, exceptions, quantities and time expressed by each version. These are a checklist, not an exhaustive list of possible differences.
Do not infer facts that neither passage states. Use surrounding sentences to understand what a condition or exception governs. Report only differences supported by the two supplied texts.
Distinguish a changed assertion from a faithful paraphrase. An extra qualification can be a difference even when most words correspond. Select the smallest exact excerpts that carry the change; retain necessary negation and qualifiers. Keep the existing severity scale and JSON contract unchanged.

## P2 — directional coverage

Additional comparison guidance:
First check what information in A is also conveyed by B. Then check what information in B is also conveyed by A. A passage elsewhere in the supplied document can convey the same information; lack of a word-for-word match is not enough to call something missing.
Use OMISSION only for information present in A and absent from B, and ADDITION only for information present in B and absent from A. When both passages express conflicting or changed information, use CHANGE. Do not report the same difference twice after checking both directions.
Base every entry on exact excerpts from the supplied texts. Keep the existing severity scale and JSON contract unchanged.

## P3 — contrastive demonstrations

Additional invented examples illustrating the existing output contract:
These examples teach the comparison format only. Their subjects and answers are not facts about the documents you are about to receive.

English A: The service is free .
German B: Der Dienst kostet nichts .
Output: {"differences": []}

English A: Applications must arrive within 30 days .
German B: Anträge müssen innerhalb von 20 Tagen eingehen .
Output: {"differences": [{"a": "30", "b": "20", "kind": "CHANGE", "severity": 4}]}

English A: You can apply online .
French B: Vous pouvez déposer votre demande en ligne .
Output: {"differences": []}

English A: The desk opens on Monday . Bring identification .
French B: Le guichet ouvre le lundi .
Output: {"differences": [{"a": "Bring identification .", "b": "", "kind": "OMISSION", "severity": 5}]}

English A: Registration is optional .
Italian B: L'iscrizione è facoltativa .
Output: {"differences": []}

English A: Registration is free .
Italian B: L'iscrizione è gratuita . È richiesta la residenza .
Output: {"differences": [{"a": "", "b": "È richiesta la residenza .", "kind": "ADDITION", "severity": 5}]}

Now compare the supplied documents using the same rules. Copy excerpts from those documents, not from these examples.

## Before execution

Validate exact excerpt matching and projection on these synthetic examples offline. Human-check multilingual meaning, directional labels and appropriateness of illustrative severities before freezing P3. Any edits happen before inference and receive a new block hash. Do not claim these illustrative severities are SwissGov human gold or calibrated estimates.
P3 contains all six examples for every language, making the prompt constant across pairs except the standard language substitution. Do not silently create language-specific prompt arms.
