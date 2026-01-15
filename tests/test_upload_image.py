"""
Unit tests for upload_image Lambda function.
"""
import json
import base64
import pytest
from unittest.mock import patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lambda_functions.upload_image import lambda_handler


class TestUploadImage:
    """Test cases for image upload functionality."""
    
    @patch('utils.s3_client')
    @patch('utils.dynamodb')
    def test_upload_image_success(self, mock_dynamodb, mock_s3_client, sample_image_base64, sample_metadata, api_gateway_event_base):
        """Test successful image upload."""
        # Mock S3 client
        mock_s3_client.put_object.return_value = {}
        
        # Mock DynamoDB table
        mock_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        
        # Prepare event
        event = api_gateway_event_base.copy()
        event['body'] = json.dumps({
            'image': sample_image_base64,
            'metadata': sample_metadata
        })
        
        # Call handler
        response = lambda_handler(event, None)
        
        # Assertions
        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        assert 'image_id' in body
        assert 's3_key' in body
        assert body['message'] == 'Image uploaded successfully'
        assert mock_s3_client.put_object.called
        assert mock_table.put_item.called
    
    def test_upload_image_missing_image(self, api_gateway_event_base, sample_metadata):
        """Test upload with missing image field."""
        event = api_gateway_event_base.copy()
        event['body'] = json.dumps({
            'metadata': sample_metadata
        })
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body
        assert 'MISSING_IMAGE' in body.get('error_code', '')
    
    def test_upload_image_invalid_base64(self, api_gateway_event_base, sample_metadata):
        """Test upload with invalid base64 data."""
        event = api_gateway_event_base.copy()
        event['body'] = json.dumps({
            'image': 'invalid-base64!!!',
            'metadata': sample_metadata
        })
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body
    
    def test_upload_image_invalid_content_type(self, api_gateway_event_base, sample_metadata):
        """Test upload with invalid content type."""
        # Create a valid base64 string but mark it as invalid type
        event = api_gateway_event_base.copy()
        event['body'] = json.dumps({
            'image': 'data:application/pdf;base64,JVBERi0xLjQKJdPr6eEKMSAwIG9iago8PAovVHlwZSAvQ2F0YWxvZwovUGFnZXMgMiAwIFIKPj4KZW5kb2JqCg==',
            'metadata': sample_metadata
        })
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body
        assert 'INVALID_CONTENT_TYPE' in body.get('error_code', '')
    
    def test_upload_image_too_large(self, sample_image_base64, sample_metadata, api_gateway_event_base):
        """Test upload with image that's too large."""
        # Create a very large base64 string (simulating large image)
        # Base64 encoding increases size by ~33%, so we need less raw data
        # 10MB limit = 10 * 1024 * 1024 = 10485760 bytes
        # Create 11MB of data: 11 * 1024 * 1024 = 11534336 bytes
        large_base64 = base64.b64encode(b'A' * (11 * 1024 * 1024)).decode('utf-8')
        
        event = api_gateway_event_base.copy()
        event['body'] = json.dumps({
            'image': large_base64,
            'metadata': sample_metadata
        })
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body
        assert 'IMAGE_TOO_LARGE' in body.get('error_code', '')
    
    @patch('utils.upload_to_s3')
    def test_upload_image_s3_error(self, mock_upload_s3, sample_image_base64, sample_metadata, api_gateway_event_base):
        """Test upload when S3 upload fails."""
        mock_upload_s3.side_effect = Exception("S3 upload failed")
        
        event = api_gateway_event_base.copy()
        event['body'] = json.dumps({
            'image': sample_image_base64,
            'metadata': sample_metadata
        })
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert 'error' in body
        assert 'S3_UPLOAD_ERROR' in body.get('error_code', '')
    
    @patch('lambda_functions.upload_image.upload_to_s3')
    @patch('lambda_functions.upload_image.save_metadata_to_dynamodb')
    @patch('utils.delete_from_s3')
    def test_upload_image_dynamodb_error(self, mock_delete_s3, mock_save_metadata, mock_upload_s3, sample_image_base64, sample_metadata, api_gateway_event_base):
        """Test upload when DynamoDB save fails."""
        mock_upload_s3.return_value = 'images/test-id.jpg'
        mock_save_metadata.side_effect = Exception("DynamoDB save failed")
        
        event = api_gateway_event_base.copy()
        event['body'] = json.dumps({
            'image': sample_image_base64,
            'metadata': sample_metadata
        })
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert 'error' in body
        # Should return DYNAMODB_ERROR, and delete_from_s3 should be called for cleanup
        assert 'DYNAMODB_ERROR' in body.get('error_code', '')
        # Verify cleanup was attempted
        assert mock_delete_s3.called
    
    def test_upload_image_invalid_json(self, api_gateway_event_base):
        """Test upload with invalid JSON."""
        event = api_gateway_event_base.copy()
        event['body'] = 'invalid json{'
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body
    
    @patch('lambda_functions.upload_image.upload_to_s3')
    @patch('lambda_functions.upload_image.save_metadata_to_dynamodb')
    def test_upload_image_empty_metadata(self, mock_ddb, mock_s3, sample_image_base64, api_gateway_event_base):
        """Test upload with empty metadata."""
        mock_s3.return_value = 'images/test-id.jpg'
        
        event = api_gateway_event_base.copy()
        event['body'] = json.dumps({
            'image': sample_image_base64,
            'metadata': {}
        })
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 201
        assert mock_s3.called
        assert mock_ddb.called
    
    @patch('lambda_functions.upload_image.upload_to_s3')
    @patch('lambda_functions.upload_image.save_metadata_to_dynamodb')
    def test_upload_image_with_data_url_header(self, mock_ddb, mock_s3, sample_image_base64, sample_metadata, api_gateway_event_base):
        """Test upload with data URL format (data:image/png;base64,...)."""
        mock_s3.return_value = 'images/test-id.png'
        
        event = api_gateway_event_base.copy()
        event['body'] = json.dumps({
            'image': f'data:image/png;base64,{sample_image_base64}',
            'metadata': sample_metadata
        })
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 201
        # Verify content type was extracted correctly
        assert mock_s3.called
        call_args = mock_s3.call_args
        assert call_args is not None
