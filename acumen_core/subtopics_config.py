"""
subtopics_config.py - Subtopic vocabulary management.
Provides load/get/validate for the master subtopics.json.
"""

import os
import json

_SUBTOPICS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subtopics.json")

_cache = None


def _load_raw():
    global _cache
    if _cache is not None:
        return _cache
    if not os.path.exists(_SUBTOPICS_FILE):
        _cache = {}
        return _cache
    with open(_SUBTOPICS_FILE, "r", encoding="utf-8") as f:
        _cache = json.load(f)
    return _cache


def load_subtopics():
    """Return full dict: {system: [subtopic1, subtopic2, ...]}"""
    return dict(_load_raw())


def get_subtopics_for_system(system):
    """Return list of valid subtopics for a given system. Empty list if unknown."""
    data = _load_raw()
    return list(data.get(system, []))


def is_valid_subtopic(system, subtopic):
    """Check if a subtopic is valid for a given system."""
    if not subtopic or not system:
        return False
    valid = get_subtopics_for_system(system)
    return subtopic in valid


def get_all_systems():
    """Return sorted list of all systems that have subtopics defined."""
    data = _load_raw()
    return sorted(data.keys())


def format_subtopics_for_prompt(system):
    """Return a formatted string of valid subtopics for LLM prompt use."""
    subtopics = get_subtopics_for_system(system)
    if not subtopics:
        return ""
    lines = [f"{i+1}. {s}" for i, s in enumerate(subtopics)]
    return "\n".join(lines)


def subtopics_exist(system):
    """Check if any subtopics are defined for a system."""
    return len(get_subtopics_for_system(system)) > 0
