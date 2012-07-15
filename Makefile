
.PHONY: clean

all: spectrogram.so

spectrogram.so: spectrogram-compile
	ln -s spectrogram/build/lib*/spectrogram.so

spectrogram-compile:
	$(MAKE) -C spectrogram

clean:
	$(MAKE) -C spectrogram clean
	$(RM) spectrogram.so
