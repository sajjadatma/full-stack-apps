# TileVision Storage Service Design

## Goal and constraints

Implement T07 as a backend storage abstraction for image upload, deletion, and
access URL generation. The MVP specification requires persistent local-volume
storage for development and defers object storage; T07 also requires a
configurable production provider. No database changes or public upload API are
part of this task. Image endpoints and persistence of image metadata remain for
later tasks.

## Architecture

- Add a provider-neutral storage service boundary with operations to upload
  validated image bytes, delete an object by key, and generate an access URL.
- Provide a local filesystem backend rooted in a configurable persistent
  directory. It returns app-relative URLs; actual HTTP delivery/private access
  controls belong to a later API task.
- Provide an optional S3-compatible backend selected by configuration. Use
  server-side endpoint/bucket/region/credential settings and generate temporary
  signed access URLs. Credentials are configuration placeholders only, never
  checked-in values.
- The public service owns upload validation and safe key creation, keeping
  provider-specific details behind the backend boundary.

## Validation and keys

- Accept only JPEG, PNG, and WebP after checking the file signature, not merely
  the caller's claimed MIME type. Reject unsupported, mismatched, and empty
  content.
- Enforce a configurable maximum size in bytes before persisting. Do not add
  dimension/orientation processing in T07; those requirements can be applied by
  the upload-domain task.
- Generate UUID-based object keys on the server, grouped by a validated
  namespace/category. Never incorporate a client filename into the storage
  path.

## Configuration and errors

- Default to local storage in development. Select the S3-compatible backend
  explicitly through a provider setting; require its bucket and relevant
  connection settings when selected, failing during initialization for an
  invalid configuration.
- Add environment-variable examples/placeholders only. Mount the local storage
  directory as a persistent volume in the development compose configuration;
  production deployment operators provide their own persistent or object
  storage configuration.
- Raise clear validation errors for rejected uploads and surface storage I/O
  errors without leaking secrets or object contents.

## Testing

- Unit-test local upload/readability through its resulting URL/key, delete,
  UUID-safe keys, MIME signature validation, MIME mismatch, empty input, and
  maximum-size rejection.
- Test provider selection/configuration and the S3-compatible adapter using a
  mocked client so tests need no cloud account or real credentials.
- Run relevant backend lint/type checks and the backend test suite.

## Out of scope

No upload/download routes, authorization policy, image metadata/database
changes, migrations, frontend work, API-client regeneration, image resizing,
or cloud credentials. Local app-relative URLs are not made publicly routable
by this service alone; a later image API must enforce the MVP's owner-only room
photo access and authenticated product-image access.
