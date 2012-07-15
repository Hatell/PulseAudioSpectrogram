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
from gi.repository import Gtk, GObject

class SpectrogramWidget(Gtk.DrawingArea):
  def __init__(self):
    Gtk.DrawingArea.__init__(self)
    self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 1024, 512)
    self.running = False
    self.red_dB_offset = 0
    self.red_dB_max = 18
    #self.bufLabel = Gtk.Label()

    spectrogram.connect()

    self.set_size_request(1024, 512)

    self.connect("draw", self.on_draw)

    pass # def __init__

  def isRunning(self):
     return self.running
     pass # def running

  def start(self):
    self.running = True
    GObject.timeout_add(25, self.on_timeout)
    pass # def start

  def stop(self):
    self.running = False
    pass # def stop

  def on_timeout(self):
    my_cr = cairo.Context(self.surface)

    my_cr.set_source_surface(self.surface, -1, 0)
    my_cr.rectangle(0, 0, 1024, 512)
    my_cr.fill()

    if spectrogram.buf_ready() > 44100 * 2.5:
      spectrogram.flush()

    self.draw_fft(my_cr, spectrogram.read())

    self.get_window().invalidate_rect(self.get_allocation(), True)
    self.get_window().process_updates(True)

    #self.bufLabel.set_label(str(round(float(spectrogram.buf_ready()) / float(44100), 2)))

    return self.running
    pass # def on_timeout

  def on_draw(self, widget, cr):
    w = self.get_allocated_width()
    h = self.get_allocated_height()

    cr.set_source_surface(self.surface, 0, 0)
    cr.rectangle(0, 0, w, h)
    cr.fill()

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

  pass # class SpectrogramWidget

class PulseSpectrogram(Gtk.Window):

  def __init__(self):
    Gtk.Window.__init__(self, title="PulseAudioSpectrogram")

    self.spec = SpectrogramWidget()

    self.button = Gtk.Button(label="Start")
    self.button.connect("clicked", self.on_button_clicked)

    self.spin = Gtk.SpinButton()
    self.spin.set_adjustment(Gtk.Adjustment(20, 0, 100, 1, 10, 0))
    self.spin.connect("value-changed", self.on_spin_value_changed)

    self.spinOffset = Gtk.SpinButton()
    self.spinOffset.set_adjustment(Gtk.Adjustment(0, -80, 80, 1, 10, 0))
    self.spinOffset.connect("value-changed", self.on_spinOffset_value_changed)

    box = Gtk.Box(spacing=6)
    box.add(Gtk.Label("Offset dB"))
    box.add(self.spinOffset)
    box.add(Gtk.Label("Max dB"))
    box.add(self.spin)
    box.add(self.button)
    #box.add(self.spec.bufLabel)

    vbox = Gtk.VBox(spacing=6)
    vbox.pack_start(self.spec, True, True, 0)
    vbox.pack_start(box, False, False, 0)

    self.add(vbox)

    pass # def __init__

  def on_spinOffset_value_changed(self, widget):
    self.spec.red_dB_offset = widget.get_value()

  def on_spin_value_changed(self, widget):
    self.spec.red_dB_max = widget.get_value()

  def on_button_clicked(self, widget):
    if self.spec.isRunning():
      self.button.set_label("Start")
      self.spec.stop()
    else:
      self.button.set_label("Stop")
      self.spec.start()
    pass # def on_button_clicked

  pass # class PulseSpectrogram

if __name__ == "__main__":
  win = PulseSpectrogram()
  win.connect("delete-event", Gtk.main_quit)
  win.show_all()
  Gtk.main()
  

