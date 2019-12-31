'''
Project repo: https://github.com/ShenTengTu/gas_sensor_lcd_nano
'''
from typing import List, Callable
from enum import Enum
from serial.tools import list_ports, list_ports_common
from serial import Serial
import time
import calendar
import sys

to_ascii_bytes = lambda s: bytes(s, 'ascii')

class Serial_Status(Enum):
  SERIAL_CMD_RESPONSE = "__RESPONSE__"
  SERIAL_CMD_SUCCESS = "_CMD_SUCCESS_"
  SERIAL_CMD_FAIL = "_CMD_FAIL_"
  SERIAL_CMD_FINISH = "_CMD_FINISH_"

class Serial_Command(Enum):
  CMD_REQUEST = "__REQUEST__"
  CMD_SYNC_TIME = "SYNC_TIME"

class Arduino_Serial_CMD_TRX:
  '''
  The Serial transceiver interface for Python to interact with Arduino boards which provides serial command API.
  
  The serial command API is built by `SerialCommands` library by Pedro Tiago Pereira.
  '''
  BAUD = 115200
  SERIAL_CMD_DELIMETER = ";"
  SERIAL_CMD_ARG_DELIMETER = " "

  @staticmethod
  def list_ports() -> List[list_ports_common.ListPortInfo]:
    '''
    Listing exist serial ports
    '''
    return list_ports.comports()
  
  @classmethod
  def build_command_msg(cls, cmd_name: str, *args) -> bytes:
    '''
    Build single serial command message
    '''
    cmd_del = to_ascii_bytes(cls.SERIAL_CMD_DELIMETER)
    cmd_arg_del = to_ascii_bytes(cls.SERIAL_CMD_ARG_DELIMETER)
    msg = b''
    msg += bytes(cmd_name, 'ascii')
    for arg in args:
      msg += cmd_arg_del
      msg += to_ascii_bytes(str(arg))
    msg += cmd_del
    return msg

  def __init__(self, serial_port_name: str):
    self.__port = Serial(port=serial_port_name, baudrate=self.BAUD)
    self._is_port_response = False
    self._send_request_count = 0
  
  def __enter__(self):
    return self.trx_main

  def __exit__(self, type, value, traceback):
    self.__port.close()
    self._is_port_response = False
    self._send_request_count = 0
  
  def __execute_command(self, wait_res_times: int, fn: Callable, *args):
    if not self._is_port_response:
      if self._send_request_count < wait_res_times:
        msg = self.build_command_msg(Serial_Command.CMD_REQUEST.value)
        self.__port.write(msg)
        self._send_request_count += 1
        print("等待回應...%r" % self._send_request_count, end="\r")
        time.sleep(1) # wait first response
    else:
      if(callable(fn)):
        fn(*args)
      time.sleep(0.1) # wait commnad response
       
  
  def __handle_feeback(self):
    while self.__port.in_waiting:
      mcu_feedback = self.__port.readline().decode()
      msg = mcu_feedback[:-2] # remove '\r\n'
      if(msg == Serial_Status.SERIAL_CMD_RESPONSE.value):
        self._is_port_response = True
        break
      elif(msg == Serial_Status.SERIAL_CMD_SUCCESS.value):
        print("指令執行成功")
      elif(msg == Serial_Status.SERIAL_CMD_FAIL.value):
        print("指令執行錯誤")
      elif(msg == Serial_Status.SERIAL_CMD_FINISH.value):
        sys.exit()
      else:
        print("> %r" % msg)
  
  def trx_main(self, wait_res_times: int, cmd_name: str, *args):
    try:
      cmd_fn = getattr(self, 'cmd_%s' % cmd_name, None)
      if cmd_fn is None:
        print("未知的指令")
        sys.exit()
      
      while True:
        self.__handle_feeback()
        self.__execute_command(wait_res_times, cmd_fn, *args)
    except (SystemExit, KeyboardInterrupt):
      self.__exit__(*sys.exc_info())

  def cmd_sync_time(self):
      """
      Command : Sync time
      """
      print('傳送時間同步指令...')
      timestamp = calendar.timegm(time.gmtime())
      print(timestamp)
      msg = self.build_command_msg(Serial_Command.CMD_SYNC_TIME.value, timestamp)
      self.__port.write(msg)