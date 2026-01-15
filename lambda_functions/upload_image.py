"""
Lambda function for uploading images with metadata.
Handles image validation, S3 upload, and DynamoDB metadata persistence.
"""
import json
import logging
import sys
import os
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils import (
    generate_image_id, validate_image_content_type, validate_image_size,
    parse_base64_image, upload_to_s3, save_metadata_to_dynamodb,
    create_api_response, create_error_response, extract_user_id_from_event
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handle_upload_image(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle image upload request.
    
    Expected event body (JSON):
    {
        "image": "<base64_encoded_image>",
        "metadata": {
            "title": "My Image",
            "description": "Image description",
            "tags": ["tag1", "tag2"],
            "category": "nature"
        }
    }
    """
    try:
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        # Extract image and metadata
        image_base64 = body.get('image')
        metadata = body.get('metadata', {})
        
        # Validate required fields
        if not image_base64:
            return create_error_response(400, "Missing required field: image", "MISSING_IMAGE")
        
        # Extract user ID
        user_id = extract_user_id_from_event(event)
        
        # Parse and validate image
        try:
            image_bytes, content_type = parse_base64_image(image_base64)
        except ValueError as e:
            return create_error_response(400, str(e), "INVALID_IMAGE_FORMAT")
        
        # Validate content type
        if not validate_image_content_type(content_type):
            allowed_types = ', '.join(['jpeg', 'jpg', 'png', 'gif', 'webp'])
            return create_error_response(
                400,
                f"Invalid image type. Allowed types: {allowed_types}",
                "INVALID_CONTENT_TYPE"
            )
        
        # Validate image size
        image_size = len(image_bytes)
        if not validate_image_size(image_size):
            max_size_mb = image_size // (1024 * 1024)
            return create_error_response(
                400,
                f"Image size exceeds maximum allowed size of {max_size_mb}MB",
                "IMAGE_TOO_LARGE"
            )
        
        # Generate unique image ID
        image_id = generate_image_id()
        
        # Upload to S3
        try:
            s3_key = upload_to_s3(image_bytes, image_id, content_type)
        except Exception as e:
            logger.error(f"Failed to upload to S3: {str(e)}")
            return create_error_response(500, "Failed to upload image", "S3_UPLOAD_ERROR")
        
        # Save metadata to DynamoDB
        try:
            metadata['content_type'] = content_type
            metadata['size_bytes'] = image_size
            save_metadata_to_dynamodb(image_id, metadata, s3_key, user_id)
        except Exception as e:
            logger.error(f"Failed to save metadata: {str(e)}")
            # Try to clean up S3 object if DynamoDB save fails
            try:
                from utils import delete_from_s3
                delete_from_s3(s3_key)
            except:
                pass
            return create_error_response(500, "Failed to save metadata", "DYNAMODB_ERROR")
        
        # Return success response
        response_body = {
            'image_id': image_id,
            's3_key': s3_key,
            'message': 'Image uploaded successfully',
            'metadata': {
                'image_id': image_id,
                'user_id': user_id,
                's3_key': s3_key,
                **metadata
            }
        }
        
        return create_api_response(201, response_body)
        
    except json.JSONDecodeError:
        return create_error_response(400, "Invalid JSON in request body", "INVALID_JSON")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return create_error_response(500, "Internal server error", "INTERNAL_ERROR")


# Backward compatibility: lambda_handler wrapper
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Backward compatibility wrapper."""
    return handle_upload_image(event, context)
