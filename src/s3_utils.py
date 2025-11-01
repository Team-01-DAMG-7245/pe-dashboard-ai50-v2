import boto3
import os
from pathlib import Path
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger(__name__)

class S3Storage:
    def __init__(self, bucket_name=None):
        """Initialize S3 client"""
        self.bucket_name = bucket_name or os.getenv('AWS_BUCKET_NAME', 'quanta-ai50-data')
        self.s3_client = boto3.client('s3')
        
    def upload_file(self, local_file_path, s3_key):
        """
        Upload a file to S3
        
        Args:
            local_file_path: Path to local file
            s3_key: S3 object key (path in bucket)
        """
        try:
            self.s3_client.upload_file(str(local_file_path), self.bucket_name, s3_key)
            logger.info(f"Uploaded {local_file_path} to s3://{self.bucket_name}/{s3_key}")
            return True
        except ClientError as e:
            logger.error(f"Error uploading to S3: {e}")
            return False
    
    def upload_directory(self, local_dir, s3_prefix):
        """
        Upload entire directory to S3
        
        Args:
            local_dir: Path to local directory
            s3_prefix: Prefix for S3 keys
        """
        local_dir = Path(local_dir)
        uploaded_count = 0
        
        for file_path in local_dir.rglob('*'):
            if file_path.is_file():
                # Create S3 key preserving directory structure
                relative_path = file_path.relative_to(local_dir)
                s3_key = f"{s3_prefix}/{relative_path}".replace('\\', '/')
                
                if self.upload_file(file_path, s3_key):
                    uploaded_count += 1
        
        logger.info(f"Uploaded {uploaded_count} files from {local_dir}")
        return uploaded_count
    
    def download_file(self, s3_key, local_file_path):
        """Download a file from S3"""
        try:
            self.s3_client.download_file(self.bucket_name, s3_key, str(local_file_path))
            logger.info(f"Downloaded s3://{self.bucket_name}/{s3_key} to {local_file_path}")
            return True
        except ClientError as e:
            logger.error(f"Error downloading from S3: {e}")
            return False
    
    def list_objects(self, prefix=''):
        """List objects in bucket with given prefix"""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            return [obj['Key'] for obj in response.get('Contents', [])]
        except ClientError as e:
            logger.error(f"Error listing S3 objects: {e}")
            return []
    
    def file_exists(self, s3_key):
        """Check if file exists in S3"""
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError:
            return False