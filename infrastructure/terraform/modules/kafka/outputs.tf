output "bootstrap_brokers" {
  description = "Plaintext bootstrap broker connection string"
  value       = aws_msk_cluster.main.bootstrap_brokers
}

output "bootstrap_brokers_tls" {
  description = "TLS bootstrap broker connection string"
  value       = aws_msk_cluster.main.bootstrap_brokers_tls
}

output "zookeeper_connect" {
  description = "ZooKeeper connection string"
  value       = aws_msk_cluster.main.zookeeper_connect_string
}

output "cluster_arn" {
  description = "MSK cluster ARN"
  value       = aws_msk_cluster.main.arn
}

output "security_group_id" {
  description = "Security group ID for Kafka"
  value       = aws_security_group.kafka.id
}
