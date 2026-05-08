variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs"
  type        = list(string)
}

variable "instance_type" {
  description = "MSK broker instance type"
  type        = string
}

variable "number_of_brokers" {
  description = "Number of Kafka brokers"
  type        = number
}

variable "ebs_volume_size" {
  description = "EBS volume size per broker in GB"
  type        = number
}

variable "eks_security_group_id" {
  description = "Security group ID of EKS nodes for ingress"
  type        = string
}
