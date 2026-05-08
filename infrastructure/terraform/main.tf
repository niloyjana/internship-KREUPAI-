locals {
  name_prefix = "${var.project_name}-${var.environment}"

  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# ---- VPC ----
module "vpc" {
  source = "./modules/vpc"

  project_name       = var.project_name
  environment        = var.environment
  vpc_cidr           = var.vpc_cidr
  availability_zones = var.availability_zones
}

# ---- EKS ----
module "eks" {
  source = "./modules/eks"

  project_name                     = var.project_name
  environment                      = var.environment
  cluster_version                  = var.eks_cluster_version
  vpc_id                           = module.vpc.vpc_id
  private_subnet_ids               = module.vpc.private_subnet_ids
  platform_node_instance_types     = var.eks_platform_node_instance_types
  platform_node_desired_size       = var.eks_platform_node_desired
  platform_node_min_size           = var.eks_platform_node_min
  platform_node_max_size           = var.eks_platform_node_max
  ai_runtime_node_instance_types   = var.eks_ai_node_instance_types
  ai_runtime_node_desired_size     = var.eks_ai_node_desired
  ai_runtime_node_min_size         = var.eks_ai_node_min
  ai_runtime_node_max_size         = var.eks_ai_node_max
}

# ---- RDS (PostgreSQL with pgvector) ----
module "rds" {
  source = "./modules/rds"

  project_name          = var.project_name
  environment           = var.environment
  vpc_id                = module.vpc.vpc_id
  private_subnet_ids    = module.vpc.private_subnet_ids
  instance_class        = var.db_instance_class
  allocated_storage     = var.db_allocated_storage
  max_allocated_storage = var.db_max_allocated_storage
  db_name               = var.db_name
  db_username           = var.db_username
  db_password           = var.db_password
  multi_az              = var.db_multi_az
  eks_security_group_id = module.eks.node_security_group_id
}

# ---- Redis (ElastiCache) ----
module "redis" {
  source = "./modules/redis"

  project_name          = var.project_name
  environment           = var.environment
  vpc_id                = module.vpc.vpc_id
  private_subnet_ids    = module.vpc.private_subnet_ids
  node_type             = var.redis_node_type
  num_cache_nodes       = var.redis_num_cache_nodes
  eks_security_group_id = module.eks.node_security_group_id
}

# ---- Kafka (MSK) ----
module "kafka" {
  source = "./modules/kafka"

  project_name          = var.project_name
  environment           = var.environment
  vpc_id                = module.vpc.vpc_id
  private_subnet_ids    = module.vpc.private_subnet_ids
  instance_type         = var.kafka_instance_type
  number_of_brokers     = var.kafka_number_of_brokers
  ebs_volume_size       = var.kafka_ebs_volume_size
  eks_security_group_id = module.eks.node_security_group_id
}

# ---- S3 ----
module "s3" {
  source = "./modules/s3"

  project_name = var.project_name
  environment  = var.environment
}

# ---- ECR ----
module "ecr" {
  source = "./modules/ecr"

  project_name = var.project_name
  environment  = var.environment

  service_names = [
    "auth-service",
    "tenant-service",
    "subscription-service",
    "agent-registry",
    "workflow-service",
    "integration-hub",
    "notification-service",
    "analytics-service",
    "ai-runtime",
    "portal",
    "admin",
  ]
}
