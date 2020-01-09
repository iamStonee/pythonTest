# -*- coding: utf-8 -*-
"""Classes for S3 Buckets."""

from pathlib import Path
import mimetypes
from botocore.exceptions import ClientError
import util


class BucketManager:
    """Manage an S3 Bucket."""

    def __init__(self, session):
        """Create a BucketManager Object."""
        self.session = session
        self.s3 = self.session.resource('s3')

    def get_region_name(self, bucket):
        """Get the bucket's region name."""
        bucket_location = self.s3.meta.client.get_bucket_location(Bucket=bucket.name)
        return bucket_location["LocationConstraint"] or 'us-east-1'

    def get_bucket_url(self, bucket):
        """Get the website URL for this bucket."""
        return "http://{}.{}".format(
            bucket.name, util.get_endpoint(self.get_region_name(bucket)).host)

    def all_buckets(self):
        """Get an iterator for all buckets."""
        return self.s3.buckets.all()

    def all_objects(self, bucket_name):
        """Get an iterator for all objects in bucket."""
        return self.s3.Bucket(bucket_name).objects.all()

    def init_bucket(self, bucket_name):
        """Create new bucket, or return existing one by name."""
        s3_bucket = None

        try:
            s3_bucket = self.s3.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={
                    'LocationConstraint': self.session.region_name})
        except ClientError as error:
            print(error)
            if error.response['Error']['Code'] == 'BucketAlreadyOwnedByYou':
                s3_bucket = self.s3.Bucket(bucket_name)
            else:
                raise error

        return s3_bucket

    def set_policy(self, bucket_name):
        """Set bucket policy to be readable by everyone."""
        policy = """
        {
          "Version":"2012-10-17",
          "Statement":[{
          "Sid":"PublicReadGetObject",
          "Effect":"Allow",
          "Principal": "*",
          "Action":["s3:GetObject"],
          "Resource":["arn:aws:s3:::%s/*"]
          }]
        }
        """ % bucket_name
        policy = policy.strip()
        pol = self.s3.Bucket(bucket_name).Policy()
        pol.put(Policy=policy)

    def configure_website(self, bucket_name):
        """Configure S3 website hosting for bucket."""
        self.s3.Bucket(bucket_name).Website().put(WebsiteConfiguration={
            'ErrorDocument': {
                'Key': 'error.html'
                },
            'IndexDocument': {
                'Suffix': 'index.html'
                }
        })
        url = "https://%s.s3-website-ap-southeast-2.amazonaws.com" \
            % bucket_name
#        print(url)

    @staticmethod
    def upload_file(bucket, path, key):
        """Upload path to s3_bucket at key."""
        # set default value of content_type
        content_type = mimetypes.guess_type(key)[0] or 'text/plain'
        return bucket.upload_file(
            path,
            key,
            ExtraArgs={'ContentType': content_type}
        )

    def sync(self, pathname, bucket_name):
        """Sync contents of PATHNAME to BUCKET."""
        #    print(Path(pathname).expanduser().resolve())
        bucket = self.s3.Bucket(bucket_name)
        root = Path(pathname).expanduser().resolve()
        #    print(root)

        def handle_directory(target):
            for p in target.iterdir():
                if p.is_dir(): handle_directory(p)
                if p.is_file():
                    self.upload_file(
                        bucket, str(p), str(p.relative_to(root))
                        )
                # print("Path: {}\n Key: {}".format(p, p.relative_to(root)))

        handle_directory(root)
