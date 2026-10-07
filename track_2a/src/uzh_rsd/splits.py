"""Development split policy.

The guard runs before any path is built, any file is opened or any network
request is made. Callers must invoke it as the first statement of every entry
point that accepts a split name.
"""

ALLOWED_DEVELOPMENT_SPLITS = frozenset({"train", "dev"})


class SplitNotAllowedError(ValueError):
    """Raised when a split outside the development policy is requested."""


def assert_development_split(split: object) -> str:
    """Reject test-set (and any unknown) split use in development code paths.

    Matching is exact: no case folding, stripping or aliasing, so ``"Test"``,
    ``" dev"``, ``"full"`` and ``"validation"`` are all rejected.
    Returns the accepted split name.
    """
    if not isinstance(split, str) or split not in ALLOWED_DEVELOPMENT_SPLITS:
        raise SplitNotAllowedError(
            f"Split {split!r} is not available in development. "
            "Only train/dev are legal before final evaluation."
        )
    return split
