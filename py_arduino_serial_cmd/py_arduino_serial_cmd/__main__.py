from . import Arduino_Serial_CMD_TRX
from .cli import CLI
from argparse import Action

class IntAction(Action):
    def __init__(self, option_strings, dest, **kwargs):
        super().__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, int(values))

serial_command_cli = CLI(
    main_params={
        "description":'Commanding Arduino boards by serial port.',
    },
    sub_params={
        "description":'Serial commands.',
        "dest": 's_cmd'
    })

serial_command_cli.add_argument('-p', '--port', help='serial port name')
serial_command_cli.add_argument('-d', '--delay', action=IntAction, default=3, 
                                help='waiting N times/sec (default N=3) for serial response')
def _get_port(namespace) -> str:
  ports = Arduino_Serial_CMD_TRX.list_ports()
  if len(ports) < 1:
    return None

  if namespace.port:
    for port in ports:
      if namespace.port == port.device or namespace.port == port.name:
        return namespace.port
    return None
  else:
    return ports[0].device

def _cli_main(namespace):
  port_name = _get_port(namespace)
  if port_name is None:
    print('No serial port.')
  else:
    with Arduino_Serial_CMD_TRX(port_name) as trx_main:
      trx_main(namespace.delay, namespace.s_cmd)


@serial_command_cli.sub_command(
  description="Synchronize Arduino board time as computer time.",
  help="Synchronize Arduino board time as computer time."
  )
def sync_time(namespace):
  _cli_main(namespace)

if __name__ == "__main__":
  namespace = serial_command_cli.handle_args()

