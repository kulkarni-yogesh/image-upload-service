"""
Pytest configuration and fixtures for testing.
"""
import os
import pytest
import boto3
from moto import mock_s3, mock_dynamodb
from botocore.exceptions import ClientError


@pytest.fixture(scope='function')
def aws_credentials():
    """Mock AWS credentials for moto."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
    yield
    # Cleanup
    os.environ.pop('AWS_ACCESS_KEY_ID', None)
    os.environ.pop('AWS_SECRET_ACCESS_KEY', None)
    os.environ.pop('AWS_SECURITY_TOKEN', None)
    os.environ.pop('AWS_SESSION_TOKEN', None)
    os.environ.pop('AWS_DEFAULT_REGION', None)


@pytest.fixture(scope='function')
def s3_client(aws_credentials):
    """Create a mock S3 client."""
    with mock_s3():
        client = boto3.client('s3', region_name='us-east-1')
        yield client


@pytest.fixture(scope='function')
def s3_bucket(s3_client):
    """Create a test S3 bucket."""
    bucket_name = 'image-upload-bucket'
    s3_client.create_bucket(Bucket=bucket_name)
    yield bucket_name


@pytest.fixture(scope='function')
def dynamodb_resource(aws_credentials):
    """Create a mock DynamoDB resource."""
    with mock_dynamodb():
        resource = boto3.resource('dynamodb', region_name='us-east-1')
        yield resource


@pytest.fixture(scope='function')
def dynamodb_table(dynamodb_resource):
    """Create a test DynamoDB table."""
    table_name = 'image-metadata'
    table = dynamodb_resource.create_table(
        TableName=table_name,
        KeySchema=[
            {
                'AttributeName': 'image_id',
                'KeyType': 'HASH'
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'image_id',
                'AttributeType': 'S'
            }
        ],
        BillingMode='PAY_PER_REQUEST'
    )
    yield table


@pytest.fixture
def sample_image_base64():
    """Sample base64 encoded image (1x1 pixel PNG)."""
    # This is a minimal valid PNG image (1x1 pixel, transparent)
    return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="


@pytest.fixture
def sample_image_base64_with_header():
    """Sample base64 encoded image with data URL header."""
    base64_data = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    return f"data:image/png;base64,{base64_data}"


@pytest.fixture
def sample_metadata():
    """Sample image metadata."""
    return {
        'title': 'Test Image',
        'description': 'A test image',
        'tags': ['test', 'sample'],
        'category': 'nature'
    }


@pytest.fixture
def api_gateway_event_base():
    """Base API Gateway event structure."""
    return {
        'headers': {
            'Content-Type': 'application/json',
            'x-user-id': 'test-user-123'
        },
        'requestContext': {
            'requestId': 'test-request-id',
            'stage': 'test'
        }
    }
