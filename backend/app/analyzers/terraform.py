"""Rule-based Terraform / HCL configuration analysis.

Uses regex-based parsing — no external HCL library required.
Supports .tf files containing resource, variable, and provider blocks.
"""

import re

from app.analyzers.interface import ConfigurationAnalyzer, InvalidConfigurationError
from app.schemas.finding import ConfigurationType, Finding, FindingCategory, FindingSeverity

# ─── compiled patterns ────────────────────────────────────────────────────────

# Detects literal secret-like assignments: password = "value", secret_key = "abc"
_SECRET_ASSIGNMENT = re.compile(
    r'(?i)\b(password|secret|secret_key|access_key|private_key|api_key|token|auth_token)'
    r'\s*=\s*"([^"]{3,})"',
)

# Security group ingress blocks containing 0.0.0.0/0 or ::/0
_OPEN_CIDR = re.compile(r'"(0\.0\.0\.0/0|::/0)"')
_INGRESS_BLOCK = re.compile(r'\bingress\s*\{([^}]*)\}', re.DOTALL)

# S3 acl = "public-read" or "public-read-write"
_S3_PUBLIC_ACL = re.compile(r'\bacl\s*=\s*"(public-read|public-read-write)"')

# encrypted = false or server_side_encryption_configuration missing hint
_ENCRYPTED_FALSE = re.compile(r'\bencrypted\s*=\s*false\b')

# provider block without required_providers version constraint
_PROVIDER_BLOCK = re.compile(r'\bprovider\s+"[^"]+"\s*\{', re.DOTALL)
_REQUIRED_PROVIDERS = re.compile(r'\brequired_providers\b')

# terraform backend without encryption
_BACKEND_BLOCK = re.compile(r'\bbackend\s+"s3"\s*\{([^}]*)\}', re.DOTALL)
_ENCRYPT_TRUE = re.compile(r'\bencrypt\s*=\s*true\b')

# database instance publicly accessible
_PUBLICLY_ACCESSIBLE = re.compile(r'\bpublicly_accessible\s*=\s*true\b')


class TerraformAnalyzer(ConfigurationAnalyzer):
    configuration_type = ConfigurationType.TERRAFORM

    def analyze(self, content: str) -> list[Finding]:
        _validate(content)
        findings: list[Finding] = []
        findings.extend(_check_hardcoded_secrets(content))
        findings.extend(_check_open_security_groups(content))
        findings.extend(_check_s3_public_acl(content))
        findings.extend(_check_encryption_disabled(content))
        findings.extend(_check_missing_provider_versions(content))
        findings.extend(_check_s3_backend_no_encrypt(content))
        findings.extend(_check_publicly_accessible_db(content))
        return findings


# ─── validation ───────────────────────────────────────────────────────────────

def _validate(content: str) -> None:
    if not content.strip():
        raise InvalidConfigurationError("Terraform configuration is empty")
    # Minimal HCL structure check: at least one block keyword
    if not re.search(r'\b(resource|variable|provider|module|data|terraform|locals)\b', content):
        raise InvalidConfigurationError(
            "Content does not appear to be a Terraform / HCL configuration"
        )


# ─── rule implementations ─────────────────────────────────────────────────────

def _check_hardcoded_secrets(content: str) -> list[Finding]:
    findings: list[Finding] = []
    seen: set[str] = set()
    for m in _SECRET_ASSIGNMENT.finditer(content):
        key = m.group(1).lower()
        value = m.group(2)
        # Skip obvious placeholders / variable references
        if value.startswith("${") or value in ("", "changeme", "CHANGEME", "your-secret-here"):
            continue
        if key in seen:
            continue
        seen.add(key)
        line = content[: m.start()].count("\n") + 1
        findings.append(Finding(
            rule_id="tf-hardcoded-secret",
            category=FindingCategory.SECURITY,
            severity=FindingSeverity.CRITICAL,
            title=f"Hardcoded secret in {m.group(1)} attribute",
            description=(
                "Storing secrets as plain-text string literals in Terraform files exposes them "
                "in version control and Terraform state files, risking credential theft."
            ),
            recommendation=(
                "Use a variable with `sensitive = true` and inject the value from environment "
                "variables (TF_VAR_*), a secrets manager (e.g. AWS Secrets Manager, HashiCorp "
                "Vault), or a Terraform Cloud workspace variable instead of a literal string."
            ),
            line_number=line,
            evidence=f'{m.group(1)} = "***"',
        ))
    return findings


def _check_open_security_groups(content: str) -> list[Finding]:
    findings: list[Finding] = []
    resource_blocks = re.finditer(
        r'\bresource\s+"aws_security_group(?:_rule)?"\s+"[^"]+"\s*\{',
        content,
    )
    for rb in resource_blocks:
        # Find the matching closing brace (simple brace-counting)
        block = _extract_block(content, rb.end() - 1)
        for im in _INGRESS_BLOCK.finditer(block):
            ingress_body = im.group(1)
            if _OPEN_CIDR.search(ingress_body):
                line = content[: rb.start()].count("\n") + 1
                findings.append(Finding(
                    rule_id="tf-open-security-group",
                    category=FindingCategory.SECURITY,
                    severity=FindingSeverity.HIGH,
                    title="Security group ingress open to the world (0.0.0.0/0 or ::/0)",
                    description=(
                        "An ingress rule allows traffic from all IPv4 or IPv6 addresses. "
                        "This exposes the resource to the entire internet."
                    ),
                    recommendation=(
                        "Restrict cidr_blocks / ipv6_cidr_blocks to the minimum required IP "
                        "ranges. For internal services, reference a VPC CIDR or use a security "
                        "group reference instead of 0.0.0.0/0."
                    ),
                    line_number=line,
                    evidence='cidr_blocks = ["0.0.0.0/0"]',
                ))
                break  # one finding per resource block
    return findings


def _check_s3_public_acl(content: str) -> list[Finding]:
    findings: list[Finding] = []
    for m in _S3_PUBLIC_ACL.finditer(content):
        line = content[: m.start()].count("\n") + 1
        findings.append(Finding(
            rule_id="tf-s3-public-acl",
            category=FindingCategory.SECURITY,
            severity=FindingSeverity.HIGH,
            title="S3 bucket ACL grants public read access",
            description=(
                f'The bucket\'s ACL is set to "{m.group(1)}", which exposes all objects '
                "to anonymous internet access. Data leaks from misconfigured S3 buckets "
                "are a leading cause of cloud breaches."
            ),
            recommendation=(
                "Remove the public ACL and enable aws_s3_bucket_public_access_block with "
                "block_public_acls = true. Serve public content through CloudFront with "
                "an Origin Access Control instead."
            ),
            line_number=line,
            evidence=f'acl = "{m.group(1)}"',
        ))
    return findings


def _check_encryption_disabled(content: str) -> list[Finding]:
    findings: list[Finding] = []
    for m in _ENCRYPTED_FALSE.finditer(content):
        line = content[: m.start()].count("\n") + 1
        findings.append(Finding(
            rule_id="tf-encryption-disabled",
            category=FindingCategory.SECURITY,
            severity=FindingSeverity.HIGH,
            title="Storage encryption explicitly disabled",
            description=(
                "Setting encrypted = false disables at-rest encryption for the storage "
                "resource. If the underlying media is ever accessed directly, data is "
                "exposed in plaintext."
            ),
            recommendation=(
                "Set encrypted = true. For EBS volumes and RDS instances AWS-managed "
                "or customer-managed KMS keys add negligible performance overhead."
            ),
            line_number=line,
            evidence="encrypted = false",
        ))
    return findings


def _check_missing_provider_versions(content: str) -> list[Finding]:
    findings: list[Finding] = []
    if _PROVIDER_BLOCK.search(content) and not _REQUIRED_PROVIDERS.search(content):
        findings.append(Finding(
            rule_id="tf-missing-provider-version",
            category=FindingCategory.MAINTAINABILITY,
            severity=FindingSeverity.MEDIUM,
            title="Provider version constraint not declared",
            description=(
                "Without a required_providers version constraint in the terraform block, "
                "running terraform init will pull the latest provider version. A future "
                "breaking provider release can silently change or break infrastructure."
            ),
            recommendation=(
                'Add a terraform { required_providers { aws = { source = "hashicorp/aws" '
                'version = "~> 5.0" } } } block to pin the provider to a compatible range.'
            ),
            line_number=None,
            evidence="provider block found but no required_providers constraint",
        ))
    return findings


def _check_s3_backend_no_encrypt(content: str) -> list[Finding]:
    findings: list[Finding] = []
    for m in _BACKEND_BLOCK.finditer(content):
        body = m.group(1)
        if not _ENCRYPT_TRUE.search(body):
            line = content[: m.start()].count("\n") + 1
            findings.append(Finding(
                rule_id="tf-s3-backend-no-encrypt",
                category=FindingCategory.SECURITY,
                severity=FindingSeverity.MEDIUM,
                title="Terraform S3 backend does not enable state file encryption",
                description=(
                    "The S3 remote backend is configured without encrypt = true. "
                    "Terraform state files contain sensitive values (passwords, private keys, "
                    "secrets) in plaintext and should always be encrypted at rest."
                ),
                recommendation=(
                    'Add encrypt = true to the backend "s3" block to enable server-side '
                    "encryption for the state file stored in S3."
                ),
                line_number=line,
                evidence='backend "s3" { ... } without encrypt = true',
            ))
    return findings


def _check_publicly_accessible_db(content: str) -> list[Finding]:
    findings: list[Finding] = []
    for m in _PUBLICLY_ACCESSIBLE.finditer(content):
        line = content[: m.start()].count("\n") + 1
        findings.append(Finding(
            rule_id="tf-db-publicly-accessible",
            category=FindingCategory.SECURITY,
            severity=FindingSeverity.HIGH,
            title="Database instance is publicly accessible",
            description=(
                "Setting publicly_accessible = true assigns a public IP to the database "
                "instance and routes it through the internet gateway. Combined with weak "
                "credentials or misconfigured security groups, this is directly exploitable."
            ),
            recommendation=(
                "Set publicly_accessible = false and access the database through a "
                "VPC-internal endpoint, a bastion host, or AWS Systems Manager Session Manager."
            ),
            line_number=line,
            evidence="publicly_accessible = true",
        ))
    return findings


# ─── HCL block extractor ──────────────────────────────────────────────────────

def _extract_block(content: str, open_brace_pos: int) -> str:
    """Return the content of the HCL block starting at open_brace_pos."""
    depth = 0
    for i in range(open_brace_pos, len(content)):
        if content[i] == "{":
            depth += 1
        elif content[i] == "}":
            depth -= 1
            if depth == 0:
                return content[open_brace_pos : i + 1]
    return content[open_brace_pos:]
