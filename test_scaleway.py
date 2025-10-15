#!/usr/bin/env python3
"""
Test script for Scaleway Object Storage connectivity
"""
import os
import sys
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def test_scaleway_connection():
    """Test Scaleway Object Storage connection"""
    
    # Get configuration from environment
    bucket_name = os.environ.get('S3_BUCKET_NAME')
    region = os.environ.get('S3_REGION', 'fr-par')
    endpoint_url = os.environ.get('S3_ENDPOINT_URL', 'https://s3.fr-par.scw.cloud')
    access_key = os.environ.get('AWS_ACCESS_KEY_ID')
    secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
    
    print("🔧 Testing Scaleway Object Storage Connection")
    print("=" * 50)
    print(f"Bucket: {bucket_name}")
    print(f"Region: {region}")
    print(f"Endpoint: {endpoint_url}")
    print(f"Access Key: {access_key[:8]}..." if access_key else "Not set")
    print()
    
    if not all([bucket_name, access_key, secret_key]):
        print("❌ Missing required configuration:")
        if not bucket_name:
            print("   - S3_BUCKET_NAME")
        if not access_key:
            print("   - AWS_ACCESS_KEY_ID")
        if not secret_key:
            print("   - AWS_SECRET_ACCESS_KEY")
        return False
    
    try:
        # Create S3 client
        s3_client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
        
        print("🔍 Testing bucket access...")
        
        # Test bucket access
        try:
            s3_client.head_bucket(Bucket=bucket_name)
            print("✅ Bucket access successful!")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                print(f"❌ Bucket '{bucket_name}' not found")
                return False
            elif error_code == '403':
                print("❌ Access denied - check your credentials")
                return False
            else:
                print(f"❌ Bucket access failed: {e}")
                return False
        
        # List objects in bucket
        print("📁 Listing bucket contents...")
        try:
            response = s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=5)
            objects = response.get('Contents', [])
            
            if objects:
                print(f"✅ Found {len(objects)} objects in bucket:")
                for obj in objects:
                    print(f"   - {obj['Key']} ({obj['Size']} bytes)")
            else:
                print("✅ Bucket is empty (no objects found)")
                
        except ClientError as e:
            print(f"❌ Failed to list objects: {e}")
            return False
        
        # Test file upload (small test file)
        print("📤 Testing file upload...")
        test_key = 'test/test-file.txt'  # This will be stored as 'notu/test/test-file.txt'
        test_content = b'This is a test file for Notu Scaleway integration.'
        
        try:
            s3_client.put_object(
                Bucket=bucket_name,
                Key=f'notu/{test_key}',  # Add notu/ prefix manually for testing
                Body=test_content,
                ContentType='text/plain'
            )
            print("✅ File upload successful!")
            print(f"   File stored as: notu/{test_key}")
            
            # Test file download
            print("📥 Testing file download...")
            response = s3_client.get_object(Bucket=bucket_name, Key=f'notu/{test_key}')
            downloaded_content = response['Body'].read()
            
            if downloaded_content == test_content:
                print("✅ File download successful!")
            else:
                print("❌ Downloaded content doesn't match uploaded content")
                return False
            
            # Clean up test file
            print("🧹 Cleaning up test file...")
            s3_client.delete_object(Bucket=bucket_name, Key=f'notu/{test_key}')
            print("✅ Test file deleted!")
            
        except ClientError as e:
            print(f"❌ File operations failed: {e}")
            return False
        
        print("\n🎉 All tests passed! Scaleway Object Storage is ready to use.")
        return True
        
    except NoCredentialsError:
        print("❌ No credentials found")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def main():
    """Main test function"""
    success = test_scaleway_connection()
    
    if success:
        print("\n✅ Scaleway configuration is working correctly!")
        print("\n📝 Next steps:")
        print("   1. Set ACTIVE_STORAGE_BACKEND=s3 in your .env file")
        print("   2. Restart your application")
        print("   3. Switch to S3 backend in the admin panel")
    else:
        print("\n❌ Scaleway configuration has issues!")
        print("\n📝 Troubleshooting:")
        print("   1. Check your Scaleway credentials")
        print("   2. Verify the bucket exists")
        print("   3. Ensure the bucket is in the correct region")
        print("   4. Check your API key permissions")
        print("\n📖 See SCALEWAY_SETUP.md for detailed instructions")

if __name__ == '__main__':
    main()
