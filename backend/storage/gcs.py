"""GCS helpers for storing and retrieving animation files."""

from google.cloud import storage as gcs

from backend.config import GCS_BUCKET


def get_bucket():
    client = gcs.Client()
    return client.bucket(GCS_BUCKET)


async def upload_file(local_path: str, gcs_path: str) -> str:
    bucket = get_bucket()
    blob = bucket.blob(gcs_path)
    blob.upload_from_filename(local_path)
    return f"gs://{GCS_BUCKET}/{gcs_path}"


async def get_signed_url(gcs_path: str, expiration: int = 3600) -> str:
    import datetime

    bucket = get_bucket()
    blob = bucket.blob(gcs_path)
    url = blob.generate_signed_url(
        expiration=datetime.timedelta(seconds=expiration),
        method="GET",
    )
    return url
