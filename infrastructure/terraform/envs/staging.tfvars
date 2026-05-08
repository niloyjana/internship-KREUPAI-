# ---- Staging Environment Configuration ----

environment = "staging"
aws_region  = "us-east-1"

# VPC
vpc_cidr           = "10.0.0.0/16"
availability_zones = ["us-east-1a", "us-east-1b"]

# EKS
eks_cluster_version              = "1.29"
eks_platform_node_instance_types = ["t3.medium"]
eks_platform_node_desired        = 2
eks_platform_node_min            = 1
eks_platform_node_max            = 5
eks_ai_node_instance_types       = ["t3.xlarge"]
eks_ai_node_desired              = 1
eks_ai_node_min                  = 1
eks_ai_node_max                  = 3

# RDS
db_instance_class        = "db.t3.large"
db_allocated_storage     = 50
db_max_allocated_storage = 200
db_name                  = "adwp_staging"
db_username              = "adwp_admin"
db_multi_az              = false

# Redis
redis_node_type       = "cache.t3.medium"
redis_num_cache_nodes = 2

# Kafka
kafka_instance_type     = "kafka.t3.small"
kafka_number_of_brokers = 2
kafka_ebs_volume_size   = 50
