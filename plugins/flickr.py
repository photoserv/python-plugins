"""
Flickr plugin for Photoserv enabling photo publishing to Flickr.

This plugin handles:
- Publishing photos to Flickr with metadata and tags
- Managing photo limits and tracking uploaded photos
- Automatic group set assignment based on tags and albums
- Photo unpublishing and cleanup
"""

import urllib.request
import urllib.parse
import urllib.error
import json
import hashlib
import hmac
import time
import uuid
import base64
import xml.etree.ElementTree as ET
from io import BytesIO

from photoserv_plugin import PhotoservPlugin

# Required module-level variables
__plugin_name__ = "Flickr"
__plugin_uuid__ = "dd5efb7c-4f55-4203-b261-468ccecc0f46"
__plugin_version__ = "0.1.0"
__plugin_author__ = "Max Loiacono"
__plugin_website__ = "https://github.com/photoserv/python-plugins/blob/main/plugins/flickr.md"

# Plugin configuration schema
__plugin_config__ = {
    "flickr_api_key": "Flickr API Key (Consumer Key)",
    "flickr_api_secret": "Flickr API Secret (Consumer Secret)",
    "flickr_oauth_token": "Flickr OAuth Access Token (obtain via OAuth flow)",
    "flickr_oauth_token_secret": "Flickr OAuth Token Secret (obtain via OAuth flow)",
    "flickr_user_id": "Flickr User ID (NSID format, e.g., 12345678@N01)",
    "flickr_photo_limit": "(int) Maximum number of photos to publish (default: 1000)",
    "flickr_photo_limit_initial_count": "(int) Number of photos already in Flickr before installing this plugin (default: 0)",
    "upload_size": "(string) Size of photo to upload to Flickr (default: 'original')",
    "photo_description_footer": "Optional footer text to append to photo descriptions",
    "group_sets": "Array of group set configurations with name, groups, auto_tags, and auto_albums",
}

# Entity parameter schema
__plugin_entity_parameters__ = {
    "override_description": "Override the default photo description",
    "additional_tags": "Additional tags to add to this photo",
    "additional_group_sets": "Additional group set names to apply to this photo",
    "force": "(bool) Force the operation to run without checking existing Flickr state (default: false)",
    "safety_level": "(int) Safety level: 1 for Safe, 2 for Moderate, or 3 for Restricted (default: user's default)",
}


class FlickrPlugin(PhotoservPlugin):
    """Flickr integration plugin implementation."""
    
    def __init__(self, config, photoserv):
        """Initialize the Flickr plugin with configuration."""
        super().__init__(config, photoserv)
        
        # Required configuration
        self.api_key = config.get('flickr_api_key')
        self.api_secret = config.get('flickr_api_secret')
        self.oauth_token = config.get('flickr_oauth_token')
        self.oauth_token_secret = config.get('flickr_oauth_token_secret')
        self.user_id = config.get('flickr_user_id')
        
        if not all([self.api_key, self.api_secret, self.oauth_token, self.oauth_token_secret, self.user_id]):
            self.logger.error("Missing required Flickr credentials in configuration")
            raise ValueError("flickr_api_key, flickr_api_secret, flickr_oauth_token, flickr_oauth_token_secret, and flickr_user_id are required")
        
        # Optional configuration
        self.flickr_photo_limit = config.get('flickr_photo_limit', 1000)
        self.flickr_photo_limit_initial_count = config.get('flickr_photo_limit_initial_count', 0)
        self.upload_size = config.get('upload_size', 'original')
        self.photo_description_footer = config.get('photo_description_footer')
        self.group_sets = config.get('group_sets', [])
        
        self.logger.info(f"Flickr plugin initialized for user {self.user_id}")
        self.logger.info(f"Max published photos: {self.flickr_photo_limit}")
        self.logger.info(f"Initial photo count: {self.flickr_photo_limit_initial_count}")
        self.logger.info(f"Upload size: {self.upload_size}")
        self.logger.info(f"Configured group sets: {len(self.group_sets)}")
        
        # Initialize published photo count if not exists
        if self.photoserv.config.get('published_photo_count') is None:
            self.photoserv.config.set('published_photo_count', self.flickr_photo_limit_initial_count)
            self.logger.info(f"Initialized published_photo_count to {self.flickr_photo_limit_initial_count}")

    def _flickr_api_call(self, method, params=None, upload=False, photo_data=None):
        """
        Make a Flickr API call with OAuth 1.0a signing.
        
        Args:
            method: Flickr API method name (e.g., 'flickr.photos.delete')
            params: Dictionary of API parameters
            upload: Whether this is an upload request
            photo_data: Binary photo data for upload (BytesIO or file-like object)
            
        Returns:
            Parsed JSON response from Flickr API (or parsed XML for uploads)
            
        Raises:
            Exception: If API call fails
        """
        if params is None:
            params = {}
        
        # Base URL for API calls
        if upload:
            base_url = "https://up.flickr.com/services/upload/"
        else:
            base_url = "https://api.flickr.com/services/rest/"
        
        # Add required OAuth parameters
        oauth_params = {
            'oauth_nonce': hashlib.md5(str(time.time()).encode()).hexdigest(),
            'oauth_timestamp': str(int(time.time())),
            'oauth_consumer_key': self.api_key,
            'oauth_token': self.oauth_token,
            'oauth_signature_method': 'HMAC-SHA1',
            'oauth_version': '1.0',
        }
        
        # Merge with method-specific parameters
        if not upload:
            params['method'] = method
            params['format'] = 'json'
            params['nojsoncallback'] = '1'
        
        all_params = {**params, **oauth_params}
        
        # Generate OAuth signature
        signature = self._generate_oauth_signature('POST', base_url, all_params)
        all_params['oauth_signature'] = signature
        
        try:
            if upload and photo_data:
                # Create multipart/form-data for upload
                boundary = f'----WebKitFormBoundary{uuid.uuid4().hex}'
                body = self._create_multipart_body(all_params, photo_data, boundary)
                
                req = urllib.request.Request(
                    base_url,
                    data=body,
                    headers={'Content-Type': f'multipart/form-data; boundary={boundary}'},
                    method='POST'
                )
            else:
                # Regular form-encoded POST
                data = urllib.parse.urlencode(all_params).encode('utf-8')
                req = urllib.request.Request(base_url, data=data, method='POST')
            
            with urllib.request.urlopen(req, timeout=120) as response:
                response_data = response.read().decode('utf-8')
                
                if upload:
                    # Upload responses are XML
                    return self._parse_upload_response(response_data)
                else:
                    result = json.loads(response_data)
                    
                    if result.get('stat') == 'fail':
                        error_msg = result.get('message', 'Unknown error')
                        raise Exception(f"Flickr API error: {error_msg}")
                    
                    return result
                    
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            self.logger.error(f"HTTP error calling Flickr API: {e.code} - {error_body}")
            raise Exception(f"Flickr API HTTP error: {e.code}")
        except urllib.error.URLError as e:
            self.logger.error(f"URL error calling Flickr API: {e.reason}")
            raise Exception(f"Flickr API connection error: {e.reason}")
        except Exception as e:
            self.logger.error(f"Error calling Flickr API: {str(e)}")
            raise

    def _create_multipart_body(self, params, photo_data, boundary):
        """
        Create multipart/form-data body for photo upload.
        
        Args:
            params: Dictionary of form parameters
            photo_data: Binary photo data (BytesIO or file-like object)
            boundary: Multipart boundary string
            
        Returns:
            Encoded multipart body as bytes
        """
        body = BytesIO()
        
        # Add text parameters
        for key, value in params.items():
            body.write(f'--{boundary}\r\n'.encode('utf-8'))
            body.write(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode('utf-8'))
            body.write(f'{value}\r\n'.encode('utf-8'))
        
        # Add photo file
        body.write(f'--{boundary}\r\n'.encode('utf-8'))
        body.write(f'Content-Disposition: form-data; name="photo"; filename="photo.jpg"\r\n'.encode('utf-8'))
        body.write(f'Content-Type: image/jpeg\r\n\r\n'.encode('utf-8'))
        
        # Read and write photo data
        photo_data.seek(0)
        body.write(photo_data.read())
        
        body.write(f'\r\n--{boundary}--\r\n'.encode('utf-8'))
        
        return body.getvalue()

    def _parse_upload_response(self, xml_response):
        """
        Parse XML response from Flickr upload API.
        
        Args:
            xml_response: XML string response
            
        Returns:
            Dictionary with parsed response data
            
        Raises:
            Exception: If response indicates failure
        """
        try:
            root = ET.fromstring(xml_response)
            
            if root.get('stat') == 'fail':
                err = root.find('err')
                error_msg = err.get('msg', 'Unknown error') if err is not None else 'Unknown error'
                error_code = err.get('code', 'unknown') if err is not None else 'unknown'
                raise Exception(f"Flickr upload error [{error_code}]: {error_msg}")
            
            # Extract photo ID from successful upload
            photoid_elem = root.find('photoid')
            if photoid_elem is not None:
                return {'photo_id': photoid_elem.text, 'stat': 'ok'}
            else:
                raise Exception("Photo ID not found in upload response")
                
        except ET.ParseError as e:
            self.logger.error(f"Failed to parse upload response XML: {e}")
            self.logger.error(f"Response was: {xml_response}")
            raise Exception(f"Invalid XML response from Flickr: {e}")

    def _generate_oauth_signature(self, method, url, params):
        """
        Generate OAuth 1.0a signature for Flickr API.
        
        Args:
            method: HTTP method (GET or POST)
            url: Base URL
            params: Dictionary of parameters
            
        Returns:
            Base64-encoded HMAC-SHA1 signature
        """
        # Sort parameters
        sorted_params = sorted(params.items())
        
        # Create parameter string
        param_string = '&'.join([f"{k}={urllib.parse.quote(str(v), safe='')}" 
                                 for k, v in sorted_params])
        
        # Create signature base string
        base_string = '&'.join([
            method.upper(),
            urllib.parse.quote(url, safe=''),
            urllib.parse.quote(param_string, safe='')
        ])
        
        # Create signing key (client_secret&token_secret)
        signing_key = f"{urllib.parse.quote(self.api_secret, safe='')}&{urllib.parse.quote(self.oauth_token_secret, safe='')}"
        
        # Generate signature
        signature = hmac.new(
            signing_key.encode('utf-8'),
            base_string.encode('utf-8'),
            hashlib.sha1
        ).digest()
        
        # Base64 encode
        return base64.b64encode(signature).decode('utf-8')

    def _build_description(self, data, params):
        """Build photo description from data and parameters."""
        # Check for override description
        if params and params.get('override_description'):
            description = params['override_description']
        else:
            description = data.get('description', '')
        
        # Add footer if configured
        if self.photo_description_footer:
            if description:
                description += f"\n\n{self.photo_description_footer}"
            else:
                description = self.photo_description_footer
        
        return description

    def _build_tags(self, data, params):
        """Build tag list from photo data and parameters."""
        tags = []
        seen_tags = set()
        
        # Add tags from photo data
        photo_tags = data.get('tags', [])
        for tag in photo_tags:
            tag_name = tag.get('name', '')
            # Remove spaces from tags as required by Flickr
            tag_name = tag_name.replace(' ', '')
            if tag_name and tag_name not in seen_tags:
                tags.append(tag_name)
                seen_tags.add(tag_name)
        
        # Add additional tags from entity parameters
        if params and params.get('additional_tags'):
            additional = params['additional_tags']
            if isinstance(additional, list):
                for tag in additional:
                    tag_name = str(tag).replace(' ', '')
                    if tag_name and tag_name not in seen_tags:
                        tags.append(tag_name)
                        seen_tags.add(tag_name)
        
        return tags

    def _get_applicable_group_sets(self, data, params):
        """Determine which group sets apply to this photo."""
        applicable_sets = []
        
        # Get photo tags and albums
        photo_tag_names = {tag.get('name') for tag in data.get('tags', [])}
        photo_album_uuids = {album.get('uuid') for album in data.get('albums', [])}
        photo_album_slugs = {album.get('slug') for album in data.get('albums', [])}
        
        for group_set in self.group_sets:
            name = group_set.get('name')
            if not name:
                continue
            
            # Check auto_tags - photo must have ALL specified tags
            auto_tags = group_set.get('auto_tags', [])
            if auto_tags:
                if all(tag in photo_tag_names for tag in auto_tags):
                    applicable_sets.append(group_set)
                    self.logger.info(f"  Auto-matched group set '{name}' via tags")
                    continue
            
            # Check auto_albums - photo must be in at least one specified album
            auto_albums = group_set.get('auto_albums', [])
            if auto_albums:
                if any(album in photo_album_uuids or album in photo_album_slugs 
                       for album in auto_albums):
                    applicable_sets.append(group_set)
                    self.logger.info(f"  Auto-matched group set '{name}' via albums")
                    continue
        
        # Add additional group sets from entity parameters
        if params and params.get('additional_group_sets'):
            additional_names = params['additional_group_sets']
            if isinstance(additional_names, list):
                for name in additional_names:
                    # Find group set by name
                    for group_set in self.group_sets:
                        if group_set.get('name') == name:
                            if group_set not in applicable_sets:
                                applicable_sets.append(group_set)
                                self.logger.info(f"  Added group set '{name}' via entity params")
                            break
        
        return applicable_sets

    def _add_photo_to_groups(self, flickr_photo_id, group_sets):
        """Add photo to Flickr groups based on group sets."""
        for group_set in group_sets:
            groups = group_set.get('groups', [])
            set_name = group_set.get('name', 'unnamed')
            
            for group_id in groups:
                try:
                    self.logger.info(f"  Adding photo to group {group_id} (set: {set_name})")
                    self._flickr_api_call('flickr.groups.pools.add', {
                        'photo_id': flickr_photo_id,
                        'group_id': group_id
                    })
                except Exception as e:
                    self.logger.error(f"  Failed to add photo to group {group_id}: {e}")
                    # Continue with other groups even if one fails

    def on_photo_publish(self, data, params, **kwargs):
        """Handle photo publish events."""
        photo_uuid = data.get('uuid')
        photo_title = data.get('title', 'Untitled')
        
        self.logger.info(f"Publishing photo to Flickr: {photo_title} (UUID: {photo_uuid})")
        
        # Check force parameter
        force = params and params.get('force', False)
        
        # Check if already uploaded (unless forced)
        upload_key = f"{photo_uuid}_uploaded"
        existing_flickr_id = self.photoserv.config.get(upload_key)
        
        if existing_flickr_id and not force:
            self.logger.info(f"  Photo already uploaded to Flickr (ID: {existing_flickr_id}), skipping")
            return
        
        if existing_flickr_id and force:
            self.logger.info(f"  Photo already uploaded to Flickr (ID: {existing_flickr_id}), but force=true, proceeding anyway")
        
        # Check photo limit
        published_count = self.photoserv.config.get('published_photo_count', 0)
        if published_count >= self.flickr_photo_limit:
            self.logger.error(f"  Photo limit reached ({self.flickr_photo_limit}), cannot publish")
            raise Exception(f"Maximum published photo limit ({self.flickr_photo_limit}) reached")
        
        # Build description and tags
        description = self._build_description(data, params)
        tags = self._build_tags(data, params)
        
        self.logger.info(f"  Title: {photo_title}")
        self.logger.info(f"  Description: {description[:50]}..." if len(description) > 50 else f"  Description: {description}")
        self.logger.info(f"  Tags: {', '.join(tags)}")
        
        # Get photo image
        try:
            # Fetch the configured upload size
            photo_stream = self.photoserv.get_photo_image(data, self.upload_size)
            if not photo_stream:
                raise Exception(f"Could not retrieve photo image at size '{self.upload_size}'")
        except Exception as e:
            self.logger.error(f"  Error getting photo image: {e}")
            raise
        
        # Ensure stream is closed even if an error occurs
        try:
            # Upload photo to Flickr
            self.logger.info("  Uploading photo to Flickr...")
            
            # Prepare upload parameters
            upload_params = {
                'title': photo_title,
                'description': description,
                'tags': ' '.join(tags),
                'is_public': '1',
                'is_friend': '0',
                'is_family': '0',
                'hidden': '2' if data.get('hidden') else '1',
            }
            
            # Add safety_level if specified in entity parameters
            if params and params.get('safety_level'):
                safety_level = params.get('safety_level')
                # Validate safety_level is 1, 2, or 3
                if safety_level in [1, 2, 3]:
                    upload_params['safety_level'] = str(safety_level)
                    self.logger.info(f"  Safety level: {safety_level}")
                else:
                    self.logger.warning(f"  Invalid safety_level '{safety_level}', using user default")
            
            # Upload the photo
            upload_response = self._flickr_api_call(
                method=None,
                params=upload_params,
                upload=True,
                photo_data=photo_stream
            )
            
            # Extract photo ID from response
            flickr_photo_id = upload_response.get('photo_id')
            if not flickr_photo_id:
                raise Exception("Failed to get photo ID from upload response")
            
            self.logger.info(f"  Photo uploaded successfully (Flickr ID: {flickr_photo_id})")
            
            # Increment published photo count (only if this is a new upload)
            if not existing_flickr_id:
                new_count = published_count + 1
                self.photoserv.config.set('published_photo_count', new_count)
            else:
                new_count = published_count
            
            # Store flickr photo ID
            self.photoserv.config.set(upload_key, flickr_photo_id)
            
            # Add to groups
            group_sets = self._get_applicable_group_sets(data, params)
            if group_sets:
                self.logger.info(f"  Adding photo to {len(group_sets)} group set(s)")
                self._add_photo_to_groups(flickr_photo_id, group_sets)
            else:
                self.logger.info("  No group sets applicable for this photo")
            
            self.logger.info(f"  Publish complete (total published: {new_count}/{self.flickr_photo_limit})")
            
        except Exception as e:
            self.logger.error(f"  Failed to publish photo: {e}")
            raise
        finally:
            # Always close the stream
            photo_stream.close()

    def on_photo_unpublish(self, data, params, **kwargs):
        """Handle photo unpublish events."""
        photo_uuid = data.get('uuid')
        photo_title = data.get('title', 'Untitled')
        
        self.logger.info(f"Unpublishing photo from Flickr: {photo_title} (UUID: {photo_uuid})")
        
        # Check force parameter
        force = params.get('force', False)
        
        # Get flickr photo ID
        upload_key = f"{photo_uuid}_uploaded"
        flickr_photo_id = self.photoserv.config.get(upload_key)
        
        if not flickr_photo_id and not force:
            self.logger.info("  Photo was not uploaded to Flickr, skipping")
            return
        
        if not flickr_photo_id and force:
            self.logger.warning("  No Flickr photo ID found, but force=true specified. Cannot unpublish without photo ID.")
            return
        
        try:
            # Delete photo from Flickr
            self.logger.info(f"  Deleting photo from Flickr (ID: {flickr_photo_id})")
            self._flickr_api_call('flickr.photos.delete', {
                'photo_id': flickr_photo_id
            })
            
            self.logger.info("  Photo deleted successfully from Flickr")
            
            # Delete upload key
            self.photoserv.config.delete(upload_key)
            
            # Decrement published photo count
            published_count = self.photoserv.config.get('published_photo_count', 0)
            if published_count > 0:
                new_count = published_count - 1
                self.photoserv.config.set('published_photo_count', new_count)
                self.logger.info(f"  Unpublish complete (total published: {new_count})")
            
        except Exception as e:
            self.logger.error(f"  Failed to unpublish photo: {e}")
            raise
