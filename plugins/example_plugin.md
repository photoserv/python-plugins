# Example Plugin

A demonstration plugin for Photoserv that showcases the complete plugin interface and best practices.

## Overview

This plugin illustrates how to build Photoserv plugins with configuration management, entity parameters, event handling, and persistent storage.

## Features

- **Configuration Schema**: Define plugin settings with `__plugin_config__` that users provide as JSON
- **Entity Parameters**: Per-photo parameters via `__plugin_entity_parameters__`
- **Event Handlers**: Respond to photo publish/unpublish and global change events
- **Persistent Storage**: Store and retrieve data across plugin invocations
- **Photo Access**: Retrieve photo thumbnails and metadata

## Configuration

The plugin expects JSON configuration with the following structure:

```json
{
  "example_param": "some value",
  "api_key": "${MY_API_KEY}",
  "max_retries": 3,
  "enabled_features": ["feature1", "feature2"]
}
```

Environment variables can be referenced using `${VAR_NAME}` syntax.

## Entity Parameters

Per-photo parameters can be provided as JSON:

```json
{
  "custom_field": "special_value",
  "priority": 5,
  "tags": ["important", "featured"]
}
```

## Implementation

The plugin demonstrates:

1. **Initialization**: Access and validate configuration values
2. **Event Handling**: Process photo lifecycle events with full metadata access
3. **Storage**: Track plugin state using the persistent storage API
4. **Logging**: Comprehensive logging for debugging and monitoring

## Usage

This is a reference implementation. Copy and modify it to create your own photoserv plugins with custom functionality for photo management workflows.
