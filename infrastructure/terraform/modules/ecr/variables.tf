variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "service_names" {
  description = "List of service names for ECR repositories"
  type        = list(string)
}
