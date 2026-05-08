variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "cluster_version" {
  description = "Kubernetes version for the EKS cluster"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs for EKS"
  type        = list(string)
}

variable "platform_node_instance_types" {
  description = "Instance types for platform node group"
  type        = list(string)
}

variable "platform_node_desired_size" {
  description = "Desired number of platform nodes"
  type        = number
}

variable "platform_node_min_size" {
  description = "Minimum number of platform nodes"
  type        = number
}

variable "platform_node_max_size" {
  description = "Maximum number of platform nodes"
  type        = number
}

variable "ai_runtime_node_instance_types" {
  description = "Instance types for AI runtime node group"
  type        = list(string)
}

variable "ai_runtime_node_desired_size" {
  description = "Desired number of AI runtime nodes"
  type        = number
}

variable "ai_runtime_node_min_size" {
  description = "Minimum number of AI runtime nodes"
  type        = number
}

variable "ai_runtime_node_max_size" {
  description = "Maximum number of AI runtime nodes"
  type        = number
}
