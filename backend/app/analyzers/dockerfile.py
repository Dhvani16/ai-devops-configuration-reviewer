"""Rule-based Dockerfile analysis."""

import re

from app.analyzers.interface import ConfigurationAnalyzer
from app.schemas.finding import ConfigurationType, Finding, FindingCategory, FindingSeverity

SECRET_PATTERN = re.compile(r"\b(password|secret|token|api[_-]?key|access[_-]?key)\b", re.IGNORECASE)


class DockerfileAnalyzer(ConfigurationAnalyzer):
    configuration_type = ConfigurationType.DOCKERFILE

    def analyze(self, content: str) -> list[Finding]:
        findings: list[Finding] = []
        lines = content.splitlines()
        instructions = [(index, line.strip()) for index, line in enumerate(lines, 1) if line.strip()]

        for line_number, line in instructions:
            from_match = re.match(r"FROM\s+(?:--platform=\S+\s+)?([^\s]+)", line, re.IGNORECASE)
            if from_match:
                image = from_match.group(1)
                if "@sha256:" not in image and (":" not in image or image.endswith(":latest")):
                    findings.append(
                        _finding(
                            "dockerfile-unpinned-base-image",
                            FindingCategory.RELIABILITY,
                            FindingSeverity.MEDIUM,
                            "Base image is not pinned",
                            "The base image can change between builds, reducing reproducibility.",
                            "Pin the image to a version tag or immutable digest.",
                            line_number,
                            line,
                        )
                    )
            if re.match(r"(?:ENV|ARG)\s+", line, re.IGNORECASE) and SECRET_PATTERN.search(line):
                instruction = line.split(maxsplit=1)[0].upper()
                findings.append(
                    _finding(
                        f"dockerfile-secret-in-{instruction.lower()}",
                        FindingCategory.SECURITY,
                        FindingSeverity.HIGH,
                        f"Possible secret stored in {instruction}",
                        "Build arguments and environment variables can be exposed through image metadata or layers.",
                        "Use BuildKit secrets or inject credentials at runtime through a secret manager.",
                        line_number,
                        line,
                    )
                )
            if re.search(r"apt-get\s+install", line, re.IGNORECASE) and "--no-install-recommends" not in line:
                findings.append(
                    _finding(
                        "dockerfile-apt-recommends",
                        FindingCategory.PERFORMANCE,
                        FindingSeverity.LOW,
                        "APT install includes recommended packages",
                        "Recommended packages can increase the image size and attack surface unnecessarily.",
                        "Add --no-install-recommends and clean the APT package cache in the same RUN instruction.",
                        line_number,
                        line,
                    )
                )

        if not any(re.match(r"USER\s+", line, re.IGNORECASE) for _, line in instructions):
            findings.append(
                _finding(
                    "dockerfile-missing-user",
                    FindingCategory.SECURITY,
                    FindingSeverity.HIGH,
                    "Container has no non-root USER instruction",
                    "Containers run as root by default, which increases the impact of a compromise.",
                    "Create a dedicated unprivileged user and switch to it with USER.",
                    None,
                    "No USER instruction found",
                )
            )

        run_count = sum(bool(re.match(r"RUN\s+", line, re.IGNORECASE)) for _, line in instructions)
        if run_count > 10:
            findings.append(
                _finding(
                    "dockerfile-excessive-layers",
                    FindingCategory.PERFORMANCE,
                    FindingSeverity.LOW,
                    "Dockerfile has excessive RUN layers",
                    "Many RUN instructions can increase image layers and make builds harder to maintain.",
                    "Combine closely related commands while keeping the Dockerfile readable.",
                    None,
                    f"{run_count} RUN instructions found",
                )
            )
        return findings


def _finding(
    rule_id: str,
    category: FindingCategory,
    severity: FindingSeverity,
    title: str,
    description: str,
    recommendation: str,
    line_number: int | None,
    evidence: str,
) -> Finding:
    return Finding(
        rule_id=rule_id,
        category=category,
        severity=severity,
        title=title,
        description=description,
        recommendation=recommendation,
        line_number=line_number,
        evidence=evidence,
    )
