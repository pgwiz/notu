# Scaleway Object Storage Configuration Guide

This guide explains how to configure Notu to use Scaleway Object Storage instead of AWS S3.

## Prerequisites

- Scaleway account with Object Storage enabled
- Scaleway bucket created
- Scaleway API credentials (Access Key and Secret Key)

## Step 1: Create Scaleway Bucket

1. Log in to your [Scaleway Console](https://console.scaleway.com/)
2. Navigate to **Object Storage** → **Buckets**
3. Click **Create Bucket**
4. Choose a unique bucket name (e.g., `notu-documents`)
5. Select region (e.g., `fr-par` for Paris)
6. Click **Create Bucket**

## Step 2: Generate API Credentials

1. In Scaleway Console, go to **IAM** → **API Keys**
2. Click **Generate API Key**
3. Give it a name (e.g., `notu-storage`)
4. Select appropriate permissions (Object Storage: Read/Write)
5. Copy the **Access Key** and **Secret Key**

## Step 3: Configure Environment Variables

Create or update your `.env` file with Scaleway configuration:

```env
# Scaleway Object Storage Configuration
S3_BUCKET_NAME=your-scaleway-bucket-name
S3_REGION=fr-par
S3_ENDPOINT_URL=https://s3.fr-par.scw.cloud
AWS_ACCESS_KEY_ID=your-scaleway-access-key
AWS_SECRET_ACCESS_KEY=your-scaleway-secret-key
ACTIVE_STORAGE_BACKEND=s3
```

### Configuration Details

| Variable | Value | Description |
|----------|-------|-------------|
| `S3_BUCKET_NAME` | `your-bucket-name` | Name of your Scaleway bucket |
| `S3_REGION` | `fr-par` | Scaleway region (fr-par, nl-ams, pl-waw) |
| `S3_ENDPOINT_URL` | `https://s3.fr-par.scw.cloud` | Scaleway S3 endpoint URL |
| `AWS_ACCESS_KEY_ID` | `your-access-key` | Scaleway API access key |
| `AWS_SECRET_ACCESS_KEY` | `your-secret-key` | Scaleway API secret key |
| `ACTIVE_STORAGE_BACKEND` | `s3` | Set to 's3' to use Scaleway storage |

## File Organization

Notu automatically organizes files in your Scaleway bucket using the following structure:

```
your-bucket/
└── notu/                    # Main Notu folder
    ├── cs/                  # Computer Science course
    │   ├── notes/
    │   │   ├── 2024/
    │   │   │   ├── 01/
    │   │   │   │   └── uuid_filename.pdf
    │   │   │   └── 02/
    │   │   └── 2023/
    │   ├── cats/
    │   └── others/
    ├── math/                 # Mathematics course
    │   ├── notes/
    │   ├── cats/
    │   └── others/
    └── physics/              # Physics course
        ├── notes/
        ├── cats/
        └── others/
```

This organization ensures:
- All Notu files are contained within the `notu/` folder
- Files are organized by course prefix (cs, math, physics, etc.)
- Files are categorized (notes, cats, others)
- Files are organized by year and month for easy management
- Each file has a unique UUID to prevent conflicts

## Step 4: Test Configuration

Test your Scaleway configuration:

```bash
# Test connection
python -c "
from app import create_app
from services.storage import get_storage_backend

app = create_app()
with app.app_context():
    storage = get_storage_backend('s3')
    print('✅ Scaleway connection successful!')
    print(f'Bucket: {storage.bucket_name}')
    print(f'Endpoint: {storage.endpoint_url}')
"
```

## Step 5: Switch to Scaleway Storage

1. Start your application:
   ```bash
   python run.py
   ```

2. Log in as admin (`admin@notu.local` / `admin123`)

3. Go to **Admin Panel** → **Storage Management**

4. Select **S3 Storage** and click **Switch Backend**

5. Verify the configuration shows:
   - Backend: S3
   - Endpoint: `https://s3.fr-par.scw.cloud`
   - Status: Available

## Scaleway Regions

Scaleway Object Storage is available in the following regions:

| Region | Endpoint URL |
|--------|--------------|
| `fr-par` | `https://s3.fr-par.scw.cloud` |
| `nl-ams` | `https://s3.nl-ams.scw.cloud` |
| `pl-waw` | `https://s3.pl-waw.scw.cloud` |

Choose the region closest to your users for better performance.

## Troubleshooting

### Common Issues

#### 1. Connection Refused
```
Error: Failed to connect to S3: An error occurred (403) when calling the HeadBucket operation: Forbidden
```

**Solution**: Check your API credentials and bucket permissions.

#### 2. Bucket Not Found
```
Error: Failed to connect to S3: An error occurred (404) when calling the HeadBucket operation: Not Found
```

**Solution**: Verify the bucket name and region are correct.

#### 3. Invalid Endpoint
```
Error: Failed to connect to S3: Invalid endpoint URL
```

**Solution**: Ensure the endpoint URL format is correct: `https://s3.{region}.scw.cloud`

### Testing Connection

Test your Scaleway connection:

```bash
# Using AWS CLI (if installed)
aws s3 ls --endpoint-url https://s3.fr-par.scw.cloud s3://your-bucket-name

# Using Python
python -c "
import boto3
s3 = boto3.client('s3', 
    endpoint_url='https://s3.fr-par.scw.cloud',
    aws_access_key_id='your-access-key',
    aws_secret_access_key='your-secret-key')
print(s3.list_buckets())
"
```

### Bucket Permissions

Ensure your Scaleway bucket has the correct permissions:

1. **Public Read**: If you want public documents to be accessible without authentication
2. **Private**: If all documents should require authentication

Configure bucket policies in Scaleway Console → Object Storage → Buckets → Your Bucket → Settings → Bucket Policy.

## Migration from Local Storage

To migrate existing files from local storage to Scaleway:

1. Ensure Scaleway configuration is working
2. Go to **Admin Panel** → **Storage Synchronization**
3. Run a **Dry Run** first to preview changes
4. Run **Full Sync** to migrate files
5. Switch to S3 backend in **Storage Management**

## Cost Optimization

### Scaleway Pricing

Scaleway Object Storage pricing (as of 2024):
- **Storage**: ~€0.01/GB/month
- **Requests**: ~€0.01/10,000 requests
- **Bandwidth**: First 1TB/month free, then ~€0.01/GB

### Optimization Tips

1. **Use appropriate storage class**: Standard for frequently accessed files
2. **Enable compression**: Reduce file sizes before upload
3. **Set up lifecycle policies**: Automatically delete old files
4. **Monitor usage**: Track storage and request usage

## Security Best Practices

1. **Use IAM policies**: Restrict API key permissions
2. **Enable bucket versioning**: Protect against accidental deletion
3. **Use HTTPS**: All connections are encrypted
4. **Rotate credentials**: Regularly update API keys
5. **Monitor access**: Review access logs regularly

## Support

For Scaleway-specific issues:

1. Check [Scaleway Documentation](https://www.scaleway.com/en/docs/)
2. Contact [Scaleway Support](https://www.scaleway.com/en/support/)
3. Review [Scaleway Object Storage FAQ](https://www.scaleway.com/en/docs/object-storage-faq/)

For Notu application issues, please open an issue on the GitHub repository.
