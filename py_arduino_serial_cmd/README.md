# Let Python to command Arduino boards by serial port.
A smiple cli to let you interact with Arduino boards which provides serial command API.
The serial command API is built by [`SerialCommands` library](https://github.com/ppedro74/Arduino-SerialCommands) by Pedro Tiago Pereira.

## How to use
```
cd your/path/py_arduino_serial_cmd
python -m py_arduino_serial_cmd --help
python -m py_arduino_serial_cmd --port COM10 sync_time
```

### Serial commands
`sync_time` : Synchronize Arduino board time as computer time.

