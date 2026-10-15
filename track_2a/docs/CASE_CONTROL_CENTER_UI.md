# Case control center and theatre — 15 October 2026

The Pages companion now uses a grey/white control-center shell, black primary actions, blue accents, searchable case table, review queue and a case workspace with Overview, Scope, Findings, Evidence, Theatre, Activity and Report tabs. Separate cases retain separate reviews. Existing v1 browser data migrates into the v2 portfolio; the original storage key is retained. Failed storage writes restore saved case state.

Design references inspected: accessibility-red-team control-center/app.css, main.tsx and theatre/README.md, theatre.html, events.schema.json. Theatre HTML inspected blob: 2de4343fc758529150bdab676f1ee200c5ddea63. Implementation here is independently authored; no upstream runtime, character coordinates or code copied.

Theatre uses a CSS-drawn man with hat and walking stick, deterministic event commentary, manual previous/next controls and an explicitly illustrated workflow preview. It has no timer, audio or continuous animation. Character is decorative; speech is available to assistive technology. Recorded events are local case actions, not model inference. Previewing changes neither reviews nor history. A real Apertus event connection remains future work and must preserve run identity, timestamps and explicit failed/blocked/completed states. No invented progress, token counts or chain-of-thought.

Validation: offline deterministic Python build test, JavaScript syntax, DOM-contract scope/review/report journey, case isolation and theatre non-execution checks passed. These tests do not constitute rendered-browser or independent review. Browser-local demonstration only; no backend, benchmark or inference changes.
