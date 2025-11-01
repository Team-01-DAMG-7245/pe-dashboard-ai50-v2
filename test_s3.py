from src.s3_utils import S3Storage
from dotenv import load_dotenv

load_dotenv()

s3 = S3Storage()
print('S3 connection successful!')
print('Bucket:', s3.bucket_name)

# Test listing (should be empty or show existing objects)
objects = s3.list_objects()
print(f'Objects in bucket: {len(objects)}')
