output "documents_bucket_name" {
  description = "Documents S3 bucket name"
  value       = aws_s3_bucket.documents.id
}

output "documents_bucket_arn" {
  description = "Documents S3 bucket ARN"
  value       = aws_s3_bucket.documents.arn
}

output "exports_bucket_name" {
  description = "Exports S3 bucket name"
  value       = aws_s3_bucket.exports.id
}

output "exports_bucket_arn" {
  description = "Exports S3 bucket ARN"
  value       = aws_s3_bucket.exports.arn
}

output "backups_bucket_name" {
  description = "Backups S3 bucket name"
  value       = aws_s3_bucket.backups.id
}

output "backups_bucket_arn" {
  description = "Backups S3 bucket ARN"
  value       = aws_s3_bucket.backups.arn
}
