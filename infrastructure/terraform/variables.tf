variable "environment" {
  description = "Deployment environment (staging, production)"
  type        = string
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "Environment must be either 'staging' or 'production'."
  }
}

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "adwp"
}

# VPC Configuration
variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

# EKS Configuration
variable "eks_cluster_version" {
  description = "Kubernetes version for EKS cluster"
  type        = string
  default     = "1.29"
}

variable "eks_platform_node_instance_types" {
  description = "Instance types for platform node group"
  type        = list(string)
  default     = ["t3.large"]
}

variable "eks_platform_node_desired" {
  description = "Desired number of platform nodes"
  type        = number
  default     = 3
}

variable "eks_platform_node_min" {
  description = "Minimum number of platform nodes"
  type        = number
  default     = 2
}

variable "eks_platform_node_max" {
  description = "Maximum number of platform nodes"
  type        = number
  default     = 10
}

variable "eks_ai_node_instance_types" {
  description = "Instance types for AI runtime node group"
  type        = list(string)
  default     = ["g5.xlarge"]
}

variable "eks_ai_node_desired" {
  description = "Desired number of AI runtime nodes"
  type        = number
  default     = 2
}

variable "eks_ai_node_min" {
  description = "Minimum number of AI runtime nodes"
  type        = number
  default     = 1
}

variable "eks_ai_node_max" {
  description = "Maximum number of AI runtime nodes"
  type        = number
  default     = 5
}

# RDS Configuration
variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.r6g.large"
}

variable "db_allocated_storage" {
  description = "Allocated storage for RDS in GB"
  type        = number
  default     = 100
}

variable "db_max_allocated_storage" {
  description = "Maximum allocated storage for RDS autoscaling in GB"
  type        = number
  default     = 500
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "adwp"
}

variable "db_username" {
  description = "Database master username"
  type        = string
  default     = "adwp_admin"
  sensitive   = true
}

variable "db_password" {
  description = "Database master password"
  type        = string
  sensitive   = true
}

variable "db_multi_az" {
  description = "Enable Multi-AZ deployment for RDS"
  type        = bool
  default     = true
}

# Redis Configuration
variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.r6g.large"
}

variable "redis_num_cache_nodes" {
  description = "Number of Redis cache nodes"
  type        = number
  default     = 3
}

# Kafka Configuration
variable "kafka_instance_type" {
  description = "MSK broker instance type"
  type        = string
  default     = "kafka.m5.large"
}

variable "kafka_number_of_brokers" {
  description = "Number of Kafka brokers"
  type        = number
  default     = 3
}

variable "kafka_ebs_volume_size" {
  description = "EBS volume size per Kafka broker in GB"
  type        = number
  default     = 100
}
