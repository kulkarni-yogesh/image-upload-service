"""
Unit tests for get_image Lambda function.
"""
import json
import pytest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lambda_functions.get_image import lambda_handler


class TestGetImage:
    """Test cases for get image functionality."""
    
    @patch('lambda_functions.get_image.get_metadata_from_dynamodb')
    @patch('lambda_functions.get_image.generate_presigned_url')
    def test_get_image_success(self, mock_presigned_url, mock_get_metadata, api_gateway_event_base):
        """Test successful image retrieval."""
        mock_get_metadata.return_value = {
            'image_id': 'test-id',
            'user_id': 'user1',
            's3_key': 'images/test-id.jpg',
            'title': 'Test Image',
            'content_type': 'image/jpeg',
            'created_at': '2024-01-01T00:00:00'
        }
        mock_presigned_url.return_value = 'https://s3.amazonaws.com/presigned-url'
        
        event = api_gateway_event_base.copy()
        event['pathParameters'] = {'image_id': 'test-id'}
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'presigned_url' in body
        assert body['image_id'] == 'test-id'
        assert 'metadata' in body
    
    @patch('lambda_functions.get_image.get_metadata_from_dynamodb')
    def test_get_image_not_found(self, mock_get_metadata, api_gateway_event_base):
        """Test retrieval of non-existent image."""
        mock_get_metadata.return_value = None
        
        event = api_gateway_event_base.copy()
        event['pathParameters'] = {'image_id': 'nonexistent-id'}
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert 'error' in body
        assert 'IMAGE_NOT_FOUND' in body.get('error_code', '')
    
    def test_get_image_missing_image_id(self, api_gateway_event_base):
        """Test retrieval without image_id parameter."""
        event = api_gateway_event_base.copy()
        event['pathParameters'] = {}
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body
        assert 'MISSING_IMAGE_ID' in body.get('error_code', '')
    
    @patch('lambda_functions.get_image.get_metadata_from_dynamodb')
    def test_get_image_missing_s3_key(self, mock_get_metadata, api_gateway_event_base):
        """Test retrieval when metadata is missing S3 key."""
        mock_get_metadata.return_value = {
            'image_id': 'test-id',
            'user_id': 'user1'
            # Missing s3_key
        }
        
        event = api_gateway_event_base.copy()
        event['pathParameters'] = {'image_id': 'test-id'}
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert 'error' in body
        assert 'CORRUPTED_METADATA' in body.get('error_code', '')
    
    @patch('lambda_functions.get_image.get_metadata_from_dynamodb')
    @patch('lambda_functions.get_image.generate_presigned_url')
    def test_get_image_url_generation_error(self, mock_presigned_url, mock_get_metadata, api_gateway_event_base):
        """Test handling of URL generation errors."""
        mock_get_metadata.return_value = {
            'image_id': 'test-id',
            's3_key': 'images/test-id.jpg'
        }
        mock_presigned_url.side_effect = Exception("URL generation failed")
        
        event = api_gateway_event_base.copy()
        event['pathParameters'] = {'image_id': 'test-id'}
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert 'error' in body
        assert 'URL_GENERATION_ERROR' in body.get('error_code', '')
    
    @patch('lambda_functions.get_image.get_metadata_from_dynamodb')
    @patch('lambda_functions.get_image.generate_presigned_url')
    def test_get_image_with_download_flag(self, mock_presigned_url, mock_get_metadata, api_gateway_event_base):
        """Test retrieval with download flag."""
        mock_get_metadata.return_value = {
            'image_id': 'test-id',
            's3_key': 'images/test-id.jpg',
            'title': 'Test Image',
            'content_type': 'image/jpeg'
        }
        mock_presigned_url.return_value = 'https://s3.amazonaws.com/presigned-url'
        
        event = api_gateway_event_base.copy()
        event['pathParameters'] = {'image_id': 'test-id'}
        event['queryStringParameters'] = {'download': 'true'}
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'download_filename' in body
    
    @patch('lambda_functions.get_image.get_metadata_from_dynamodb')
    @patch('lambda_functions.get_image.generate_presigned_url')
    def test_get_image_custom_expiration(self, mock_presigned_url, mock_get_metadata, api_gateway_event_base):
        """Test retrieval with custom expiration time."""
        mock_get_metadata.return_value = {
            'image_id': 'test-id',
            's3_key': 'images/test-id.jpg'
        }
        mock_presigned_url.return_value = 'https://s3.amazonaws.com/presigned-url'
        
        event = api_gateway_event_base.copy()
        event['pathParameters'] = {'image_id': 'test-id'}
        event['queryStringParameters'] = {'expiration': '7200'}
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['expiration_seconds'] == 7200
        # Verify presigned URL was called (expiration is handled in get_image.py, not passed to generate_presigned_url)
        mock_presigned_url.assert_called_once()
    
    @patch('lambda_functions.get_image.get_metadata_from_dynamodb')
    @patch('lambda_functions.get_image.generate_presigned_url')
    def test_get_image_expiration_max_limit(self, mock_presigned_url, mock_get_metadata, api_gateway_event_base):
        """Test that expiration is capped at maximum (7 days)."""
        mock_get_metadata.return_value = {
            'image_id': 'test-id',
            's3_key': 'images/test-id.jpg'
        }
        mock_presigned_url.return_value = 'https://s3.amazonaws.com/presigned-url'
        
        event = api_gateway_event_base.copy()
        event['pathParameters'] = {'image_id': 'test-id'}
        event['queryStringParameters'] = {'expiration': '1000000'}  # Exceeds max
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['expiration_seconds'] <= 604800  # Max 7 days
