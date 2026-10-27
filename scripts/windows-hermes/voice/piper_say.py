"""TTS command provider for Hermes: piper_say.py INPUT_TXT OUTPUT_WAV  (lokal, Piper Thorsten emotional medium, Sprecher 0, Datensatz CC0)."""
import sys, os, wave
from piper import PiperVoice, SynthesisConfig
here = os.path.dirname(os.path.abspath(__file__))
v = PiperVoice.load(os.path.join(here, "models", "de_DE-thorsten_emotional-medium.onnx"))
text = open(sys.argv[1], encoding="utf-8").read()
with wave.open(sys.argv[2], "wb") as w:
    v.synthesize_wav(text, w, syn_config=SynthesisConfig(speaker_id=0))
