"""Tests for the Terraform / HCL configuration analyzer."""

import pytest

from app.analyzers.interface import InvalidConfigurationError
from app.analyzers.terraform import TerraformAnalyzer

_BASE_TF = '''
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

resource "aws_instance" "web" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.micro"
}
'''

_SECURITY_GROUP_TF = '''
terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

resource "aws_security_group" "allow_all" {
  name = "allow_all"
  ingress {
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
  }
}
'''


@pytest.mark.parametrize(
    ("content", "rule_id"),
    [
        # hardcoded secret
        (
            _BASE_TF.replace(
                'resource "aws_instance" "web" {',
                'resource "aws_instance" "web" {\n  password = "mysecretpassword"',
            ),
            "tf-hardcoded-secret",
        ),
        # S3 public acl
        (
            _BASE_TF.replace(
                'instance_type = "t3.micro"',
                'instance_type = "t3.micro"\n  acl = "public-read"',
            ),
            "tf-s3-public-acl",
        ),
        # encryption disabled
        (
            _BASE_TF.replace(
                'instance_type = "t3.micro"',
                'instance_type = "t3.micro"\n  encrypted = false',
            ),
            "tf-encryption-disabled",
        ),
        # publicly accessible db
        (
            _BASE_TF.replace(
                'instance_type = "t3.micro"',
                'instance_type = "t3.micro"\n  publicly_accessible = true',
            ),
            "tf-db-publicly-accessible",
        ),
        # open security group (0.0.0.0/0)
        (
            _SECURITY_GROUP_TF.replace(
                '"10.0.0.0/8"',
                '"0.0.0.0/0"',
            ),
            "tf-open-security-group",
        ),
        # missing provider version
        (
            'provider "aws" {\n  region = "us-east-1"\n}\n\nresource "aws_instance" "w" {\n  ami = "ami-1"\n  instance_type = "t3.micro"\n}\n',
            "tf-missing-provider-version",
        ),
        # S3 backend without encrypt
        (
            'terraform {\n  backend "s3" {\n    bucket = "my-tf-state"\n    key    = "state"\n    region = "us-east-1"\n  }\n  required_providers {\n    aws = { source = "hashicorp/aws", version = "~> 5.0" }\n  }\n}\n',
            "tf-s3-backend-no-encrypt",
        ),
    ],
)
def test_terraform_rule_fires(content: str, rule_id: str) -> None:
    rule_ids = {f.rule_id for f in TerraformAnalyzer().analyze(content)}
    assert rule_id in rule_ids, f"Expected rule {rule_id!r} not found in: {rule_ids}"


def test_clean_terraform_has_no_findings() -> None:
    findings = TerraformAnalyzer().analyze(_BASE_TF)
    assert findings == []


def test_clean_security_group_no_findings() -> None:
    findings = TerraformAnalyzer().analyze(_SECURITY_GROUP_TF)
    assert findings == []


def test_s3_backend_with_encrypt_true_no_finding() -> None:
    content = (
        'terraform {\n'
        '  backend "s3" {\n'
        '    bucket  = "my-tf-state"\n'
        '    key     = "state"\n'
        '    region  = "us-east-1"\n'
        '    encrypt = true\n'
        '  }\n'
        '  required_providers {\n'
        '    aws = { source = "hashicorp/aws", version = "~> 5.0" }\n'
        '  }\n'
        '}\n'
    )
    rule_ids = {f.rule_id for f in TerraformAnalyzer().analyze(content)}
    assert "tf-s3-backend-no-encrypt" not in rule_ids


def test_variable_reference_not_flagged_as_secret() -> None:
    content = (
        _BASE_TF
        + '\nvariable "db_password" {\n  type      = string\n  sensitive = true\n}\n'
        + '\nresource "aws_db_instance" "db" {\n'
        '  password = var.db_password\n'
        '  instance_class = "db.t3.micro"\n'
        '}\n'
    )
    rule_ids = {f.rule_id for f in TerraformAnalyzer().analyze(content)}
    assert "tf-hardcoded-secret" not in rule_ids


def test_empty_content_raises() -> None:
    with pytest.raises(InvalidConfigurationError):
        TerraformAnalyzer().analyze("   ")


def test_non_terraform_content_raises() -> None:
    with pytest.raises(InvalidConfigurationError):
        TerraformAnalyzer().analyze("FROM python:3.12\nRUN apt-get update")


def test_factory_includes_terraform() -> None:
    from app.analyzers.factory import get_analyzer
    from app.schemas.finding import ConfigurationType

    analyzer = get_analyzer(ConfigurationType.TERRAFORM)
    assert isinstance(analyzer, TerraformAnalyzer)
