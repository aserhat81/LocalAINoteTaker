import io
import struct
import threading
import time
import wave

import pyaudiowpatch as pyaudio
from PySide6.QtCore import QObject, Signal


class AudioCaptureManager(QObject):
    chunk_ready = Signal(bytes, str)  # (wav_bytes, source_label)
    audio_level = Signal(int)         # 0 - 100

    SILENCE_EMIT_SECONDS = 1.6
    MAX_SPEECH_CHUNK_SECONDS = 22.0
    IDLE_RESET_SECONDS = 4.0
    VAD_LEVEL_THRESHOLD = 4
    MIC_ECHO_GATE_LEVEL = 6
    SYS_ACTIVE_LEVEL = 12
    MIN_VOICED_FRAMES = 4

    def __init__(self):
        super().__init__()
        self.p = pyaudio.PyAudio()
        self.is_recording = False
        self.mic_stream = None
        self.sys_stream = None
        self.record_thread = None
        self.current_sys_level = 0
        self.last_sys_level_time = 0
        self.threads = []

    def get_input_devices(self):
        devices = []
        try:
            for i in range(self.p.get_device_count()):
                dev = self.p.get_device_info_by_index(i)
                if dev.get("maxInputChannels", 0) > 0 and not dev.get("isLoopbackDevice", False):
                    devices.append({"index": i, "name": dev["name"]})
        except Exception as e:
            print(f"Error getting input devices: {e}")
        return devices

    def get_default_loopback_device(self):
        try:
            return self.p.get_default_wasapi_loopback()
        except OSError:
            return None

    def get_loopback_devices(self):
        devices = []
        try:
            for i in range(self.p.get_device_count()):
                dev = self.p.get_device_info_by_index(i)
                if dev.get("isLoopbackDevice", False):
                    devices.append({"index": i, "name": dev["name"]})
        except Exception as e:
            print(f"Error getting loopback devices: {e}")
        return devices

    def get_default_mic_device(self):
        try:
            return self.p.get_default_input_device_info()
        except OSError:
            return None

    def start_recording(self, mode="online", mic_index=None, sys_index=None):
        if self.is_recording:
            return

        self.is_recording = True
        self.mode = mode
        self.current_sys_level = 0
        self.last_sys_level_time = 0

        sys_info = None
        if sys_index is not None:
            try:
                sys_info = self.p.get_device_info_by_index(sys_index)
            except Exception:
                sys_info = self.get_default_loopback_device()
        else:
            sys_info = self.get_default_loopback_device()

        mic_info = None
        if mic_index is not None:
            try:
                mic_info = self.p.get_device_info_by_index(mic_index)
            except Exception:
                mic_info = self.get_default_mic_device()
        else:
            mic_info = self.get_default_mic_device()

        chunk_size = 4096
        fmt = pyaudio.paInt16

        mic_rate = None
        mic_channels = None
        if mic_info:
            try:
                rates_to_try = [int(mic_info["defaultSampleRate"]), 44100, 48000, 16000]
                channels_to_try = [max(1, int(mic_info["maxInputChannels"])), 1, 2]

                opened = False
                for rate in rates_to_try:
                    if opened:
                        break
                    for channels in channels_to_try:
                        try:
                            self.mic_stream = self.p.open(
                                format=fmt,
                                channels=channels,
                                rate=rate,
                                input=True,
                                input_device_index=mic_info["index"],
                                frames_per_buffer=chunk_size,
                            )
                            mic_rate = rate
                            mic_channels = channels
                            opened = True
                            break
                        except Exception:
                            continue

                if not opened:
                    print(f"Could not open mic stream for {mic_info['name']}")
                    self.mic_stream = None
            except Exception as e:
                print(f"Error initializing mic stream search: {e}")
                self.mic_stream = None

        sys_rate = None
        sys_channels = None
        if self.mode == "online" and sys_info:
            try:
                sys_rate = int(sys_info["defaultSampleRate"])
                sys_channels = sys_info["maxInputChannels"]
                self.sys_stream = self.p.open(
                    format=fmt,
                    channels=sys_channels,
                    rate=sys_rate,
                    input=True,
                    input_device_index=sys_info["index"],
                    frames_per_buffer=chunk_size,
                )
            except Exception as e:
                print(f"Error opening sys stream: {e}")
                try:
                    self.sys_stream = self.p.open(
                        format=fmt,
                        channels=2,
                        rate=44100,
                        input=True,
                        input_device_index=sys_info["index"],
                        frames_per_buffer=chunk_size,
                    )
                    sys_rate = 44100
                    sys_channels = 2
                except Exception:
                    self.sys_stream = None

        self.threads = []
        if self.mic_stream:
            t_mic = threading.Thread(
                target=self._mic_record_loop,
                args=(self.mic_stream, mic_rate, mic_channels),
                daemon=True,
            )
            t_mic.start()
            self.threads.append(t_mic)

        if self.sys_stream:
            t_sys = threading.Thread(
                target=self._sys_record_loop,
                args=(self.sys_stream, sys_rate, sys_channels),
                daemon=True,
            )
            t_sys.start()
            self.threads.append(t_sys)

    def stop_recording(self):
        self.is_recording = False

        for thread in getattr(self, "threads", []):
            thread.join(timeout=1.0)
        self.threads = []

        if self.mic_stream:
            try:
                self.mic_stream.stop_stream()
                self.mic_stream.close()
            except Exception:
                pass
            self.mic_stream = None

        if self.sys_stream:
            try:
                self.sys_stream.stop_stream()
                self.sys_stream.close()
            except Exception:
                pass
            self.sys_stream = None

        self.audio_level.emit(0)

    def _calculate_level(self, data):
        try:
            count = len(data) // 2
            if count == 0:
                return 0
            shorts = struct.unpack(f"<{count}h", data)
            peak = max(abs(s) for s in shorts)
            if peak > 0:
                return min(100, max(0, int((peak / 10000.0) * 100)))
            return 0
        except Exception:
            return 0

    def _mic_record_loop(self, stream, rate, channels):
        chunk_size = 4096
        fmt = pyaudio.paInt16
        frames = []
        last_ui_update = time.time()
        max_chunk_level = 0
        is_speaking = False
        last_speech_time = time.time()
        chunk_start_time = time.time()
        voiced_frames = 0

        while self.is_recording and stream and stream.is_active():
            try:
                if stream.get_read_available() < chunk_size:
                    time.sleep(0.01)
                    continue

                data = stream.read(chunk_size, exception_on_overflow=False)
                raw_level = self._calculate_level(data)

                sys_lvl = getattr(self, "current_sys_level", 0)
                sys_time = getattr(self, "last_sys_level_time", 0)
                now = time.time()
                if now - sys_time > 0.3:
                    sys_lvl = 0

                # Speaker leakage'ini bastir, ama kullanicinin ustune konusmasini koru.
                if sys_lvl >= self.SYS_ACTIVE_LEVEL and raw_level <= self.MIC_ECHO_GATE_LEVEL:
                    data = b"\x00" * len(data)

                frames.append(data)
                level = self._calculate_level(data)

                if level >= self.VAD_LEVEL_THRESHOLD:
                    voiced_frames += 1
                    if not is_speaking:
                        is_speaking = True
                        if len(frames) == 1:
                            chunk_start_time = now
                    last_speech_time = now

                if level > max_chunk_level:
                    max_chunk_level = level

                if now - last_ui_update >= 0.1:
                    self.audio_level.emit(level)
                    last_ui_update = now

                chunk_duration = now - chunk_start_time
                silence_duration = now - last_speech_time

                if not is_speaking and chunk_duration > self.IDLE_RESET_SECONDS:
                    frames.clear()
                    max_chunk_level = 0
                    voiced_frames = 0
                    chunk_start_time = now
                    last_speech_time = now
                    continue

                should_emit = False
                if is_speaking and silence_duration >= self.SILENCE_EMIT_SECONDS:
                    should_emit = True
                elif is_speaking and chunk_duration >= self.MAX_SPEECH_CHUNK_SECONDS:
                    should_emit = True

                if should_emit:
                    if (
                        frames
                        and max_chunk_level >= self.VAD_LEVEL_THRESHOLD
                        and voiced_frames >= self.MIN_VOICED_FRAMES
                    ):
                        wav_bytes = self._frames_to_wav(
                            frames,
                            channels,
                            self.p.get_sample_size(fmt),
                            rate,
                        )
                        self.chunk_ready.emit(wav_bytes, "BEN")
                    frames.clear()
                    max_chunk_level = 0
                    voiced_frames = 0
                    is_speaking = False
                    chunk_start_time = now
                    last_speech_time = now

            except Exception:
                time.sleep(0.1)

        if (
            frames
            and max_chunk_level >= self.VAD_LEVEL_THRESHOLD
            and voiced_frames >= self.MIN_VOICED_FRAMES
        ):
            wav_bytes = self._frames_to_wav(
                frames,
                channels,
                self.p.get_sample_size(fmt),
                rate,
            )
            self.chunk_ready.emit(wav_bytes, "BEN")

    def _sys_record_loop(self, stream, rate, channels):
        chunk_size = 4096
        fmt = pyaudio.paInt16
        frames = []
        max_chunk_level = 0
        is_speaking = False
        last_speech_time = time.time()
        chunk_start_time = time.time()

        while self.is_recording and stream and stream.is_active():
            try:
                if stream.get_read_available() < chunk_size:
                    time.sleep(0.01)
                    continue

                data = stream.read(chunk_size, exception_on_overflow=False)
                level = self._calculate_level(data)
                self.current_sys_level = level
                now = time.time()
                self.last_sys_level_time = now

                if level >= self.VAD_LEVEL_THRESHOLD:
                    if not is_speaking:
                        is_speaking = True
                        if len(frames) == 0:
                            chunk_start_time = now
                    last_speech_time = now

                if level > max_chunk_level:
                    max_chunk_level = level

                frames.append(data)
                chunk_duration = now - chunk_start_time
                silence_duration = now - last_speech_time

                if not is_speaking and chunk_duration > self.IDLE_RESET_SECONDS:
                    frames.clear()
                    max_chunk_level = 0
                    chunk_start_time = now
                    last_speech_time = now
                    continue

                should_emit = False
                if is_speaking and silence_duration >= self.SILENCE_EMIT_SECONDS:
                    should_emit = True
                elif is_speaking and chunk_duration >= self.MAX_SPEECH_CHUNK_SECONDS:
                    should_emit = True

                if should_emit:
                    if frames and max_chunk_level >= self.VAD_LEVEL_THRESHOLD:
                        wav_bytes = self._frames_to_wav(
                            frames,
                            channels,
                            self.p.get_sample_size(fmt),
                            rate,
                        )
                        self.chunk_ready.emit(wav_bytes, "DIGER")
                    frames.clear()
                    max_chunk_level = 0
                    is_speaking = False
                    chunk_start_time = now
                    last_speech_time = now

            except Exception:
                time.sleep(0.1)

        if frames and max_chunk_level >= self.VAD_LEVEL_THRESHOLD:
            wav_bytes = self._frames_to_wav(
                frames,
                channels,
                self.p.get_sample_size(fmt),
                rate,
            )
            self.chunk_ready.emit(wav_bytes, "DIGER")

    def _frames_to_wav(self, frames, channels, sample_width, rate):
        wav_io = io.BytesIO()
        wf = wave.open(wav_io, "wb")
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(b"".join(frames))
        wf.close()
        return wav_io.getvalue()
