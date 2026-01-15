"""
Lambda function for viewing/downloading images.
Returns presigned URL for secure image access.
"""
import json
import logging
import sys
import os
from typing import Dict, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils import (
    get_metadata_from_dynamodb, generate_presigned_url,
    create_api_response, create_error_response, extract_user_id_from_event
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handle_get_image(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle get image request.
    
    Path Parameters:
    - image_id: The ID of the image to retrieve
    
    Query Parameters:
    - download: If true, return download URL (default: false)
    - expiration: URL expiration time in seconds (default: 3600, max: 604800)
    """
    try:
        # Extract path parameters
        path_params = event.get('pathParameters') or {}
        image_id = path_params.get('image_id')
        
        if not image_id:
            return create_error_response(400, "Missing required path parameter: image_id", "MISSING_IMAGE_ID")
        
        # Extract query parameters
        query_params = event.get('queryStringParameters') or {}
        is_download = query_params.get('download', 'false').lower() == 'true'
        
        # Get expiration time (max 7 days)
        try:
            expiration = int(query_params.get('expiration', 3600))
            if expiration < 1:
                expiration = 3600
            elif expiration > 604800:  # 7 days max
                expiration = 604800
        except (ValueError, TypeError):
            expiration = 3600
        
        # Get metadata from DynamoDB
        metadata = get_metadata_from_dynamodb(image_id)
        
        if not metadata:
            return create_error_response(404, f"Image with ID {image_id} not found", "IMAGE_NOT_FOUND")
        
        # Extract user ID (for authorization check - optional)
        user_id = extract_user_id_from_event(event)
        
        # Optional: Check if user has permission to view this image
        # For now, we'll allow all authenticated users to view any image
        # In production, add proper authorization logic here
        
        # Get S3 key from metadata
        s3_key = metadata.get('s3_key')
        if not s3_key:
            return create_error_response(500, "Image metadata is corrupted: missing S3 key", "CORRUPTED_METADATA")
        
        # Generate presigned URL
        try:
            presigned_url = generate_presigned_url(s3_key, expiration)
        except Exception as e:
            logger.error(f"Failed to generate presigned URL: {str(e)}")
            return create_error_response(500, "Failed to generate image URL", "URL_GENERATION_ERROR")
        
        # Prepare response
        response_body = {
            'image_id': image_id,
            'presigned_url': presigned_url,
            'expiration_seconds': expiration,
            'metadata': {
                k: v for k, v in metadata.items()
                if k not in ['s3_key', 's3_bucket']  # Don't expose internal details
            }
        }
        
        # If download requested, add Content-Disposition header info
        if is_download:
            # Extract filename from metadata or use image_id
            title = metadata.get('title', image_id)
            content_type = metadata.get('content_type', 'image/jpeg')
            extension = content_type.split('/')[-1] if '/' in content_type else 'jpg'
            filename = f"{title}.{extension}" if title else f"{image_id}.{extension}"
            response_body['download_filename'] = filename
        
        return create_api_response(200, response_body)
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return create_error_response(500, "Internal server error", "INTERNAL_ERROR")


# Backward compatibility: lambda_handler wrapper
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Backward compatibility wrapper."""
    return handle_get_image(event, context)
