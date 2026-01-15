"""
Simple script to test the Lambda endpoints locally.
This simulates API Gateway events and calls the Lambda functions directly.
"""
import json
import base64
import sys
import os

# Set environment variables for LocalStack BEFORE importing anything
os.environ['AWS_ENDPOINT_URL'] = 'http://localhost:4566'
os.environ['AWS_REGION'] = 'us-east-1'
os.environ['S3_BUCKET_NAME'] = 'image-upload-bucket'
os.environ['DYNAMODB_TABLE_NAME'] = 'image-metadata'
os.environ['AWS_ACCESS_KEY_ID'] = 'test'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'test'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Import unified Lambda handler (after env vars are set)
from lambda_functions.api_handler import lambda_handler as api_handler


def create_api_event(method, path, body=None, query_params=None, path_params=None, headers=None):
    """Create a mock API Gateway event."""
    event = {
        'httpMethod': method,
        'path': path,
        'headers': headers or {'Content-Type': 'application/json', 'x-user-id': 'test-user-123'},
        'queryStringParameters': query_params or {},
        'pathParameters': path_params or {},
        'requestContext': {
            'requestId': 'test-request-id',
            'stage': 'test'
        }
    }
    
    if body:
        if isinstance(body, dict):
            event['body'] = json.dumps(body)
        else:
            event['body'] = body
    
    return event


def print_response(response):
    """Pretty print API response."""
    print("\n" + "="*60)
    print(f"Status Code: {response['statusCode']}")
    print(f"Headers: {json.dumps(response.get('headers', {}), indent=2)}")
    body = json.loads(response['body'])
    print(f"Body: {json.dumps(body, indent=2)}")
    print("="*60 + "\n")


def test_upload_image():
    """Test uploading an image."""
    print("Testing: Upload Image")
    print("-" * 60)
    
    # Create a minimal valid PNG image (1x1 pixel, transparent)
    # This is a real base64-encoded PNG
    base64_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    
    event = create_api_event(
        method='POST',
        path='/images',
        body={
            'image': base64_image,
            'metadata': {
                'title': 'Test Image',
                'description': 'A test image for testing',
                'tags': ['test', 'sample'],
                'category': 'test'
            }
        }
    )
    
    try:
        response = api_handler(event, None)
        print_response(response)
        
        if response['statusCode'] == 201:
            body = json.loads(response['body'])
            return body.get('image_id')  # Return image_id for other tests
        else:
            print("Upload failed!")
            return None
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def test_list_images():
    """Test listing images."""
    print("Testing: List Images")
    print("-" * 60)
    
    event = create_api_event(
        method='GET',
        path='/images',
        query_params={
            'user_id': 'test-user-123',
            'page': '1',
            'page_size': '10'
        }
    )
    
    try:
        response = api_handler(event, None)
        print_response(response)
        
        if response['statusCode'] == 200:
            body = json.loads(response['body'])
            print(f"Found {body.get('count', 0)} images")
            return True
        else:
            print("List failed!")
            return False
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_get_image(image_id):
    """Test getting an image."""
    if not image_id:
        print("Skipping get image test (no image_id)")
        return False
    
    print("Testing: Get Image")
    print("-" * 60)
    
    event = create_api_event(
        method='GET',
        path=f'/images/{image_id}',
        query_params={
            'download': 'true',
            'expiration': '3600'
        },
        path_params={'image_id': image_id}
    )
    
    try:
        response = api_handler(event, None)
        print_response(response)
        
        if response['statusCode'] == 200:
            body = json.loads(response['body'])
            print(f"Got presigned URL: {body.get('presigned_url', '')[:50]}...")
            return True
        else:
            print("Get image failed!")
            return False
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_delete_image(image_id):
    """Test deleting an image."""
    if not image_id:
        print("Skipping delete image test (no image_id)")
        return False
    
    print("Testing: Delete Image")
    print("-" * 60)
    
    event = create_api_event(
        method='DELETE',
        path=f'/images/{image_id}',
        path_params={'image_id': image_id}
    )
    
    try:
        response = api_handler(event, None)
        print_response(response)
        
        if response['statusCode'] == 200:
            print("Image deleted successfully!")
            return True
        else:
            print("Delete failed!")
            return False
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("Testing Image Upload Service Endpoints")
    print("="*60)
    print("\nMake sure LocalStack is running and resources are set up!")
    print("Run: .\\setup_localstack.ps1\n")
    
    input("Press Enter to start testing...")
    
    results = {}
    
    # Test 1: Upload
    image_id = test_upload_image()
    results['upload'] = image_id is not None
    
    # Test 2: List
    results['list'] = test_list_images()
    
    # Test 3: Get
    results['get'] = test_get_image(image_id)
    
    # Test 4: Delete
    results['delete'] = test_delete_image(image_id)
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    for test_name, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        print(f"{test_name.upper():15} {status}")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
