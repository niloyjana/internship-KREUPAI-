output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "eks_cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = module.eks.cluster_endpoint
}

output "eks_cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = module.rds.endpoint
}

output "rds_database_name" {
  description = "RDS database name"
  value       = module.rds.database_name
}

output "redis_endpoint" {
  description = "ElastiCache Redis primary endpoint"
  value       = module.redis.primary_endpoint
}

output "redis_port" {
  description = "ElastiCache Redis port"
  value       = module.redis.port
}

output "kafka_bootstrap_brokers" {
  description = "MSK Kafka bootstrap broker connection string"
  value       = module.kafka.bootstrap_brokers
}

output "s3_documents_bucket" {
  description = "S3 bucket for documents"
  value       = module.s3.documents_bucket_name
}

output "s3_exports_bucket" {
  description = "S3 bucket for exports"
  value       = module.s3.exports_bucket_name
}

output "s3_backups_bucket" {
  description = "S3 bucket for backups"
  value       = module.s3.backups_bucket_name
}

output "ecr_repository_urls" {
  description = "Map of ECR repository URLs"
  value       = module.ecr.repository_urls
}
