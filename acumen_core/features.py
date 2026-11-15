"""Per-user feature flags shared by the portal (webapp/) and the admin console (dashboard/).

One list: a flag that exists in only one of the two used to be dropped whenever the other saved a
user or the defaults (the console did not know `bookmarks`, so saving a user erased its override).
"""

# Order matters: it is the order of the flags in the portal page and in the console.
FEATURE_FLAGS = [
    "papers",
    "guidelines",
    "pearls",
    "trials",
    "trials_detail",
    "condensed_trials",
    "search",
    "bookmarks",
    "theory",
]

FEATURE_LABELS = {
    "papers": "Papers",
    "guidelines": "Guidelines",
    "pearls": "Pearls",
    "trials": "Trials",
    "trials_detail": "Trial Details",
    "condensed_trials": "Condensed Trials",
    "search": "Search",
    "bookmarks": "Bookmarks",
    "theory": "Theory",
}

# Flags that are OFF unless an admin turns them on; every other flag defaults to ON.
DEFAULT_FEATURE_STATES = {
    "condensed_trials": False,
    "theory": False,
}


def resolve_defaults(stored):
    """The account-wide defaults: stored values layered over DEFAULT_FEATURE_STATES, for every flag."""
    stored = stored if isinstance(stored, dict) else {}
    return {f: stored.get(f, DEFAULT_FEATURE_STATES.get(f, True)) for f in FEATURE_FLAGS}


def clean_flags(values):
    """Keep only known flags, coerced to bool (what an admin may set per user or as defaults)."""
    return {k: bool(v) for k, v in (values or {}).items() if k in FEATURE_FLAGS}
