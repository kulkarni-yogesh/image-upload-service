"""
Configuration settings for the image upload service.
"""
import os

# AWS Configuration
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
AWS_ENDPOINT_URL = os.environ.get('AWS_ENDPOINT_URL', None)  # For LocalStack

# S3 Configuration
S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'image-upload-bucket')
S3_PRESIGNED_URL_EXPIRATION = int(os.environ.get('S3_PRESIGNED_URL_EXPIRATION', 3600))  # 1 hour

# DynamoDB Configuration
DYNAMODB_TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME', 'image-metadata')
DYNAMODB_REGION = os.environ.get('DYNAMODB_REGION', AWS_REGION)

# Image Validation
ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
MAX_IMAGE_SIZE_MB = int(os.environ.get('MAX_IMAGE_SIZE_MB', 10))
MAX_IMAGE_SIZE_BYTES = MAX_IMAGE_SIZE_MB * 1024 * 1024

# Pagination
DEFAULT_PAGE_SIZE = int(os.environ.get('DEFAULT_PAGE_SIZE', 20))
MAX_PAGE_SIZE = int(os.environ.get('MAX_PAGE_SIZE', 100))
