# python-elmoclient

A Python module for communicating with Elmo control units via TCPIP protocol.

## Installation

You can install the package via pip:

```bash
pip install python-elmoclient
```

## Usage

```python
from elmoclient import ElmoClient

# Initialize the client
client = ElmoClient(
    host="192.168.1.100",  # IP address of your Elmo control unit
    port=10001,            # Default port is 10001
    user="your_username",  # Optional: username for authentication
    password="your_password"  # Optional: password for authentication
)

# Start the client
client.start()

# Login to the system
client.accesso_sistema()

# Subscribe to events
def on_sector_change(sigtype, pos, value):
    print(f"Sector {pos} changed to {value}")

client.subscribe("settore", 1, on_sector_change)

# Arm a sector
client.inserisci_settore(1)

# Disarm a sector
client.disinserisci_settore(1)

# Stop the client when done
client.stop()
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Troubleshooting

### TimeoutError

If you encounter a `TimeoutError: timed out` when using the client, it could be due to network issues or the Elmo control unit not responding in time. The client has built-in handling for timeouts, but you may need to adjust the timeout value:

```python
client = ElmoClient(
    host="192.168.1.100",
    port=10001,
    timeout=5,  # Increase timeout to 5 seconds (default is 2)
    user="your_username",
    password="your_password"
)
```

### Changelog

For a list of changes in each version, see the [CHANGELOG.md](CHANGELOG.md) file.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
