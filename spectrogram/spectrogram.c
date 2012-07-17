/* vi: et sw=2 fileencoding=utf8
 *
 * Copyright 2012 Harry Karvonen
 *
 * This file is part of PulseAudioSpectrogram.
 *
 * PulseAudioSpectrogram is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * PulseAudioSpectrogram is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with PulseAudioSpectrogram. If not, see <http://www.gnu.org/licenses/>.
 */

#include <Python.h>

#include <pulse/pulseaudio.h>
#include <fftw3.h>
#include <math.h>

#include <string.h>
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>

// 44100 * 20
#define BUF_SIZE 882000

// Sample buffers
static int n_samples = 0;
static double *fft_buf = 0;
static int16_t *buf = 0;
static uint32_t buf_w_index = 0;
static uint32_t buf_r_index = 0;
static uint32_t buf_ready = 0;

// For Pulseaudio
static const char *source_name = 0;
static const pa_source_info *source_info = 0;
static pa_threaded_mainloop *mainloop = 0;
static pa_mainloop_api *mainloop_api = 0;
static pa_context *context = 0;
static pa_stream *stream = 0;
static pa_proplist *proplist = 0;

static pa_sample_spec sample_spec = {
  .format = PA_SAMPLE_S16LE,
  .rate = 44100,
  .channels = 2
};

static void quit(const char* source)
{
  fprintf(stderr, "%s\n", source);

  if (mainloop_api) {
    mainloop_api->quit(mainloop_api, 0);
  }
}

static void get_source_info_cb(
        pa_context *c,
        const pa_source_info *info,
        int is_last,
        void *userdata
) {
  if (is_last || info->monitor_of_sink == PA_INVALID_INDEX) {
    source_info = 0;
    pa_threaded_mainloop_signal(mainloop, 0);
    return;
  }

  source_info = info;

  pa_threaded_mainloop_signal(mainloop, 1);
}

static void stream_state_cb(
        pa_stream *s,
        void *userdata
) {
  switch (pa_stream_get_state(s)) {
    case PA_STREAM_READY:
    case PA_STREAM_FAILED:
    case PA_STREAM_TERMINATED:
      pa_threaded_mainloop_signal(mainloop, 0);
      break;

    case PA_STREAM_UNCONNECTED:
    case PA_STREAM_CREATING:
      break;
  }
}

static void stream_success_cb(
        pa_stream *s,
        int success,
        void *userdata
) {
  pa_threaded_mainloop_signal(mainloop, 0);
}

static void stream_read_cb(
        pa_stream *s,
        size_t length,
        void *userdata
) {
  const void *data = 0;
  const int16_t *signal = 0;
  size_t peeked = 0;
  size_t i = 0;

  if (pa_stream_peek(s, &data, &peeked)) {
    quit("pa_stream_peek");
    return;
  }

  signal = (int16_t*)data;

  /* Length is in bytes, one sample is 2 bytes and data contains 2 channels */
  for (i = 0; i < peeked / 4; i++) {
    // FIXME what if buffer is full?
    buf[buf_w_index] = signal[i*2] / 2 + signal[i*2 + 1] / 2;

    buf_w_index = (buf_w_index + 1) % BUF_SIZE;
    buf_ready++;
  }

  pa_stream_drop(s);
}

static void context_state_cb(
        pa_context *c,
        void *userdata
) {
  pa_context_state_t state = pa_context_get_state(c);

  switch (state) {
    case PA_CONTEXT_CONNECTING:
    case PA_CONTEXT_AUTHORIZING:
    case PA_CONTEXT_SETTING_NAME:
      break;
    case PA_CONTEXT_READY:
      pa_threaded_mainloop_signal(mainloop, 0);
      break;

    case PA_CONTEXT_TERMINATED:
      quit("context_state_cb TERMINATED");
      pa_threaded_mainloop_signal(mainloop, 0);
      break;

    case PA_CONTEXT_FAILED:
      quit("context_state_cb FAILED");
      pa_threaded_mainloop_signal(mainloop, 0);
      break;

    default:
      quit("context_state_cb UNKNOWN");
  }
}

void pulse_stop()
{
  free(fft_buf);
  free(buf);

  pa_threaded_mainloop_stop(mainloop);
}

int pulse_connect()
{
  // Setup sample buffers
  fft_buf = (double*) malloc(sizeof(double) * n_samples);
  buf = (int16_t*)malloc(sizeof(int16_t) * BUF_SIZE);
  buf_r_index = 0;
  buf_w_index = 0;
  buf_ready = 0;

  memset(buf, 0, BUF_SIZE);

  // Setup Pulseaudio
  mainloop = pa_threaded_mainloop_new();

  if (!mainloop) {
    quit("pa_threaded_mainloop_new");
    return -1;
  }

  mainloop_api = pa_threaded_mainloop_get_api(mainloop);

  if (pa_signal_init(mainloop_api)) {
    quit("pa_signal_init");
    return -2;
  }

  proplist = pa_proplist_new();

  pa_proplist_sets(proplist, "media.role", "event");

  context = pa_context_new_with_proplist(
    mainloop_api,
    "PulseSpectrogram",
    proplist
  );

  if (!context) {
    quit("pa_conext_new_with_proplist");
    return -3;
  }

  pa_context_set_state_callback(
    context,
    context_state_cb,
    0
  );

  pa_context_connect(context, 0, 0, 0);

  pa_threaded_mainloop_lock(mainloop);

  pa_threaded_mainloop_start(mainloop);

  // Wait for connection
  pa_threaded_mainloop_wait(mainloop);

  if (pa_context_get_state(context) != PA_CONTEXT_READY) {
    quit("pa_context_get_state");
    return -4;
  }

  stream = pa_stream_new(context, "PulseSpectrogram", &sample_spec, 0);

  if (!stream) {
    quit("pa_stream_new");
    return -5;
  }

  pa_stream_set_state_callback(stream, stream_state_cb, 0);
  pa_stream_set_read_callback(stream, stream_read_cb, 0);

  pa_operation *o = 0;
  o = pa_context_get_source_info_list(context, get_source_info_cb, 0);

  while (pa_operation_get_state(o) == PA_OPERATION_RUNNING) {
    pa_threaded_mainloop_wait(mainloop);

    if (source_info) {
      if (!source_name) {
        source_name = pa_xstrdup(source_info->name);
      }

      pa_threaded_mainloop_accept(mainloop);
    }
  }

  pa_operation_unref(o);

  if (pa_stream_connect_record(stream, source_name, 0, 0)) {
    quit("pa_stream_connect_record");
    return -6;
  }

  pa_threaded_mainloop_wait(mainloop);

  if (pa_stream_get_state(stream) != PA_STREAM_READY) {
    quit("pa_stream_get_state");
    return -7;
  }

  pa_threaded_mainloop_unlock(mainloop);

  return 0;
}

double *pulse_read()
{
  pa_operation *o = 0;

  pa_threaded_mainloop_lock(mainloop);

  o = pa_stream_update_timing_info(stream, stream_success_cb, 0);

  while (pa_operation_get_state(o) == PA_OPERATION_RUNNING) {
    pa_threaded_mainloop_wait(mainloop);
  }

  pa_operation_unref(o);

  const pa_timing_info* t = pa_stream_get_timing_info(stream);

  if (t) {
    buf_ready = (uint32_t)((double)44.1 * (double)(t->sink_usec / 1000));
    buf_r_index = buf_w_index - buf_ready;
    buf_r_index %= BUF_SIZE;
  }

  pa_threaded_mainloop_unlock(mainloop);

  double *signal = 0;
  fftw_complex *cpx = 0;
  fftw_plan fft;
  uint32_t i = 0;
  uint32_t window_size;

  memset(fft_buf, 0, n_samples);

  // 25ms
  window_size = 1103; //MIN(MAX(buf_ready / 40, n_samples * 2), 1200);

  signal = (double*) malloc(sizeof(double) * window_size);
  cpx = (fftw_complex*) fftw_malloc(sizeof(fftw_complex) * window_size);

  //printf("window: %6d, bufferlen: %d samples, %f seconds\n", window_size, buf_ready, (double)buf_ready/44100);

  for (i = 0; i < window_size; i++) {
    if (buf_ready > 0) {
      signal[i] = (double)buf[buf_r_index] / (double)((uint16_t)-1);
      signal[i] *=  0.54 - 0.46 * cos(2 * M_PI * i / (window_size - 1));

      buf_r_index = (buf_r_index + 1) % BUF_SIZE;
      buf_ready--;
    } else {
      signal[i] = 0;
    }
  }

  fft = fftw_plan_dft_r2c_1d(n_samples * 2, signal, cpx, FFTW_ESTIMATE);

  fftw_execute(fft);

  for (i = 0; i < n_samples; i++) {
    fft_buf[i] = sqrt(pow(cpx[i][0], 2) + pow(cpx[i][1], 2));
  }

  fftw_destroy_plan(fft);
  fftw_free(cpx);

  free(signal);

  return fft_buf;
}

int pulse_buf_ready()
{
  return buf_ready;
}

const char * pulse_source_name()
{
  return source_name;
}

/*
 */

static PyObject *SpectrogramError;

static PyObject * spectrogram_buf_ready(PyObject *self, PyObject *args)
{
  return Py_BuildValue("i", pulse_buf_ready());
}

static PyObject * spectrogram_source_name(PyObject *self, PyObject *args)
{
  return Py_BuildValue("s", pulse_source_name());
}

static PyObject * spectrogram_read(PyObject *self, PyObject *args)
{
  PyObject *res;

  res = PyTuple_New( n_samples );

  double *m = pulse_read();

  int i;
  for ( i = 0; i < n_samples; i++ )
    PyTuple_SetItem( res, i, PyFloat_FromDouble( m[ i ] ) );

  return res;
}

static PyObject * spectrogram_connect(PyObject *self, PyObject *args)
{
  if (!PyArg_ParseTuple(args, "i", &n_samples)) {
    n_samples = 512;
  }

  int ret = pulse_connect();

  if (ret) {
    PyErr_SetString(SpectrogramError, "Virhe");
    return 0;
  }

  Py_RETURN_NONE;
}

static PyMethodDef SpectrogramMethods[ ] = {
  {"buf_ready",
   spectrogram_buf_ready,
   0,
   "Returns readed samples in buffer"},
  {"source_name",
   spectrogram_source_name,
   0,
   "Returns Pulseaudio source name."},
  {"read",
   spectrogram_read,
   0,
   "Read data from Pulseaudio. returns abs(fft(s))"},
  {"connect",
   spectrogram_connect,
   METH_VARARGS,
   "Connect to Pulseaudio"},
  {0, 0, 0, 0}
};

PyMODINIT_FUNC initspectrogram ( void ) {
  PyObject *m;

  m = Py_InitModule("spectrogram", SpectrogramMethods);

  if (m == NULL)
    return;

  SpectrogramError = PyErr_NewException( "spectrogram.error", NULL, NULL );
  Py_INCREF(SpectrogramError);
  PyModule_AddObject(m, "error", SpectrogramError);

  Py_AtExit(&pulse_stop);

  return;
}

