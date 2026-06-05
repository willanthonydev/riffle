from dataclasses import dataclass
from urllib.parse import unquote


@dataclass(frozen=True)
class S3Location:
    bucket: str
    key: str


def parse_s3_uri(uri: str) -> S3Location:
    if not uri.startswith("s3://"):
        raise ValueError("must use s3:// scheme")

    without_scheme = uri.removeprefix("s3://")
    bucket, _, key = without_scheme.partition("/")
    if not bucket or not key:
        raise ValueError("must include bucket and object key")

    return S3Location(bucket=bucket, key=unquote(key))
