/* MA-HOME HQ — AudioWorklet: Mikrofon (beliebige Abtastrate) -> 16 kHz Mono, Bloecke zu 512 Samples (Silero-VAD-Rahmen).
   Box-Tiefpass (Breite ~ Verhaeltnis) + lineare Interpolation; reicht fuer Sprache (Wakeword/VAD/Whisper arbeiten mit 16 kHz). */
class Pcm16k extends AudioWorkletProcessor {
  constructor() {
    super();
    this.ratio = sampleRate / 16000;
    this.box = Math.max(1, Math.round(this.ratio));
    this.hist = new Float32Array(this.box);      // gleitender Mittelwert
    this.hi = 0; this.hsum = 0;
    this.prev = 0; this.pos = 0;                 // Position des naechsten Ausgabesamples relativ zum aktuellen Eingabeindex
    this.out = new Float32Array(512); this.n = 0;
    this.on = true;
    this.port.onmessage = e => { if (e.data && e.data.cmd === 'pause') this.on = !e.data.value; };
  }
  process(inputs) {
    const ch = inputs[0] && inputs[0][0];
    if (!ch) return true;
    for (let i = 0; i < ch.length; i++) {
      // gleitender Mittelwert ueber `box` Samples
      this.hsum += ch[i] - this.hist[this.hi]; this.hist[this.hi] = ch[i]; this.hi = (this.hi + 1) % this.box;
      const cur = this.hsum / this.box;
      // alle Ausgabepunkte zwischen prev (t=-1) und cur (t=0) erzeugen
      while (this.pos <= 1) {
        const v = this.prev + (cur - this.prev) * this.pos;
        this.out[this.n++] = v;
        if (this.n === 512) { if (this.on) this.port.postMessage(this.out.slice(0)); this.n = 0; }
        this.pos += this.ratio;
      }
      this.pos -= 1; this.prev = cur;
    }
    return true;
  }
}
registerProcessor('pcm16k', Pcm16k);
