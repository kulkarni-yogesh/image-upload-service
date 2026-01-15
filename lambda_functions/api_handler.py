"""
Unified Lambda function handler for all image upload service endpoints.
Routes requests internally based on HTTP method and path.
"""
import logging
import sys
import os
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils import (
    create_error_response
)

# Import individual handler functions
from lambda_functions.upload_image import handle_upload_image
from lambda_functions.list_images import handle_list_images
from lambda_functions.get_image import handle_get_image
from lambda_functions.delete_image import handle_delete_image

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Unified Lambda handler that routes requests to appropriate handlers.
    
    Routes:
    - POST /images -> upload_handler
    - GET /images -> list_handler
    - GET /images/{image_id} -> get_handler
    - DELETE /images/{image_id} -> delete_handler
    """
    try:
        # Extract HTTP method and path
        http_method = event.get('httpMethod', '')
        path = event.get('path', '')
        path_params = event.get('pathParameters') or {}
        
        # Route based on method and path
        if http_method == 'POST' and path == '/images':
            return handle_upload_image(event, context)
        
        elif http_method == 'GET' and path == '/images':
            return handle_list_images(event, context)
        
        elif http_method == 'GET' and path.startswith('/images/') and path_params.get('image_id'):
            return handle_get_image(event, context)
        
        elif http_method == 'DELETE' and path.startswith('/images/') and path_params.get('image_id'):
            return handle_delete_image(event, context)
        
        else:
            return create_error_response(
                404,
                f"Endpoint not found: {http_method} {path}",
                "NOT_FOUND"
            )
    
    except Exception as e:
        logger.error(f"Unexpected error in router: {str(e)}", exc_info=True)
        return create_error_response(500, "Internal server error", "INTERNAL_ERROR")
