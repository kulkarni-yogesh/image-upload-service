"""
Unit tests for utility functions.
"""
import pytest
import base64
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils import (
    validate_image_content_type, validate_image_size,
    parse_base64_image, generate_image_id,
    create_api_response, create_error_response
)
from config import ALLOWED_IMAGE_TYPES, MAX_IMAGE_SIZE_BYTES


class TestUtils:
    """Test cases for utility functions."""
    
    def test_validate_image_content_type_valid(self):
        """Test validation of valid content types."""
        for content_type in ALLOWED_IMAGE_TYPES:
            assert validate_image_content_type(content_type) is True
            assert validate_image_content_type(content_type.upper()) is True
    
    def test_validate_image_content_type_invalid(self):
        """Test validation of invalid content types."""
        assert validate_image_content_type('application/pdf') is False
        assert validate_image_content_type('text/plain') is False
        assert validate_image_content_type('') is False
    
    def test_validate_image_size_valid(self):
        """Test validation of valid image sizes."""
        assert validate_image_size(1024) is True
        assert validate_image_size(MAX_IMAGE_SIZE_BYTES) is True
        assert validate_image_size(1) is True
    
    def test_validate_image_size_invalid(self):
        """Test validation of invalid image sizes."""
        assert validate_image_size(0) is False
        assert validate_image_size(-1) is False
        assert validate_image_size(MAX_IMAGE_SIZE_BYTES + 1) is False
    
    def test_parse_base64_image_simple(self):
        """Test parsing simple base64 image."""
        # Create a minimal valid base64 string
        test_data = b'test image data'
        base64_data = base64.b64encode(test_data).decode('utf-8')
        
        image_bytes, content_type = parse_base64_image(base64_data)
        
        assert image_bytes == test_data
        assert content_type == 'image/jpeg'  # Default
    
    def test_parse_base64_image_with_header(self):
        """Test parsing base64 image with data URL header."""
        test_data = b'test image data'
        base64_data = base64.b64encode(test_data).decode('utf-8')
        full_data = f'data:image/png;base64,{base64_data}'
        
        image_bytes, content_type = parse_base64_image(full_data)
        
        assert image_bytes == test_data
        assert content_type == 'image/png'
    
    def test_parse_base64_image_invalid(self):
        """Test parsing invalid base64 data."""
        with pytest.raises(ValueError):
            parse_base64_image('invalid!!!base64')
    
    def test_generate_image_id(self):
        """Test image ID generation."""
        image_id1 = generate_image_id()
        image_id2 = generate_image_id()
        
        assert image_id1 != image_id2
        assert len(image_id1) > 0
        assert isinstance(image_id1, str)
    
    def test_create_api_response(self):
        """Test API response creation."""
        body = {'message': 'success'}
        response = create_api_response(200, body)
        
        assert response['statusCode'] == 200
        assert 'headers' in response
        assert 'body' in response
        assert 'Content-Type' in response['headers']
        assert 'Access-Control-Allow-Origin' in response['headers']
    
    def test_create_error_response(self):
        """Test error response creation."""
        response = create_error_response(400, 'Bad request', 'BAD_REQUEST')
        
        assert response['statusCode'] == 400
        body = eval(response['body'])  # Parse JSON string
        assert 'error' in body
        assert body['error'] == 'Bad request'
        assert body.get('error_code') == 'BAD_REQUEST'
