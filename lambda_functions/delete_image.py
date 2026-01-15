"""
Lambda function for deleting images.
Removes image from S3 and metadata from DynamoDB.
"""
import json
import logging
import sys
import os
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils import (
    get_metadata_from_dynamodb, delete_from_s3, delete_metadata_from_dynamodb,
    create_api_response, create_error_response, extract_user_id_from_event
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handle_delete_image(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle delete image request.
    
    Path Parameters:
    - image_id: The ID of the image to delete
    """
    try:
        # Extract path parameters
        path_params = event.get('pathParameters') or {}
        image_id = path_params.get('image_id')
        
        if not image_id:
            return create_error_response(400, "Missing required path parameter: image_id", "MISSING_IMAGE_ID")
        
        # Get metadata to retrieve S3 key
        metadata = get_metadata_from_dynamodb(image_id)
        
        if not metadata:
            return create_error_response(404, f"Image with ID {image_id} not found", "IMAGE_NOT_FOUND")
        
        # Extract user ID for authorization check
        user_id = extract_user_id_from_event(event)
        
        # Optional: Check if user has permission to delete this image
        # Only allow deletion if user owns the image
        image_owner = metadata.get('user_id')
        if image_owner and image_owner != user_id and user_id != 'anonymous':
            return create_error_response(403, "You do not have permission to delete this image", "FORBIDDEN")
        
        # Get S3 key
        s3_key = metadata.get('s3_key')
        
        # Delete from S3 (if S3 key exists)
        s3_deleted = False
        if s3_key:
            try:
                delete_from_s3(s3_key)
                s3_deleted = True
            except Exception as e:
                logger.warning(f"Failed to delete from S3: {str(e)}")
                # Continue with DynamoDB deletion even if S3 deletion fails
                # This ensures metadata is cleaned up
        
        # Delete metadata from DynamoDB
        try:
            delete_metadata_from_dynamodb(image_id)
        except Exception as e:
            logger.error(f"Failed to delete metadata: {str(e)}")
            # If DynamoDB deletion fails but S3 was deleted, we have inconsistent state
            # In production, consider implementing a cleanup job for orphaned S3 objects
            if s3_deleted:
                return create_error_response(
                    500,
                    "Image deleted from storage but metadata deletion failed. Image may be orphaned.",
                    "PARTIAL_DELETION_ERROR"
                )
            return create_error_response(500, "Failed to delete image metadata", "DYNAMODB_ERROR")
        
        # Return success response
        response_body = {
            'image_id': image_id,
            'message': 'Image deleted successfully',
            's3_deleted': s3_deleted,
            'metadata_deleted': True
        }
        
        return create_api_response(200, response_body)
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return create_error_response(500, "Internal server error", "INTERNAL_ERROR")


# Backward compatibility: lambda_handler wrapper
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Backward compatibility wrapper."""
    return handle_delete_image(event, context)
