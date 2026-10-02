ALLOWED_DEVELOPMENT_SPLITS = {"train", "dev"}


def assert_development_split(split: str) -> None:
    """Reject test-set use in normal development code paths."""
    if split not in ALLOWED_DEVELOPMENT_SPLITS:
        raise ValueError(
            f"Split {split!r} is not available in development. "
            "Only train/dev are legal before final evaluation."
        )
