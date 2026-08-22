import pytest

from app.analyzers.github_actions import GitHubActionsAnalyzer
from app.analyzers.interface import InvalidConfigurationError


def workflow(job: str, trigger: str = "push", permissions: str = "") -> str:
    return f"on: {trigger}\n{permissions}jobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n{job}\n"


@pytest.mark.parametrize(
    ("content", "rule_id"),
    [
        (workflow("      - run: echo safe", trigger="pull_request_target"), "actions-pull-request-target"),
        (workflow("      - uses: third-party/action@v1"), "actions-unpinned-action"),
        (workflow("      - run: echo safe", permissions="permissions: write-all\n"), "actions-write-all-permissions"),
        (workflow("      - run: echo safe", permissions="permissions:\n  contents: write\n"), "actions-write-permission"),
        (workflow("      - run: echo '${{ github.event.pull_request.title }}'"), "actions-untrusted-shell-input"),
        (workflow("      - run: echo ${{ secrets.DEPLOY_TOKEN }}"), "actions-secret-in-logs"),
    ],
)
def test_github_actions_rules(content: str, rule_id: str) -> None:
    findings = GitHubActionsAnalyzer().analyze(content)

    assert rule_id in {finding.rule_id for finding in findings}


def test_pinned_action_is_not_flagged() -> None:
    content = workflow("      - uses: actions/checkout@" + "a" * 40)

    assert GitHubActionsAnalyzer().analyze(content) == []


def test_workflow_requires_jobs() -> None:
    with pytest.raises(InvalidConfigurationError):
        GitHubActionsAnalyzer().analyze("on: push")
