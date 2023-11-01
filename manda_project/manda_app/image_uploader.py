import boto3
import uuid
from django.conf import settings

class S3ImgUploader:
    def __init__(self, file):
        self.file = file

    def upload(self):
        s3_client = boto3.client(
            's3',
            aws_access_key_id     = settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key = settings.AWS_SECRET_ACCESS_KEY
        )
        url = 'img'+'/'+uuid.uuid1().hex
        
        s3_client.upload_fileobj(
            self.file, 
            "webmage-bucket", 
            url, 
            ExtraArgs={
                "ContentType": 'image/jpeg/png/jpg'
            }
        )
        return url
    