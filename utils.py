"""
Utility functions for image upload service.
"""
import json
import base64
import uuid
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError
from config import (
    AWS_REGION, AWS_ENDPOINT_URL, S3_BUCKET_NAME, S3_PRESIGNED_URL_EXPIRATION,
    DYNAMODB_TABLE_NAME, ALLOWED_IMAGE_TYPES, MAX_IMAGE_SIZE_BYTES
)

# Initialize AWS clients
# Use dummy credentials for LocalStack if endpoint URL is set
client_kwargs = {
    'region_name': AWS_REGION,
    'endpoint_url': AWS_ENDPOINT_URL
}
if AWS_ENDPOINT_URL:
    client_kwargs['aws_access_key_id'] = os.environ.get('AWS_ACCESS_KEY_ID', 'test')
    client_kwargs['aws_secret_access_key'] = os.environ.get('AWS_SECRET_ACCESS_KEY', 'test')

s3_client = boto3.client('s3', **client_kwargs)
dynamodb = boto3.resource('dynamodb', **client_kwargs)
dynamodb_client = boto3.client('dynamodb', **client_kwargs)


def generate_image_id() -> str:
    """Generate a unique image ID."""
    return str(uuid.uuid4())


def validate_image_content_type(content_type: str) -> bool:
    """Validate if the content type is an allowed image type."""
    return content_type.lower() in [t.lower() for t in ALLOWED_IMAGE_TYPES]


def validate_image_size(size: int) -> bool:
    """Validate if the image size is within limits."""
    return 0 < size <= MAX_IMAGE_SIZE_BYTES


def parse_base64_image(base64_string: str) -> tuple[bytes, str]:
    """
    Parse base64 encoded image string.
    Returns: (image_bytes, content_type)
    """
    try:
        # Handle data URL format: data:image/jpeg;base64,<data>
        if ',' in base64_string:
            header, data = base64_string.split(',', 1)
            # Extract content type from header
            if 'data:' in header and ';' in header:
                content_type = header.split(';')[0].split(':')[1]
            else:
                content_type = 'image/jpeg'  # Default
        else:
            data = base64_string
            content_type = 'image/jpeg'  # Default
        
        image_bytes = base64.b64decode(data)
        return image_bytes, content_type
    except Exception as e:
        raise ValueError(f"Invalid base64 image data: {str(e)}")


def upload_to_s3(image_bytes: bytes, image_id: str, content_type: str) -> str:
    """
    Upload image to S3 bucket.
    Returns: S3 key
    """
    try:
        # Determine file extension from content type
        extension_map = {
            'image/jpeg': 'jpg',
            'image/jpg': 'jpg',
            'image/png': 'png',
            'image/gif': 'gif',
            'image/webp': 'webp'
        }
        extension = extension_map.get(content_type.lower(), 'jpg')
        s3_key = f"images/{image_id}.{extension}"
        
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=s3_key,
            Body=image_bytes,
            ContentType=content_type,
            Metadata={
                'image-id': image_id,
                'uploaded-at': datetime.now(timezone.utc).isoformat()
            }
        )
        
        return s3_key
    except ClientError as e:
        raise Exception(f"Failed to upload image to S3: {str(e)}")


def save_metadata_to_dynamodb(image_id: str, metadata: Dict[str, Any], s3_key: str, user_id: str) -> None:
    """
    Save image metadata to DynamoDB.
    """
    try:
        table = dynamodb.Table(DYNAMODB_TABLE_NAME)
        
        item = {
            'image_id': image_id,
            'user_id': user_id,
            's3_key': s3_key,
            's3_bucket': S3_BUCKET_NAME,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat(),
            **metadata
        }
        
        table.put_item(Item=item)
    except ClientError as e:
        raise Exception(f"Failed to save metadata to DynamoDB: {str(e)}")


def get_metadata_from_dynamodb(image_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve image metadata from DynamoDB.
    """
    try:
        table = dynamodb.Table(DYNAMODB_TABLE_NAME)
        response = table.get_item(Key={'image_id': image_id})
        
        if 'Item' in response:
            return response['Item']
        return None
    except ClientError as e:
        raise Exception(f"Failed to retrieve metadata from DynamoDB: {str(e)}")


def generate_presigned_url(s3_key: str, expiration: int = S3_PRESIGNED_URL_EXPIRATION) -> str:
    """
    Generate a presigned URL for S3 object access.
    """
    try:
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': S3_BUCKET_NAME, 'Key': s3_key},
            ExpiresIn=expiration
        )
        return url
    except ClientError as e:
        raise Exception(f"Failed to generate presigned URL: {str(e)}")


def delete_from_s3(s3_key: str) -> None:
    """
    Delete image from S3 bucket.
    """
    try:
        s3_client.delete_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
    except ClientError as e:
        raise Exception(f"Failed to delete image from S3: {str(e)}")


def delete_metadata_from_dynamodb(image_id: str) -> None:
    """
    Delete image metadata from DynamoDB.
    """
    try:
        table = dynamodb.Table(DYNAMODB_TABLE_NAME)
        table.delete_item(Key={'image_id': image_id})
    except ClientError as e:
        raise Exception(f"Failed to delete metadata from DynamoDB: {str(e)}")


def convert_decimals(obj):
    """Convert Decimal types to float/int for JSON serialization."""
    if isinstance(obj, Decimal):
        return float(obj) if obj % 1 else int(obj)
    elif isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    return obj


def create_api_response(status_code: int, body: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Create a standardized API Gateway response.
    """
    default_headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }
    
    if headers:
        default_headers.update(headers)
    
    # Convert Decimal types to native Python types for JSON serialization
    body = convert_decimals(body)
    
    return {
        'statusCode': status_code,
        'headers': default_headers,
        'body': json.dumps(body)
    }


def create_error_response(status_code: int, error_message: str, error_code: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a standardized error response.
    """
    body = {
        'error': error_message
    }
    if error_code:
        body['error_code'] = error_code
    
    return create_api_response(status_code, body)


def extract_user_id_from_event(event: Dict[str, Any]) -> str:
    """
    Extract user ID from API Gateway event.
    In a real scenario, this would come from authentication token.
    For now, we'll use a header or default to 'anonymous'.
    """
    headers = event.get('headers', {}) or {}
    user_id = headers.get('x-user-id') or headers.get('X-User-Id') or 'anonymous'
    return user_id
