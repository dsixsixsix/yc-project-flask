"""Сервис для работы с Object Storage (MinIO/S3)."""
import os
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError
from flask import current_app


def get_s3_client():
    """Создаёт клиент S3."""
    return boto3.client(
        "s3",
        endpoint_url=os.getenv("S3_ENDPOINT_URL"),
        aws_access_key_id=os.getenv("S3_ACCESS_KEY"),
        aws_secret_access_key=os.getenv("S3_SECRET_KEY"),
        region_name=os.getenv("S3_REGION", "us-east-1"),
    )


def extract_key_from_url(file_url: str, bucket: str) -> str | None:
    """Извлекает object key из сохранённого URL."""
    if not file_url:
        return None
    try:
        endpoint = os.getenv("S3_PUBLIC_ENDPOINT", os.getenv("S3_ENDPOINT_URL", ""))
        if endpoint:
            endpoint = endpoint.rstrip("/")
            if file_url.startswith(endpoint):
                path = file_url[len(endpoint) :].lstrip("/")
                if path.startswith(f"{bucket}/"):
                    key = path[len(f"{bucket}/") :]
                    return key
        if f"/{bucket}/" in file_url:
            key = file_url.split(f"/{bucket}/", 1)[1]
            return key
    except Exception as e:
        current_app.logger.warning("Failed to extract key from URL %s: %s", file_url, e)
    return None


def upload_to_storage(bucket: str, file_storage) -> str:
    """Загружает файл в Object Storage и возвращает публичный URL."""
    client = get_s3_client()
    key = f"uploads/{uuid4()}_{file_storage.filename}"
    try:
        client.upload_fileobj(
            file_storage.stream, bucket, key, ExtraArgs={"ACL": "public-read"}
        )
        location = (
            client.get_bucket_location(Bucket=bucket)["LocationConstraint"]
            or "us-east-1"
        )
        endpoint = os.getenv("S3_PUBLIC_ENDPOINT", os.getenv("S3_ENDPOINT_URL", ""))
        if endpoint:
            return f"{endpoint.rstrip('/')}/{bucket}/{key}"
        return f"https://{bucket}.s3.{location}.amazonaws.com/{key}"
    except ClientError as exc:
        current_app.logger.exception("Failed to upload file to bucket=%s, key=%s", bucket, key)
        raise RuntimeError(f"Failed to upload file: {exc}") from exc


def delete_from_storage(bucket: str, key: str) -> bool:
    """Удаляет файл из Object Storage."""
    try:
        client = get_s3_client()
        client.delete_object(Bucket=bucket, Key=key)
        current_app.logger.info("Deleted object from bucket=%s, key=%s", bucket, key)
        return True
    except ClientError as exc:
        current_app.logger.exception("Failed to delete object from bucket=%s, key=%s", bucket, key)
        return False
