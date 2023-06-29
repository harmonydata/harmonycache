# Harmony Cache

Make sure the following environment variables are added to Azure:

- `HARMONY_API` Harmony API URL
- `AZURE_STORAGE_CONNECTION_STRING` Connection string for Azure Blob Storage

## Endpoints

### /api/parse

This endpoint is a wrapper for the endpoint `/text/parse` in `Harmony API`. Instruments of files will be cached to
Azure Blob Storage. If all instruments are found in the cache, these will be returned in the response. If not all
instruments are found in the cache, then the missing instruments will be requested from `Harmony API`.