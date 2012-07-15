# vi: et sw=2 fileencoding=utf8

from distutils.core import setup, Extension

import commands

def pkgconfig(packages, **kw):
  flag_map = {'-I': 'include_dirs', '-L': 'library_dirs', '-l': 'libraries'}
  for token in commands.getoutput(
        "pkg-config --libs --cflags %s" % ' '.join(packages)
  ).split():
    if flag_map.has_key(token[:2]):
      kw.setdefault(flag_map.get(token[:2]), []).append(token[2:])
    else: # throw others to extra_link_args
      kw.setdefault('extra_link_args', []).append(token)

  for k, v in kw.iteritems(): # remove duplicated
    kw[k] = list(set(v))
  return kw

module = Extension(
  "spectrogram",
  sources = ["spectrogram.c"],
  **pkgconfig(("fftw3", "libpulse",))
)


setup(
  name = "Spectrogram",
  version = "0.1",
  ext_modules = [module],
)
