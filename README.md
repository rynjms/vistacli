# VistaCLI

A collection of command-line tools for interacting with Vista Social's internal APIs, providing programmatic access to media library management and file uploads.

## Installation

```bash
# Install using uv
uv tool install .

# Or install from the current directory
uv pip install .
```

## Tools Overview

### vsauth - Authentication Management

Extracts authentication cookies from Firefox for `vistasocial.com` and stores them locally for use by other tools.

```bash
# Extract cookies from Firefox and save to ~/.vsauth
vsauth

# Use custom auth file location
vsauth --auth-file /path/to/custom/auth/file
```

**Features:**
- Automatically extracts cookies from Firefox browser
- Stores authentication data in `~/.vsauth` (JSON format)
- Supports custom auth file locations
- Browser-like headers for API requests

### vsdir - Folder Management

Create and delete folders in the Vista Social media library. 

#### List Folders
```bash
# List all folders (titles only, lexically sorted)
vsdir list

# List folders with full JSON output
vsdir list --json

# List folders in CSV format (title,id,created_at)
vsdir list --csv

# List subfolders within a parent folder
vsdir list --media-path <parent_folder_id>

# Use custom auth file
vsdir list --auth-file /path/to/custom/auth.json

# Debug mode
vsdir list --log-level DEBUG
```

#### Create Folders
```bash
# Create a basic folder
vsdir add "My Folder"

# Create folder with description
vsdir add "My Folder" --description "Folder description"

# Create folder with labels
vsdir add "My Folder" --labels "Label1" --labels "Label2"

# Create folder with entity associations
vsdir add "My Folder" --entity-gids "entity-id-1" --entity-gids "entity-id-2"

# Create subfolder within existing folder
vsdir add "Subfolder" --media-path <parent_folder_id>

# Use custom auth file
vsdir add "My Folder" --auth-file /path/to/custom/auth.json

# Debug mode
vsdir add "My Folder" --log-level DEBUG
```

#### Delete Folders
```bash
# Delete folder by ID
vsdir delete <folder_id>

# Use custom auth file
vsdir delete <folder_id> --auth-file /path/to/custom/auth.json

# Debug mode
vsdir delete <folder_id> --log-level DEBUG
```

### vsput - File Upload

Uploads files to the Vista Social media library.

```bash
# Upload file to root level
vsput /path/to/image.png

# Upload file to specific subfolder
vsput /path/to/image.png --subfolder <folder_id>

# Use custom auth file
vsput /path/to/image.png --auth-file /path/to/custom/auth.json

# Debug mode to see detailed upload process
vsput /path/to/image.png --subfolder <folder_id> --log-level DEBUG
```

**Features:**
- **Supported file types**: Images only (PNG, JPEG, GIF, WebP, etc.)
- **Folder placement**: Upload to root (default) or specific subfolder


## Logging

All tools support configurable logging levels:

```bash
# Available log levels: DEBUG, INFO, WARNING, ERROR
--log-level DEBUG    # Most verbose - shows all HTTP requests/responses
--log-level INFO     # General information
--log-level WARNING  # Default - only warnings and errors
--log-level ERROR    # Only errors
```

## Authentication

The tools use Firefox browser cookies for authentication:

1. **Login to Vista Social** in Firefox browser
2. **Run `vsauth`** to extract and store cookies
3. **Use other tools** - they will automatically use the stored authentication

**Note**: Cookies expire periodically. If you get authentication errors, re-run `vsauth` to refresh the stored cookies.

## File Type Support

### Currently Supported
- **Images**: PNG, JPEG, GIF, WebP, BMP, TIFF, and other common image formats
- **MIME types**: All standard image MIME types (image/png, image/jpeg, etc.)

### Not Yet Tested
- **Video files**: Video uploads have not been tested and may not work correctly
- **Audio files**: Audio uploads are not supported
- **Documents**: Document uploads are not supported

## Error Handling

Tools provide clear error messages and appropriate exit codes:

- **0**: Success
- **1**: General error (file not found, API error, etc.)
- **Validation errors**: Clear messages for unsupported file types

## Examples

### Complete Workflow

```bash
# 1. Authenticate
vsauth

# 2. Create a folder
vsdir add "My Photos" --description "Personal photo collection"

# 3. List folders to get the ID
vsdir list --json

# 4. Upload files to the folder
vsput photo1.jpg --subfolder <folder_id>
vsput photo2.png --subfolder <folder_id>

# 5. List subfolder contents
vsdir list --media-path <folder_id>
```

### Batch Operations

```bash
# Upload multiple files to a folder
for file in *.jpg; do
    vsput "$file" --subfolder <folder_id>
done

# Create multiple folders
vsdir add "Folder 1" --description "First folder"
vsdir add "Folder 2" --description "Second folder"
vsdir add "Folder 3" --description "Third folder"
```

## Technical Details

### Dependencies
- **httpx**: Modern HTTP client with async support
- **browser-cookie3**: Firefox cookie extraction
- **click**: Command-line interface framework
- **pathlib2**: Path manipulation (Python < 3.4 compatibility)


## Limitations

1. **Video uploads untested**: Video file uploads have not been tested and may not work
2. **Firefox only**: Cookie extraction currently only supports Firefox
3. **Single user**: Tools are designed for single-user authentication
4. **Rate limiting**: No built-in rate limiting for API requests

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details. 