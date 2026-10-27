"""Local CPU speech-to-text; input audio stays local. Called only on demand."""
import os,sys,pathlib
os.environ.setdefault('HF_HUB_DISABLE_XET','1')
from faster_whisper import WhisperModel
root=pathlib.Path(__file__).resolve().parent
model=WhisperModel('base',device='cpu',compute_type='int8',cpu_threads=2,num_workers=1,download_root=str(root/'models/whisper'))
segments,info=model.transcribe(sys.argv[1],language='de',beam_size=3,vad_filter=True)
text=' '.join(s.text.strip() for s in segments).strip()
if not text:raise SystemExit('No speech detected')
pathlib.Path(sys.argv[2]).write_text(text,encoding='utf-8')
