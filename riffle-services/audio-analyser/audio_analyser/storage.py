from botocore.exceptions import BotoCoreError, ClientError

from audio_analyser.config import Settings
from audio_analyser.errors import AudioObjectNotFoundError, StorageReadFailedError
from audio_analyser.s3_uri import parse_s3_uri


class S3AudioStorage:
    def __init__(self, settings: Settings):
        import boto3

        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
        )

    def read_audio(self, audio_uri: str) -> bytes:
        location = parse_s3_uri(audio_uri)
        try:
            response = self._client.get_object(Bucket=location.bucket, Key=location.key)
            return response["Body"].read()
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code")
            if error_code in {"NoSuchBucket", "NoSuchKey", "404", "NotFound"}:
                raise AudioObjectNotFoundError from exc
            raise StorageReadFailedError from exc
        except BotoCoreError as exc:
            raise StorageReadFailedError from exc
