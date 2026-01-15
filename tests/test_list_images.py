"""
Unit tests for list_images Lambda function.
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lambda_functions.list_images import lambda_handler


class TestListImages:
    """Test cases for list images functionality."""
    
    @patch('lambda_functions.list_images.dynamodb')
    def test_list_images_success(self, mock_dynamodb, api_gateway_event_base):
        """Test successful image listing."""
        # Mock DynamoDB table
        mock_table = MagicMock()
        mock_table.scan.return_value = {
            'Items': [
                {
                    'image_id': 'img1',
                    'user_id': 'user1',
                    'title': 'Image 1',
                    'created_at': '2024-01-01T00:00:00'
                },
                {
                    'image_id': 'img2',
                    'user_id': 'user1',
                    'title': 'Image 2',
                    'created_at': '2024-01-02T00:00:00'
                }
            ]
        }
        mock_dynamodb.Table.return_value = mock_table
        
        event = api_gateway_event_base.copy()
        event['queryStringParameters'] = {}
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'images' in body
        assert body['count'] == 2
        assert 'page' in body
        assert 'page_size' in body
    
    @patch('lambda_functions.list_images.dynamodb')
    def test_list_images_filter_by_user_id(self, mock_dynamodb, api_gateway_event_base):
        """Test filtering images by user_id."""
        mock_table = MagicMock()
        mock_table.scan.return_value = {
            'Items': [
                {
                    'image_id': 'img1',
                    'user_id': 'user1',
                    'title': 'Image 1'
                }
            ]
        }
        mock_dynamodb.Table.return_value = mock_table
        
        event = api_gateway_event_base.copy()
        event['queryStringParameters'] = {'user_id': 'user1'}
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        # Verify scan was called with filter
        assert mock_table.scan.called
    
    @patch('lambda_functions.list_images.dynamodb')
    def test_list_images_filter_by_category(self, mock_dynamodb, api_gateway_event_base):
        """Test filtering images by category."""
        mock_table = MagicMock()
        mock_table.scan.return_value = {'Items': []}
        mock_dynamodb.Table.return_value = mock_table
        
        event = api_gateway_event_base.copy()
        event['queryStringParameters'] = {'category': 'nature'}
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        assert mock_table.scan.called
    
    @patch('lambda_functions.list_images.dynamodb')
    def test_list_images_filter_by_tags(self, mock_dynamodb, api_gateway_event_base):
        """Test filtering images by tags."""
        mock_table = MagicMock()
        mock_table.scan.return_value = {'Items': []}
        mock_dynamodb.Table.return_value = mock_table
        
        event = api_gateway_event_base.copy()
        event['queryStringParameters'] = {'tag': 'nature,landscape'}
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        assert mock_table.scan.called
    
    @patch('lambda_functions.list_images.dynamodb')
    def test_list_images_filter_by_date_range(self, mock_dynamodb, api_gateway_event_base):
        """Test filtering images by date range."""
        mock_table = MagicMock()
        mock_table.scan.return_value = {'Items': []}
        mock_dynamodb.Table.return_value = mock_table
        
        start_date = (datetime.now() - timedelta(days=7)).isoformat()
        end_date = datetime.now().isoformat()
        
        event = api_gateway_event_base.copy()
        event['queryStringParameters'] = {
            'start_date': start_date,
            'end_date': end_date
        }
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        assert mock_table.scan.called
    
    def test_list_images_invalid_date_format(self, api_gateway_event_base):
        """Test with invalid date format."""
        event = api_gateway_event_base.copy()
        event['queryStringParameters'] = {'start_date': 'invalid-date'}
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body
        assert 'INVALID_DATE' in body.get('error_code', '')
    
    @patch('lambda_functions.list_images.dynamodb')
    def test_list_images_pagination(self, mock_dynamodb, api_gateway_event_base):
        """Test pagination functionality."""
        mock_table = MagicMock()
        mock_table.scan.return_value = {
            'Items': [{'image_id': f'img{i}'} for i in range(10)],
            'LastEvaluatedKey': {'image_id': 'img10'}
        }
        mock_dynamodb.Table.return_value = mock_table
        
        event = api_gateway_event_base.copy()
        event['queryStringParameters'] = {
            'page': 1,
            'page_size': 10
        }
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['has_more'] is True
        assert 'last_key' in body
    
    @patch('lambda_functions.list_images.dynamodb')
    def test_list_images_max_page_size(self, mock_dynamodb, api_gateway_event_base):
        """Test that page_size is capped at maximum."""
        mock_table = MagicMock()
        mock_table.scan.return_value = {'Items': []}
        mock_dynamodb.Table.return_value = mock_table
        
        event = api_gateway_event_base.copy()
        event['queryStringParameters'] = {'page_size': '1000'}  # Exceeds max
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        # Verify scan was called with max page size
        call_kwargs = mock_table.scan.call_args[1]
        assert call_kwargs['Limit'] <= 100  # MAX_PAGE_SIZE
    
    @patch('lambda_functions.list_images.dynamodb')
    def test_list_images_empty_result(self, mock_dynamodb, api_gateway_event_base):
        """Test listing when no images match filters."""
        mock_table = MagicMock()
        mock_table.scan.return_value = {'Items': []}
        mock_dynamodb.Table.return_value = mock_table
        
        event = api_gateway_event_base.copy()
        event['queryStringParameters'] = {'user_id': 'nonexistent'}
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['count'] == 0
        assert body['has_more'] is False
    
    @patch('lambda_functions.list_images.dynamodb')
    def test_list_images_dynamodb_error(self, mock_dynamodb, api_gateway_event_base):
        """Test handling of DynamoDB errors."""
        mock_table = MagicMock()
        from botocore.exceptions import ClientError
        mock_table.scan.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException'}},
            'Scan'
        )
        mock_dynamodb.Table.return_value = mock_table
        
        event = api_gateway_event_base.copy()
        event['queryStringParameters'] = {}
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert 'error' in body
