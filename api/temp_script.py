import os
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))
sys.path.append(str(Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient
from moto import mock_aws
import boto3

os.environ['APP_ENV'] = 'development'
os.environ['S3_ENABLED'] = 'true'
os.environ['S3_BUCKET'] = 'gridboss-test'
os.environ['S3_REGION'] = 'us-east-1'
os.environ['S3_ENDPOINT'] = 'https://s3.amazonaws.com'
os.environ['S3_ACCESS_KEY'] = 'test-access'
os.environ['S3_SECRET_KEY'] = 'test-secret'
os.environ['S3_PRESIGN_TTL'] = '600'

from gridboss_config import get_settings
from app.services import storage

@mock_aws
def main():
    get_settings.cache_clear()
    storage._cached_client.cache_clear()  # type: ignore[attr-defined]
    boto3.client('s3', region_name='us-east-1', aws_access_key_id='test-access', aws_secret_access_key='test-secret').create_bucket(Bucket='gridboss-test')
    from app.main import app
    client = TestClient(app)
    resp = client.post('/uploads/sign', json={'kind': 'avatar', 'filename': 'driver.png', 'content_type': 'image/png'})
    print(resp.status_code)
    print(resp.json())

if __name__ == '__main__':
    main()
