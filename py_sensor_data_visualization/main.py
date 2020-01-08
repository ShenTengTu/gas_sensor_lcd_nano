'''
Project repo: https://github.com/ShenTengTu/gas_sensor_lcd_nano
'''
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import os
from typing import List

here = os.path.dirname(__file__)


class CycleCounter:
    def __init__(self, limit: int):
        self.__limit = limit
        self.__num = -1
        self.step = 1

    def __iter__(self):
        return self

    def __next__(self):
        return self.next()

    def next(self):
        self.__num += self.step
        self.__num %= self.__limit
        return self.__num


def get_file_entries() -> List[os.DirEntry]:
    data_dir = os.path.join(here, "./SENSOR")
    file_entries = []
    for entry in os.scandir(path=data_dir):
        if entry.is_file() and entry.name.endswith(".CSV"):
            file_entries.append(entry)
    return file_entries


def parse_data(file_path: str) -> np.recarray:
    return np.genfromtxt(
        file_path,
        dtype="datetime64[s],f,f",
        delimiter=",",
        names=True,
        filling_values=(None, None, None)
    ).view(np.recarray)


def plot_data(ax: plt.Axes, np_data: np.recarray, time_offset=8):
    N = len(np_data)
    ind = np.arange(N)  # the evenly spaced plot indices

    # Matplotlib works better with datetime.datetime than np.datetime64,
    # but thelatter is more portable.
    datetime = np.add(np_data.timestamp, np.timedelta64(
        time_offset, 'h')).astype('O')

    def format_date(x, pos=None, c=0):
        thisind = np.clip(int(x + 0.5), 0, N - 1)
        return datetime[thisind].strftime('%y-%m-%d\n%H:%M:%S')

    ax.plot(ind, np_data.LPG_ppm, '-', label="LPG")
    ax.plot(ind, np_data.CH4_ppm, '-', label="CH4")
    ax.legend(loc='upper right', ncol=2, fancybox=True)
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(format_date))
    ax.set_title(" Gas Sensing (UTC%+d)" % time_offset)
    ax.set_xlabel('time')
    ax.set_ylabel('ppm')


# ===

# click forward or back button of navigation toolbar to change dataset
file_entries = get_file_entries()
cc = CycleCounter(len(file_entries))
plt.rcParams['toolbar'] = 'toolmanager'
fig, ax = plt.subplots()


def update_figure(index: int):
    ax.clear()
    entry = file_entries[index]
    np_data = parse_data(entry.path)
    plot_data(ax, np_data)
    fig.autofmt_xdate()
    fig.suptitle(entry.name)
    fig.canvas.set_window_title(entry.name)


def on_click(event):
    if event.name == "tool_trigger_forward":
        cc.step = 1
    if event.name == "tool_trigger_back":
        cc.step = -1

    update_figure(cc.next())


fig.canvas.manager.toolmanager.toolmanager_connect(
    "tool_trigger_forward", on_click)
fig.canvas.manager.toolmanager.toolmanager_connect(
    "tool_trigger_back", on_click)


update_figure(cc.next())
plt.show()
