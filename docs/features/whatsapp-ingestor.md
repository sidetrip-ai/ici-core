# WhatsApp Ingestor

## Overview

The WhatsApp ingestor allows ICI to fetch and process messages from WhatsApp. It leverages a Node.js service that uses WhatsApp Web JS to interact with WhatsApp's web client.

## Architecture

The WhatsApp integration consists of two components:

1. **Node.js WhatsApp Service**: A standalone service that handles the direct integration with WhatsApp Web using the WhatsApp Web JS library.

2. **Python WhatsApp Ingestor**: An implementation of the ICI Ingestor interface that communicates with the Node.js service to retrieve messages.

```
┌─────────────────────────────────────────────────────────────────────┐
│                           ICI Core System                           │
│                                                                     │
│  ┌───────────────────┐       ┌──────────────┐      ┌─────────────┐  │
│  │ WhatsAppIngestor  │───────│ Preprocessor │──────│  Embedder   │  │
│  └───────────────────┘       └──────────────┘      └─────────────┘  │
│             │                                                       │
└─────────────┼───────────────────────────────────────────────────────┘
              │
              │ HTTP
              │
┌─────────────▼───────────────────────────────────────────────────────┐
│                      Node.js WhatsApp Service                       │
│                                                                     │
│  ┌─────────────┐    ┌───────────────┐      ┌─────────────────────┐  │
│  │  REST API   │    │ Session Store │      │ WhatsApp Web Client │  │
│  └─────────────┘    └───────────────┘      └─────────────────────┘  │
│                                                     │               │
└─────────────────────────────────────────────────────┼───────────────┘
                                                      │
                                                      │ WebSocket
                                                      │
┌─────────────────────────────────────────────────────▼───────────────┐
│                         WhatsApp Servers                            │
└─────────────────────────────────────────────────────────────────────┘
```

## Configuration

### WhatsApp Ingestor Configuration

Add the following to your `config.yaml` file:

```yaml
ingestors:
  whatsapp:
    service_url: "http://localhost:3000/api"   # URL of the Node.js service API
    session_id: "default_session"              # Session identifier for WhatsApp
    request_timeout: 30                        # Timeout for HTTP requests in seconds
```

### Preprocessor Configuration

```yaml
preprocessors:
  whatsapp:
    chunk_size: 512                # Maximum number of tokens per document chunk
    include_overlap: true          # Whether to include overlap between chunks
    max_messages_per_chunk: 10     # Maximum number of messages to include in a single chunk
    time_window_minutes: 15        # Time window for grouping messages into conversations
```

## Usage

### Setup WhatsApp Node.js Service

1. Navigate to the WhatsApp service directory:
   ```bash
   cd whatsapp-service
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the service:
   ```bash
   npm start
   ```

### Authentication

When running the WhatsApp ingestor for the first time, you'll need to authenticate with WhatsApp:

1. The ingestor will display instructions with a URL to view the QR code.
2. Open WhatsApp on your phone.
3. Go to Settings > WhatsApp Web/Desktop.
4. Scan the QR code displayed at the provided URL.
5. Once authenticated, the session will be saved for future use.

### Using the Ingestor

Use the standard ICI ingestion pipeline with the WhatsApp ingestor:

```python
from ici.adapters.ingestors import WhatsAppIngestor
from ici.adapters.pipelines import IngestionPipeline

# Initialize and run the pipeline
async def main():
    # Create ingestor
    ingestor = WhatsAppIngestor()
    await ingestor.initialize()
    
    # Fetch data
    data = await ingestor.fetch_full_data()
    
    # Process with pipeline
    # ...

```

## Limitations

- Only text messages are supported; media files are ignored.
- Group messages are supported but require the user to be a participant.
- The WhatsApp session needs to remain active with periodic connection to WhatsApp servers.

## Troubleshooting

### QR Code Authentication Issues

If authentication fails:

1. Ensure your phone has an active internet connection.
2. Try clearing WhatsApp Web sessions on your phone (Settings > WhatsApp Web > Log out from all devices).
3. Restart the Node.js service and try again.

### Connection Issues

If the ingestor cannot connect to the Node.js service:

1. Verify the service_url in config.yaml is correct.
2. Check that the Node.js service is running.
3. Ensure no firewall is blocking the connection between the ingestor and the service.

## Security Considerations

- WhatsApp Web sessions contain sensitive authentication data. Secure the `data/sessions` directory.
- The Node.js service should be deployed in a secure environment, ideally not exposed to the public internet.
- Consider using HTTPS if the service needs to be accessed over a network. 