# Blinded diagnostic audit

The 15-item sample was drawn only after predictions were frozen: five model
discrepancies absent from official positives, five gold positives missed by the
baseline and S2, and five seeded controls. `blind-review.json` omits method,
prediction, official label, and sample category. Review judgments were recorded
in `reviewed.json` before consulting `audit-key.json`; official labels remain
unchanged.

The review found 6 unsupported differences, 9 unresolved, and 0 supported.
Nine correspondences were invalid, largely because single-token anchors or
unavailable anchors did not supply a reviewable proposition. This is diagnostic
evidence that passage plausibility and one-token localization are not
interchangeable, and it reinforces the negative verifier decision.
