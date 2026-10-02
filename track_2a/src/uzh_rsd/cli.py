from __future__ import annotations

import argparse
import json

from .contracts import DifferenceKind, SemanticDifference, TokenSpan
from .projection import project_differences
from .splits import assert_development_split


def main() -> None:
    parser = argparse.ArgumentParser(description="SwissGov-RSD experiment scaffold")
    parser.add_argument("--strategy", default="dry-run")
    parser.add_argument("--split", default="dev")
    args = parser.parse_args()
    assert_development_split(args.split)
    if args.strategy != "dry-run":
        raise SystemExit("Only the dry-run scaffold exists. Implement B0 before adding strategies.")
    example = SemanticDifference(source=TokenSpan(1, 2), target=TokenSpan(1, 2), kind=DifferenceKind.CHANGE, severity=4.0, confidence=0.9)
    source_scores, target_scores = project_differences(3, 3, [example])
    print(json.dumps({"status":"scaffold-ok","split":args.split,"strategy":args.strategy,"source_scores":source_scores,"target_scores":target_scores,"next":"implement dev-only SwissGov-RSD adapter and B0"}, indent=2))


if __name__ == "__main__":
    main()
