output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "vpc_cidr" {
  description = "VPC CIDR block"
  value       = aws_vpc.main.cidr_block
}

output "public_subnet_ids" {
  description = "List of public subnet IDs"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "List of private subnet IDs"
  value       = aws_subnet.private[*].id
}

output "internal_security_group_id" {
  description = "Security group ID for internal VPC traffic"
  value       = aws_security_group.internal.id
}

output "nat_gateway_ips" {
  description = "NAT Gateway Elastic IP addresses"
  value       = aws_eip.nat[*].public_ip
}
