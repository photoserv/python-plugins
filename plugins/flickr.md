# Flickr Plugin

Integration plugin for publishing photos from Photoserv to Flickr using the Flickr API.

## Overview

The Flickr plugin enables automatic photo publishing and management on Flickr. It handles photo uploads, metadata synchronization, tag management, and automatic group assignment based on configurable rules.

## Features

- **Photo Publishing**: Automatically upload photos to Flickr when published in Photoserv
- **Photo Unpublishing**: Remove photos from Flickr when unpublished in Photoserv
- **Metadata Sync**: Sync photo titles, descriptions, and tags
- **Tag Management**: Automatically process and format tags for Flickr compatibility
- **Smart Group Management**: Automatically add photos to Flickr groups using flexible OR-based matching with glob pattern support (`*` wildcards)
- **Pattern Matching**: Match tags and albums with patterns like `wildlife*`, `vacation-*`, or `*` for all
- **Photo Limits**: Configure maximum number of published photos
- **Per-Photo Customization**: Override descriptions and tags on a per-photo basis

## Configuration

### Plugin Configuration

The plugin requires the following configuration (provided as JSON in the Photoserv admin interface):

```json
{
  "group_sets": [
    {
      "name": "mines",
      "groups": [
        "1505902@N25"
      ],
      "autoAlbums": [
        "test-album"
      ]
    }
  ],
  "upload_size": "social_flickr",
  "flickr_api_key": "${FLICKR_API_KEY}",
  "flickr_user_id": "92384792@N08",
  "flickr_api_secret": "${FLICKR_API_KEY_SECRET}",
  "flickr_oauth_token": "${FLICKR_OAUTH_TOKEN}",
  "flickr_photo_limit": 1000,
  "photo_description_footer": "Posted by Photoserv",
  "flickr_oauth_token_secret": "${FLICKR_OAUTH_TOKEN_SECRET}",
  "flickr_photo_limit_initial_count": 58
}
```

#### Configuration Parameters

- **flickr_api_key** (required): Your Flickr API Key (Consumer Key)
- **flickr_api_secret** (required): Your Flickr API Secret (Consumer Secret)
- **flickr_oauth_token** (required): OAuth Access Token obtained through OAuth authorization flow
- **flickr_oauth_token_secret** (required): OAuth Token Secret obtained through OAuth authorization flow
- **flickr_user_id** (required): Your Flickr user ID in N format (e.g., `12345678@N01`)
- **flickr_photo_limit** (optional, default: 1000): Maximum number of photos to publish to Flickr
- **flickr_photo_limit_initial_count** (optional, default: 0): Number of photos already existing in your Flickr account before installing this plugin. This helps accurately track the total photo count.
- **upload_size** (optional, default: 'original'): Size of the photo to fetch and upload to Flickr (e.g., 'original', 'large', 'medium', 'small')
- **photo_description_footer** (optional): Text to append to all photo descriptions
- **group_sets** (optional): Array of group set configurations

#### Group Sets

Group sets define rules for automatically adding photos to Flickr groups using **OR-based matching** with **glob pattern support**:

- **name**: Identifier for the group set
- **groups**: Array of Flickr group IDs where photos should be added
- **auto_tags**: Glob patterns for tag matching. A photo is matched if **ANY** of its tags matches **ANY** pattern (OR-based). Supports wildcards like `*` (e.g., `wildlife*` matches `wildlife`, `wildlife-bird`, etc.)
- **auto_albums**: Glob patterns for album matching. A photo is matched if it belongs to **ANY** album whose UUID or slug matches **ANY** pattern (OR-based). Supports wildcards like `*` (e.g., `vacation-*` matches `vacation-2024`, `vacation-2025`, etc.)

**Pattern Examples:**
- `*` - Matches everything (all photos)
- `wildlife` - Exact match only
- `wildlife*` - Matches tags/albums starting with "wildlife"
- `*landscape*` - Matches tags/albums containing "landscape"
- `photo-202?` - Matches tags/albums like "photo-2024", "photo-2025" (? matches single character)

### Entity Parameters

Per-photo parameters can be configured as JSON for each photo:

```json
{
  "override_description": "Custom description for this specific photo",
  "additional_tags": ["exclusive", "featured"],
  "additional_group_sets": ["Landscape Photography"],
  "force": true,
  "safety_level": 1
}
```

#### Entity Parameter Options

- **override_description**: Replace the default photo description with custom text
- **additional_tags**: Add extra tags to this specific photo
- **additional_group_sets**: Add this photo to additional group sets by name
- **force** (boolean, default: false): Force the operation to run without checking existing Flickr state. Useful for re-uploading photos.
- **safety_level** (integer, optional): Set content safety level - 1 for Safe, 2 for Moderate, or 3 for Restricted. If omitted or invalid, uses user's default.

## Getting Flickr API Credentials

### Step 1: Get API Key and Secret

1. Go to [Flickr App Garden](https://www.flickr.com/services/apps/create/)
2. Create a new app and request an API key
3. Note your API Key (Consumer Key) and Secret (Consumer Secret)

### Step 2: Get OAuth Access Token

Flickr requires OAuth 1.0a authentication with an access token. You need to obtain the `oauth_token` and `oauth_token_secret` through the OAuth authorization flow.

**Important**: These tokens do NOT expire. Once obtained, they remain valid indefinitely unless you revoke access from your Flickr account.

#### Using Python Script (Recommended)

Use this interactive Python script to obtain your OAuth tokens:

```python
#!/usr/bin/env python3
"""
Flickr OAuth Token Generator

This script helps you obtain OAuth access tokens for the Flickr plugin.
Run this script once to get your oauth_token and oauth_token_secret.

Requirements: pip install requests requests-oauthlib
"""

import requests
from requests_oauthlib import OAuth1
import webbrowser

def main():
    print("=" * 60)
    print("Flickr OAuth Token Generator")
    print("=" * 60)
    print()
    print("This script will help you obtain OAuth access tokens for Flickr.")
    print("These tokens do NOT expire and can be used indefinitely.")
    print()
    
    # Get API credentials
    api_key = input("Enter your Flickr API Key: ").strip()
    api_secret = input("Enter your Flickr API Secret: ").strip()
    
    if not api_key or not api_secret:
        print("\nError: API Key and Secret are required!")
        return
    
    print("\n" + "-" * 60)
    print("Step 1: Getting Request Token...")
    print("-" * 60)
    
    # Step 1: Get request token
    request_token_url = "https://www.flickr.com/services/oauth/request_token"
    oauth = OAuth1(api_key, client_secret=api_secret, callback_uri='oob')
    
    try:
        response = requests.post(request_token_url, auth=oauth)
        response.raise_for_status()
    except Exception as e:
        print(f"\nError: Failed to get request token: {e}")
        print("Please verify your API Key and Secret are correct.")
        return
    
    # Parse response
    request_credentials = dict(param.split('=') for param in response.text.split('&'))
    request_token = request_credentials.get('oauth_token')
    request_token_secret = request_credentials.get('oauth_token_secret')
    
    if not request_token or not request_token_secret:
        print("\nError: Invalid response from Flickr API")
        return
    
    print(f"Request token obtained: {request_token[:20]}...")
    
    # Step 2: User authorization
    print("\n" + "-" * 60)
    print("Step 2: User Authorization")
    print("-" * 60)
    print("\nYou need to authorize this application to access your Flickr account.")
    print("A browser window will open. Please:")
    print("1. Sign in to Flickr if needed")
    print("2. Click 'OK, I'LL AUTHORIZE IT' to grant access")
    print("3. Copy the 9-digit verification code shown (format: XXX-XXX-XXX)")
    print()
    
    auth_url = f"https://www.flickr.com/services/oauth/authorize?oauth_token={request_token}&perms=delete"
    
    input("Press ENTER to open the authorization page in your browser...")
    
    try:
        webbrowser.open(auth_url)
    except:
        print("\nCouldn't open browser automatically. Please visit this URL:")
        print(auth_url)
    
    print()
    verifier = input("Enter the verification code from Flickr: ").strip()
    
    if not verifier:
        print("\nError: Verification code is required!")
        return
    
    # Step 3: Exchange for access token
    print("\n" + "-" * 60)
    print("Step 3: Getting Access Token...")
    print("-" * 60)
    
    access_token_url = "https://www.flickr.com/services/oauth/access_token"
    oauth = OAuth1(
        api_key,
        client_secret=api_secret,
        resource_owner_key=request_token,
        resource_owner_secret=request_token_secret,
        verifier=verifier
    )
    
    try:
        response = requests.post(access_token_url, auth=oauth)
        response.raise_for_status()
    except Exception as e:
        print(f"\nError: Failed to get access token: {e}")
        print("Please verify the verification code is correct.")
        return
    
    # Parse response
    access_credentials = dict(param.split('=') for param in response.text.split('&'))
    oauth_token = access_credentials.get('oauth_token')
    oauth_token_secret = access_credentials.get('oauth_token_secret')
    user_nsid = access_credentials.get('user_nsid', 'unknown')
    username = access_credentials.get('username', 'unknown')
    fullname = access_credentials.get('fullname', 'unknown')
    
    if not oauth_token or not oauth_token_secret:
        print("\nError: Invalid response from Flickr API")
        return
    
    # Display results
    print("\n" + "=" * 60)
    print("SUCCESS! Your OAuth Tokens:")
    print("=" * 60)
    print()
    print(f"User: {fullname} (@{username})")
    print(f"User ID (NSID): {user_nsid}")
    print()
    print("Add these to your Flickr plugin configuration:")
    print()
    print("{")
    print(f'  "flickr_api_key": "{api_key}",')
    print(f'  "flickr_api_secret": "{api_secret}",')
    print(f'  "flickr_oauth_token": "{oauth_token}",')
    print(f'  "flickr_oauth_token_secret": "{oauth_token_secret}",')
    print(f'  "flickr_user_id": "{user_nsid}"')
    print("}")
    print()
    print("=" * 60)
    print("IMPORTANT: These tokens do NOT expire!")
    print("Store them securely and use them in your plugin configuration.")
    print("=" * 60)
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
```

**To use this script:**

1. Install required dependencies:
   ```bash
   pip install requests requests-oauthlib
   ```

2. Run the script:
   ```bash
   python3 flickr_oauth.py
   ```

3. Follow the prompts to authorize and obtain your tokens

#### Alternative Methods

If you prefer not to use the Python script above:

**Option A: Use Postman or Insomnia**
1. Set up OAuth 1.0a authentication in the tool
2. Configure:
   - Consumer Key: Your API Key
   - Consumer Secret: Your API Secret
   - Request Token URL: `https://www.flickr.com/services/oauth/request_token`
   - Authorization URL: `https://www.flickr.com/services/oauth/authorize?perms=delete`
   - Access Token URL: `https://www.flickr.com/services/oauth/access_token`
3. Complete the OAuth flow to get your access token and token secret

**Option B: Use Flickr's API Explorer**
1. Go to [Flickr API Explorer](https://www.flickr.com/services/api/explore/flickr.test.login)
2. Sign in with your Flickr account
3. Call the test.login method
4. Look at the signed request to extract your oauth_token and oauth_token_secret

### Step 3: Get Your User ID

Your User ID (NSID) will be shown in the script output above. Alternatively:

- Use [idGettr](https://www.flickr.com/services/api/explore/flickr.people.getInfo)
- Check your profile URL (e.g., `flickr.com/photos/12345678@N01/`)

**Important**: You must complete the OAuth authorization flow outside of this plugin to obtain your `oauth_token` and `oauth_token_secret`. These tokens grant the plugin permission to upload and manage photos on your behalf.

## Usage

### Publishing Photos

When a photo is published in Photoserv:

1. The plugin checks if the photo is already uploaded to Flickr
2. Verifies the published photo limit hasn't been reached
3. Builds the photo description (with optional footer)
4. Processes and formats tags (removes spaces as required by Flickr)
5. Uploads the photo to Flickr
6. Adds the photo to applicable groups based on group set rules
7. Tracks the upload in persistent storage

### Unpublishing Photos

When a photo is unpublished in Photoserv:

1. The plugin retrieves the Flickr photo ID from storage
2. Deletes the photo from Flickr via the API
3. Removes the tracking data from persistent storage
4. Decrements the published photo count

### Tag Processing

The plugin automatically:
- Removes spaces from tags (Flickr requirement)
- Combines tags from photo data and entity parameters
- Filters out empty tags

### Group Assignment

Photos are automatically added to groups when:
- The photo has ALL tags specified in a group set's `auto_tags`
- The photo belongs to an album specified in a group set's `auto_albums` (by UUID or slug)
- The photo's entity parameters include the group set name in `additional_group_sets`

## Persistent Storage

The plugin tracks state using Photoserv's persistent configuration:

- `published_photo_count`: Total number of photos currently published to Flickr
- `{photo_uuid}_uploaded`: Flickr photo ID for each uploaded photo

## Error Handling

The plugin includes comprehensive error handling:

- Validation of required configuration parameters
- API error handling with detailed logging
- Network error handling with timeouts
- Graceful degradation for group assignment failures
- Proper cleanup on unpublish failures

## Limitations

- **OAuth Tokens Required**: You must obtain OAuth access tokens through an external OAuth flow before using this plugin. The plugin does not implement the interactive OAuth authorization flow.

## Example Scenarios

### Scenario 1: Basic Photo Publishing

Configuration:
```json
{
  "flickr_api_key": "abc123",
  "flickr_api_secret": "xyz789",
  "flickr_oauth_token": "72157123456789-abcdef1234567890",
  "flickr_oauth_token_secret": "fedcba0987654321",
  "flickr_user_id": "12345678@N01",
  "flickr_photo_limit": 1000, // free account limit
  "flickr_photo_limit_initial_count": 58, // if you already have 58 photos before using the plugin
  "upload_size": "large"
}
```

Result: Photos are uploaded to Flickr at 'large' size with their title, description, and tags. No automatic group assignment. The plugin starts tracking from a baseline of 58 existing photos.

### Scenario 2: Automatic Group Assignment with Glob Patterns

Configuration:
```json
{
  "flickr_api_key": "abc123",
  "flickr_api_secret": "xyz789",
  "flickr_oauth_token": "72157123456789-abcdef1234567890",
  "flickr_oauth_token_secret": "fedcba0987654321",
  "flickr_user_id": "12345678@N01",
  "group_sets": [
    {
      "name": "Wildlife",
      "groups": ["11111111@N01", "22222222@N01"],
      "auto_tags": ["wildlife*", "animal*"]
    },
    {
      "name": "All Vacations",
      "groups": ["33333333@N01"],
      "auto_albums": ["vacation-*"]
    }
  ]
}
```

Result: 
- Photos with tags matching `wildlife*` OR `animal*` (e.g., "wildlife", "wildlife-bird", "animals", "animal-cat") are added to the Wildlife group set
- Photos in albums matching `vacation-*` (e.g., "vacation-2024", "vacation-2025", "vacation-europe") are added to the All Vacations group set
- Matching is OR-based, so only ONE pattern needs to match

### Scenario 3: Per-Photo Customization

Entity parameters for a specific photo:
```json
{
  "override_description": "Award-winning shot from the 2025 competition",
  "additional_tags": ["award", "featured"],
  "additional_group_sets": ["Wildlife"],
  "safety_level": 1
}
```

Result: This photo uses a custom description, gets extra tags, is added to the Wildlife group set, and is marked as Safe content.

### Scenario 4: Match All Photos with Wildcard

Configuration:
```json
{
  "flickr_api_key": "abc123",
  "flickr_api_secret": "xyz789",
  "flickr_oauth_token": "72157123456789-abcdef1234567890",
  "flickr_oauth_token_secret": "fedcba0987654321",
  "flickr_user_id": "12345678@N01",
  "group_sets": [
    {
      "name": "All Photos Group",
      "groups": ["44444444@N01"],
      "auto_tags": ["*"]
    }
  ]
}
```

Result: ALL photos are automatically added to the "All Photos Group" because the `*` wildcard matches any tag. This is useful for adding all your photos to a general portfolio group.

### Scenario 5: Force Re-upload

Entity parameters to force re-upload an existing photo:
```json
{
  "force": true
}
```

Result: The photo will be re-uploaded to Flickr even if it was already uploaded, generating a new Flickr photo ID. The published photo count is not incremented since it's a replacement.

## Troubleshooting

### Authentication Errors

**Error**: `oauth_problem=parameter_absent&oauth_parameters_absent=oauth_token`
- **Cause**: Missing OAuth access tokens in configuration
- **Solution**: Complete the OAuth flow to obtain your `oauth_token` and `oauth_token_secret`. You need all four credential fields: `flickr_api_key`, `flickr_api_secret`, `oauth_token`, and `oauth_token_secret`.

**Question**: Do I need to re-authenticate periodically?
- **Answer**: No! Flickr OAuth tokens do not expire. Once obtained, they work indefinitely unless you revoke access from your Flickr account settings.

### Photo Not Uploading

- Verify Flickr API credentials are correct
- Check the published photo limit hasn't been reached
- Ensure the photo image can be retrieved
- Review logs for API error messages

### Groups Not Being Assigned

- Verify group IDs are correct (should be in N format)
- Check that auto_tags and auto_albums patterns are correct (supports glob patterns with *)
- Remember: Matching is OR-based - only ONE pattern needs to match
- Patterns are case-sensitive
- Review logs for group assignment errors and which patterns matched

### Duplicate Photos

The plugin prevents duplicates by tracking uploaded photos. If you see duplicates:
- Check the persistent storage integrity
- Verify the `{photo_uuid}_uploaded` keys are being set correctly
- Review logs for upload confirmation messages

**Note**: If you intentionally want to re-upload a photo, use the `force: true` entity parameter.

### Force Re-upload Not Working

- Ensure the entity parameter is set as a boolean: `"force": true` (not a string)
- Check logs to confirm the force parameter is being recognized
- Verify you have not reached the `flickr_photo_limit` limit

## Development Notes

This plugin demonstrates:
- OAuth 1.0a signature generation without external libraries
- HTTP API interaction using urllib
- JSON configuration parsing
- Persistent state management
- Glob pattern matching for flexible tag and album filtering
- OR-based conditional logic for auto-tagging and group assignment
- Error handling and logging best practices

## Changelog

- **0.2.0** (2026-01-02): Pattern matching update
  - **BREAKING CHANGE**: Group set matching changed from AND-based to OR-based
  - Added glob pattern support for `auto_tags` and `auto_albums` (supports `*` wildcard)
  - A photo now matches if ANY tag/album matches ANY pattern (more flexible)
  - Improved logging to show which specific patterns matched
  - Example: `"auto_tags": ["wildlife*"]` now matches "wildlife", "wildlife-bird", "wildlifephotography", etc.

- **0.1.0** (2025-12-30): Initial release
  - Photo upload and deletion
  - Automatic group assignment
  - Tag processing
  - Photo limit management
  - OAuth 1.0a signing
  - Force re-upload capability
  - Safety level configuration per photo
  - Initial photo count tracking
