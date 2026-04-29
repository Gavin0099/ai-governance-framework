# USB Hub Firmware Checklist

- Board family: RTD-based USB hub controller
- CFU requests must produce matching CFU responses in order
- D+/D- routing must remain unchanged during firmware update handling
- Any pointer arithmetic touching endpoint buffers requires an interrupt safety review
