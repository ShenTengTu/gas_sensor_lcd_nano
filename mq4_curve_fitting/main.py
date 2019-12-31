import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
import matplotlib.image as mpimg
from matplotlib.widgets import Cursor, CheckButtons, Slider
from decimal import Decimal, ROUND_HALF_UP

plt.rcParams['toolbar'] = 'toolmanager'

class Controller:
  '''
  Display coordinate of the point if mouse hover on the plot
  '''

  @staticmethod
  def decimal_quantize(value, format='.00', rounding=ROUND_HALF_UP):
    return float(Decimal(value).quantize(Decimal('.00'), ROUND_HALF_UP))
  
  def __init__(self, fig, ax):
    self.__fig = fig
    self.__ax = ax
    self.__point_annot = self.__ax.annotate("", (0, 0), xytext=(5, 5),textcoords='offset points')
    self.__cursor = Cursor(ax, useblit=False, color='red', linewidth=0.5)
    self.__checkbox_ax = self.__fig.add_axes([0.02, 0.65, 0.1, 0.15], facecolor="lightgoldenrodyellow")
    self.__checkbox = CheckButtons(self.__checkbox_ax, ["curve\nfitting"], [self.__ax.get_visible()])
    self.__slider_ax = self.__fig.add_axes([0.3, 0.02, 0.5, 0.02], facecolor="lightgoldenrodyellow")
    self.__slider = Slider(self.__slider_ax, 'facecolor alpha', np.float64(0), np.float64(255), valinit=125, valstep=5)
    self._xdata = 0
    self._ydata = 0
    
    self.__checkbox.on_clicked(self.check_box_click)
    self.__slider.on_changed(self.slider_change)
    self.__fig.canvas.mpl_connect("motion_notify_event", self.on_hover)
  
  def  _update_point_annot(self):
    self.__point_annot.xy = (self._xdata, self._ydata)
    self.__point_annot.set_text("%r , %r" % self.__point_annot.xy)

  def on_hover(self, event):
      point_annot_vis = self.__point_annot.get_visible()
      if event.inaxes == self.__ax:
        self._xdata = self.decimal_quantize(event.xdata)
        self._ydata = self.decimal_quantize(event.ydata)
        self._update_point_annot()
        self.__point_annot.set_visible(True)
      else:
        if point_annot_vis:
          self.__point_annot.set_visible(False)
      self.__fig.canvas.draw_idle()
  
  def check_box_click(self, label):
    self.__ax.set_visible(not self.__ax.get_visible())
    self.__fig.canvas.draw_idle()
  
  def slider_change(self, val):
    # val is numpy.float64
    hex_val = '%02x' % int(val.item())
    self.__ax.set_facecolor('#ffffff'+ hex_val)
    self.__fig.canvas.draw_idle()


# ----

class LogLogCurveFit:
  '''
  Calculate paramters of curve fitting on Log-Log plot
  '''

  @staticmethod
  def exp_fn(x, a, b):
    '''
    "y = a * x^b" on log-log plot is straight line
    
    =>  log(y) = b * log(x) + log(a)
    =>  Y = m * X + c

    `m` is slope of the line, `c` is the intercept on the (log y)-axis
    '''
    return a * np.power(x, b)

  def __init__(self, ax, x_log_space):
    self.__ax = ax
    self._x_log_space = x_log_space
  
  def calc_opt_params(self, x_arr, y_arr):
    # Optimal values for the parameters, here is (a, b)
    opt_params, _ = curve_fit(self.exp_fn, x_arr, y_arr)
    return opt_params
  
  def plot_fitting_line(self, opt_params, **kwargs):
    self.__ax.plot(self._x_log_space, self.exp_fn(self._x_log_space, *opt_params), **kwargs)
  
  def plot_data(self, x_arr, y_arr, **kwargs):
    self.__ax.scatter(x_arr, y_arr, **kwargs)
    
# ----

fig_, ax_ = plt.subplots()

# bottom axis - MQ4 Characteristic figure image
image = mpimg.imread("MQ4_ch_0.png")
im_h, im_w, _ = image.shape
ax_.imshow(image)
ax_.axis('off')
ax_.set_title("MQ-4")

# top axis - plotting curve fitting
inset_ax = fig_.add_axes([0.13, 0.115, 0.765, 0.765], facecolor="#ffffff7F")
inset_ax.loglog()
inset_ax.set_xlim(1e2, 1e4)
inset_ax.set_ylim(1e-1, 1e1)
inset_ax.set_aspect(im_h/im_w)
inset_ax.set_title("MQ-4")
inset_ax.xaxis.grid(True, which='major')
inset_ax.xaxis.grid(True, which='minor')
inset_ax.yaxis.grid(True, which='major')
inset_ax.yaxis.grid(True, which='minor')

controller = Controller(fig_, inset_ax)

loglog_curve_fit = LogLogCurveFit(inset_ax, np.logspace(2, 4, base=10)) # 10^2 to 10^4 

x_arr = np.array([200., 1000., 5000., 10000.])
data_dict = {
  "LPG": {
    "data": np.array([2.55, 1.5, 0.9, 0.74]),
    "line_props": {
      "color": "blue",
      "linestyle": "-"
    },
    "point_props": {
      "color": "#0000aa",
      "marker":"D",
    }
  },
  "CH4": {
    "data": np.array([1.74, 1, 0.56, 0.44]),
    "line_props": {
      "color": "red",
      "linestyle": "-"
    },
    "point_props": {
      "color": "#aa0000",
      "marker":"s"
    }
  }
}

for name, props in data_dict.items():
  opt_params = loglog_curve_fit.calc_opt_params(x_arr, props['data'])

  kwargs = {
    **props["line_props"],
    "linewidth": 0.5,
    "label": "%s (a=%f, b=%f)" % ((name,) + tuple(opt_params))
  } 
  loglog_curve_fit.plot_fitting_line(opt_params, **kwargs)
  
  kwargs = {
    **props["point_props"],
    "label": name
  } 
  loglog_curve_fit.plot_data(x_arr, props['data'], **kwargs)

inset_ax.legend(loc='lower right')
plt.show()