"""T07 generator: sine-wave WAV of a seeded duration."""
import math
import random
import struct
import wave
from pathlib import Path


def make(out: Path, seed: int, name: str = 'ton.wav') -> Path:
    rnd = random.Random(seed)
    dur, freq, rate = round(rnd.uniform(1.5, 6.0), 2), rnd.choice([220, 440, 880]), 22050
    out.mkdir(parents=True, exist_ok=True)
    p = out / name
    with wave.open(str(p), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(b''.join(struct.pack('<h', int(12000 * math.sin(2 * math.pi * freq * i / rate))) for i in range(int(dur * rate))))
    return p


def duration(p: Path) -> float:
    with wave.open(str(p)) as w:
        return w.getnframes() / w.getframerate()


def visible(out: Path):
    make(out, 1)
