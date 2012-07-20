# FFTWidget.py
# vi: et sw=2 fileencoding=utf8
#
# Copyright 2012 Harry Karvonen
#
# This file is part of PulseAudioSpectrogram.
#
# PulseAudioSpectrogram is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PulseAudioSpectrogram is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PulseAudioSpectrogram.  If not, see <http://www.gnu.org/licenses/>.


import math
import cairo
from gi.repository import Gtk, Gdk, GObject

class FFTWidget(Gtk.DrawingArea):
  def __init__(self):
    Gtk.DrawingArea.__init__(self)
    self.avg = None
    self.dB_offset = 0
    self.dB_max = 20
    self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 1024, 512)

    self.set_size_request(1024, 512)

    self.connect("draw", self.on_draw)

    pass # def __init__

  def setDBMax(self, value):
    self.dB_max = value
    pass

  def setDBOffset(self, value):
    self.dB_offset = value
    pass

  def timeout(self, fft_data):
    if self.avg is None:
      self.avg = fft_data
    else:
      self.avg = [(i + 2*j) / 3 for i, j in zip(self.avg, fft_data)]

    my_cr = cairo.Context(self.surface)

    my_cr.set_source_surface(self.surface, 0, 0)
    my_cr.rectangle(0, 0, 1024, 512)
    my_cr.fill()

    self.draw_fft(my_cr, self.avg)

    self.get_window().invalidate_rect(self.get_allocation(), True)
    self.get_window().process_updates(True)

    pass # def timeout

  def on_draw(self, widget, cr):
    w = self.get_allocated_width()
    h = self.get_allocated_height()

    cr.set_source_surface(self.surface, 0, 0)
    cr.rectangle(0, 0, w, h)
    cr.fill()

    pass # def on_draw

  def draw_fft(self, cr, fft):
    cr.set_source_rgba(0, 0, 0, 0.1)
    cr.rectangle(0, 0, 1024, 512)
    cr.fill()

    # Color
    cr.set_source_rgb(1, 0, 0)
    cr.set_line_width(0.5)

    for i in range(0, len(fft)):
      audio_y = -80

      if fft[i] > 0:
        audio_y = 10 * math.log10(fft[i]) * 20 / self.dB_max

      audio_y = 512 - audio_y - 200 - self.dB_offset

      if i == 0:
        cr.move_to(0, audio_y)
      else:
        cr.line_to((i+1) * 1024 / len(fft), audio_y)

      pass # for i in range(0, len(fft))

    cr.stroke()
    pass # def draw_fft

  def draw_ruler(self, cr):

    cr.set_source_rgb(1, 1, 1)
    cr.rectangle(1024, 0, 20, 532)
    cr.fill()

    cr.rectangle(0, 512, 1044, 20)
    cr.fill()

    cr.set_source_rgb(0, 0, 0)
    cr.move_to(1024, 0)
    cr.line_to(1024, 512)
    cr.line_to(0, 512)
    cr.stroke()

    cr.move_to(0, 531)
    cr.line_to(1043, 531)
    cr.line_to(1043, 0)
    cr.stroke()

    if -1 < self.press_y < 512 and -1 < self.press_x < 1024:
      fix_y = -2
      fix_x = -2

      Hz_str = "%d Hz" % int(float(512 - int(self.press_y)) * 22050.0 / 512.0)
      s_str = "%.2f s" % ((1023 - self.press_x) * 0.025)

      if self.press_y > 256:
        fix_y = cr.text_extents(Hz_str)[2] + 4

      if self.press_x > 512:
        fix_x = cr.text_extents(s_str)[2] + 4

      cr.move_to(1030, self.press_y - fix_y)
      cr.rotate(3.14 / 2)
      cr.show_text(Hz_str)

      cr.rotate(-3.14 / 2)
      cr.move_to(1024, self.press_y)
      cr.line_to(1044, self.press_y)
      cr.stroke()

      cr.move_to(self.press_x - fix_x, 526)
      cr.show_text(s_str)

      cr.move_to(self.press_x, 512)
      cr.line_to(self.press_x, 532)
      cr.stroke()

      cr.set_source_rgba(1, 1, 1, 0.2)
      cr.move_to(self.press_x, 0)
      cr.line_to(self.press_x, 511)
      cr.move_to(0, self.press_y)
      cr.line_to(self.press_x - 1, self.press_y)
      cr.move_to(self.press_x + 1, self.press_y)
      cr.line_to(1023, self.press_y)
      cr.stroke()

      pass # for i in range(0, 512)
    pass

  pass # class SpectrogramWidget

