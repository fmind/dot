# Copy to tests/bdd/conftest.py alongside tests/bdd/test_features.py (`scenarios(".")`).
from __future__ import annotations

import re

import allure
import pytest

_ISSUE_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def pytest_bdd_apply_tag(tag, function):
    if tag.startswith("issue_"):
        issue_id = tag.removeprefix("issue_")
        if not _ISSUE_ID_RE.fullmatch(issue_id):
            return None
        allure.issue(issue_id)(function)
        return True
    if tag.startswith("severity_"):
        level = allure.severity_level.__members__.get(tag.removeprefix("severity_").upper())
        if level is None:
            return None
        allure.severity(level)(function)
        return True
    return None


@pytest.hookimpl(trylast=True)
def pytest_bdd_before_scenario(scenario):
    if scenario.rule:
        allure.dynamic.story(scenario.rule.name)


def pytest_bdd_step_func_lookup_error(request, step):
    if request.node.get_closest_marker("wip"):
        pytest.skip(f"WIP step not yet implemented: {step.name}")
