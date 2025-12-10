# S3/MinIO SSL Configuration

This guide explains how to configure SSL verification for S3/MinIO uploads.

## Problem

When using MinIO with HTTPS and self-signed certificates, you may encounter SSL verification errors during model upload:

```
SSLError: SSL verification failed
```

## Solution

Use the `AWS_S3_VERIFY_SSL` environment variable to control SSL verification.

### Option 1: Disable SSL Verification (For Development/Self-Signed Certs)

**⚠️ WARNING: Only use this in development or with trusted self-signed certificates!**

```bash
export AWS_S3_VERIFY_SSL=0
```

Then run the upload:

```bash
python scripts/upload_to_s3.py \
    --model models/yolo11n.onnx \
    --bucket $AWS_S3_BUCKET \
    --endpoint $AWS_S3_ENDPOINT
```

Or in Jupyter notebook, the variable will be read automatically from the environment.

### Option 2: Enable SSL Verification (Production/Valid Certs)

For production use with valid SSL certificates:

```bash
export AWS_S3_VERIFY_SSL=1  # Default
```

Or simply don't set it (defaults to enabled).

## Complete Environment Variables

For MinIO with HTTPS and self-signed certificate:

```bash
# S3/MinIO credentials
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_S3_ENDPOINT="https://minio.your-domain.com"
export AWS_S3_BUCKET="models"
export AWS_DEFAULT_REGION="us-east-1"

# SSL configuration
export AWS_S3_VERIFY_SSL=0  # Disable for self-signed certs
```

## Using in Scripts

### Python Script

```bash
python scripts/upload_to_s3.py \
    --model models/yolo11n.onnx \
    --bucket models \
    --endpoint https://minio.example.com
```

The script will:
- Read `AWS_S3_VERIFY_SSL` from environment
- Default to `1` (enabled) if not set
- Display SSL verification status:
  ```
  S3 Client configured:
    Endpoint: https://minio.example.com
    Region: us-east-1
    SSL Verification: Disabled
  ⚠️  SSL verification disabled (insecure)
  ```

### Jupyter Notebook

The notebook `02_export_and_upload.ipynb` reads the environment variable automatically:

```python
AWS_S3_VERIFY_SSL = os.getenv('AWS_S3_VERIFY_SSL', '1') != '0'
```

Just set the environment variable before starting Jupyter:

```bash
export AWS_S3_VERIFY_SSL=0
jupyter notebook
```

## Security Considerations

### When to Disable SSL Verification

✅ Development environment with self-signed certificates
✅ Internal MinIO instance with corporate CA
✅ Testing on localhost

### When to Keep SSL Verification Enabled

✅ Production deployments
✅ Public S3 endpoints (AWS S3, etc.)
✅ MinIO with valid SSL certificates

### Best Practices

1. **Use valid certificates in production**
   - Get certificates from Let's Encrypt or your CA
   - Configure MinIO with proper SSL certificates

2. **If using self-signed certificates**
   - Add CA certificate to system trust store
   - Or use certificate bundle: `export AWS_CA_BUNDLE=/path/to/ca-bundle.crt`

3. **Never disable SSL verification in production with untrusted endpoints**

## Troubleshooting

### Error: SSL verification failed

```bash
# Check if endpoint is HTTPS
echo $AWS_S3_ENDPOINT
# Should be: https://...

# Disable SSL verification for self-signed certs
export AWS_S3_VERIFY_SSL=0
```

### Error: Connection refused

```bash
# Check if MinIO is running
curl -k https://minio.your-domain.com/minio/health/live

# Verify endpoint URL
echo $AWS_S3_ENDPOINT
```

### Error: Access denied

```bash
# Verify credentials
aws s3 ls --endpoint-url $AWS_S3_ENDPOINT

# Or with MinIO client
mc alias set myminio $AWS_S3_ENDPOINT $AWS_ACCESS_KEY_ID $AWS_SECRET_ACCESS_KEY
mc ls myminio
```

## Alternative: Using CA Bundle

If you have the CA certificate file, use it instead of disabling verification:

```bash
export AWS_CA_BUNDLE=/path/to/ca-bundle.crt
export AWS_S3_VERIFY_SSL=1  # Keep verification enabled
```

This is more secure than disabling verification completely.

## References

- [Boto3 SSL Configuration](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html#using-a-configuration-file)
- [MinIO TLS Configuration](https://min.io/docs/minio/linux/operations/network-encryption.html)
- [AWS S3 Endpoint Configuration](https://docs.aws.amazon.com/general/latest/gr/s3.html)
