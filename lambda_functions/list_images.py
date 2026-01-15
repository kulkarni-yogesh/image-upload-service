"""
Lambda function for listing images with filtering and pagination support.
Supports filtering by user_id, category, tags, and date range.
"""
import json
import logging
import sys
import os
from typing import Dict, Any
from datetime import datetime
from botocore.exceptions import ClientError

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils import (
    create_api_response, create_error_response
)
from config import DYNAMODB_TABLE_NAME, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Use shared DynamoDB clients from utils to avoid duplicate initialization
from utils import dynamodb, dynamodb_client


def handle_list_images(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle list images request with filtering and pagination.
    
    Query Parameters:
    - user_id: Filter by user ID
    - category: Filter by category
    - tag: Filter by tag (can be used multiple times)
    - start_date: Filter images created after this date (ISO format)
    - end_date: Filter images created before this date (ISO format)
    - page: Page number (default: 1)
    - page_size: Number of items per page (default: 20, max: 100)
    - last_key: Last evaluated key for pagination (from previous response)
    """
    try:
        # Extract query parameters
        query_params = event.get('queryStringParameters') or {}
        
        # Pagination parameters
        try:
            page = int(query_params.get('page', 1))
            if page < 1:
                page = 1
        except (ValueError, TypeError):
            page = 1
        
        try:
            page_size = int(query_params.get('page_size', DEFAULT_PAGE_SIZE))
            if page_size < 1:
                page_size = DEFAULT_PAGE_SIZE
            elif page_size > MAX_PAGE_SIZE:
                page_size = MAX_PAGE_SIZE
        except (ValueError, TypeError):
            page_size = DEFAULT_PAGE_SIZE
        
        # Extract filters
        user_id_filter = query_params.get('user_id')
        category_filter = query_params.get('category')
        tags_filter = query_params.get('tag')  # Can be comma-separated or multiple values
        start_date = query_params.get('start_date')
        end_date = query_params.get('end_date')
        
        # Parse tags if provided
        tags_list = []
        if tags_filter:
            if isinstance(tags_filter, str):
                tags_list = [tag.strip() for tag in tags_filter.split(',')]
            elif isinstance(tags_filter, list):
                tags_list = tags_filter
        
        # Parse dates if provided
        start_datetime = None
        end_datetime = None
        if start_date:
            try:
                start_datetime = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except ValueError:
                return create_error_response(400, "Invalid start_date format. Use ISO format.", "INVALID_DATE")
        
        if end_date:
            try:
                end_datetime = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except ValueError:
                return create_error_response(400, "Invalid end_date format. Use ISO format.", "INVALID_DATE")
        
        # Build filter expression
        table = dynamodb.Table(DYNAMODB_TABLE_NAME)
        
        # Start with scan (since we need to filter on multiple attributes)
        # In production, consider using GSI (Global Secondary Index) for better performance
        filter_expressions = []
        expression_attribute_names = {}
        expression_attribute_values = {}
        
        if user_id_filter:
            filter_expressions.append('#user_id = :user_id')
            expression_attribute_names['#user_id'] = 'user_id'
            expression_attribute_values[':user_id'] = user_id_filter
        
        if category_filter:
            filter_expressions.append('#category = :category')
            expression_attribute_names['#category'] = 'category'
            expression_attribute_values[':category'] = category_filter
        
        if tags_list:
            # Check if any tag in the image's tags list matches
            # Assuming tags is stored as a list attribute
            tag_conditions = []
            for idx, tag in enumerate(tags_list):
                tag_key = f':tag{idx}'
                expression_attribute_values[tag_key] = tag
                tag_conditions.append(f'contains(#tags, {tag_key})')
            
            if tag_conditions:
                expression_attribute_names['#tags'] = 'tags'
                filter_expressions.append(f"({' OR '.join(tag_conditions)})")
        
        if start_datetime:
            filter_expressions.append('#created_at >= :start_date')
            expression_attribute_names['#created_at'] = 'created_at'
            expression_attribute_values[':start_date'] = start_datetime.isoformat()
        
        if end_datetime:
            filter_expressions.append('#created_at <= :end_date')
            expression_attribute_names['#created_at'] = 'created_at'
            expression_attribute_values[':end_date'] = end_datetime.isoformat()
        
        # Build scan parameters
        scan_kwargs = {
            'Limit': page_size
        }
        
        if filter_expressions:
            scan_kwargs['FilterExpression'] = ' AND '.join(filter_expressions)
            scan_kwargs['ExpressionAttributeNames'] = expression_attribute_names
            scan_kwargs['ExpressionAttributeValues'] = expression_attribute_values
        
        # Handle pagination with last evaluated key
        last_key = query_params.get('last_key')
        if last_key:
            try:
                # Parse last_key from previous response
                last_key_dict = json.loads(last_key)
                scan_kwargs['ExclusiveStartKey'] = last_key_dict
            except (json.JSONDecodeError, TypeError):
                pass  # Ignore invalid last_key
        
        # Perform scan
        try:
            response = table.scan(**scan_kwargs)
            items = response.get('Items', [])
            
            # Sort by created_at descending (newest first)
            items.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            # Prepare response
            result = {
                'images': items,
                'count': len(items),
                'page': page,
                'page_size': page_size
            }
            
            # Add pagination info
            if 'LastEvaluatedKey' in response:
                result['last_key'] = json.dumps(response['LastEvaluatedKey'])
                result['has_more'] = True
            else:
                result['has_more'] = False
            
            return create_api_response(200, result)
            
        except ClientError as e:
            logger.error(f"DynamoDB error: {str(e)}")
            return create_error_response(500, "Failed to retrieve images", "DYNAMODB_ERROR")
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return create_error_response(500, "Internal server error", "INTERNAL_ERROR")


# Backward compatibility: lambda_handler wrapper
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Backward compatibility wrapper."""
    return handle_list_images(event, context)
