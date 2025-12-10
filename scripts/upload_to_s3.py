#!/usr/bin/env python3
"""
Upload ONNX model to S3/MinIO storage for OpenShift AI deployment.

Usage:
    python scripts/upload_to_s3.py --model models/yolo11n.onnx --bucket train-detection-models
"""

import argparse
import boto3
from pathlib import Path
from botocore.exceptions import ClientError
from botocore.config import Config
import os
import urllib3


def upload_to_s3(model_path: str, bucket_name: str, object_key: str = None,
                 endpoint_url: str = None, region: str = 'us-east-1'):
    """
    Upload model file to S3/MinIO storage.

    Args:
        model_path: Path to model file
        bucket_name: S3 bucket name
        object_key: S3 object key (defaults to model filename)
        endpoint_url: S3 endpoint URL (for MinIO or custom S3)
        region: AWS region
    """
    model_path = Path(model_path)

    if not model_path.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")

    if object_key is None:
        object_key = model_path.name

    # Get credentials from environment variables
    aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    verify_ssl = os.getenv('AWS_S3_VERIFY_SSL', '1') != '0'

    if not aws_access_key_id or not aws_secret_access_key:
        print("Warning: AWS credentials not found in environment variables")
        print("Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")

    # Disable SSL warnings if verification is disabled
    if not verify_ssl:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        print("⚠️  SSL verification disabled (insecure)")

    # Configure S3 client with SSL settings
    s3_config = Config(
        signature_version='s3v4',
        retries={'max_attempts': 3, 'mode': 'standard'}
    )

    # Create S3 client
    s3_client = boto3.client(
        's3',
        endpoint_url=endpoint_url,
        region_name=region,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        config=s3_config,
        verify=verify_ssl  # Control SSL verification
    )

    print(f"S3 Client configured:")
    print(f"  Endpoint: {endpoint_url}")
    print(f"  Region: {region}")
    print(f"  SSL Verification: {'Enabled' if verify_ssl else 'Disabled'}")

    # Check if bucket exists, create if not
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        print(f"Bucket '{bucket_name}' exists")
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            print(f"Bucket '{bucket_name}' not found, creating...")
            s3_client.create_bucket(Bucket=bucket_name)
            print(f"Bucket '{bucket_name}' created")
        else:
            raise

    # Upload file
    print(f"Uploading {model_path} to s3://{bucket_name}/{object_key}")

    try:
        # Get file size for progress display
        file_size = model_path.stat().st_size
        print(f"File size: {file_size / (1024**2):.2f} MB")

        # Use put_object with file read to avoid multipart upload issues with MinIO
        # This is more reliable for MinIO than upload_file which uses multipart
        with open(model_path, 'rb') as f:
            s3_client.put_object(
                Bucket=bucket_name,
                Key=object_key,
                Body=f,
                ContentLength=file_size
            )

        print(f"Upload successful!")
        print(f"S3 URI: s3://{bucket_name}/{object_key}")

        if endpoint_url:
            print(f"Endpoint: {endpoint_url}")

        return f"s3://{bucket_name}/{object_key}"

    except ClientError as e:
        print(f"Upload failed: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Upload model to S3/MinIO storage")
    parser.add_argument(
        '--model',
        type=str,
        required=True,
        help='Path to model file'
    )
    parser.add_argument(
        '--bucket',
        type=str,
        required=True,
        help='S3 bucket name'
    )
    parser.add_argument(
        '--key',
        type=str,
        help='S3 object key (defaults to model filename)'
    )
    parser.add_argument(
        '--endpoint',
        type=str,
        help='S3 endpoint URL (for MinIO or custom S3)'
    )
    parser.add_argument(
        '--region',
        type=str,
        default='us-east-1',
        help='AWS region (default: us-east-1)'
    )

    args = parser.parse_args()

    upload_to_s3(
        args.model,
        args.bucket,
        args.key,
        args.endpoint,
        args.region
    )


if __name__ == '__main__':
    main()
