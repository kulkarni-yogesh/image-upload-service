# PowerShell setup script for LocalStack environment
$ErrorActionPreference = "Stop"

Write-Host "Setting up LocalStack environment..." -ForegroundColor Green

$ENDPOINT_URL = "http://localhost:4566"
$REGION = "us-east-1"
$BUCKET_NAME = "image-upload-bucket"
$TABLE_NAME = "image-metadata"

# Set dummy AWS credentials for LocalStack
$env:AWS_ACCESS_KEY_ID = "test"
$env:AWS_SECRET_ACCESS_KEY = "test"
$env:AWS_DEFAULT_REGION = $REGION

# Wait for LocalStack
Write-Host "Waiting for LocalStack..." -ForegroundColor Yellow
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:4566/_localstack/health" -UseBasicParsing -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Host "LocalStack is ready!" -ForegroundColor Green
            $ready = $true
            break
        }
    }
    catch {
        Start-Sleep -Seconds 2
    }
}

if (-not $ready) {
    Write-Host "LocalStack not ready. Check if it's running." -ForegroundColor Red
    exit 1
}

# Create S3 bucket
Write-Host "Creating S3 bucket..." -ForegroundColor Yellow
aws --endpoint-url=$ENDPOINT_URL s3 mb "s3://$BUCKET_NAME" --region $REGION 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "S3 bucket created" -ForegroundColor Green
} else {
    Write-Host "S3 bucket exists or created" -ForegroundColor Green
}

# Create DynamoDB table
Write-Host "Creating DynamoDB table..." -ForegroundColor Yellow

# Check if table already exists
$tableExists = aws dynamodb describe-table --endpoint-url=$ENDPOINT_URL --region $REGION --table-name $TABLE_NAME 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "DynamoDB table already exists" -ForegroundColor Green
} else {
    # Create the table
    $createOutput = aws dynamodb create-table `
        --endpoint-url=$ENDPOINT_URL `
        --region $REGION `
        --table-name $TABLE_NAME `
        --attribute-definitions AttributeName=image_id,AttributeType=S `
        --key-schema AttributeName=image_id,KeyType=HASH `
        --billing-mode PAY_PER_REQUEST 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "DynamoDB table created" -ForegroundColor Green
    } else {
        # Check if error is because table already exists
        if ($createOutput -match "already exists" -or $createOutput -match "ResourceInUseException") {
            Write-Host "DynamoDB table already exists" -ForegroundColor Green
        } else {
            Write-Host "Error creating DynamoDB table:" -ForegroundColor Red
            Write-Host $createOutput -ForegroundColor Red
            exit 1
        }
    }
}

Start-Sleep -Seconds 2
Write-Host "Setup complete!" -ForegroundColor Green
