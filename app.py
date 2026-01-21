"""
Flask application to test Lambda functions locally with Postman.
Converts HTTP requests to API Gateway events and invokes Lambda handlers.
"""
import json
import os
from flask import Flask, request, jsonify
from flask_cors import CORS

# Set environment variables for LocalStack BEFORE importing Lambda handlers
os.environ['AWS_ENDPOINT_URL'] = 'http://localhost:4566'
os.environ['AWS_REGION'] = 'us-east-1'
os.environ['S3_BUCKET_NAME'] = 'image-upload-bucket'
os.environ['DYNAMODB_TABLE_NAME'] = 'image-metadata'
os.environ['AWS_ACCESS_KEY_ID'] = 'test'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'test'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

# Import Lambda handler after env vars are set
from lambda_functions.api_handler import lambda_handler

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes


def create_api_gateway_event(http_method, path, body=None, query_params=None, path_params=None, headers=None):
    """Convert Flask request to API Gateway event format."""
    event = {
        'httpMethod': http_method,
        'path': path,
        'pathParameters': path_params or {},
        'queryStringParameters': query_params or {},
        'headers': headers or {},
        'body': body or '',
        'requestContext': {
            'requestId': 'test-request-id',
            'stage': 'test'
        }
    }
    return event


@app.route('/images', methods=['POST'])
def upload_image():
    """Upload image endpoint."""
    try:
        # Get request body
        if request.is_json:
            body = json.dumps(request.json)
        else:
            body = request.data.decode('utf-8') if request.data else '{}'
        
        # Get headers
        headers = dict(request.headers)
        
        # Create API Gateway event
        event = create_api_gateway_event(
            http_method='POST',
            path='/images',
            body=body,
            headers=headers
        )
        
        # Invoke Lambda handler
        response = lambda_handler(event, None)
        
        # Convert Lambda response to Flask response
        status_code = response['statusCode']
        response_body = json.loads(response['body'])
        
        return jsonify(response_body), status_code
    
    except Exception as e:
        return jsonify({'error': str(e), 'error_code': 'INTERNAL_ERROR'}), 500


@app.route('/images', methods=['GET'])
def list_images():
    """List images endpoint."""
    try:
        # Get query parameters
        query_params = dict(request.args)
        
        # Get headers
        headers = dict(request.headers)
        
        # Create API Gateway event
        event = create_api_gateway_event(
            http_method='GET',
            path='/images',
            query_params=query_params,
            headers=headers
        )
        
        # Invoke Lambda handler
        response = lambda_handler(event, None)
        
        # Convert Lambda response to Flask response
        status_code = response['statusCode']
        response_body = json.loads(response['body'])
        
        return jsonify(response_body), status_code
    
    except Exception as e:
        return jsonify({'error': str(e), 'error_code': 'INTERNAL_ERROR'}), 500


@app.route('/images/<image_id>', methods=['GET'])
def get_image(image_id):
    """Get image endpoint."""
    try:
        # Get query parameters
        query_params = dict(request.args)
        
        # Get headers
        headers = dict(request.headers)
        
        # Create API Gateway event
        event = create_api_gateway_event(
            http_method='GET',
            path=f'/images/{image_id}',
            query_params=query_params,
            path_params={'image_id': image_id},
            headers=headers
        )
        
        # Invoke Lambda handler
        response = lambda_handler(event, None)
        
        # Convert Lambda response to Flask response
        status_code = response['statusCode']
        response_body = json.loads(response['body'])
        
        return jsonify(response_body), status_code
    
    except Exception as e:
        return jsonify({'error': str(e), 'error_code': 'INTERNAL_ERROR'}), 500


@app.route('/images/<image_id>', methods=['DELETE'])
def delete_image(image_id):
    """Delete image endpoint."""
    try:
        # Get headers
        headers = dict(request.headers)
        
        # Create API Gateway event
        event = create_api_gateway_event(
            http_method='DELETE',
            path=f'/images/{image_id}',
            path_params={'image_id': image_id},
            headers=headers
        )
        
        # Invoke Lambda handler
        response = lambda_handler(event, None)
        
        # Convert Lambda response to Flask response
        status_code = response['statusCode']
        response_body = json.loads(response['body'])
        
        return jsonify(response_body), status_code
    
    except Exception as e:
        return jsonify({'error': str(e), 'error_code': 'INTERNAL_ERROR'}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'healthy', 'service': 'image-upload-service'}), 200


if __name__ == '__main__':
    print("=" * 60)
    print("Image Upload Service - Local Testing Server")
    print("=" * 60)
    print("\nEndpoints:")
    print("  POST   http://localhost:5000/images")
    print("  GET    http://localhost:5000/images")
    print("  GET    http://localhost:5000/images/<image_id>")
    print("  DELETE http://localhost:5000/images/<image_id>")
    print("  GET    http://localhost:5000/health")
    print("\nMake sure LocalStack is running and resources are set up!")
    print("Run: .\\setup_localstack.ps1")
    print("=" * 60 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
