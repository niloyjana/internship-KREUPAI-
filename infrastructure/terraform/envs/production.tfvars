# ---- Production Environment Configuration ----

environment = "production"
aws_region  = "us-east-1"

# VPC
vpc_cidr           = "10.0.0.0/16"
availability_zones = ["us-east-1a", "us-east-1b", "us-east-1c"]

# EKS
eks_cluster_version              = "1.29"
eks_platform_node_instance_types = ["t3.large"]
eks_platform_node_desired        = 3
eks_platform_node_min            = 2
eks_platform_node_max            = 10
eks_ai_node_instance_types       = ["g5.xlarge"]
eks_ai_node_desired              = 2
eks_ai_node_min                  = 1
eks_ai_node_max                  = 5

# RDS
db_instance_class        = "db.r6g.large"
db_allocated_storage     = 100
db_max_allocated_storage = 500
db_name                  = "adwp"
db_username              = "adwp_admin"
db_multi_az              = true

# Redis
redis_node_type       = "cache.r6g.large"
redis_num_cache_nodes = 3

# Kafka
kafka_instance_type     = "kafka.m5.large"
kafka_number_of_brokers = 3
kafka_ebs_volume_size   = 100
