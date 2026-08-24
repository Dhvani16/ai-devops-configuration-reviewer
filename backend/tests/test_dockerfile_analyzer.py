import pytest

from app.analyzers.dockerfile import DockerfileAnalyzer


@pytest.mark.parametrize(
    ("content", "rule_id"),
    [
        ("FROM python\nUSER app", "dockerfile-unpinned-base-image"),
        ("FROM python:latest\nUSER app", "dockerfile-unpinned-base-image"),
        ("FROM python:3.12", "dockerfile-missing-user"),
        ("FROM python:3.12\nENV API_KEY=literal\nUSER app", "dockerfile-secret-in-env"),
        ("FROM python:3.12\nARG TOKEN=literal\nUSER app", "dockerfile-secret-in-arg"),
        (
            "FROM ubuntu:24.04\nRUN apt-get update && apt-get install curl\nUSER app",
            "dockerfile-apt-recommends",
        ),
        (
            "FROM python:3.12\n" + "\n".join("RUN echo test" for _ in range(11)) + "\nUSER app",
            "dockerfile-excessive-layers",
        ),
    ],
)
def test_dockerfile_rules(content: str, rule_id: str) -> None:
    findings = DockerfileAnalyzer().analyze(content)

    assert rule_id in {finding.rule_id for finding in findings}


def test_digest_pinned_non_root_dockerfile_has_no_findings() -> None:
    content = "FROM python@sha256:" + "a" * 64 + "\nUSER app"

    assert DockerfileAnalyzer().analyze(content) == []
