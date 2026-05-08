locals {
  name_prefix = "${var.project_name}-${var.environment}"
}

# ---- Security Group ----
resource "aws_security_group" "kafka" {
  name_prefix = "${local.name_prefix}-kafka-"
  description = "Security group for MSK Kafka"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 9092
    to_port         = 9098
    protocol        = "tcp"
    security_groups = [var.eks_security_group_id]
    description     = "Allow Kafka from EKS nodes"
  }

  ingress {
    from_port       = 2181
    to_port         = 2181
    protocol        = "tcp"
    security_groups = [var.eks_security_group_id]
    description     = "Allow ZooKeeper from EKS nodes"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound"
  }

  tags = {
    Name = "${local.name_prefix}-kafka-sg"
  }

  lifecycle {
    create_before_destroy = true
  }
}

# ---- MSK Configuration ----
resource "aws_msk_configuration" "main" {
  name              = "${local.name_prefix}-kafka-config"
  kafka_versions    = ["3.5.1"]
  server_properties = <<PROPERTIES
auto.create.topics.enable=true
delete.topic.enable=true
default.replication.factor=3
min.insync.replicas=2
num.partitions=6
log.retention.hours=168
log.retention.bytes=1073741824
PROPERTIES
}

# ---- MSK Cluster ----
resource "aws_msk_cluster" "main" {
  cluster_name           = "${local.name_prefix}-kafka"
  kafka_version          = "3.5.1"
  number_of_broker_nodes = var.number_of_brokers

  broker_node_group_info {
    instance_type   = var.instance_type
    client_subnets  = var.private_subnet_ids
    security_groups = [aws_security_group.kafka.id]

    storage_info {
      ebs_storage_info {
        volume_size = var.ebs_volume_size
      }
    }
  }

  configuration_info {
    arn      = aws_msk_configuration.main.arn
    revision = aws_msk_configuration.main.latest_revision
  }

  encryption_info {
    encryption_in_transit {
      client_broker = "TLS_PLAINTEXT"
      in_cluster    = true
    }
  }

  logging_info {
    broker_logs {
      cloudwatch_logs {
        enabled   = true
        log_group = aws_cloudwatch_log_group.kafka.name
      }
    }
  }

  open_monitoring {
    prometheus {
      jmx_exporter {
        enabled_in_broker = true
      }
      node_exporter {
        enabled_in_broker = true
      }
    }
  }

  tags = {
    Name = "${local.name_prefix}-kafka"
  }
}

# ---- CloudWatch Log Group ----
resource "aws_cloudwatch_log_group" "kafka" {
  name              = "/aws/msk/${local.name_prefix}-kafka"
  retention_in_days = 30

  tags = {
    Name = "${local.name_prefix}-kafka-logs"
  }
}
