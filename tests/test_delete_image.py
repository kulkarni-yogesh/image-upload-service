"""
Unit tests for delete_image Lambda function.
"""
import json
import pytest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lambda_functions.delete_image import lambda_handler


class TestDeleteImage:
    """Test cases for delete image functionality."""
    
    @patch('lambda_functions.delete_image.get_metadata_from_dynamodb')
    @patch('lambda_functions.delete_image.delete_from_s3')
    @patch('lambda_functions.delete_image.delete_metadata_from_dynamodb')
    def test_delete_image_success(self, mock_delete_ddb, mock_delete_s3, mock_get_metadata, api_gateway_event_base):
        """Test successful image deletion."""
        mock_get_metadata.return_value = {
            'image_id': 'test-id',
            'user_id': 'test-user-123',
            's3_key': 'images/test-id.jpg'
        }
        
        event = api_gateway_event_base.copy()
        event['pathParameters'] = {'image_id': 'test-id'}
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['message'] == 'Image deleted successfully'
        assert body['s3_deleted'] is True
        assert body['metadata_deleted'] is True
        assert mock_delete_s3.called
        assert mock_delete_ddb.called
    
    @patch('lambda_functions.delete_image.get_metadata_from_dynamodb')
    def test_delete_image_not_found(self, mock_get_metadata, api_gateway_event_base):
        """Test deletion of non-existent image."""
        mock_get_metadata.return_value = None
        
        event = api_gateway_event_base.copy()
        event['pathParameters'] = {'image_id': 'nonexistent-id'}
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert 'error' in body
        assert 'IMAGE_NOT_FOUND' in body.get('error_code', '')
    
    def test_delete_image_missing_image_id(self, api_gateway_event_base):
        """Test deletion without image_id parameter."""
        event = api_gateway_event_base.copy()
        event['pathParameters'] = {}
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body
        assert 'MISSING_IMAGE_ID' in body.get('error_code', '')
    
    @patch('lambda_functions.delete_image.get_metadata_from_dynamodb')
    @patch('lambda_functions.delete_image.delete_from_s3')
    @patch('lambda_functions.delete_image.delete_metadata_from_dynamodb')
    def test_delete_image_permission_denied(self, mock_delete_ddb, mock_delete_s3, mock_get_metadata, api_gateway_event_base):
        """Test deletion when user doesn't have permission."""
        mock_get_metadata.return_value = {
            'image_id': 'test-id',
            'user_id': 'other-user',
            's3_key': 'images/test-id.jpg'
        }
        
        event = api_gateway_event_base.copy()
        event['pathParameters'] = {'image_id': 'test-id'}
        # User ID in header is 'test-user-123', but image belongs to 'other-user'
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert 'error' in body
        assert 'FORBIDDEN' in body.get('error_code', '')
        assert not mock_delete_s3.called
        assert not mock_delete_ddb.called
    
    @patch('lambda_functions.delete_image.get_metadata_from_dynamodb')
    @patch('lambda_functions.delete_image.delete_from_s3')
    @patch('lambda_functions.delete_image.delete_metadata_from_dynamodb')
    def test_delete_image_s3_error_continues(self, mock_delete_ddb, mock_delete_s3, mock_get_metadata, api_gateway_event_base):
        """Test that DynamoDB deletion continues even if S3 deletion fails."""
        mock_get_metadata.return_value = {
            'image_id': 'test-id',
            'user_id': 'test-user-123',
            's3_key': 'images/test-id.jpg'
        }
        mock_delete_s3.side_effect = Exception("S3 deletion failed")
        
        event = api_gateway_event_base.copy()
        event['pathParameters'] = {'image_id': 'test-id'}
        
        response = lambda_handler(event, None)
        
        # Should still succeed, but note S3 deletion failed
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['s3_deleted'] is False
        assert body['metadata_deleted'] is True
        assert mock_delete_ddb.called
    
    @patch('lambda_functions.delete_image.get_metadata_from_dynamodb')
    @patch('lambda_functions.delete_image.delete_from_s3')
    @patch('lambda_functions.delete_image.delete_metadata_from_dynamodb')
    def test_delete_image_dynamodb_error(self, mock_delete_ddb, mock_delete_s3, mock_get_metadata, api_gateway_event_base):
        """Test handling of DynamoDB deletion errors."""
        mock_get_metadata.return_value = {
            'image_id': 'test-id',
            'user_id': 'test-user-123',
            's3_key': 'images/test-id.jpg'
        }
        mock_delete_s3.return_value = None
        mock_delete_ddb.side_effect = Exception("DynamoDB deletion failed")
        
        event = api_gateway_event_base.copy()
        event['pathParameters'] = {'image_id': 'test-id'}
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert 'error' in body
        # When S3 deletion succeeds but DynamoDB fails, it returns PARTIAL_DELETION_ERROR
        assert 'DYNAMODB_ERROR' in body.get('error_code', '') or 'PARTIAL_DELETION_ERROR' in body.get('error_code', '')
    
    @patch('lambda_functions.delete_image.get_metadata_from_dynamodb')
    @patch('lambda_functions.delete_image.delete_from_s3')
    @patch('lambda_functions.delete_image.delete_metadata_from_dynamodb')
    def test_delete_image_partial_deletion_error(self, mock_delete_ddb, mock_delete_s3, mock_get_metadata, api_gateway_event_base):
        """Test handling when S3 deletion succeeds but DynamoDB fails."""
        mock_get_metadata.return_value = {
            'image_id': 'test-id',
            'user_id': 'test-user-123',
            's3_key': 'images/test-id.jpg'
        }
        mock_delete_s3.return_value = None
        mock_delete_ddb.side_effect = Exception("DynamoDB deletion failed")
        
        event = api_gateway_event_base.copy()
        event['pathParameters'] = {'image_id': 'test-id'}
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert 'error' in body
        # Should indicate partial deletion
        assert 'PARTIAL_DELETION_ERROR' in body.get('error_code', '') or 'DYNAMODB_ERROR' in body.get('error_code', '')
    
    @patch('lambda_functions.delete_image.get_metadata_from_dynamodb')
    @patch('lambda_functions.delete_image.delete_from_s3')
    @patch('lambda_functions.delete_image.delete_metadata_from_dynamodb')
    def test_delete_image_no_s3_key(self, mock_delete_ddb, mock_delete_s3, mock_get_metadata, api_gateway_event_base):
        """Test deletion when metadata doesn't have S3 key."""
        mock_get_metadata.return_value = {
            'image_id': 'test-id',
            'user_id': 'test-user-123'
            # Missing s3_key
        }
        
        event = api_gateway_event_base.copy()
        event['pathParameters'] = {'image_id': 'test-id'}
        
        response = lambda_handler(event, None)
        
        # Should still succeed, but S3 deletion skipped
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['s3_deleted'] is False
        assert not mock_delete_s3.called
        assert mock_delete_ddb.called
