# AWS ECR Configuration for Docker Container Registry
# This file manages ECR repositories for all microservices

locals {
  ecr_repositories = [
    "auth-service",
    "analysis-service",
    "data-ingestions-service"
  ]
}

# Create ECR repositories for each service
resource "aws_ecr_repository" "service_repos" {
  for_each = toset(local.ecr_repositories)

  name                 = "qnt9-srs/${each.value}"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = merge(
    local.common_tags,
    {
      Name        = "qnt9-srs-${each.value}-ecr"
      Service     = each.value
      Description = "ECR repository for ${each.value}"
    }
  )
}

# Lifecycle policy to manage image retention
resource "aws_ecr_lifecycle_policy" "service_repos_policy" {
  for_each   = aws_ecr_repository.service_repos
  repository = each.value.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 30 images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["v", "release"]
          countType     = "imageCountMoreThan"
          countNumber   = 30
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Keep last 10 untagged images"
        selection = {
          tagStatus   = "untagged"
          countType   = "imageCountMoreThan"
          countNumber = 10
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 3
        description  = "Expire dev/test images older than 7 days"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["dev", "test", "feature"]
          countType     = "sinceImagePushed"
          countUnit     = "days"
          countNumber   = 7
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# IAM policy for EKS nodes to pull images from ECR
resource "aws_iam_role_policy_attachment" "eks_ecr_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
  role       = module.eks.eks_managed_node_groups["one"].iam_role_name
}

# Create a policy document for cross-account access if needed
data "aws_iam_policy_document" "ecr_policy" {
  statement {
    sid    = "AllowPull"
    effect = "Allow"

    principals {
      type = "Service"
      identifiers = [
        "eks.amazonaws.com"
      ]
    }

    actions = [
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchGetImage",
      "ecr:BatchCheckLayerAvailability",
    ]
  }

  statement {
    sid    = "AllowPushPull"
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = [data.aws_caller_identity.current.account_id]
    }

    actions = [
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchGetImage",
      "ecr:BatchCheckLayerAvailability",
      "ecr:PutImage",
      "ecr:InitiateLayerUpload",
      "ecr:UploadLayerPart",
      "ecr:CompleteLayerUpload",
    ]
  }
}

# Get current AWS account ID
data "aws_caller_identity" "current" {}

# Apply repository policy
resource "aws_ecr_repository_policy" "service_repos_policy" {
  for_each   = aws_ecr_repository.service_repos
  repository = each.value.name
  policy     = data.aws_iam_policy_document.ecr_policy.json
}

# Outputs for ECR repositories
output "ecr_repository_urls" {
  description = "URLs of the ECR repositories"
  value = {
    for k, v in aws_ecr_repository.service_repos : k => v.repository_url
  }
}

output "ecr_repository_arns" {
  description = "ARNs of the ECR repositories"
  value = {
    for k, v in aws_ecr_repository.service_repos : k => v.arn
  }
}

output "ecr_registry_id" {
  description = "The registry ID where the repositories were created"
  value       = data.aws_caller_identity.current.account_id
}

output "ecr_login_command" {
  description = "Command to login to ECR"
  value       = "aws ecr get-login-password --region ${var.region} | docker login --username AWS --password-stdin ${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.region}.amazonaws.com"
}
