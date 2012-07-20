# PulseAudioSpectrogram.py
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


import spectrogram

import math
import cairo
from gi.repository import Gtk, Gdk, GObject

class SpectrogramWidget(Gtk.DrawingArea):
  def __init__(self):
    Gtk.DrawingArea.__init__(self)
    self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 1024, 512)
    self.red_dB_offset = 0
    self.red_dB_max = 18
    #self.bufLabel = Gtk.Label()
    self.sourceLabel = Gtk.Label()
    self.press_x = -1
    self.press_y = -1

    self.connect("button-press-event", self.on_mouse_press_event)
    self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)

    spectrogram.connect()

    self.sourceLabel.set_label(spectrogram.source_name())

    self.set_size_request(1024 + 20, 512 + 20)

    self.connect("draw", self.on_draw)

    pass # def __init__

  def setRedDBMax(self, value):
    self.red_dB_max = value
    pass # def setRedDBMax

  def setRedDBOffset(self, value):
    self.red_dB_offset = value
    pass # def setRedDBOffset

  def on_mouse_press_event(self, widget, event):
    self.press_x, self.press_y = event.get_coords()
    self.get_window().invalidate_rect(self.get_allocation(), True)
    pass # def on_mouse_press_event

  def timeout(self):
    my_cr = cairo.Context(self.surface)

    my_cr.set_source_surface(self.surface, -1, 0)
    my_cr.rectangle(0, 0, 1024, 512)
    my_cr.fill()

    self.draw_fft(my_cr, spectrogram.read())

    self.get_window().invalidate_rect(self.get_allocation(), True)
    self.get_window().process_updates(True)

    #self.bufLabel.set_label(str(round(float(spectrogram.buf_ready()) / float(44100), 2)))

    pass # def timeout

  def on_draw(self, widget, cr):
    w = self.get_allocated_width()
    h = self.get_allocated_height()

    cr.set_source_surface(self.surface, 0, 0)
    cr.rectangle(0, 0, w, h)
    cr.fill()

    self.draw_ruler(cr)

    pass # def on_draw

  def draw_fft(self, cr, fft):

    for i in range(0, len(fft)):
      audio_dB = -80

      if fft[i] > 0:
        audio_dB = 10 * math.log10(fft[i])
        audio_dB += self.red_dB_offset

      # Color
      cr.set_source_rgb(audio_dB / self.red_dB_max, 0, 0)

      # Dot
      cr.rectangle(1024 - 1, 512 - (i+1) * 512 / len(fft), 1, 512/len(fft))
      cr.fill()
      pass # for i in range(0, len(fft))

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

class PulseSpectrogram(Gtk.Window):

  def __init__(self):
    Gtk.Window.__init__(self, title="PulseAudioSpectrogram")

    self.running = False
    self.spec = SpectrogramWidget()

    self.button = Gtk.Button(label="Start")
    self.button.connect("clicked", self.on_button_clicked)

    self.scaleMax = Gtk.HScale()
    self.scaleMax.set_value_pos(1)#Gtk.GTK_POS_LEFT)
    self.scaleMax.set_digits(0)
    self.scaleMax.set_size_request(200, 20)
    self.scaleMax.set_adjustment(Gtk.Adjustment(20, 1, 100, 1, 10, 0))
    self.scaleMax.set_increments(0.5, 5)
    self.scaleMax.connect(
      "value-changed",
      self.on_scale_value_changed,
      self.spec.setRedDBMax
    )

    self.scaleOffset = Gtk.HScale()
    self.scaleOffset.set_value_pos(1)#Gtk.GTK_POS_LEFT)
    self.scaleOffset.set_digits(0)
    self.scaleOffset.set_size_request(200, 20)
    self.scaleOffset.set_adjustment(Gtk.Adjustment(0, -80, 80, 1, 10, 1))
    self.scaleOffset.set_increments(0.5, 5)
    self.scaleOffset.connect(
      "value-changed",
      self.on_scale_value_changed,
      self.spec.setRedDBOffset
    )

    box = Gtk.Box(spacing=6)
    box.add(Gtk.Label("Offset dB"))
    box.add(self.scaleOffset)
    box.add(Gtk.Label("Max dB"))
    box.add(self.scaleMax)
    box.add(self.button)
    box.add(self.spec.sourceLabel)

    vbox = Gtk.VBox(spacing=6)
    vbox.pack_start(self.spec, True, True, 0)
    vbox.pack_start(box, False, False, 0)

    self.add(vbox)

    pass # def __init__

  def on_scale_value_changed(self, widget, setScale):
    setScale(widget.get_value())

  def on_button_clicked(self, widget):
    if self.running:
      self.button.set_label("Start")
      self.running = False
    else:
      self.button.set_label("Stop")
      GObject.timeout_add(25, self.on_timeout)
      self.running = True
    pass # def on_button_clicked

  def on_timeout(self):
    self.spec.timeout()
    return self.running

  pass # class PulseSpectrogram

if __name__ == "__main__":
  win = PulseSpectrogram()
  win.connect("delete-event", Gtk.main_quit)
  win.show_all()
  Gtk.main()
  

