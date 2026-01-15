# Image Upload Service

A scalable, serverless image upload and storage service built with AWS Lambda, API Gateway, S3, and DynamoDB. This service supports uploading images with metadata, listing with filters, viewing/downloading, and deletion.

## Features

- ✅ **Image Upload**: Upload images with metadata (title, description, tags, category)
- ✅ **Image Listing**: List images with multiple filters (user_id, category, tags, date range)
- ✅ **Pagination**: Efficient pagination support for large result sets
- ✅ **Image Viewing**: Generate presigned URLs for secure image access
- ✅ **Image Deletion**: Delete images with proper authorization checks
- ✅ **Scalable Architecture**: Serverless design using AWS Lambda
- ✅ **Local Development**: LocalStack support for local testing
- ✅ **Comprehensive Testing**: Unit tests covering all scenarios and edge cases

## Architecture

```
API Gateway → Unified Lambda Function (api_handler.py) → S3 (Images) + DynamoDB (Metadata)
                                    ├─→ handle_upload_image()
                                    ├─→ handle_list_images()
                                    ├─→ handle_get_image()
                                    └─→ handle_delete_image()
```

- **API Gateway**: RESTful API endpoint
- **Unified Lambda Function**: Single serverless function with internal routing for all operations
- **S3**: Object storage for images
- **DynamoDB**: NoSQL database for image metadata

**Why Unified Lambda?** Using a single Lambda function reduces cold starts, simplifies deployment, and lowers costs while maintaining clean code organization with separate handler functions.

## Prerequisites

- Python 3.7 or higher
- Docker and Docker Compose (for LocalStack)
- AWS CLI (for LocalStack setup)
- pip (Python package manager)


## Installation

1. **Clone the repository** (or navigate to the project directory)

2. **Create a virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

## Local Development Setup

### 1. Start LocalStack

LocalStack provides a local AWS cloud stack for development and testing.

```bash
docker-compose up -d
```

This starts LocalStack on `http://localhost:4566`.

### 2. Setup AWS Resources

Run the setup script to create S3 bucket and DynamoDB table:

**Windows (PowerShell)**:
```powershell
.\setup_localstack.ps1
```

**Linux/Mac** (using AWS CLI directly):
```bash
# Create S3 bucket
aws --endpoint-url=http://localhost:4566 s3 mb s3://image-upload-bucket --region us-east-1

# Create DynamoDB table
aws dynamodb create-table \
  --endpoint-url=http://localhost:4566 \
  --region us-east-1 \
  --table-name image-metadata \
  --attribute-definitions AttributeName=image_id,AttributeType=S \
  --key-schema AttributeName=image_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```


### 3. Configure Environment Variables

Set environment variables for LocalStack:

```bash
export AWS_ENDPOINT_URL=http://localhost:4566
export AWS_REGION=us-east-1
export S3_BUCKET_NAME=image-upload-bucket
export DYNAMODB_TABLE_NAME=image-metadata
```

**Windows (PowerShell)**:
```powershell
$env:AWS_ENDPOINT_URL="http://localhost:4566"
$env:AWS_REGION="us-east-1"
$env:S3_BUCKET_NAME="image-upload-bucket"
$env:DYNAMODB_TABLE_NAME="image-metadata"
```

## Running Tests

Run all unit tests:

```bash
pytest tests/ -v
```

Run tests with coverage:

```bash
pytest tests/ --cov=. --cov-report=html
```

Run specific test file:

```bash
pytest tests/test_upload_image.py -v
```

## Project Structure

```
image-upload-service/
├── lambda_functions/          # Lambda function handlers
│   ├── api_handler.py         # Unified Lambda handler (main entry point)
│   ├── upload_image.py        # Upload handler function
│   ├── list_images.py         # List handler function
│   ├── get_image.py           # Get handler function
│   └── delete_image.py        # Delete handler function
├── tests/                     # Unit tests
│   ├── test_upload_image.py
│   ├── test_list_images.py
│   ├── test_get_image.py
│   ├── test_delete_image.py
│   └── test_utils.py
├── config.py                  # Configuration settings
├── utils.py                   # Utility functions
├── requirements.txt           # Python dependencies
├── pytest.ini                 # Pytest configuration
├── docker-compose.yml         # LocalStack configuration
├── setup_localstack.ps1       # Setup script (Windows)
├── test_endpoints.py          # Manual endpoint testing script
└── README.md                  # This file
```

## API Usage

### Quick Start Examples

**Upload an image**:
```python
import requests
import base64

with open('image.jpg', 'rb') as f:
    image_data = base64.b64encode(f.read()).decode('utf-8')

response = requests.post(
    'http://localhost:4566/images',
    json={
        'image': image_data,
        'metadata': {
            'title': 'My Photo',
            'tags': ['nature'],
            'category': 'landscape'
        }
    },
    headers={'x-user-id': 'user-123'}
)
print(response.json())
```

**List images**:
```python
response = requests.get(
    'http://localhost:4566/images',
    params={'user_id': 'user-123', 'page': 1}
)
print(response.json())
```

## Configuration

Configuration can be customized via environment variables:

- `AWS_REGION`: AWS region (default: `us-east-1`)
- `AWS_ENDPOINT_URL`: LocalStack endpoint (default: `None`)
- `S3_BUCKET_NAME`: S3 bucket name (default: `image-upload-bucket`)
- `DYNAMODB_TABLE_NAME`: DynamoDB table name (default: `image-metadata`)
- `MAX_IMAGE_SIZE_MB`: Maximum image size in MB (default: `10`)
- `DEFAULT_PAGE_SIZE`: Default pagination size (default: `20`)
- `MAX_PAGE_SIZE`: Maximum pagination size (default: `100`)

## Edge Cases Handled

The service handles various edge cases:

1. **Upload**:
   - Missing image field
   - Invalid base64 encoding
   - Unsupported image types
   - Images exceeding size limits
   - S3 upload failures
   - DynamoDB save failures (with S3 cleanup)

2. **List**:
   - Invalid date formats
   - Empty result sets
   - Pagination edge cases
   - Multiple filter combinations
   - Page size limits

3. **Get**:
   - Non-existent images
   - Missing S3 keys in metadata
   - URL generation failures
   - Expiration time limits

4. **Delete**:
   - Non-existent images
   - Permission checks
   - Partial deletion scenarios
   - S3 deletion failures

## Deployment to AWS

### 1. Package Lambda Function

Package the unified Lambda function with its dependencies:

```bash
# Create deployment package
zip -r image-upload-service.zip \
  lambda_functions/ \
  utils.py \
  config.py \
  requirements.txt

# Install dependencies to a local directory
pip install -r requirements.txt -t package/

# Add dependencies to zip
cd package
zip -r ../image-upload-service.zip .
cd ..
```

### 2. Create Lambda Function

Use AWS CLI or Terraform/CloudFormation to create the Lambda function:

```bash
aws lambda create-function \
  --function-name image-upload-service \
  --runtime python3.9 \
  --role arn:aws:iam::ACCOUNT:role/lambda-execution-role \
  --handler lambda_functions.api_handler.lambda_handler \
  --zip-file fileb://image-upload-service.zip \
  --timeout 30 \
  --memory-size 256
```

### 3. Configure API Gateway

Set up API Gateway REST API with all routes pointing to the single Lambda function:
- POST `/images` → `image-upload-service` Lambda
- GET `/images` → `image-upload-service` Lambda
- GET `/images/{image_id}` → `image-upload-service` Lambda
- DELETE `/images/{image_id}` → `image-upload-service` Lambda

The unified handler routes requests internally based on HTTP method and path.

### 4. Set Environment Variables

Configure environment variables for the Lambda function:
- `S3_BUCKET_NAME`
- `DYNAMODB_TABLE_NAME`
- `AWS_REGION`

### 5. Set IAM Permissions

Ensure Lambda execution roles have permissions for:
- S3: `PutObject`, `GetObject`, `DeleteObject`
- DynamoDB: `PutItem`, `GetItem`, `Scan`, `DeleteItem`

## Testing Strategy

The test suite covers:

- ✅ **Unit Tests**: Individual function testing with mocks
- ✅ **Edge Cases**: Invalid inputs, error conditions
- ✅ **Integration Scenarios**: End-to-end workflows
- ✅ **Error Handling**: All error paths and responses

Run tests before deployment:
```bash
pytest tests/ -v --cov=. --cov-report=term-missing
```

## Performance Considerations

1. **DynamoDB**: Consider adding Global Secondary Indexes (GSI) for better query performance on filtered attributes
2. **S3**: Use CloudFront for image delivery in production
3. **Lambda**: Configure appropriate memory and timeout settings
4. **Pagination**: Always use pagination for list operations
5. **Caching**: Consider caching presigned URLs for frequently accessed images

## Security Considerations

1. **Authentication**: Implement proper authentication (JWT, API keys) in production
2. **Authorization**: Current implementation checks user ownership for deletions
3. **Input Validation**: All inputs are validated before processing
4. **Presigned URLs**: URLs expire after specified time to limit access
5. **CORS**: Configure CORS headers appropriately for your frontend

## Limitations

- Current implementation uses DynamoDB scan for filtering (consider GSI for production)
- No image resizing/optimization (consider adding Lambda@Edge or separate service)
- No duplicate detection (consider adding content hash)
- Basic authorization (enhance for production use)

## Future Enhancements

- [ ] Image resizing and optimization
- [ ] Thumbnail generation
- [ ] Duplicate detection
- [ ] Advanced search with full-text search
- [ ] Image analytics and usage tracking
- [ ] CDN integration for faster delivery
- [ ] Batch operations support
- [ ] Image metadata extraction (EXIF data)

## Troubleshooting

### LocalStack not starting
- Ensure Docker is running
- Check if port 4566 is available
- Review docker-compose logs: `docker-compose logs`

### Tests failing
- Ensure LocalStack is running
- Check environment variables are set
- Verify dependencies are installed: `pip install -r requirements.txt`

### AWS CLI not working with LocalStack
- Ensure `--endpoint-url=http://localhost:4566` is included
- Check AWS credentials are set (even dummy values work)

## Contributing

1. Follow PEP 8 style guidelines
2. Write tests for new features
3. Update documentation
4. Ensure all tests pass before submitting

## License

(Specify your license here)

## Support

For issues and questions, please open an issue in the repository.
