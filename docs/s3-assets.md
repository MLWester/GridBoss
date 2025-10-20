# S3 Asset Storage

This note captures the rollout steps for PBI-071 and how GridBoss services interact with object storage.

## Bucket & IAM setup
- Create a production bucket such as `gridboss-prod-assets` in the target AWS region. Enable encryption at rest (SSE-S3 or SSE-KMS) and block all public ACLs/policies.
- Apply a restrictive bucket policy that denies any requests not using TLS and not signed by the GridBoss IAM principal.
- Provision an IAM user or role dedicated to the application with the following permissions only:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowScopedObjectAccess",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::gridboss-prod-assets/*"
    },
    {
      "Sid": "AllowListing",
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket"
      ],
      "Resource": "arn:aws:s3:::gridboss-prod-assets"
    }
  ]
}
```

- Store the access key ID and secret in the deployment platform (Render, Fly.io, etc.). Never commit credentials to the repository.
- For non-AWS providers (MinIO, Cloudflare R2, Backblaze B2) expose an S3-compatible endpoint and pass it through `S3_ENDPOINT`.

## Runtime configuration
Add or update the following keys in `.env`/secrets management:

| Key | Description |
| --- | --- |
| `S3_ENABLED` | Toggle for environments that should support uploads. |
| `S3_REGION` | Region of the target bucket (e.g. `us-east-1`). |
| `S3_BUCKET` | Bucket name (no `s3://` prefix). |
| `S3_ENDPOINT` | Optional custom endpoint (leave empty for AWS). |
| `S3_ACCESS_KEY` / `S3_SECRET_KEY` | Credentials with the IAM policy above. |
| `S3_PRESIGN_TTL` | Optional override (seconds) for signed URL expiry (defaults to 3600). |

The shared `gridboss_config.Settings` class enforces that all fields above are present whenever `S3_ENABLED=true`.

## API capabilities
- `POST /uploads/sign`: issues a short-lived pre-signed POST so the browser can stream bytes directly into S3. Profiles currently supported:
  - `avatar`: JPEG, PNG, WebP, ≤ 2 MiB.
  - `export`: CSV, JSON, PDF, ZIP, ≤ 25 MiB.
- `POST /uploads/complete`: called after the browser upload finishes. The API verifies the object exists, checks MIME + size limits, strips EXIF metadata for avatars, and returns a signed download URL.
- `POST /uploads/download`: returns a signed GET URL for an object (avatars or exports) as long as the key matches the configured prefix.

All responses contain `expiresIn` so the client can schedule refreshes. No public ACLs are required—the URLs are signed per-request.

## Client workflow
1. Call `POST /uploads/sign` with `{kind, filename, content_type}` and obtain the POST target + form fields.
2. Submit the file directly to S3 using the returned `url` and `fields`. The frontend should use `FormData` and `fetch`/`XMLHttpRequest`.
3. Call `POST /uploads/complete` with the `objectKey` to sanitise, validate, and retrieve the download URL.
4. Persist the returned `objectKey` (or URL) against the relevant domain record.

If step 3 returns an error, the client should surface the message and allow the user to retry with a different file.

## Export jobs
Background workers can write generated CSV/PDF exports to the same bucket. Store files under the `exports/` prefix then surface them to the UI either by:
- returning `objectKey` to the API for `POST /uploads/download`, or
- generating a download URL inside the job via `app.services.storage.generate_presigned_get_url`.

## Optional CloudFront
Fronting the bucket with CloudFront (recommended for production) enables HTTPS terminators close to the user and cache control:
- Set the origin to the S3 bucket (private origin access).
- Configure the distribution hostname (e.g. `cdn.grid-boss.com`) and add it to DNS.
- Forward only the headers required for signed URLs (default behaviour works because requests use query params).
- Configure reasonable TTLs (avatars can be cached for 1 day, exports for a few hours) and allow cache invalidation for urgent updates.

When using CloudFront, you can expose the distribution URL to the frontend so avatars render from the CDN rather than signed GETs.

## Local development
- For unit/integration tests we rely on `moto` to emulate AWS S3—no external services required.
- To exercise the stack manually, run MinIO locally and set `S3_ENDPOINT=http://localhost:9000` together with a dev access/secret key. Remember to add the endpoint to `.env` but keep it empty in `.env.example` unless required.
- The Docker Compose profile can mount additional services later if we adopt MinIO as part of the dev stack.
