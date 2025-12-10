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
import os


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

    if not aws_access_key_id or not aws_secret_access_key:
        print("Warning: AWS credentials not found in environment variables")
        print("Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")

    # Create S3 client
    s3_client = boto3.client(
        's3',
        endpoint_url=endpoint_url,
        region_name=region,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key
    )

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
        with open(model_path, 'rb') as f:
            s3_client.upload_fileobj(f, bucket_name, object_key)

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
