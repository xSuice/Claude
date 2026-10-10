#requires -Version 5.1
<#
MA Auto Router V7 - automatische Modell-, Effort-, Kontext- und Workflow-Wahl, rein lokal.

Was der Installer tut (in dieser Reihenfolge, bei jedem Fehler VOR Schritt 5 bleibt alles unveraendert):
  1. Claude Code und Version pruefen.
  2. V7 in einem temporaeren Staging-Ordner aufbauen.
  3. `claude plugin validate --strict` auf dem Staging-Ordner.
  4. Vollstaendige Tests (`claude plugin test`, deterministisch, keine Modellanfragen, kein Login noetig).
  5. Nur bei Erfolg: Sicherung der bestehenden Installation (inkl. Lerndaten) nach
     %LOCALAPPDATA%\ma-auto-router-backups\<Zeitstempel>, dann V7 installieren.
  6. rollback.ps1 + rollback.json in der Sicherung ablegen.
Dieses Skript ersetzt NICHT die Datei install-model-router-v6.2.ps1. Andere Plugins und FixMyPrompt werden nicht angefasst.
Das PowerShell-Profil wird nur geaendert, wenn der Mod dort noch nicht eingetragen ist.
Lerndaten aus V6.x werden gelesen und uebernommen; die V6-Originale bleiben unveraendert.
Aufruf: powershell -ExecutionPolicy Bypass -File .\install-model-router-v7.ps1 [-VaultPath "D:\Obsidian\MeinVault"]
#>
param([string]$VaultPath = '')
$ErrorActionPreference = 'Stop'
function Write-Utf8([string]$Path, [string]$Text) {
    [IO.File]::WriteAllText($Path, $Text, (New-Object Text.UTF8Encoding $false))
}
$TargetModDir = Join-Path (Join-Path (Join-Path $env:USERPROFILE '.claude') 'mods') 'ma-auto-router'
$StageDir = Join-Path ([IO.Path]::GetTempPath()) ('ma-router-v7-' + [guid]::NewGuid().ToString('N'))
$ModDir = $StageDir
$PluginDir = Join-Path $ModDir '.claude-plugin'
$HooksDir = Join-Path $ModDir 'hooks'
$TestsDir = Join-Path $ModDir 'tests'
$preferred = Join-Path (Join-Path (Join-Path $env:USERPROFILE '.local') 'bin') 'claude.exe'
if (Test-Path -LiteralPath $preferred) { $RealClaude = $preferred }
else {
    $cmd = Get-Command claude -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $cmd) { throw 'Claude Code nicht gefunden.' }
    $RealClaude = $cmd.Source
}
$versionText = (& $RealClaude --version 2>&1 | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $versionText -notmatch '(\d+\.\d+\.\d+)') { throw 'Claude-Code-Version nicht lesbar.' }
$currentVersion = [version]$Matches[1]
if ($currentVersion -lt [version]'2.1.287') { throw 'Claude Code >= 2.1.287 erforderlich.' }
$installFiles = @('.claude-plugin/plugin.json', 'hooks/hooks.json', 'hooks/register.js', 'hooks/core.js', 'tests/router.test.ts')
$legacyFiles = @('tests/repair.test.ts')
$touchedFiles = $installFiles + $legacyFiles
$oldEnv = $env:CLAUDE_CODE_PLUGIN_DIRS
$Mutated = $false
$BackupDir = $null
try {
    New-Item -ItemType Directory -Force -Path $PluginDir, $HooksDir, $TestsDir | Out-Null
    Write-Utf8 (Join-Path $PluginDir 'plugin.json') @'
{ "name": "ma-auto-router", "version": "0.7.0", "description": "Local automatic model, effort and context router (V7): no extra model calls, learns locally", "author": { "name": "Local" } }
'@
    Write-Utf8 (Join-Path $HooksDir 'hooks.json') '{"modules":["./register.js"]}'
    Write-Utf8 (Join-Path $HooksDir 'core.js') @'
// MA Auto Router V7 - core: reine Logik ohne Zugriff auf die Mod-API ($).
// Alles hier ist deterministisch und lokal. Keine Netzwerkaufrufe, keine Modellaufrufe.
export const VERSION = 'V7.0'
export const EFFORTS = ['low', 'medium', 'high', 'xhigh', 'max']
export const FAMILIES = ['haiku', 'sonnet', 'opus', 'fable']

export function normalize(text) { return String(text || '').trim().replace(/\s+/g, ' ') }
export function clamp(n, lo, hi) { return Math.max(lo, Math.min(hi, n)) }

// ---------------------------------------------------------------- Merkmale
export const PATTERNS = {
  read: [/\bliste\b/i, /\bzeige\b/i, /\bwas steht\b/i, /\blies\b/i, /\bsuche\b/i, /\bfinde\b/i, /\bstatus\b/i,
    /\bdocker ps\b/i, /\bgit status\b/i, /\bshow\b/i, /\blist\b/i, /\bfind\b/i],
  write: [/\berstell/i, /\bschreib/i, /\bimplement/i, /\bänder/i, /\baender/i, /\brepar/i, /\bbeheb/i,
    /\bfix(?:e|en|es|t)?\b/i, /\bkonfigurier/i, /\binstallier/i, /\bentfern/i, /\blösch/i, /\bloesch/i,
    /\bmigrier/i, /\baktualisier/i, /\bbenenne/i, /\bcreate\b/i, /\bwrite\b/i, /\bmodify\b/i, /\bchange\b/i, /\brename\b/i],
  code: [/\bcode\b/i, /\bpython\b/i, /\bbash\b/i, /\bpowershell\b/i, /\bskript\b/i, /\bscript\b/i, /\bapi\b/i,
    /\bcompose\b/i, /\bdockerfile\b/i, /\brefactor/i, /\btest(?:e|en)?\b/i, /\bfunktion\b/i, /\bklasse\b/i, /\bvariable\b/i],
  debug: [/\bdebug/i, /\bfehler\b/i, /\bbug\b/i, /\bexception\b/i, /\btraceback\b/i, /\bfunktioniert nicht\b/i,
    /\bgeht nicht\b/i, /\bursache\b/i, /\bproblem\b/i, /\bkaputt\b/i, /\bbroken\b/i, /\babsturz\b/i, /\bcrash/i],
  analysis: [/\banalysier/i, /\bprüf/i, /\bpruef/i, /\bbewert/i, /\bvergleich/i, /\buntersuch/i, /\banaly[sz]e\b/i, /\breview\b/i],
  multi: [/\bdanach\b/i, /\banschließend\b/i, /\banschliessend\b/i, /\bund dann\b/i, /\bmehrere schritte\b/i,
    /\bvollständig\b/i, /\bvollstaendig\b/i, /\bkomplett\b/i, /\bend[- ]to[- ]end\b/i, /\bschritt\s*\d/i],
  arch: [/architektur/i, /\barchitecture\b/i, /\bsystem design\b/i, /\bdesignentscheidung/i],
  security: [/sicherheit/i, /\bsecurity\b/i, /\bauth(?:entifizierung|entication)?\b/i, /\bzero[- ]trust\b/i, /\bthreat\b/i,
    /\bbedrohungsmodell\b/i, /\bfirewall\b/i, /\bhardening\b/i, /\bschwachstell/i, /\bvulnerab/i],
  hard: [/\bkomplex/i, /\btiefgehend\b/i, /\bgrundlegend/i, /\bschwierig/i],
  race: [/\brace condition\b/i, /\bdeadlock\b/i, /\bconcurrency\b/i, /\bheisenbug\b/i, /\bnebenläufig/i, /\bthread[- ]?safe/i],
  rootcause: [/\broot cause\b/i, /\bgrundursache\b/i, /\bursachenanalyse\b/i],
  uncertain: [/\bsporadisch/i, /\bmanchmal\b/i, /\bunklar\b/i, /\bkeine ahnung\b/i, /\bnicht reproduzierbar\b/i,
    /\bschwer reproduzier/i, /\bintermittent/i, /\bflaky\b/i, /\bunerklärlich/i],
  critical: [/\bkritisch/i, /\bcritical\b/i, /\bexploit/i, /\bpentest/i, /\bproduktion/i, /\bproduction\b/i, /\bcve-\d/i],
  edge: [/\bedge[- ]?cases?\b/i, /\brandf[aä]ll/i, /\bsonderf[aä]ll/i, /\bgrenzf[aä]ll/i],
  explain: [/^(erkl[aä]re?|was macht|wie funktioniert|was bedeutet|explain|what does)\b/i],
  ultrathink: [/\bultrathink\b/i]
}
export const CONTINUATION =
  /^(ja|ja bitte|ok|okay|weiter|mach weiter|ja mach|mach das|genau|yes|continue|go ahead|do it)[.! ]*$/i
const NEG_STRONG = [/\bfalsch\b/i, /\bstimmt nicht\b/i, /\bimmer noch nicht\b/i, /\bnoch immer\b/i,
  /\bhat nicht funktioniert\b/i, /\bnicht geholfen\b/i, /\bwrong\b/i, /\bstill (?:does not|doesn't|not) work/i,
  /\bdid not work\b/i, /\bdidn't work\b/i, /\bgeht noch nicht\b/i]
const NEG_WEAK = [/\bgeht (?:noch )?nicht\b/i, /\bfunktioniert (?:noch )?nicht\b/i, /\bklappt (?:noch )?nicht\b/i,
  /\bdoes not work\b/i, /\bdoesn't work\b/i]
const POSITIVE = [/^((perfekt|super|genau|passt|danke|vielen dank|top|gut so|prima|klasse)[,.! ]*)+$/i, /\bgeht jetzt\b/i, /\bfunktioniert jetzt\b/i,
  /\bklappt jetzt\b/i, /\bworks now\b/i, /\bthat worked\b/i]

// Rueckmeldung nur an kurzen Nachrichten erkennen; lange Texte sind neue Aufgaben/Bugreports.
export function isNegativeFeedback(text) {
  const n = text.length
  if (n > 220) return false
  if (NEG_STRONG.some((r) => r.test(text))) return true
  return n <= 70 && NEG_WEAK.some((r) => r.test(text))
}
export function isPositiveFeedback(text) { return text.length <= 120 && POSITIVE.some((r) => r.test(text)) }

export function countComponents(p) {
  const files = new Set((p.match(/\b[\w\-./\\]+\.(?:js|ts|tsx|py|ps1|json|ya?ml|md|sh|go|rs|java|cs|sql|toml|ini|env|conf)\b/gi) || []).map((x) => x.toLowerCase()))
  const words = (p.match(/\b(?:komponente|modul|service|dienst|endpoint|tabelle|klasse|container|datei|schnittstelle)\w*/gi) || []).length
  return Math.min(8, files.size + Math.min(4, words))
}

export function extractFeatures(text) {
  const p = normalize(text)
  const f = []
  for (const [name, patterns] of Object.entries(PATTERNS)) if (patterns.some((r) => r.test(p))) f.push(name)
  const techy = f.some((x) => ['write', 'code', 'debug', 'arch', 'security', 'hard', 'race', 'rootcause', 'analysis', 'multi'].includes(x))
  if (p.length > 0 && p.length <= 180 &&
      /^(was ist|was sind|wo ist|wo sind|wer ist|welche|welcher|welches|wann|wie viele|what is|what are|where is|where are|how many)\b/i.test(p) &&
      !techy) f.push('simple')
  if (f.includes('explain') && (p.length > 140 || techy)) f.splice(f.indexOf('explain'), 1)
  if (p.length > 700) f.push('long')
  if (p.length > 2500) f.push('verylong')
  if (f.includes('write') && f.includes('read')) f.splice(f.indexOf('read'), 1)
  if (f.length === 0 && p.length > 0 && p.length <= 45) f.push('vague')
  return [...new Set(f)].sort()
}
export function signature(features) {
  const clean = features.filter((x) => !['continuation', 'feedback', 'vague', 'ultrathink'].includes(x))
  return clean.length ? clean.join('+') : 'default'
}
// anonyme Task-Signatur fuer Protokolle: Hash der Merkmalsliste, kein Prompt-Text
export function sigHash(sig) {
  let h = 2166136261
  for (let i = 0; i < sig.length; i++) { h ^= sig.charCodeAt(i); h = Math.imul(h, 16777619) }
  return (h >>> 0).toString(16).padStart(8, '0')
}

// ---------------------------------------------------------------- Modelle
export function parseModelId(id) {
  const s = String(id || '').toLowerCase().replace(/\[1m\]$/, '')
  const m = s.match(/claude-(haiku|sonnet|opus|fable)-(\d+)(?:-(\d{1,2})(?!\d))?/)
  if (!m) return null
  return { family: m[1], major: Number(m[2]), minor: m[3] ? Number(m[3]) : 0, raw: String(id) }
}
const ALL5 = EFFORTS
const NOXH = ['low', 'medium', 'high', 'max']
// Quelle: Claude-Code-Doku "Adjust effort level" (Tabelle der Stufen je Modell). Unbekannte IDs: keine Stufen.
export function effortLevelsFor(id) {
  const p = parseModelId(id)
  if (!p) return []
  const v = p.major + p.minor / 10
  if (p.family === 'fable') return ALL5
  if (p.family === 'opus') return v >= 4.7 ? ALL5 : v >= 4.6 ? NOXH : []
  if (p.family === 'sonnet') return v >= 5 ? ALL5 : v >= 4.6 ? NOXH : []
  if (p.family === 'haiku') return v >= 5.5 ? ALL5 : []
  return []
}
// Natives 1M-Fenster laut Doku (Anthropic-API). Es werden nie [1m]-Varianten gewaehlt.
export function contextWindowFor(id, provider) {
  const p = parseModelId(id)
  if (!p || provider !== 'anthropic') return 200000
  const v = p.major + p.minor / 10
  const native1m = p.family === 'fable' || (p.family === 'sonnet' && v >= 5) || (p.family === 'haiku' && v >= 5.5) || (p.family === 'opus' && v >= 4.7)
  return native1m ? 1000000 : 200000
}
// Wirkt der Wechsel der Effort-Stufe auf den Cache? Doku "Changing effort level".
export function effortChangeKeepsCache(id, provider, flags) {
  const p = parseModelId(id)
  if (!p || provider !== 'anthropic' || (flags && flags.noBetas)) return false
  const v = p.major + p.minor / 10
  return (p.family === 'opus' && v >= 5.5) || (p.family === 'sonnet' && v >= 5.5) || (p.family === 'fable' && v >= 5.1)
}
// Dokumentierte Standard-IDs der Anthropic-API (nur dort verwendet; ueberschreibbar in router-config.json).
export const DOCUMENTED_DEFAULTS = { haiku: 'claude-haiku-5-5', sonnet: 'claude-sonnet-5-5', opus: 'claude-opus-5-5', fable: 'claude-fable-5-1' }

function entryMatches(entry, family, id) {
  const e = String(entry || '').toLowerCase().replace(/\[1m\]$/, '')
  const i = String(id || '').toLowerCase()
  return e === family || e === i || i.startsWith(e) || e.startsWith(i)
}
export function allowedByLists(family, id, settings) {
  const s = settings || {}
  if (Array.isArray(s.deniedModels) && s.deniedModels.some((e) => entryMatches(e, family, id) && e !== family ? true : e === family)) return false
  if (Array.isArray(s.availableModels)) {
    if (s.availableModels.length === 0) return false
    return s.availableModels.some((e) => entryMatches(e, family, id))
  }
  return true
}

// Capability-Registry. Prioritaet der ID-Quelle: Env-Pin > Konfiguration > beobachtet > dokumentierter Standard (nur Anthropic-API).
export function buildRegistry(inp) {
  const provider = inp.provider || 'unknown'
  const cfg = inp.config || {}
  const reg = { provider, models: [], byFamily: {}, notes: [] }
  for (const family of FAMILIES) {
    let id = null; let source = 'none'
    const pin = inp.envPins && inp.envPins[family]
    if (pin && !['haiku', 'sonnet', 'opus', 'fable', 'default', 'best', 'opusplan', 'inherit'].includes(pin.trim())) { id = pin.trim().replace(/\[1m\]$/, ''); source = 'env-pin' }
    else if (cfg.modelIds && cfg.modelIds[family]) { id = String(cfg.modelIds[family]); source = 'config' }
    else if (inp.observed && inp.observed[family]) { id = inp.observed[family]; source = 'observed' }
    else if (provider === 'anthropic') { id = DOCUMENTED_DEFAULTS[family]; source = 'documented-default' }
    let available = !!id
    let why = id ? '' : 'ID unbekannt (nicht geraten)'
    if (id && !allowedByLists(family, id, inp.settings)) { available = false; why = 'durch availableModels/deniedModels gesperrt' }
    if (id && inp.unavailable && inp.unavailable.has(family)) { available = false; why = 'Verfuegbarkeitsfehler in dieser Session' }
    let creditRisk = false
    if (family === 'fable') {
      creditRisk = true
      if (!(cfg.allowFable === true && cfg.fableCreditsConfirmed === true)) { available = false; why = 'Fable: standardmaessig aus (moegliche Usage Credits)' }
    }
    let levels = id ? effortLevelsFor(id) : []
    const cap = inp.settings && inp.settings.maxEffortLevel
    if (cap && EFFORTS.includes(cap)) levels = levels.filter((l) => EFFORTS.indexOf(l) <= EFFORTS.indexOf(cap))
    const cap2 = cfg.maxEffort
    if (cap2 && EFFORTS.includes(cap2)) levels = levels.filter((l) => EFFORTS.indexOf(l) <= EFFORTS.indexOf(cap2))
    const m = {
      id, family, source, available, why, effortLevels: levels,
      contextWindow: id ? contextWindowFor(id, provider) : 0,
      adaptiveReasoning: id ? levels.length > 0 : false,
      supportsUltracode: levels.includes('xhigh'),
      supportsFastMode: 'unknown', // wird nie automatisch aktiviert
      mayRequireUsageCredits: creditRisk
    }
    reg.models.push(m); reg.byFamily[family] = m
  }
  return reg
}

// ---------------------------------------------------------------- Ladder
const PREF = { haiku: ['low', 'medium'], sonnet: ['low', 'medium', 'high', 'xhigh'], opus: ['medium', 'high', 'xhigh', 'max'], fable: ['xhigh', 'max'] }
export const STATIC_ORDER = ['haiku:low', 'haiku:medium', 'sonnet:low', 'sonnet:medium', 'sonnet:high', 'sonnet:xhigh',
  'opus:medium', 'opus:high', 'opus:xhigh', 'opus:max', 'fable:xhigh', 'fable:max']
export function buildLadder(reg) {
  const rungs = []
  for (const family of ['haiku', 'sonnet', 'opus', 'fable']) {
    const m = reg.byFamily[family]
    if (!m || !m.available || !m.id) continue
    if (m.effortLevels.length === 0) { rungs.push({ family, id: m.id, effort: null, key: family + ':-', window: m.contextWindow }); continue }
    for (const e of PREF[family]) if (m.effortLevels.includes(e)) rungs.push({ family, id: m.id, effort: e, key: family + ':' + e, window: m.contextWindow })
  }
  return rungs
}
function staticIndex(fam, eff) {
  const i = STATIC_ORDER.indexOf(fam + ':' + (eff || ''))
  if (i >= 0) return i
  // Familie ohne Effort: Mitte der Familie
  const idx = STATIC_ORDER.map((k, n) => [k, n]).filter(([k]) => k.startsWith(fam + ':'))
  return idx.length ? idx[Math.floor(idx.length / 2)][1] : 3
}
// naechstliegende nutzbare Sprosse (Gleichstand: hoeher = Qualitaet zuerst)
export function pickRung(ladder, fam, eff) {
  if (!ladder.length) return -1
  const want = staticIndex(fam, eff)
  let best = 0; let bd = 1e9
  ladder.forEach((r, i) => {
    const d = Math.abs(staticIndex(r.family, r.effort) - want)
    if (d < bd || (d === bd && staticIndex(r.family, r.effort) > staticIndex(ladder[best].family, ladder[best].effort))) { bd = d; best = i }
  })
  return best
}

// ---------------------------------------------------------------- Regeln
export function ruleChoice(f, len, comps) {
  const has = (x) => f.includes(x)
  let fam = 'sonnet'; let eff = 'medium'; let why = 'Standard'
  const small = len <= 200 && comps <= 1 && !has('multi') && !has('edge')
  if (has('race') || (has('rootcause') && has('debug'))) {
    fam = 'opus'; eff = (has('uncertain') || has('hard') || has('multi') || len > 600) ? 'max' : 'xhigh'; why = 'Race/Root-Cause'
  } else if (has('security') && (has('critical') || has('arch'))) {
    fam = 'opus'; eff = (has('critical') && has('arch') && (has('hard') || has('uncertain'))) ? 'max' : 'xhigh'; why = 'Security kritisch/Architektur'
  } else if (has('arch')) {
    fam = 'opus'; eff = (has('multi') || len > 700 || comps >= 4 || has('hard')) ? 'high' : 'medium'; why = 'Architektur'
  } else if (has('security')) {
    fam = has('hard') ? 'opus' : 'sonnet'; eff = 'high'; why = 'Security'
  } else if (has('debug')) {
    fam = 'sonnet'; eff = (has('hard') || (has('uncertain') && (has('multi') || len > 500))) ? 'xhigh' : 'high'; why = 'Debugging'
  } else if (has('write') || has('code')) {
    fam = 'sonnet'
    if (has('edge') || has('multi') || len > 600 || comps >= 3) { eff = 'high'; why = 'Code mit Randfaellen/mehreren Teilen' }
    else if (small) { eff = 'low'; why = 'kleine eindeutige Codeaufgabe' }
    else { eff = 'medium'; why = 'normale Codeaufgabe' }
  } else if (has('analysis')) {
    fam = 'sonnet'; eff = (len > 600 || has('multi')) ? 'high' : 'medium'; why = 'Analyse'
  } else if ((has('read') || has('simple')) && !has('long')) {
    fam = 'haiku'; eff = 'low'; why = 'einfache Leseaufgabe'
  } else if (has('explain') && len <= 120) {
    fam = 'haiku'; eff = 'low'; why = 'kurze Erklaerung'
  } else if (has('explain')) {
    fam = 'sonnet'; eff = 'low'; why = 'Erklaerung'
  }
  if (has('long') && fam === 'haiku') { fam = 'sonnet'; eff = 'low'; why += ' (lang)' }
  let ei = EFFORTS.indexOf(eff)
  if (has('verylong') && fam !== 'haiku') ei = Math.min(3, ei + 1)
  if (has('edge') && fam !== 'haiku') ei = Math.max(ei, 2)
  if (has('ultrathink')) { ei = Math.max(ei, 1); if (fam === 'haiku') { fam = 'sonnet'; ei = Math.max(ei, 1) } }
  return { fam, eff: EFFORTS[ei], why }
}

// ---------------------------------------------------------------- Lernmodelle (gehashte Unigramm-/Bigramm-Gewichte)
const LM_DIM = 4096
function hashStr(s) {
  let h = 2166136261
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619) }
  return (h >>> 0) % LM_DIM
}
// Liefert nur gehashte Indizes (Zahlen). Prompt-Text wird nicht aufbewahrt.
export function lmFeatureIdx(text, ruleFeatures) {
  const t = normalize(text).toLowerCase().replace(/[^\p{L}\p{N}_.\-\/]+/gu, ' ').split(' ').filter((x) => x.length > 1).slice(0, 150)
  const out = []
  for (let i = 0; i < t.length; i++) {
    out.push('u:' + t[i].slice(0, 6))
    if (i + 1 < t.length) out.push('b:' + t[i].slice(0, 6) + ' ' + t[i + 1].slice(0, 6))
  }
  for (const f of ruleFeatures || []) out.push('f:' + f)
  out.push('len:' + Math.min(6, Math.floor(Math.log2(1 + normalize(text).length / 20))))
  return [...new Set([...new Set(out)].slice(0, 220).map(hashStr))]
}
export function newLM(classes) { return { n: 0, c: classes, w: {} } }
function softmax(z) { const m = Math.max(...z); const e = z.map((v) => Math.exp(v - m)); const s = e.reduce((a, b) => a + b, 0); return e.map((v) => v / s) }
export function lmProbs(lm, idx) {
  const C = lm.c; const z = new Array(C).fill(0)
  for (const i of idx) { const w = lm.w[i]; if (w) for (let c = 0; c < C; c++) z[c] += w[c] }
  const k = Math.sqrt(Math.max(1, idx.length))
  return softmax(z.map((v) => v / k))
}
export function lmTrain(lm, idx, y, lr) {
  if (!idx || !idx.length || y < 0 || y >= lm.c) return false
  const p = lmProbs(lm, idx); const k = Math.sqrt(Math.max(1, idx.length))
  for (const i of idx) {
    const w = lm.w[i] || (lm.w[i] = new Array(lm.c).fill(0))
    for (let c = 0; c < lm.c; c++) w[c] = clamp(w[c] + (lr * ((c === y ? 1 : 0) - p[c])) / k * 4, -6, 6)
  }
  lm.n += 1
  const keys = Object.keys(lm.w)
  if (keys.length > 6000) {
    keys.map((key) => [key, lm.w[key].reduce((a, b) => a + Math.abs(b), 0)]).sort((a, b) => a[1] - b[1])
      .slice(0, keys.length - 4000).forEach(([key]) => delete lm.w[key])
  }
  return true
}
// Gewicht des Lernmodells waechst langsam mit der Zahl der Beispiele.
export function rampWeight(n) { return n < 20 ? 0.1 : n < 50 ? 0.25 : n < 100 ? 0.55 : 1 }

// ---------------------------------------------------------------- Zustand
export function newState() {
  return { v: 7, lmModel: newLM(3), lmEffort: newLM(5), cells: {}, legacy: { featureBias: {}, signatureBias: {} },
    counters: { corrections: 0, autoCorrections: 0, confirmations: 0, escalations: 0, effortEscalations: 0, modelEscalations: 0, turns: 0, migrated: '' } }
}
// Migration: V6.x-Daten uebernehmen (nichts wird geloescht)
export function migrateFromV6(state, learningV6, lmV6) {
  let moved = false
  if (learningV6 && typeof learningV6 === 'object') {
    state.legacy.featureBias = learningV6.featureBias || {}
    state.legacy.signatureBias = learningV6.signatureBias || {}
    const c = state.counters
    c.corrections += Number(learningV6.corrections || 0); c.autoCorrections += Number(learningV6.autoCorrections || 0)
    c.confirmations += Number(learningV6.confirmations || 0)
    moved = true
  }
  if (lmV6 && typeof lmV6 === 'object' && lmV6.w && typeof lmV6.w === 'object') {
    const w = {}
    for (const [k, v] of Object.entries(lmV6.w)) if (Array.isArray(v) && v.length === 3 && v.every((x) => Number.isFinite(x))) w[k] = v.map((x) => clamp(x, -6, 6))
    state.lmModel = { n: Number(lmV6.n || 0), c: 3, w }
    moved = true
  }
  if (moved) state.counters.migrated = 'v6'
  return moved
}
// beschaedigte/fremde Daten abfangen
export function sanitizeState(raw) {
  const s = newState()
  try {
    if (!raw || typeof raw !== 'object' || raw.v !== 7) return { state: s, ok: false }
    for (const [key, cls] of [['lmModel', 3], ['lmEffort', 5]]) {
      const l = raw[key]
      if (l && typeof l === 'object' && l.c === cls && l.w && typeof l.w === 'object') {
        const w = {}
        for (const [k, v] of Object.entries(l.w)) if (Array.isArray(v) && v.length === cls && v.every((x) => Number.isFinite(x))) w[k] = v.map((x) => clamp(x, -6, 6))
        s[key] = { n: Math.max(0, Number(l.n) || 0), c: cls, w }
      }
    }
    if (raw.cells && typeof raw.cells === 'object') {
      for (const [sig, rungs] of Object.entries(raw.cells)) {
        if (!rungs || typeof rungs !== 'object') continue
        s.cells[sig] = {}
        for (const [rk, st] of Object.entries(rungs)) if (st && typeof st === 'object') s.cells[sig][rk] = { ok: Math.max(0, Number(st.ok) || 0), bad: Math.max(0, Number(st.bad) || 0), over: Math.max(0, Number(st.over) || 0) }
      }
    }
    if (raw.legacy && typeof raw.legacy === 'object') s.legacy = { featureBias: raw.legacy.featureBias || {}, signatureBias: raw.legacy.signatureBias || {} }
    if (raw.counters && typeof raw.counters === 'object') for (const k of Object.keys(s.counters)) if (typeof raw.counters[k] === typeof s.counters[k]) s.counters[k] = raw.counters[k]
    return { state: s, ok: true }
  } catch { return { state: newState(), ok: false } }
}

function cell(state, sig, rungKey) {
  const c = state.cells[sig] || (state.cells[sig] = {})
  return c[rungKey] || (c[rungKey] = { ok: 0, bad: 0, over: 0 })
}
function pruneCells(state) {
  const sigs = Object.keys(state.cells)
  if (sigs.length <= 300) return
  const size = (s) => Object.values(state.cells[s]).reduce((a, c) => a + c.ok + c.bad, 0)
  sigs.sort((a, b) => size(a) - size(b)).slice(0, sigs.length - 250).forEach((s) => delete state.cells[s])
}
export function cellStats(state, sig, rungKey) {
  const c = state.cells[sig] && state.cells[sig][rungKey]
  return c || { ok: 0, bad: 0, over: 0 }
}
const insufficient = (c) => c.bad >= 2 && c.bad / Math.max(0.001, c.ok + c.bad) >= 0.5
const reliable = (c) => c.ok >= 3 && c.bad / Math.max(0.001, c.ok + c.bad) <= 0.2

// Ergebnis lernen. kind: bad | ok | weak-ok | over | escalated
export function learnOutcome(state, d, ladder, kind) {
  if (!d || !d.sig || !d.finalKey) return
  const finalRung = ladder.find((r) => r.key === d.finalKey)
  const startRung = ladder.find((r) => r.key === d.startKey)
  const lrFor = { bad: 0.5, ok: 0.12, 'weak-ok': 0.03, over: 0.2, escalated: 0.35 }
  const lr = lrFor[kind]
  if (kind === 'bad') {
    cell(state, d.sig, d.finalKey).bad += 1
    // darunterliegende Sprossen der Familie waren dann erst recht zu schwach
    const i = ladder.findIndex((r) => r.key === d.finalKey)
    for (let j = Math.max(0, i - 1); j < i; j++) cell(state, d.sig, ladder[j].key).bad += 0.5
    const up = ladder[Math.min(ladder.length - 1, i + 1)]
    if (up) lrTrain(state, d, up, lr)
  } else if (kind === 'escalated') {
    if (d.startKey !== d.finalKey) cell(state, d.sig, d.startKey).bad += 1
    cell(state, d.sig, d.finalKey).ok += 1
    lrTrain(state, d, finalRung, lr)
  } else if (kind === 'ok') {
    cell(state, d.sig, d.finalKey).ok += 1
    if (d.steps <= Math.max(2, (d.expectedSteps || 4) / 2) && !d.escalated) cell(state, d.sig, d.finalKey).over += 1
    lrTrain(state, d, finalRung, lr)
  } else if (kind === 'weak-ok') {
    cell(state, d.sig, d.finalKey).ok += 0.3
    lrTrain(state, d, finalRung, lr)
  } else if (kind === 'over') {
    const i = ladder.findIndex((r) => r.key === d.finalKey)
    const down = ladder[Math.max(0, i - 1)]
    cell(state, d.sig, d.finalKey).over += 1
    if (down) lrTrain(state, d, down, lr)
  }
  void startRung
  pruneCells(state)
}
function lrTrain(state, d, rung, lr) {
  if (!rung || !d.lmIdx) return
  lmTrain(state.lmModel, d.lmIdx, ['haiku', 'sonnet', 'opus'].indexOf(rung.family === 'fable' ? 'opus' : rung.family), lr)
  if (rung.effort) lmTrain(state.lmEffort, d.lmIdx, EFFORTS.indexOf(rung.effort), lr)
}

// ---------------------------------------------------------------- Entscheidung
function addBias(scores, bias, scale) {
  if (!bias) return
  for (const k of ['haiku', 'sonnet', 'opus']) scores[k] += Number(bias[k] || 0) * scale
}
// Cache-Strafe fuer einen Wechsel von der Sprosse "from" zu "to"
export function switchPenalty(from, to, sess) {
  if (!from || !to || from.key === to.key) return 0
  const cold = 0.2
  if (!sess.warm) return cold
  const ctx = Math.max(0, sess.ctxTokens || 0)
  const full = clamp(Math.log2(1 + ctx / 2000) * 0.5, 0.3, 6)
  if (from.id !== to.id) return full
  return sess.effortKeepsCache ? 0.15 : full * 0.9
}

export function decide(inp) {
  const { state, ladder, sess } = inp
  const p = normalize(inp.text)
  if (!ladder.length) return null
  if ((!p || CONTINUATION.test(p)) && sess.lastKey) {
    const keep = ladder.find((r) => r.key === sess.lastKey)
    if (keep) return { features: ['continuation'], sig: 'continuation', rung: keep, startKey: keep.key, finalKey: keep.key, conf: 0.9,
      reason: 'Fortsetzung: Modell und Effort des vorherigen Turns beibehalten', scores: sess.lastScores || {}, escScores: {}, lmIdx: null, kept: true, learned: 0 }
  }
  const features = extractFeatures(p)
  const comps = countComponents(p)
  const sig = signature(features)
  const rule = ruleChoice(features, p.length, comps)
  const nM = state.lmModel.n; const nE = state.lmEffort.n
  const wM = rampWeight(nM); const wE = rampWeight(nE)
  const idx = lmFeatureIdx(p, features)

  // Familie: Regelwert + Altgewichte + Lernmodell
  const fam = { haiku: 0, sonnet: 0, opus: 0 }
  const ruleFam = rule.fam === 'fable' ? 'opus' : rule.fam
  fam[ruleFam] += 5
  if (ruleFam === 'sonnet') { fam.haiku += 1; fam.opus += 1 } else if (ruleFam === 'opus') fam.sonnet += 2; else fam.sonnet += 2
  for (const f of features) addBias(fam, state.legacy.featureBias[f], 0.5)
  addBias(fam, state.legacy.signatureBias[sig], 0.5)
  let learned = 0
  if (nM > 0) { const pr = lmProbs(state.lmModel, idx); ['haiku', 'sonnet', 'opus'].forEach((k, c) => { fam[k] += clamp(wM * 3 * Math.log(pr[c] + 1e-6), -6, 0) }); learned += 1 }
  const present = ['haiku', 'sonnet', 'opus'].filter((k) => ladder.some((r) => r.family === k))
  const ranked = present.map((k) => [k, fam[k]]).sort((a, b) => b[1] - a[1])
  let famPick = ranked[0][0]
  const margin = ranked.length > 1 ? ranked[0][1] - ranked[1][1] : 5
  if (famPick !== ruleFam && margin < 3 && present.includes(ruleFam)) famPick = ruleFam
  if (!present.includes(famPick)) famPick = present[0]
  if (famPick === 'haiku') {
    const evidence = (features.includes('read') || features.includes('simple') || features.includes('explain')) && !features.includes('long')
    const learnedOk = nM >= 25 && lmProbs(state.lmModel, idx)[0] > 0.75
    if (!(evidence || learnedOk) || margin < 1.5) famPick = present.includes('sonnet') ? 'sonnet' : famPick
  }
  if (famPick === 'opus' && margin < 3 && ruleFam !== 'opus' && present.includes('sonnet')) famPick = 'sonnet'

  // Effort: Regelwert + Lernmodell, Abweichung von der Regel begrenzt
  const e0 = EFFORTS.indexOf(rule.eff)
  const allowedE = ladder.filter((r) => r.family === famPick && r.effort).map((r) => r.effort)
  const esc = {}
  let ePick = null
  if (allowedE.length) {
    const prE = nE > 0 ? lmProbs(state.lmEffort, idx) : null
    if (prE) learned += 1
    let bestS = -1e9
    for (const e of allowedE) {
      const i = EFFORTS.indexOf(e)
      const s = -2 * Math.abs(i - e0) + (prE ? clamp(wE * 3 * Math.log(prE[i] + 1e-6), -6, 0) : 0)
      esc[e] = Number(s.toFixed(2))
      if (s > bestS) { bestS = s; ePick = e }
    }
    const maxDev = nE >= 100 ? 2 : 1
    const closest = allowedE.reduce((a, b) => Math.abs(EFFORTS.indexOf(b) - e0) < Math.abs(EFFORTS.indexOf(a) - e0) ? b : a)
    if (Math.abs(EFFORTS.indexOf(ePick) - e0) > maxDev) ePick = closest
  }
  let i = pickRung(ladder, famPick, ePick || rule.eff)
  const reasons = [rule.why]

  // Zellen-Statistik: bekannte unzureichende Sprosse meiden, guenstigere zuverlaessige bevorzugen
  const startI = i
  let guard = 0
  while (i < ladder.length - 1 && insufficient(cellStats(state, sig, ladder[i].key)) && guard++ < 6) i += 1
  if (i !== startI) reasons.push('Zelle unzureichend gelernt: ' + ladder[startI].key + ' -> ' + ladder[i].key)
  if (i === startI && i > 0) {
    const cur = cellStats(state, sig, ladder[i].key); const below = cellStats(state, sig, ladder[i - 1].key)
    if (reliable(below) && !insufficient(below)) { i -= 1; reasons.push('guenstigere Sprosse zuverlaessig gelernt') }
    else if (cur.over >= 3 && cur.ok >= 5 && cur.bad === 0 && !insufficient(below)) { i -= 1; reasons.push('Downshift gelernt (mehrfach ueberdimensioniert)') }
  }

  // Erzwungenes Hoch (Feedback/Eskalation aus dem vorigen Turn)
  let forced = false
  if (sess.forcedUp > 0) { i = Math.min(ladder.length - 1, i + sess.forcedUp); forced = true; reasons.push(sess.forcedReason || 'Korrektur nach Rueckmeldung') }

  // Kontextbedarf: Fenster der Sprosse muss zum bisherigen Kontext passen
  const need = (sess.ctxTokens || 0) * 1.15
  if (need > ladder[i].window) {
    const j = ladder.findIndex((r, n) => n >= i && r.window >= need)
    if (j >= 0) { i = j; reasons.push('Kontext braucht groesseres Fenster') }
  }

  // Cache-bewusst: nur wechseln, wenn der Nutzen die Strafe uebersteigt
  const last = sess.lastKey ? ladder.find((r) => r.key === sess.lastKey) : null
  let held = false
  if (last && !forced && ladder[i].key !== last.key) {
    const lastI = ladder.findIndex((r) => r.key === last.key)
    const dist = i - lastI
    const gain = dist > 0 ? dist * 2.0 : -dist * 1.0
    const pen = switchPenalty(last, ladder[i], sess)
    const strong = margin >= 6 && dist > 0
    if (gain <= pen && !strong) { i = lastI; held = true; reasons.push('Wechsel gehalten (Cache-Strafe ' + pen.toFixed(1) + ' > Nutzen ' + gain.toFixed(1) + ')') }
  }
  const conf = clamp(0.45 + margin / 12 + (features.includes('vague') ? -0.15 : 0), 0.25, 0.95)
  const expectedSteps = { haiku: 2, sonnet: 6, opus: 9 }[ladder[i].family] + (ladder[i].effort === 'xhigh' || ladder[i].effort === 'max' ? 3 : 0)
  return { features: features.length ? features : ['default'], sig, rung: ladder[i], startKey: ladder[i].key, finalKey: ladder[i].key,
    conf, reason: reasons.join(' · '), scores: { ...fam }, escScores: esc, lmIdx: idx, learned, held, forced, expectedSteps,
    ruleKey: rule.fam + ':' + rule.eff, len: p.length, comps }
}

// Eskalation innerhalb einer Aufgabe: erst Effort, dann Modell (Leiter laeuft in dieser Reihenfolge)
export function escalateRung(ladder, key, by) {
  const i = ladder.findIndex((r) => r.key === key)
  if (i < 0) return null
  return ladder[Math.min(ladder.length - 1, i + (by || 1))]
}
'@
    Write-Utf8 (Join-Path $HooksDir 'register.js') @'
// MA Auto Router V7 - Verdrahtung. Reine Logik steht in core.js (ohne Engine-Zugriff, einzeln testbar).
// Alles lokal: keine Netzwerkaufrufe, keine zusaetzlichen Modellaufrufe, kein Subagent.
import * as C from './core.js'

const STORE_KEY = 'ma-auto-router-v7-state'
const LOG_KEY = 'ma-auto-router-v7-log'
const V6_LEARN_KEY = 'adaptive-learning-v2'
const V6_LM_KEY = 'router-lm-v1'

const DEFAULT_STRIP = [
  /<fix-?my-?prompt[^>]*>[\s\S]*?<\/fix-?my-?prompt>/gi,
  /^[ \t]*\[fix-?my-?prompt\][^\n]*$/gim
]
const UNAVAILABLE_RE = /not[_ ]?found|unavailable|unrecogni[sz]ed|invalid[_ ]model|does not exist|not (?:have )?access|model_not|no such model/i

const fresh = () => ({
  loaded: false, provider: 'unknown', surface: null, surfaces: [], cfg: {}, settings: {}, envPins: {}, flags: {},
  observed: {}, unavailable: new Map(), stateNotes: [], reg: null, ladder: [], state: C.newState(), log: [],
  sess: { lastKey: null, lastScores: null, warm: false, ctxTokens: 0, effortKeepsCache: false, forcedUp: 0, forcedReason: '', lastTurnAt: 0 },
  modelPaused: false, effortPaused: false, modelReason: '', effortReason: '',
  base: null, turns: new Map(), last: null, lastReal: null, current: null, lastDecision: null,
  lastReq: { model: null, effort: null }, used: { model: '', effort: null }, fallback: '', engineFallback: '',
  strip: [], ignoreTools: [/fix-?my-?prompt/i], stripped: 0, errs: {},
  storage: { store: 'offen', local: 'offen', vault: 'aus', state: 'neu' }, vault: '', dataDir: '', opusplan: false, ttl: 300000, registryNote: ''
})
const S = fresh()

// ------------------------------------------------------------------ Helfer
function cleanPrompt(text, count) {
  const orig = String(text || '')
  let t = orig
  for (const r of [...DEFAULT_STRIP, ...S.strip]) t = t.replace(r, '')
  t = t.trim()
  if (!t) return orig
  if (count && t !== orig.trim()) S.stripped += 1
  return t
}
function firstParagraph(text) { return String(text || '').split(/\n\s*\n/)[0].trim() }
function onlyIgnoredTools(result) {
  const uses = result && Array.isArray(result.toolUses) ? result.toolUses : []
  if (!uses.length) return false
  return uses.every((u) => { const n = String((u && u.name) || ''); return n && S.ignoreTools.some((r) => r.test(n)) })
}
function isIgnoredTool(name) { return S.ignoreTools.some((r) => r.test(String(name || ''))) }
function round3(v) { return typeof v === 'number' ? Math.round(v * 1000) / 1000 : v }
function serializeState() {
  const s = S.state
  const lm = (m) => { const w = {}; for (const [k, v] of Object.entries(m.w)) w[k] = v.map(round3); return { n: m.n, c: m.c, w } }
  return { v: 7, lmModel: lm(s.lmModel), lmEffort: lm(s.lmEffort), cells: s.cells, legacy: s.legacy, counters: s.counters }
}
function lines(raw) { return String(raw || '').replace(/^﻿/, '').split(/\r?\n/).map((l) => l.trim()).filter((l) => l && !l.startsWith('#')) }
async function readText($, path) { try { return await $.fs.read(path) } catch { return null } }
async function writeText($, path, text, slot) {
  try { await $.fs.write(path, text); S.storage[slot] = 'ok'; return true } catch { S.storage[slot] = 'nicht verfuegbar'; return false }
}
function levelsOf(id) {
  const m = S.reg && S.reg.models.find((x) => x.id === id)
  if (m) return m.effortLevels
  let lv = C.effortLevelsFor(id)
  const cap = (S.settings && S.settings.maxEffortLevel) || S.cfg.maxEffort
  if (cap && C.EFFORTS.includes(cap)) lv = lv.filter((l) => C.EFFORTS.indexOf(l) <= C.EFFORTS.indexOf(cap))
  return lv
}
function nearestLevel(levels, want) {
  if (!levels.length || !want) return undefined
  const w = C.EFFORTS.indexOf(want); let best = levels[0]; let bd = 9
  for (const l of levels) { const d = Math.abs(C.EFFORTS.indexOf(l) - w); if (d < bd || (d === bd && C.EFFORTS.indexOf(l) > C.EFFORTS.indexOf(best))) { bd = d; best = l } }
  return best
}
function rebuild() {
  S.reg = C.buildRegistry({ provider: S.provider, envPins: S.envPins, config: S.cfg, observed: S.observed, settings: S.settings, unavailable: new Set(S.unavailable.keys()) })
  S.ladder = C.buildLadder(S.reg)
}
function rungName(key) { return key ? String(key).replace(':-', '') : '-' }

// ------------------------------------------------------------------ Laden / Speichern
async function loadAll($) {
  const ev = async (get) => { try { return await get() } catch { return undefined } }
  const pin = async (n) => { const v = n; return typeof v === 'string' && v.trim() ? v.trim() : undefined }
  S.envPins = {
    haiku: await pin(await ev(() => $.env.get('ANTHROPIC_DEFAULT_HAIKU_MODEL'))),
    sonnet: await pin(await ev(() => $.env.get('ANTHROPIC_DEFAULT_SONNET_MODEL'))),
    opus: await pin(await ev(() => $.env.get('ANTHROPIC_DEFAULT_OPUS_MODEL'))),
    fable: await pin(await ev(() => $.env.get('ANTHROPIC_DEFAULT_FABLE_MODEL')))
  }
  const bedrock = await ev(() => $.env.get('CLAUDE_CODE_USE_BEDROCK'))
  const vertex = await ev(() => $.env.get('CLAUDE_CODE_USE_VERTEX'))
  const foundry = await ev(() => $.env.get('CLAUDE_CODE_USE_FOUNDRY'))
  const base = await ev(() => $.env.get('ANTHROPIC_BASE_URL'))
  const noBetas = await ev(() => $.env.get('CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS'))
  const truthy = (v) => typeof v === 'string' && v !== '' && v !== '0' && v.toLowerCase() !== 'false'
  S.provider = truthy(bedrock) ? 'bedrock' : truthy(vertex) ? 'vertex' : truthy(foundry) ? 'foundry'
    : (typeof base === 'string' && base.trim() && !/^https?:\/\/api\.anthropic\.com\/?$/i.test(base.trim())) ? 'gateway' : 'anthropic'
  S.flags = { noBetas: truthy(noBetas) }
  const settings = await ev(() => $.settings.read())
  S.settings = settings && typeof settings === 'object' ? settings : {}
  S.opusplan = String(S.settings.model || '').toLowerCase() === 'opusplan'
  if (S.opusplan) { S.modelPaused = true; S.modelReason = 'opusplan: Engine wechselt Plan/Ausfuehrung selbst (kein konkurrierender Modellwechsel)' }
  const ttl = String(S.settings.promptCacheTtl || '')
  S.ttl = /1\s*h|3600/i.test(ttl) ? 3600000 : 300000
  try { const s = await $.session.surfaces(); S.surfaces = Array.isArray(s) ? [...s] : [] } catch { S.surfaces = [] }

  let root = ''
  try { root = String($.plugin.root || '').replace(/[\\/]+$/, '') } catch {}
  S.dataDir = root ? root + '/data' : ''
  if (S.dataDir) {
    const cfg = await readText($, S.dataDir + '/router-config.json')
    if (cfg) { try { const j = JSON.parse(cfg.replace(/^﻿/, '')); if (j && typeof j === 'object') S.cfg = j } catch { S.registryNote = 'router-config.json unlesbar (ignoriert)' } }
    const blocks = await readText($, S.dataDir + '/ignore-blocks.txt')
    if (blocks) S.strip = lines(blocks).map((l) => { try { return new RegExp(l, 'gim') } catch { return null } }).filter(Boolean)
    const tools = await readText($, S.dataDir + '/ignore-tools.txt')
    if (tools) S.ignoreTools = [/fix-?my-?prompt/i, ...lines(tools).map((l) => { try { return new RegExp(l, 'i') } catch { return null } }).filter(Boolean)]
    let v = await readText($, S.dataDir + '/vault.txt')
    v = v ? lines(v)[0] : ''
    if (!v) { const ve = await ev(() => $.env.get('MA_ROUTER_VAULT')); v = typeof ve === 'string' ? ve.trim() : '' }
    S.vault = v ? v.replace(/[\\/]+$/, '') + '/Auto Router' : ''
    S.storage.vault = S.vault ? 'konfiguriert' : 'aus'
  }

  // Lernzustand: Store, lokale Datei, Vault - der mit den meisten Beispielen gewinnt; V6-Daten werden uebernommen
  const candidates = []
  const fromStore = await ev(() => $.store.get(STORE_KEY))
  if (fromStore) candidates.push(['store', fromStore])
  for (const [src, path] of [['local', S.dataDir && S.dataDir + '/router-state-v7.json'], ['vault', S.vault && S.vault + '/_router-state-v7.json']]) {
    if (!path) continue
    const t = await readText($, path)
    if (t) { try { candidates.push([src, JSON.parse(t)]) } catch { S.stateNotes.push('Datei beschaedigt: ' + src + ' (ignoriert)') } }
  }
  let best = null; let bestScore = -1
  for (const [src, raw] of candidates) {
    const { state, ok } = C.sanitizeState(raw)
    if (!ok) { S.stateNotes.push('beschaedigt: ' + src + ' (ignoriert)'); continue }
    const score = state.lmModel.n + state.lmEffort.n + state.counters.turns
    if (score > bestScore) { best = state; bestScore = score; S.storage.state = 'geladen aus ' + src }
  }
  S.storage.state = best ? S.storage.state : 'neu'
  if (best) S.state = best
  else {
    S.state = C.newState()
    let l6 = await ev(() => $.store.get(V6_LEARN_KEY)); let m6 = await ev(() => $.store.get(V6_LM_KEY))
    if (!l6 && !m6) {
      // V6.x-Dateien (lokal / Vault) lesen, nur lesend; die Originale bleiben unveraendert
      for (const path of [S.dataDir && S.dataDir + '/router-learning.json', S.vault && S.vault + '/_router-state.json']) {
        if (!path) continue
        const t = await readText($, path)
        if (!t) continue
        try { const j = JSON.parse(t); if (j && j.lm && Number(j.lm.n || 0) > Number((m6 && m6.n) || 0)) { m6 = j.lm; l6 = j.learning || l6 } } catch {}
      }
    }
    if (C.migrateFromV6(S.state, l6, m6)) S.stateNotes.push('V6-Lerndaten uebernommen (Original unveraendert)')
  }
  const log = await ev(() => $.store.get(LOG_KEY))
  S.log = Array.isArray(log) ? log.filter((r) => r && typeof r === 'object').slice(-200) : []
  rebuild()
  S.loaded = true
}

function stateNote() {
  const c = S.state.counters
  return ['# Auto Router V7 - Lernstand', '',
    '- Beispiele Modell-Lernen: ' + S.state.lmModel.n, '- Beispiele Effort-Lernen: ' + S.state.lmEffort.n,
    '- Turns: ' + c.turns, '- Korrekturen: ' + c.corrections + ' (automatisch: ' + c.autoCorrections + ')', '- Bestaetigungen: ' + c.confirmations,
    '- Eskalationen: ' + c.escalations + ' (Effort ' + c.effortEscalations + ', Modell ' + c.modelEscalations + ')',
    '- Aufgabenmuster (nur Hashes): ' + Object.keys(S.state.cells).length, '',
    'Es werden nur gehashte Merkmale gespeichert, keine Prompt-Texte.'].join('\n')
}
function logNote() {
  const rows = S.log.slice(-100).map((r) => '- ' + [r.t, r.key, 'conf ' + r.conf, 'Schritte ' + r.steps, r.esc ? 'Eskalation ' + r.esc : '', r.nl ? 'ohne Lernen' : '', 'sig ' + r.sig, (r.f || []).join(',')].filter(Boolean).join(' | '))
  return '# Auto Router V7 - Entscheidungen (letzte 100, ohne Prompt-Text)\n\n' + rows.join('\n') + '\n'
}
async function persist($) {
  try { await $.store.set(STORE_KEY, serializeState()); await $.store.set(LOG_KEY, S.log); S.storage.store = 'ok' } catch { S.storage.store = 'nicht verfuegbar' }
  const json = JSON.stringify(serializeState())
  if (S.dataDir) await writeText($, S.dataDir + '/router-state-v7.json', json, 'local')
  if (S.vault) {
    const ok = await writeText($, S.vault + '/_router-state-v7.json', json, 'vault')
    if (ok) { await writeText($, S.vault + '/Lernstand V7.md', stateNote(), 'vault'); await writeText($, S.vault + '/Entscheidungen V7.md', logNote(), 'vault') }
  }
}

// ------------------------------------------------------------------ Status
function fmtScores(o) { return o && Object.keys(o).length ? Object.entries(o).map(([k, v]) => k + ' ' + Number(v).toFixed(1)).join(' · ') : '-' }
function statusText() {
  const d = S.lastDecision; const st = S.state
  const L = []
  L.push('Auto Router ' + C.VERSION + ' - lokal, ohne zusaetzliche Modellaufrufe')
  L.push('Oberflaeche: ' + (S.surfaces.length ? S.surfaces.join(', ') : (S.surface || 'unbekannt')) + ' · Provider: ' + S.provider + ' · lokale Mod-Sessions (nicht in Anthropic-gehosteten Cloud-Sessions)')
  L.push('Routing: Modell ' + (S.modelPaused ? 'PAUSIERT (' + S.modelReason + ')' : 'aktiv') + ' · Effort ' + (S.effortPaused ? 'PAUSIERT (' + S.effortReason + ')' : 'aktiv') + (S.modelPaused || S.effortPaused ? ' · Wieder an: /autorouter' : ''))
  if (!S.ladder.length) L.push('ACHTUNG: kein sicher erkanntes Modell - Router reicht alles unveraendert durch (kein Raten).')
  L.push('Gewaehlt: ' + (d ? rungName(d.finalKey) : 'noch keine Entscheidung') + ' · angefordert: ' + (S.lastReq.model || '-') + (S.lastReq.effort ? ' / ' + S.lastReq.effort : ' / (kein Effort)') + ' · tatsaechlich genutzt (API): ' + (S.used.model || '-'))
  if (d) {
    L.push('Merkmale: ' + d.features.join(', '))
    L.push('Modell-Scores: ' + fmtScores(d.scores) + ' · Effort-Scores: ' + fmtScores(d.escScores))
    L.push('Konfidenz: ' + Number(d.conf).toFixed(2) + ' · Grund: ' + d.reason)
    if (d.escalated) L.push('In-Task-Eskalation: ' + rungName(d.startKey) + ' -> ' + rungName(d.finalKey) + ' (' + (d.escReason || '') + ')')
  }
  const sess = S.sess
  L.push('Cache-Schutz: aktiv (Wechselstrafe Modell+Effort) · Cache ' + (sess.warm ? 'warm' : 'kalt') + ' · Kontext ca. ' + Math.round(sess.ctxTokens / 1000) + 'k Token' + (S.sess.effortKeepsCache ? ' · Effort-Wechsel behaelt Cache' : ''))
  const cur = d && S.ladder.find((r) => r.key === d.finalKey)
  L.push('Kontext: Standardfenster' + (cur ? ' ' + Math.round(cur.window / 1000) + 'k (nativ, keine bezahlten [1m]-Varianten automatisch)' : '') + ' · gezielte Reads statt Gesamtlesen bleiben Pflicht')
  L.push('Lernen: Modell-Beispiele ' + st.lmModel.n + ' (Gewicht ' + C.rampWeight(st.lmModel.n) + ') · Effort-Beispiele ' + st.lmEffort.n + ' (Gewicht ' + C.rampWeight(st.lmEffort.n) + ') · Muster ' + Object.keys(st.cells).length)
  L.push('Auto-Eskalationen: ' + st.counters.escalations + ' (Effort ' + st.counters.effortEscalations + ', Modell ' + st.counters.modelEscalations + ') · Auto-Korrekturen: ' + st.counters.autoCorrections + ' · Bestaetigungen: ' + st.counters.confirmations + ' · bereinigte Zusatzbloecke: ' + S.stripped)
  L.push('Verfuegbarkeits-Fallback: ' + (S.fallback || S.engineFallback || 'nein'))
  L.push('Registry: ' + S.reg.models.map((m) => m.family + '=' + (m.id || '?') + (m.available ? '' : ' [aus: ' + m.why + ']') + (m.effortLevels.length ? ' effort ' + m.effortLevels.join('/') : '')).join(' · '))
  L.push('Nie automatisch: Fable (Standard aus), best, Fast-Mode, Advisor, bezahlte 1M-Varianten' + (S.opusplan ? ' · opusplan erkannt: Modellwahl liegt bei der Engine, Router steuert nur Effort' : ''))
  L.push('Speicher: Store ' + S.storage.store + ' · lokal ' + S.storage.local + ' · Obsidian ' + S.storage.vault + ' · Zustand: ' + [S.storage.state, ...S.stateNotes].join('; ') + (S.registryNote ? ' · ' + S.registryNote : ''))
  return L.join('\n')
}

// ------------------------------------------------------------------ Register
export function register(on) {
  on('session.start', async ($, e, next) => {
    Object.assign(S, fresh())
    S.surface = e.surface || null
    try { await loadAll($) } catch { S.loaded = true; try { rebuild() } catch {} }
    for (const [name, description] of [
      ['autorouter', 'Auto-Router-Status; schaltet pausiertes Routing wieder ein (/autorouter status = nur Anzeige)'],
      ['router-auto', 'Modell- und Effort-Routing wieder einschalten'],
      ['router-model-auto', 'Automatische Modellwahl wieder einschalten'],
      ['router-effort-auto', 'Automatische Effort-Wahl wieder einschalten'],
      ['router-reset', 'Gelerntes Routing zuruecksetzen'],
      ['router-zu-schwach', 'Letzte Wahl war zu schwach: Router lernt hoeher'],
      ['router-zu-stark', 'Letzte Wahl war ueberdimensioniert: Router lernt guenstiger']
    ]) { try { await $.command.register({ name, description }) } catch {} }
    return next(e)
  })

  const enable = (which) => {
    if (which !== 'effort') { S.modelPaused = false; S.modelReason = '' }
    if (which !== 'model') { S.effortPaused = false; S.effortReason = ''; S.base = null }
  }
  on('command.run', { command: 'autorouter' }, async ($, e) => {
    // /autorouter zeigt den Status und schaltet pausiertes Routing wieder ein; /autorouter status zeigt nur an
    const readOnly = /^\s*status\b/i.test(e.args || '')
    const was = S.modelPaused || S.effortPaused
    if (!readOnly) enable('both')
    return { text: (was && !readOnly ? 'Routing war pausiert und ist jetzt wieder aktiv.\n' : '') + statusText() }
  })
  on('command.run', { command: 'router-auto' }, async () => { enable('both'); return { text: 'Auto Router: Modell- und Effort-Routing wieder aktiv.' } })
  on('command.run', { command: 'router-model-auto' }, async () => { enable('model'); return { text: 'Auto Router: Modell-Routing wieder aktiv.' } })
  on('command.run', { command: 'router-effort-auto' }, async () => { enable('effort'); return { text: 'Auto Router: Effort-Routing wieder aktiv.' } })
  on('command.run', { command: 'router-reset' }, async ($) => {
    S.state = C.newState(); S.lastDecision = null; S.last = null; S.lastReal = null; S.log = []
    S.modelPaused = false; S.effortPaused = false; S.modelReason = ''; S.effortReason = ''
    await persist($)
    return { text: 'Auto Router: gelerntes Routing zurueckgesetzt, Pausen aufgehoben. Registry bleibt.' }
  })
  on('command.run', { command: 'router-zu-schwach' }, async ($) => {
    const d = S.lastReal || S.last
    if (!d) return { text: 'Noch keine abgeschlossene Aufgabe zum Bewerten.' }
    C.learnOutcome(S.state, d, S.ladder, 'bad'); d.fb = true
    S.state.counters.corrections += 1; S.sess.forcedUp = 1; S.sess.forcedReason = 'manuelle Korrektur (zu schwach)'
    await persist($)
    return { text: 'Gelernt: ' + rungName(d.finalKey) + ' war fuer aehnliche Aufgaben zu schwach.' }
  })
  on('command.run', { command: 'router-zu-stark' }, async ($) => {
    const d = S.lastReal || S.last
    if (!d) return { text: 'Noch keine abgeschlossene Aufgabe zum Bewerten.' }
    C.learnOutcome(S.state, d, S.ladder, 'over'); d.fb = true
    S.state.counters.corrections += 1
    await persist($)
    return { text: 'Gelernt: ' + rungName(d.finalKey) + ' war fuer aehnliche Aufgaben ueberdimensioniert (vorsichtig, Qualitaet zuerst).' }
  })
  on('prompt.submit', async ($, e, next) => {
    try {
      const full = cleanPrompt(e.text)
      const head = firstParagraph(full)
      const prev = S.lastReal && S.last && !S.last.fb ? S.last : null
      const target = prev && prev.kept && S.lastReal ? S.lastReal : prev
      if (prev && target && S.state) {
        const neg = C.isNegativeFeedback(head)
        if (neg) {
          prev.fb = true; target.fb = true
          if (!prev.noLearn) C.learnOutcome(S.state, target, S.ladder, 'bad')
          S.state.counters.autoCorrections += 1; S.state.counters.corrections += 1
          S.sess.forcedUp = 1; S.sess.forcedReason = 'negatives Feedback: ' + rungName(target.finalKey) + ' war zu schwach'
          await persist($)
        } else if (C.isPositiveFeedback(head)) {
          prev.fb = true; target.fb = true
          if (!prev.noLearn) C.learnOutcome(S.state, target, S.ladder, 'ok')
          S.state.counters.confirmations += 1
          await persist($)
        } else if (full && !C.CONTINUATION.test(full)) {
          prev.fb = true
          if (!prev.noLearn && !prev.inherited && !prev.kept) C.learnOutcome(S.state, target, S.ladder, 'weak-ok')
        }
      }
    } catch {}
    return next(e)
  })

  on('turn.start', async ($, e, next) => {
    try {
      if (S.ladder.length) {
        const text = cleanPrompt(typeof e.text === 'string' ? e.text : '', true)
        let now = 0
        try { now = await $.clock.now() } catch {}
        const lastRung = S.sess.lastKey ? S.ladder.find((r) => r.key === S.sess.lastKey) : null
        S.sess.warm = !!(lastRung && S.sess.lastTurnAt && now - S.sess.lastTurnAt < S.ttl)
        S.sess.effortKeepsCache = lastRung ? C.effortChangeKeepsCache(lastRung.id, S.provider, S.flags) : false
        // abgelaufene Verfuegbarkeitssperren (30 min) aufheben
        let pruned = false
        for (const [fam, ts] of [...S.unavailable.entries()]) if (now - ts > 1800000) { S.unavailable.delete(fam); pruned = true }
        if (pruned) { rebuild(); S.fallback = '' }
        const fu = S.sess.forcedUp
        const d = C.decide({ state: S.state, text, ladder: S.ladder, sess: { ...S.sess, forcedUp: 0 } })
        if (d) {
          d.steps = 0; d.escCount = 0; d.lastEscStep = 0; d.escalated = false; d.maxErrRepeat = 0; d.noLearn = false
          if (d.kept && S.lastReal) { d.sig = S.lastReal.sig; d.lmIdx = S.lastReal.lmIdx; d.features = S.lastReal.features; d.expectedSteps = S.lastReal.expectedSteps; d.inherited = true }
          if (fu > 0) {
            // negatives Feedback: mindestens eine Stufe ueber der vorigen (erst Effort, dann Modell), nie darunter
            const iPrev = lastRung ? S.ladder.findIndex((r) => r.key === lastRung.key) : -1
            const iNow = S.ladder.findIndex((r) => r.key === d.finalKey)
            const t = S.ladder[Math.min(S.ladder.length - 1, Math.max(iNow, iPrev >= 0 ? iPrev + fu : iNow + fu))]
            d.rung = t; d.startKey = t.key; d.finalKey = t.key; d.forced = true
            d.reason += ' · ' + (S.sess.forcedReason || 'Korrektur nach Rueckmeldung')
          }
          d.t = now
          S.turns.set(e.turnId, d); S.current = d; S.lastDecision = d
          S.sess.forcedUp = 0; S.sess.forcedReason = ''
          S.errs = {}
          if (d.features.includes('vague') && (S.state.counters.turns % 3 === 0)) $.ui.log('Auto Router: Prompt ist sehr knapp. Ziel, Datei und erwartetes Ergebnis nennen spart Rueckfragen und Tokens.')
          if (S.turns.size > 40) S.turns.delete(S.turns.keys().next().value)
        }
      }
    } catch {}
    return next(e)
  })

  on('tool.call', async ($, e, next) => {
    const r = await next(e)
    try {
      if (!e.agentId && !isIgnoredTool(e.tool) && r && r.isError === true) {
        const sig = String(e.tool) + ':' + C.sigHash(String(r.text || '').toLowerCase().replace(/\d+/g, '#').slice(0, 160))
        S.errs[sig] = (S.errs[sig] || 0) + 1
        const d = S.current
        if (d) d.maxErrRepeat = Math.max(d.maxErrRepeat || 0, S.errs[sig])
      }
    } catch {}
    return r
  })

  on('turn.step', async function* ($, e, next) {
    if (e.agentId || !S.ladder.length) return yield* next(e)
    // Beobachtete Basis-IDs (nur wenn nicht gepinnt/konfiguriert) und manuelles /effort
    try {
      const p = C.parseModelId(e.model)
      if (p && !S.observed[p.family] && !S.envPins[p.family] && !(S.cfg.modelIds && S.cfg.modelIds[p.family]) && S.provider !== 'anthropic') {
        S.observed[p.family] = e.model; rebuild()
      }
      if (e.index === 0) {
        const b = S.base
        const dd0 = S.turns.get(e.turnId)
        const ult = !!(dd0 && dd0.features && dd0.features.includes('ultrathink'))
        if (!ult && b && b.model === e.model && b.effort !== e.effort && !S.effortPaused) {
          // Basiswert der Engine hat sich geaendert, ohne dass wir es waren: manuelles /effort
          S.effortPaused = true; S.effortReason = 'manuelles /effort erkannt (Basis ' + String(b.effort) + ' -> ' + String(e.effort) + ')'
        }
        if (!ult) S.base = { model: e.model, effort: e.effort }
      }
    } catch {}
    const d = S.turns.get(e.turnId)
    if (!d || (S.modelPaused && S.effortPaused)) return yield* next(e)

    d.steps += 1
    if (S.modelPaused || S.effortPaused) d.noLearn = true
    // In-Task-Eskalation: erst Effort (Leiter), dann Modell
    try {
      if (d.escCount < 2 && d.steps - d.lastEscStep >= 3) {
        const fam = (S.ladder.find((r) => r.key === d.finalKey) || {}).family
        const over = d.steps > (d.expectedSteps || 4) * 1.5 + (fam === 'haiku' ? 1 : 3)
        const rep = (d.maxErrRepeat || 0) >= 3
        if (over || rep) {
          const up = C.escalateRung(S.ladder, d.finalKey, 1)
          if (up && up.key !== d.finalKey) {
            const prevFam = fam
            d.escReason = rep ? 'gleicher Fehler wiederholt' : 'deutlich mehr Schritte als erwartet'
            d.finalKey = up.key; d.rung = up; d.escCount += 1; d.lastEscStep = d.steps; d.escalated = true; d.maxErrRepeat = 0; S.errs = {}
            S.state.counters.escalations += 1
            if (up.family === prevFam) S.state.counters.effortEscalations += 1; else S.state.counters.modelEscalations += 1
            $.ui.log('Auto Router: Eskalation ' + rungName(d.startKey) + ' -> ' + rungName(up.key) + ' (' + d.escReason + ')')
          }
        }
      }
    } catch {}

    const plan = (rung) => {
      let model = e.model; let effort = e.effort
      if (!S.modelPaused) {
        model = rung.id
        const lv = levelsOf(model)
        effort = S.effortPaused ? (typeof e.effort === 'string' && lv.includes(e.effort) ? e.effort : nearestLevel(lv, typeof e.effort === 'string' ? e.effort : undefined)) : (rung.effort || undefined)
      } else if (!S.effortPaused) {
        const lv = levelsOf(e.model)
        effort = lv.length && rung.effort ? nearestLevel(lv, rung.effort) : e.effort
      }
      return { model, effort }
    }
    const withPlan = (p) => { const { effort: _x, ...rest } = e; return p.effort === undefined ? { ...rest, model: p.model } : { ...rest, model: p.model, effort: p.effort } }

    let p = plan(d.rung)
    S.lastReq = { model: p.model, effort: p.effort }
    let result
    let yielded = false
    const attempt = async function* (x) {
      const it = next(x)
      while (true) {
        const n = await it.next()
        if (n.done) return n.value
        yielded = true
        yield n.value
      }
    }
    try {
      result = yield* attempt(withPlan(p))
    } catch (err) {
      // Nur wenn UNSER Modell (nicht das der Engine) vor jeder Ausgabe scheiterte: Fallback-Kette versuchen.
      const failed = S.ladder.find((r) => r.id === p.model)
      if (!failed || p.model === e.model || yielded) throw err
      const msg = String((err && (err.message || err.name)) || err)
      const sure = UNAVAILABLE_RE.test(msg)
      const chain = ['opus', 'sonnet', 'haiku']
      const from = chain.indexOf(failed.family)
      const cands = []
      for (const f of chain.slice(from + 1)) { const r = S.ladder.find((x) => x.family === f); if (r) cands.push(r) }
      let lastErr = err; let done = false
      for (const r of cands.slice(0, 2)) {
        const np = plan(r)
        try {
          S.lastReq = { model: np.model, effort: np.effort }
          result = yield* attempt(withPlan(np)); done = true
          d.finalKey = r.key; d.rung = r; p = np
          break
        } catch (e2) { lastErr = e2; if (yielded) throw e2 }
      }
      if (!done) {
        if (p.model !== e.model) {
          try { S.lastReq = { model: e.model, effort: e.effort }; result = yield* attempt(e); done = true; p = { model: e.model, effort: e.effort } } catch (e3) { lastErr = e3 }
        }
        if (!done) throw lastErr
      }
      // Verfuegbarkeitssignal (kein Qualitaetssignal): ein anderes Modell klappte, unseres nicht
      let now = 0
      try { now = await $.clock.now() } catch {}
      S.unavailable.set(failed.family, now); d.noLearn = true; rebuild()
      S.fallback = failed.family + ' nicht verfuegbar' + (sure ? '' : ' (Fehler, anderes Modell ging)') + ' -> ' + (d.finalKey ? rungName(d.finalKey) : 'Engine-Modell')
    }
    try {
      if (onlyIgnoredTools(result)) { d.steps = Math.max(0, d.steps - 1) }
      const u = result && result.usage
      if (u) {
        if (u.model) { S.used = { model: u.model, effort: S.lastReq.effort }; d.actual = u.model
          if (p.model && u.model !== p.model && !u.model.startsWith(p.model) && !p.model.startsWith(u.model)) { S.engineFallback = 'angefordert ' + p.model + ', geliefert ' + u.model; d.noLearn = true } }
        const t = (u.input_tokens || 0) + (u.cache_read_input_tokens || 0) + (u.cache_creation_input_tokens || 0) + (u.output_tokens || 0)
        if (t > 0) S.sess.ctxTokens = t
      }
    } catch {}
    return result
  })

  on('turn.complete', async ($, e, next) => {
    if (!e.agentId) {
      try {
        const d = S.turns.get(e.turnId)
        if (d) {
          let now = 0
          try { now = await $.clock.now() } catch {}
          S.state.counters.turns += 1
          S.sess.lastKey = d.finalKey; S.sess.lastScores = d.scores; S.sess.lastTurnAt = now
          if (e.reason === 'error' || e.reason === 'refusal') d.noLearn = true
          if (e.reason === 'aborted') { d.noLearn = true; d.fb = true }
          if (e.usage && e.usage.model) { S.used = { model: e.usage.model, effort: S.lastReq.effort }; d.actual = e.usage.model }
          if (d.escalated && !d.noLearn && !d.kept) { C.learnOutcome(S.state, d, S.ladder, 'escalated'); d.fb = true }
          S.last = d
          if (!d.kept) S.lastReal = d
          S.log.push({ t: new Date(now || 0).toISOString().slice(0, 19), sig: d.sig, f: d.features.slice(0, 8), key: rungName(d.finalKey), conf: Number(d.conf.toFixed(2)), steps: d.steps, esc: d.escalated ? rungName(d.startKey) + '>' + rungName(d.finalKey) : '', nl: d.noLearn ? 1 : 0 })
          if (S.log.length > 200) S.log = S.log.slice(-200)
          await persist($)
        }
      } catch {}
    }
    return next(e)
  })

  on('classic.PostModelSwitch', async ($, e, next) => {
    try {
      const to = String(e.to_model || '')
      if (e.source === 'auto') {
        S.engineFallback = 'Engine-Fallback auf ' + to + ' (Verfuegbarkeit, kein Qualitaetssignal)'
      } else if (e.source === 'resume') {
        // Modell beim Fortsetzen wiederhergestellt: kein manueller Eingriff
      } else if (to && to !== S.lastReq.model) {
        S.modelPaused = true; S.modelReason = 'manuelles /model (' + e.source + ') auf ' + to
      }
    } catch {}
    return next(e)
  })

  on('ui.render', { component: 'Spinner' }, async ($, e, next) => {
    const d = S.lastDecision
    if (!d || (S.modelPaused && S.effortPaused)) return next(e)
    const old = e.props.suffix || ''
    const tag = 'auto:' + rungName(d.finalKey) + (d.escalated ? ' escalated' : '')
    return next({ ...e, props: { ...e.props, suffix: old ? old + ' · ' + tag : ' · ' + tag } })
  })
}
'@
    Write-Utf8 (Join-Path $TestsDir 'router.test.ts') @'
import { test, expect, mock } from 'claude-code/testing'
import * as C from '../hooks/core.js'

const H = 'claude-haiku-5-5'
const S = 'claude-sonnet-5-5'
const O = 'claude-opus-5-5'

// Kleine Test-Hilfe: stellt die Engine unter dem Plugin nach (keine Modellanfragen, kein Netzwerk).
async function boot($: any, on: any, o: any = {}) {
  const store = new Map<string, any>(Object.entries(o.store || {}))
  const rec: any = { store, cacheRead: undefined, steps: [], writes: {}, logs: [], toolUses: [], fail: null, usageModel: null }
  const files: Record<string, string> = { ...(o.files || {}) }
  on('store.get', async (_$: any, e: any) => ({ value: store.get(e.key) }))
  on('store.set', async (_$: any, e: any) => { store.set(e.key, JSON.parse(JSON.stringify(e.value))); return { value: undefined } })
  on('store.delete', async (_$: any, e: any) => { store.delete(e.key); return { value: undefined } })
  on('store.keys', async () => ({ value: [...store.keys()] }))
  on('classic.PostModelSwitch', async () => ({}))
  mock.env(on, o.env || {})
  const clock = mock.clock(on, { now: 1_800_000_000_000 })
  on('session.start', async (_$: any, e: any) => ({ cwd: e.cwd }))
  on('settings.read', async () => ({ value: o.settings || {} }))
  on('session.surfaces', async () => ({ value: o.surfaces || ['terminal'] }))
  on('fs.read', async (_$: any, e: any) => {
    const hit = Object.keys(files).find((k) => String(e.path).replace(/\\/g, '/').endsWith(k))
    if (hit === undefined) return { deny: 'ENOENT' }
    return { value: files[hit] }
  })
  on('fs.write', async (_$: any, e: any) => {
    if (o.noWrite) return { deny: 'EACCES' }
    rec.writes[String(e.path).replace(/\\/g, '/')] = e.text
    return { value: undefined }
  })
  on('command.register', async (_$: any, e: any) => ({ value: { command: e.name } }))
  on('ui.log', async (_$: any, e: any) => { rec.logs.push(String(e.text ?? e.message ?? JSON.stringify(e))); return { value: undefined } })
  on('prompt.submit', async (_$: any, e: any) => ({ text: e.text }))
  on('turn.start', async (_$: any, e: any) => ({ turnId: e.turnId }))
  on('turn.complete', async (_$: any, e: any) => ({ text: e.answer }))
  on('turn.step', async function* (_$: any, e: any) {
    rec.steps.push(e)
    if (rec.fail) { const err = rec.fail(e); if (err) throw err }
    const usage = { model: rec.usageModel || e.model, input_tokens: 800, output_tokens: 100, cache_read_input_tokens: rec.cacheRead ?? 3000, cache_creation_input_tokens: 0 }
    yield { kind: 'stop', stopReason: 'end_turn', usage }
    return { turnId: e.turnId, index: e.index, answer: 'ok', toolUses: rec.toolUses, stopReason: 'end_turn', usage }
  })
  on('tool.call', async (_$: any, e: any) => (rec.toolErr ? { result: 'x', text: rec.toolErr, isError: true } : { result: 'x', text: 'x' }))
  await $.session.start({ cwd: '/work', surface: 'terminal', isInteractive: true })
  let n = 0
  const base = { model: o.baseModel || S, effort: o.baseEffort === undefined ? 'medium' : o.baseEffort }
  const api = {
    rec, clock, base,
    // ein Turn; liefert die an die Engine gesendeten Schritte
    async ask(text: string, opt: any = {}) {
      const turnId = 't' + ++n
      const from = rec.steps.length
      await $.prompt.submit({ text, wait: false, origin: { kind: 'composer' } })
      await $.turn.start({ text, turnId })
      for (let i = 0; i < (opt.steps || 1); i++) {
        if (opt.toolErrEach) await $.tool.call({ tool: 'Bash', command: 'false' })
        const st = $.turn.step({ turnId, index: i, model: opt.baseModel || base.model, effort: opt.baseEffort === undefined ? base.effort : opt.baseEffort, messageCount: 2 + i, ...(opt.agentId ? { agentId: opt.agentId } : {}) })
        for await (const _c of st) { /* verbrauchen */ }
        await st.result
      }
      await $.turn.complete({ answer: 'fertig', durationMs: 5, isAborted: !!opt.abort, turnId, reason: opt.abort ? 'aborted' : (opt.reason || 'answer') })
      if (opt.advance) await clock.advance(opt.advance)
      return rec.steps.slice(from)
    },
    async cmd(name: string, args = '') {
      return await $.command.run({ command: name, args, origin: { kind: 'composer' }, presentation: { layout: 'main', columns: 120 } } as any)
    },
    async status() { return String((await api.cmd('autorouter', 'status')).text) }
  }
  return api
}

test('Smoke: einfache Leseaufgabe -> Haiku, Effort low', async ($, on) => {
  const t = await boot($, on)
  const s = await t.ask('Zeige mir den Inhalt der Datei README.md')
  expect(s[0].model).toBe(H)
  expect(s[0].effort).toBe('low')
})

const BEDROCK = { CLAUDE_CODE_USE_BEDROCK: '1' }
const last = (s: any[]) => s[s.length - 1]

// ---------------------------------------------------------------- Routing nach Aufgabenart
test('Kurze Erklaerung -> Haiku low', async ($, on) => {
  const t = await boot($, on)
  const s = await t.ask('Erkläre kurz den Unterschied zwischen TCP und UDP')
  expect([s[0].model, s[0].effort]).toEqual([H, 'low'])
})
test('Kleine eindeutige Codeaufgabe -> Sonnet low', async ($, on) => {
  const t = await boot($, on)
  const s = await t.ask('Fuege in utils.py eine kleine Funktion add(a,b) hinzu')
  expect([s[0].model, s[0].effort]).toEqual([S, 'low'])
})
test('Normale Codeaenderung (mehrere Dateien) -> Sonnet medium', async ($, on) => {
  const t = await boot($, on)
  const s = await t.ask('Erweitere server.py und models.py um eine Validierung der Eingaben und schreibe Tests dafuer')
  expect([s[0].model, s[0].effort]).toEqual([S, 'medium'])
})
test('Debugging bestehender Code -> Sonnet high', async ($, on) => {
  const t = await boot($, on)
  const s = await t.ask('Der Docker Container startet nicht, Fehler: permission denied beim Mount von /data. Finde die Ursache und behebe den Bug')
  expect([s[0].model, s[0].effort]).toEqual([S, 'high'])
})
test('Komplexes Debugging -> Sonnet xhigh', async ($, on) => {
  const t = await boot($, on)
  const s = await t.ask('Komplexer Fehler: der Worker haengt manchmal, Ursache unklar, mehrere Services betroffen. Debugge das gruendlich')
  expect([s[0].model, s[0].effort]).toEqual([S, 'xhigh'])
})
test('Architektur -> Opus (medium/high)', async ($, on) => {
  const t = await boot($, on)
  const s = await t.ask('Entwirf die Architektur fuer ein Microservice-System mit Event-Bus, mehreren Datenbanken und Skalierung')
  expect(s[0].model).toBe(O)
  expect(['medium', 'high']).toContain(s[0].effort)
})
test('Security kritisch -> Opus xhigh/max', async ($, on) => {
  const t = await boot($, on)
  const s = await t.ask('Pruefe die Authentifizierung auf kritische Sicherheitsluecken und Architektur-Schwachstellen, schwieriges Threat Model')
  expect(s[0].model).toBe(O)
  expect(['xhigh', 'max']).toContain(s[0].effort)
})
test('Race Condition -> Opus xhigh/max', async ($, on) => {
  const t = await boot($, on)
  const s = await t.ask('Finde die Race Condition in der Queue, die nur selten auftritt und deren Ursache unbekannt ist')
  expect(s[0].model).toBe(O)
  expect(['xhigh', 'max']).toContain(s[0].effort)
})
test('Sehr langer Prompt wird nie Haiku und nicht niedriger als normal', async ($, on) => {
  const t = await boot($, on)
  const long = 'Zeige mir den Inhalt der Datei. ' + 'Zusaetzlicher Kontext zum Projekt und seinen Anforderungen. '.repeat(60)
  const s = await t.ask(long)
  expect(s[0].model).not.toBe(H)
})
test('ultrathink ist kein Effort-Wert', async ($, on) => {
  const t = await boot($, on)
  const s = await t.ask('ultrathink: plane die Migration der Datenbank von server.py und models.py')
  expect(C.EFFORTS).toContain(s[0].effort)
})

// ---------------------------------------------------------------- Fortsetzung, Feedback, Lernen
test('"weiter" behaelt Modell und Effort (Cache)', async ($, on) => {
  const t = await boot($, on)
  const a = await t.ask('Entwirf die Architektur fuer ein Microservice-System mit Event-Bus, mehreren Datenbanken und Skalierung')
  for (const w of ['weiter', 'ok', 'ja', 'mach weiter', 'genau']) {
    const b = await t.ask(w)
    expect([b[0].model, b[0].effort]).toEqual([a[0].model, a[0].effort])
  }
})
test('Negatives Feedback -> eine Stufe hoeher, Zaehler, kein Umkippen der Strategie', async ($, on) => {
  const t = await boot($, on)
  const a = await t.ask('Fuege in utils.py eine kleine Funktion add(a,b) hinzu')
  expect(a[0].effort).toBe('low')
  const b = await t.ask('das ist falsch, geht noch nicht')
  expect([b[0].model, b[0].effort]).toEqual([S, 'medium'])
  expect(await t.status()).toContain('Auto-Korrekturen: 1')
  // eine Korrektur aendert die Strategie nicht: neue gleichartige Aufgabe startet wieder nach Regel
  await t.ask('danke', { advance: 600_000 })
  const c = await t.ask('Zeige mir den Inhalt der Datei README.md', { advance: 600_000 })
  expect([c[0].model, c[0].effort]).toEqual([H, 'low'])
})
test('Positives Feedback zaehlt als Bestaetigung (schwach), aendert die Stufe nicht', async ($, on) => {
  const t = await boot($, on)
  const a = await t.ask('Fuege in utils.py eine kleine Funktion add(a,b) hinzu')
  const b = await t.ask('perfekt, danke')
  expect(await t.status()).toContain('Bestaetigungen: 1')
  expect(b[0].model).not.toBe(O)
  expect(a[0].effort).toBe('low')
})
test('Effort-Eskalation in der Aufgabe: erst Effort, gleiches Modell', async ($, on) => {
  const t = await boot($, on)
  const s = await t.ask('Erweitere server.py und models.py um eine Validierung der Eingaben und schreibe Tests dafuer', { steps: 14 })
  expect(s[0].effort).toBe('medium')
  expect(last(s).model).toBe(S)
  expect(C.EFFORTS.indexOf(last(s).effort)).toBeGreaterThan(C.EFFORTS.indexOf('medium'))
  expect(await t.status()).toContain('Effort 1')
})
test('Modell-Eskalation in der Aufgabe: Sonnet xhigh -> Opus', async ($, on) => {
  const t = await boot($, on)
  const s = await t.ask('Komplexer Fehler: der Worker haengt manchmal, Ursache unklar, mehrere Services betroffen. Debugge das gruendlich', { steps: 20 })
  expect([s[0].model, s[0].effort]).toEqual([S, 'xhigh'])
  expect(last(s).model).toBe(O)
})
test('Wiederholter gleicher Fehler eskaliert', async ($, on) => {
  const t = await boot($, on)
  t.rec.toolErr = 'ModuleNotFoundError: No module named foo'
  const s = await t.ask('Erweitere server.py und models.py um eine Validierung der Eingaben und schreibe Tests dafuer', { steps: 5, toolErrEach: true })
  expect(C.EFFORTS.indexOf(last(s).effort)).toBeGreaterThan(C.EFFORTS.indexOf(s[0].effort))
})
test('Downshift wird vorsichtig gelernt (viele sichere Erfolge)', async ($, on) => {
  const t = await boot($, on)
  const p = 'Der Docker Container startet nicht, Fehler: permission denied beim Mount von /data. Finde die Ursache und behebe den Bug'
  const first = await t.ask(p)
  expect(first[0].effort).toBe('high')
  for (let i = 0; i < 6; i++) { await t.ask(p, { advance: 600_000 }); await t.ask('danke', { advance: 600_000 }) }
  const after = await t.ask(p, { advance: 600_000 })
  expect(after[0].model).toBe(S)
  expect(C.EFFORTS.indexOf(after[0].effort)).toBeLessThan(C.EFFORTS.indexOf('high'))
})
test('Gelernt: Sonnet high reicht - kein Sprung auf Opus nach Eskalation medium->high', async ($, on) => {
  const t = await boot($, on)
  const p = 'Erweitere server.py und models.py um eine Validierung der Eingaben und schreibe Tests dafuer'
  for (let i = 0; i < 3; i++) { await t.ask(p, { steps: 14, advance: 600_000 }) }
  const s = await t.ask(p, { advance: 600_000 })
  expect(s[0].model).toBe(S)
  expect(['high', 'medium']).toContain(s[0].effort)
})

// ---------------------------------------------------------------- Registry / Verfuegbarkeit
test('Modell ohne Effort-Unterstuetzung bekommt keinen erfundenen Effort', async ($, on) => {
  const m = 'claude-sonnet-4-5'
  const t = await boot($, on, { env: { ...BEDROCK, ANTHROPIC_DEFAULT_SONNET_MODEL: m }, baseModel: m, baseEffort: undefined })
  const s = await t.ask('Erweitere server.py und models.py um eine Validierung der Eingaben und schreibe Tests dafuer', { baseModel: m, baseEffort: undefined })
  expect(s[0].model).toBe(m)
  expect('effort' in s[0] && s[0].effort !== undefined).toBe(false)
})
test('Unbekannte IDs werden nicht geraten (Provider ohne Pins) - Router reicht durch', async ($, on) => {
  const t = await boot($, on, { env: BEDROCK, baseModel: 'my-custom-arn', baseEffort: undefined })
  const s = await t.ask('Entwirf die Architektur fuer ein Microservice-System', { baseModel: 'my-custom-arn', baseEffort: undefined })
  expect(s[0].model).toBe('my-custom-arn')
  expect(await t.status()).toContain('kein sicher erkanntes Modell')
})
test('Providerspezifische Modell-IDs werden exakt verwendet', async ($, on) => {
  const ids = { H: 'us.anthropic.claude-haiku-5-5-v1:0', S: 'us.anthropic.claude-sonnet-5-5-v1:0', O: 'us.anthropic.claude-opus-5-5-v1:0' }
  const t = await boot($, on, { env: { ...BEDROCK, ANTHROPIC_DEFAULT_HAIKU_MODEL: ids.H, ANTHROPIC_DEFAULT_SONNET_MODEL: ids.S, ANTHROPIC_DEFAULT_OPUS_MODEL: ids.O }, baseModel: ids.S })
  const a = await t.ask('Zeige mir den Inhalt der Datei README.md', { baseModel: ids.S })
  const b = await t.ask('Entwirf die Architektur fuer ein Microservice-System mit Event-Bus, mehreren Datenbanken und Skalierung', { baseModel: ids.S, advance: 600_000 })
  expect(a[0].model).toBe(ids.H)
  expect(b[0].model).toBe(ids.O)
})
test('availableModels beschraenkt die Auswahl (kein Opus)', async ($, on) => {
  const t = await boot($, on, { settings: { availableModels: ['sonnet', 'haiku'] } })
  const s = await t.ask('Entwirf die Architektur fuer ein Microservice-System mit Event-Bus, mehreren Datenbanken und Skalierung', { steps: 16 })
  for (const x of s) expect(x.model).not.toBe(O)
})
test('maxEffortLevel begrenzt den Effort', async ($, on) => {
  const t = await boot($, on, { settings: { maxEffortLevel: 'high' } })
  const s = await t.ask('Finde die Race Condition in der Queue, die nur selten auftritt und deren Ursache unbekannt ist')
  expect(C.EFFORTS.indexOf(s[0].effort)).toBeLessThanOrEqual(C.EFFORTS.indexOf('high'))
})
test('Modell nicht verfuegbar -> Fallback-Kette, kein Qualitaetslernen', async ($, on) => {
  const t = await boot($, on)
  t.rec.fail = (e: any) => (e.model === O ? new Error('404 not_found_error: model: ' + O) : null)
  const s = await t.ask('Entwirf die Architektur fuer ein Microservice-System mit Event-Bus, mehreren Datenbanken und Skalierung')
  expect(s[0].model).toBe(O)
  expect(last(s).model).toBe(S)
  const st = await t.status()
  expect(st).toContain('opus nicht verfuegbar')
  const b = await t.ask('Entwirf eine weitere Architektur fuer ein Event-System mit mehreren Datenbanken', { advance: 600_000 })
  expect(b[0].model).not.toBe(O)
  expect(await t.status()).toContain('Modell-Beispiele 0')
})
test('Anderer Fehler (kein Verfuegbarkeitsfehler) wird nicht verschluckt', async ($, on) => {
  const t = await boot($, on)
  t.rec.fail = () => new Error('network reset')
  let threw = false
  try { await t.ask('Entwirf die Architektur fuer ein Microservice-System mit Event-Bus, mehreren Datenbanken und Skalierung') } catch { threw = true }
  expect(threw).toBe(true)
})
test('Fable bleibt aus (Standard, Konfig allein reicht nicht, nie automatisch)', async ($, on) => {
  const t = await boot($, on, { files: { 'data/router-config.json': JSON.stringify({ allowFable: true }) } })
  const hard = 'Finde die Race Condition in der Queue, die nur selten auftritt und deren Ursache unbekannt ist. Kritisch, in Produktion, Architektur, schwierig'
  const s = await t.ask(hard, { steps: 30 })
  for (const x of s) expect(String(x.model)).not.toContain('fable')
  const st = await t.status()
  expect(st).toContain('fable=claude-fable-5-1 [aus')
})
test('Fable nur mit allowFable UND fableCreditsConfirmed im Registry-Status', async ($, on) => {
  const t = await boot($, on, { files: { 'data/router-config.json': JSON.stringify({ allowFable: true, fableCreditsConfirmed: true }) } })
  const st = await t.status()
  expect(st).toContain('fable=claude-fable-5-1 effort')
  const reg = C.buildRegistry({ provider: 'anthropic', config: { allowFable: true }, settings: {} })
  expect(reg.byFamily.fable.available).toBe(false)
  expect(reg.byFamily.fable.mayRequireUsageCredits).toBe(true)
})
test('Fast-Mode/Advisor/best: der Router fuegt nur model und effort hinzu', async ($, on) => {
  const t = await boot($, on)
  const inKeys = ['turnId', 'index', 'model', 'effort', 'messageCount'].sort()
  const s = await t.ask('Entwirf die Architektur fuer ein Microservice-System mit Event-Bus, mehreren Datenbanken und Skalierung')
  expect(Object.keys(s[0]).sort()).toEqual(inKeys)
  expect(await t.status()).toContain('Nie automatisch: Fable')
  const reg = C.buildRegistry({ provider: 'anthropic', settings: {}, config: {} })
  expect(reg.byFamily.sonnet.supportsFastMode).toBe('unknown')
})

// ---------------------------------------------------------------- Manuelle Eingriffe
test('Manuelles /model pausiert nur die Modellwahl', async ($, on) => {
  const t = await boot($, on)
  await $.classic.PostModelSwitch({ from_model: S, to_model: H, requested_model: 'haiku', source: 'command', context_tokens: 0, cache_warm: false } as any)
  const s = await t.ask('Entwirf die Architektur fuer ein Microservice-System mit Event-Bus, mehreren Datenbanken und Skalierung', { baseModel: H, baseEffort: 'low' })
  expect(s[0].model).toBe(H)
  const st = await t.status()
  expect(st).toContain('Modell PAUSIERT')
  await t.cmd('router-model-auto')
  const b = await t.ask('Entwirf die Architektur fuer ein Microservice-System mit Event-Bus, mehreren Datenbanken und Skalierung', { baseModel: H, baseEffort: 'low', advance: 600_000 })
  expect(b[0].model).toBe(O)
})
test('Automatischer Engine-Fallback ist kein manueller Eingriff', async ($, on) => {
  const t = await boot($, on)
  await $.classic.PostModelSwitch({ from_model: O, to_model: S, requested_model: null, source: 'auto', context_tokens: 0 } as any)
  const st = await t.status()
  expect(st).toContain('Modell aktiv')
  expect(st).toContain('Engine-Fallback')
})
test('Manuelles /effort pausiert nur die Effort-Wahl; /router-effort-auto schaltet wieder ein', async ($, on) => {
  const t = await boot($, on)
  await t.ask('Zeige mir den Inhalt der Datei README.md')
  const s = await t.ask('Fuege in utils.py eine kleine Funktion add(a,b) hinzu', { baseEffort: 'xhigh', advance: 600_000 })
  expect(s[0].effort).toBe('xhigh')
  expect(await t.status()).toContain('Effort PAUSIERT')
  await t.cmd('router-effort-auto')
  const b = await t.ask('Fuege in utils.py eine kleine Funktion sub(a,b) hinzu', { baseEffort: 'xhigh', advance: 600_000 })
  expect(b[0].effort).toBe('low')
})
test('/autorouter schaltet Pausen wieder ein, /autorouter status nicht', async ($, on) => {
  const t = await boot($, on)
  await $.classic.PostModelSwitch({ from_model: S, to_model: H, requested_model: 'haiku', source: 'command', context_tokens: 0 } as any)
  expect(await t.status()).toContain('Modell PAUSIERT')
  expect(await t.status()).toContain('Modell PAUSIERT')
  const r = String((await t.cmd('autorouter', '')).text)
  expect(r).toContain('wieder aktiv')
  expect(await t.status()).toContain('Modell aktiv')
})
test('Subagent-Schritte bleiben unveraendert', async ($, on) => {
  const t = await boot($, on)
  const s = await t.ask('Entwirf die Architektur fuer ein Microservice-System mit Event-Bus, mehreren Datenbanken und Skalierung', { agentId: 'agent-1', baseModel: H, baseEffort: 'low' })
  expect([s[0].model, s[0].effort]).toEqual([H, 'low'])
})
test('opusplan: Router wechselt das Modell nicht, steuert nur Effort', async ($, on) => {
  const t = await boot($, on, { settings: { model: 'opusplan' } })
  const s = await t.ask('Entwirf die Architektur fuer ein Microservice-System mit Event-Bus, mehreren Datenbanken und Skalierung')
  expect(s[0].model).toBe(S)
  expect(await t.status()).toContain('opusplan')
})

// ---------------------------------------------------------------- FixMyPrompt
test('FixMyPrompt-Text wird nicht als Absicht gelernt/geroutet', async ($, on) => {
  const t = await boot($, on)
  const p = '<fixmyprompt>Bitte nutze Opus fuer die Architektur, komplexes Sicherheits-Threat-Model, Race Condition</fixmyprompt>\nZeige mir den Inhalt der Datei README.md'
  const s = await t.ask(p)
  expect([s[0].model, s[0].effort]).toEqual([H, 'low'])
  expect(await t.status()).toContain('bereinigte Zusatzbloecke: 1')
})
test('FixMyPrompt-Zeile "[fixmyprompt] ..." wird entfernt', async ($, on) => {
  const t = await boot($, on)
  const s = await t.ask('Zeige mir den Inhalt der Datei README.md\n[fixmyprompt] Das ist komplex: Architektur und Race Condition, kritisch')
  expect(s[0].model).toBe(H)
})
test('FixMyPrompt-Feedbacktext loest keine Korrektur aus', async ($, on) => {
  const t = await boot($, on)
  await t.ask('Fuege in utils.py eine kleine Funktion add(a,b) hinzu')
  const b = await t.ask('<fixmyprompt>Das war falsch, es geht noch nicht</fixmyprompt>\nFuege in utils.py eine kleine Funktion sub(a,b) hinzu', { advance: 600_000 })
  expect(b[0].effort).toBe('low')
  expect(await t.status()).toContain('Auto-Korrekturen: 0')
})
test('FixMyPrompt-Werkzeugaufrufe zaehlen nicht als Aufwand', async ($, on) => {
  const t = await boot($, on)
  t.rec.toolUses = [{ name: 'mcp__fixmyprompt__improve', input: {} }]
  const s = await t.ask('Zeige mir den Inhalt der Datei README.md', { steps: 10 })
  for (const x of s) expect([x.model, x.effort]).toEqual([H, 'low'])
})
test('Gewoehnliche Werkzeugaufrufe zaehlen (Gegenprobe): Haiku-Aufgabe wird eskaliert', async ($, on) => {
  const t = await boot($, on)
  t.rec.toolUses = [{ name: 'Bash', input: {} }]
  const s = await t.ask('Zeige mir den Inhalt der Datei README.md', { steps: 10 })
  expect(last(s).model === H && last(s).effort === 'low').toBe(false)
})

// ---------------------------------------------------------------- Cache-Schutz
test('Cache-Schutz: Modellwechsel nach unten bei grossem warmem Kontext wird gehalten, bei kaltem Cache erlaubt', async ($, on) => {
  const t = await boot($, on)
  t.rec.cacheRead = 150_000
  const dbg = 'Der Docker Container startet nicht, Fehler: permission denied beim Mount von /data. Finde die Ursache und behebe den Bug'
  await t.ask('Entwirf die Architektur fuer ein Microservice-System mit Event-Bus, mehreren Datenbanken und Skalierung')
  const warm = await t.ask(dbg)
  expect(warm[0].model).toBe(O)
  const st = await t.status()
  expect(st).toContain('Cache-Schutz: aktiv')
  expect(st).toContain('Cache warm')
  await t.clock.advance(2 * 3_600_000)
  const cold = await t.ask(dbg)
  expect([cold[0].model, cold[0].effort]).toEqual([S, 'high'])
})
test('Kleine Effort-Wechsel im selben Modell bleiben bei warmem Cache moeglich', async ($, on) => {
  const t = await boot($, on)
  const a = await t.ask('Fuege in utils.py eine kleine Funktion add(a,b) hinzu')
  const b = await t.ask('Der Docker Container startet nicht, Fehler: permission denied beim Mount von /data. Finde die Ursache und behebe den Bug')
  expect(a[0].model).toBe(b[0].model)
  expect(b[0].effort).toBe('high')
})
test('Starke Qualitaetssignale umgehen den Cache-Schutz (negatives Feedback)', async ($, on) => {
  const t = await boot($, on)
  t.rec.cacheRead = 150_000
  await t.ask('Fuege in utils.py eine kleine Funktion add(a,b) hinzu')
  const b = await t.ask('das stimmt nicht, falsch')
  expect(C.EFFORTS.indexOf(b[0].effort)).toBeGreaterThan(C.EFFORTS.indexOf('low'))
})

// ---------------------------------------------------------------- Speicher, Datenschutz, Migration
test('Obsidian: Lernstand wird abgelegt, ohne Prompt-Text', async ($, on) => {
  const t = await boot($, on, { files: { 'data/vault.txt': 'C:/Vault' } })
  await t.ask('Zeige mir den Inhalt der Datei GEHEIM-4711-passwort.md')
  const paths = Object.keys(t.rec.writes)
  expect(paths.some((p) => p.endsWith('/Auto Router/Lernstand V7.md'))).toBe(true)
  expect(paths.some((p) => p.endsWith('/Auto Router/Entscheidungen V7.md'))).toBe(true)
  for (const body of Object.values(t.rec.writes) as string[]) { expect(body).not.toContain('GEHEIM-4711'); expect(body).not.toContain('passwort') }
  const stored = JSON.stringify(t.rec.store.get('ma-auto-router-v7-state')) + JSON.stringify(t.rec.store.get('ma-auto-router-v7-log'))
  expect(stored).not.toContain('GEHEIM-4711')
})
test('Obsidian/Dateien nicht beschreibbar: Routing laeuft weiter', async ($, on) => {
  const t = await boot($, on, { files: { 'data/vault.txt': 'C:/Vault' }, noWrite: true })
  const s = await t.ask('Zeige mir den Inhalt der Datei README.md')
  expect(s[0].model).toBe(H)
  const st = await t.status()
  expect(st).toContain('lokal nicht verfuegbar')
  expect(st).toContain('Obsidian nicht verfuegbar')
})
test('Beschaedigte Lerndatei wird abgefangen', async ($, on) => {
  const t = await boot($, on, { files: { 'data/router-state-v7.json': '{kaputt' }, store: { 'ma-auto-router-v7-state': { v: 7, lmModel: { c: 3, n: 'x', w: { a: ['x'] } }, cells: 5 } } })
  const s = await t.ask('Zeige mir den Inhalt der Datei README.md')
  expect([s[0].model, s[0].effort]).toEqual([H, 'low'])
  expect(await t.status()).toMatch(/beschaedigt/)
})
test('V6-Lerndaten werden uebernommen, Original bleibt', async ($, on) => {
  const v6 = { corrections: 4, autoCorrections: 2, confirmations: 3, featureBias: { debug: { haiku: 0, sonnet: 1, opus: 0 } }, signatureBias: {} }
  const lm6 = { n: 42, w: { 'u:docker': [-0.1, 0.4, 0.2] } }
  const t = await boot($, on, { store: { 'adaptive-learning-v2': v6, 'router-lm-v1': lm6 } })
  const st = await t.status()
  expect(st).toContain('Modell-Beispiele 42')
  expect(st).toContain('V6-Lerndaten uebernommen')
  expect(t.rec.store.get('adaptive-learning-v2')).toEqual(v6)
  expect(t.rec.store.get('router-lm-v1')).toEqual(lm6)
})
test('Eigene Ignore-Muster aus data/ignore-blocks.txt', async ($, on) => {
  const t = await boot($, on, { files: { 'data/ignore-blocks.txt': '# Kommentar\n<meta-hilfe>[\\s\\S]*?</meta-hilfe>\n' } })
  const s = await t.ask('<meta-hilfe>komplexe Architektur, Race Condition, Security kritisch</meta-hilfe>\nZeige mir den Inhalt der Datei README.md')
  expect(s[0].model).toBe(H)
})
test('/router-reset setzt Gelerntes zurueck', async ($, on) => {
  const t = await boot($, on, { store: { 'router-lm-v1': { n: 30, w: {} } } })
  expect(await t.status()).toContain('Modell-Beispiele 30')
  await t.cmd('router-reset')
  expect(await t.status()).toContain('Modell-Beispiele 0')
})
test('/router-zu-schwach und /router-zu-stark lernen vorsichtig', async ($, on) => {
  const t = await boot($, on)
  await t.ask('Fuege in utils.py eine kleine Funktion add(a,b) hinzu')
  expect(String((await t.cmd('router-zu-schwach')).text)).toContain('zu schwach')
  const b = await t.ask('Fuege in utils.py eine kleine Funktion sub(a,b) hinzu', { advance: 600_000 })
  expect(C.EFFORTS.indexOf(b[0].effort)).toBeGreaterThanOrEqual(C.EFFORTS.indexOf('low'))
  expect(String((await t.cmd('router-zu-stark')).text)).toContain('ueberdimensioniert')
})

// ---------------------------------------------------------------- Status / Oberflaeche
test('Status zeigt alle geforderten Felder', async ($, on) => {
  const t = await boot($, on, { surfaces: ['desktop'] })
  await t.ask('Entwirf die Architektur fuer ein Microservice-System mit Event-Bus, mehreren Datenbanken und Skalierung')
  const st = await t.status()
  for (const k of ['Auto Router V7.0', 'Oberflaeche: desktop', 'Routing: Modell aktiv', 'Gewaehlt: opus', 'angefordert:', 'tatsaechlich genutzt (API):', 'Merkmale:', 'Modell-Scores:', 'Effort-Scores:', 'Lernen:', 'Auto-Eskalationen:', 'Cache-Schutz: aktiv', 'Kontext:', 'Verfuegbarkeits-Fallback: nein', 'Registry:', 'Nie automatisch', 'Speicher:', 'nicht in Anthropic-gehosteten Cloud-Sessions']) expect(st).toContain(k)
})
test('Abgebrochener Turn wird nicht gelernt', async ($, on) => {
  const t = await boot($, on)
  await t.ask('Fuege in utils.py eine kleine Funktion add(a,b) hinzu', { abort: true })
  await t.ask('danke')
  expect(await t.status()).toContain('Modell-Beispiele 0')
})

// ---------------------------------------------------------------- reine Logik (core.js)
test('core: Effort-Stufen je Modell laut Tabelle, unbekannte IDs ohne Stufen', () => {
  expect(C.effortLevelsFor('claude-sonnet-4-5')).toEqual([])
  expect(C.effortLevelsFor('claude-haiku-5-5')).toEqual(C.EFFORTS)
  expect(C.effortLevelsFor('irgendwas')).toEqual([])
  expect(C.effortLevelsFor('us.anthropic.claude-opus-5-5-v1:0')).toEqual(C.EFFORTS)
})
test('core: Zustand wird bereinigt, Prompt-Text nie gespeichert', () => {
  const r = C.sanitizeState({ v: 7, lmModel: { c: 3, n: 1, w: { a: [1, 2, 'x'] } } })
  expect(r.ok).toBe(true)
  expect(r.state.lmModel.w.a).toBeUndefined()
  expect(C.sanitizeState('müll').ok).toBe(false)
  const idx = C.lmFeatureIdx('mein geheimer text', [])
  expect(idx.every((n: any) => typeof n === 'number')).toBe(true)
})
test('core: Lerngewicht waechst langsam', () => {
  expect([C.rampWeight(0), C.rampWeight(25), C.rampWeight(60), C.rampWeight(150)]).toEqual([0.1, 0.25, 0.55, 1])
})

test('V6.x-Dateien (lokal) werden gelesen, nie ueberschrieben', async ($, on) => {
  const t = await boot($, on, { files: { 'data/router-learning.json': JSON.stringify({ v: 1, learning: { corrections: 1, autoCorrections: 0, confirmations: 0, featureBias: {}, signatureBias: {} }, lm: { n: 17, w: {} } }) } })
  expect(await t.status()).toContain('Modell-Beispiele 17')
  await t.ask('Zeige mir den Inhalt der Datei README.md')
  expect(Object.keys(t.rec.writes).some((p) => p.endsWith('router-learning.json'))).toBe(false)
})
'@

    Write-Host '== 1/3 Strikte Plugin-Validierung (Staging) =='
    & $RealClaude plugin validate $StageDir --strict
    if ($LASTEXITCODE -ne 0) { throw 'Mod-Validierung fehlgeschlagen; bestehende Installation unveraendert.' }
    Write-Host '== 2/3 Tests (deterministisch, keine Modellanfragen) =='
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $testOut = (& $RealClaude plugin test $StageDir 2>&1 | Out-String)
    $testExit = $LASTEXITCODE
    $ErrorActionPreference = $prevEap
    Write-Host $testOut
    if ($testExit -ne 0) { throw 'Tests fehlgeschlagen; bestehende Installation unveraendert.' }
    $passCount = 0; $failCount = 0
    if ($testOut -match '(\d+)\s+pass') { $passCount = [int]$Matches[1] }
    if ($testOut -match '(\d+)\s+fail') { $failCount = [int]$Matches[1] }
    if ($failCount -gt 0 -or $passCount -lt 1) { throw 'Testausgabe meldet Fehler oder keine bestandenen Tests; bestehende Installation unveraendert.' }

    Write-Host '== 3/3 Sicherung und Installation =='
    $stamp = (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N').Substring(0, 8)
    $BackupDir = Join-Path (Join-Path $env:LOCALAPPDATA 'ma-auto-router-backups') $stamp
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
    if (Test-Path -LiteralPath $TargetModDir) {
        Copy-Item -LiteralPath $TargetModDir -Destination (Join-Path $BackupDir 'mod') -Recurse
    }
    $ProfileExisted = Test-Path -LiteralPath $PROFILE
    if ($ProfileExisted) { Copy-Item -LiteralPath $PROFILE -Destination (Join-Path $BackupDir 'profile.ps1') }
    $oldProfile = if ($ProfileExisted) { [IO.File]::ReadAllText($PROFILE) } else { '' }
    $newProfile = $oldProfile
    # Profil nur aendern, wenn noetig: ein vorhandener Block, der schon auf genau diesen Mod-Ordner zeigt, bleibt unveraendert.
    $escapedMod = $TargetModDir.Replace("'", "''")
    $blockPresent = $false
    $mBlock = [regex]::Match($oldProfile, '(?ms)^# BEGIN MA AUTO ROUTER V6\r?\n.*?^# END MA AUTO ROUTER V6')
    if ($mBlock.Success -and $mBlock.Value.Contains("'" + $escapedMod + "'")) { $blockPresent = $true }
    if (-not $blockPresent) {
        foreach ($version in @('V4', 'V5', 'V6')) {
            $pattern = '(?ms)^# BEGIN MA AUTO ROUTER ' + $version + '\r?\n.*?^# END MA AUTO ROUTER ' + $version + '[^\r\n]*(?:\r?\n)?'
            $newProfile = [regex]::Replace($newProfile, $pattern, '')
        }
        $block = @"
# BEGIN MA AUTO ROUTER V6
`$script:MA_AUTO_ROUTER_MOD_DIR = '$escapedMod'
if ([string]::IsNullOrWhiteSpace(`$env:CLAUDE_CODE_PLUGIN_DIRS)) {
    `$env:CLAUDE_CODE_PLUGIN_DIRS = `$script:MA_AUTO_ROUTER_MOD_DIR
} elseif (-not ((`$env:CLAUDE_CODE_PLUGIN_DIRS -split ';') -contains `$script:MA_AUTO_ROUTER_MOD_DIR)) {
    `$env:CLAUDE_CODE_PLUGIN_DIRS += ';' + `$script:MA_AUTO_ROUTER_MOD_DIR
}
# END MA AUTO ROUTER V6
"@
        $newProfile = $newProfile.TrimEnd() + "`r`n`r`n" + $block + "`r`n"
    }

    $Mutated = $true
    foreach ($relative in $installFiles) {
        $target = Join-Path $TargetModDir $relative
        New-Item -ItemType Directory -Force -Path (Split-Path $target) | Out-Null
        Copy-Item -LiteralPath (Join-Path $StageDir $relative) -Destination $target -Force
    }
    foreach ($relative in $legacyFiles) {
        $target = Join-Path $TargetModDir $relative
        if (Test-Path -LiteralPath $target) { Remove-Item -LiteralPath $target -Force }
    }
    # Datenordner: bestehende Dateien (Lerndaten, vault.txt, Ignore-Listen) bleiben unveraendert.
    $dataDir = Join-Path $TargetModDir 'data'
    New-Item -ItemType Directory -Force -Path $dataDir | Out-Null
    if ([string]::IsNullOrWhiteSpace($VaultPath)) {
        $existing = Join-Path $dataDir 'vault.txt'
        if (Test-Path -LiteralPath $existing) { $VaultPath = ([IO.File]::ReadAllText($existing)).Trim() }
        else { $VaultPath = (Read-Host 'Pfad zum Obsidian-Vault (Enter = nur lokaler Ordner)').Trim().Trim('"') }
    }
    if (-not [string]::IsNullOrWhiteSpace($VaultPath) -and (Test-Path -LiteralPath $VaultPath -PathType Container)) {
        Write-Utf8 (Join-Path $dataDir 'vault.txt') $VaultPath
        Write-Host ('Obsidian-Ablage: ' + (Join-Path $VaultPath 'Auto Router'))
    } elseif (-not [string]::IsNullOrWhiteSpace($VaultPath)) {
        Write-Warning "Vault-Pfad nicht gefunden: $VaultPath. Es wird nur lokal gespeichert."
    }
    $ignoreFile = Join-Path $dataDir 'ignore-blocks.txt'
    if (-not (Test-Path -LiteralPath $ignoreFile)) {
        Write-Utf8 $ignoreFile @'
# Hook-Fall: Eine Regex pro Zeile. Passender Text wird vor Einordnung und Lernen aus dem Prompt entfernt.
# Standardmuster fuer <fixmyprompt>...</fixmyprompt> und Zeilen mit [FixMyPrompt] sind schon eingebaut (Annahme).
# Beispiel, wenn dein Hook Text nach einer Trennzeile anhaengt (ohne # eintragen):
# ^---FMP---[\s\S]*$
'@
    }
    $ignoreTools = Join-Path $dataDir 'ignore-tools.txt'
    if (-not (Test-Path -LiteralPath $ignoreTools)) {
        Write-Utf8 $ignoreTools @'
# MCP-Fall: Eine Regex pro Zeile fuer Werkzeugnamen (z.B. mcp__server__tool).
# Schritte, die nur diese Werkzeuge aufrufen, zaehlen nicht als Aufwand und loesen keine Eskalation aus.
# "fixmyprompt" ist schon eingebaut (Annahme ueber den Namen); weitere Namen hier eintragen.
'@
    }
    $configFile = Join-Path $dataDir 'router-config.json'
    if (-not (Test-Path -LiteralPath $configFile)) {
        Write-Utf8 $configFile @'
{
  "allowFable": false,
  "fableCreditsConfirmed": false,
  "maxEffort": "max",
  "modelIds": {}
}
'@
    }
    New-Item -ItemType Directory -Force -Path (Split-Path $PROFILE) | Out-Null
    if ($newProfile -ne $oldProfile) {
        # UTF-8 BOM keeps Windows PowerShell 5.1 profiles readable too.
        [IO.File]::WriteAllText($PROFILE, $newProfile, (New-Object Text.UTF8Encoding $true))
    }
    if ([string]::IsNullOrWhiteSpace($oldEnv)) { $env:CLAUDE_CODE_PLUGIN_DIRS = $TargetModDir }
    elseif (-not (($oldEnv -split ';') -contains $TargetModDir)) { $env:CLAUDE_CODE_PLUGIN_DIRS = $oldEnv + ';' + $TargetModDir }

    $rollback = @'
$ErrorActionPreference = 'Stop'
$state = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'rollback.json') -Raw | ConvertFrom-Json
# Aenderungen seit der Installation vor dem Zuruecksetzen sichern.
$before = Join-Path $PSScriptRoot ('before-rollback-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Force -Path $before | Out-Null
foreach ($rel in $state.files) {
    $target = Join-Path $state.target $rel
    if (Test-Path -LiteralPath $target) {
        $save = Join-Path $before $rel
        New-Item -ItemType Directory -Force -Path (Split-Path $save) | Out-Null
        Copy-Item -LiteralPath $target -Destination $save
    }
    $old = Join-Path (Join-Path $PSScriptRoot 'mod') $rel
    if (Test-Path -LiteralPath $old) { Copy-Item -LiteralPath $old -Destination $target -Force }
    elseif (Test-Path -LiteralPath $target) { Remove-Item -LiteralPath $target -Force }
}
# Profil nur zuruecksetzen, wenn es seit der Installation nicht weiter geaendert wurde.
$profileNow = if (Test-Path -LiteralPath $state.profile) { [IO.File]::ReadAllText($state.profile) } else { '' }
if ($profileNow -eq $state.installedProfile) {
    if ($state.profileExisted) { Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'profile.ps1') -Destination $state.profile -Force }
    elseif (Test-Path -LiteralPath $state.profile) { Remove-Item -LiteralPath $state.profile -Force }
} else { Write-Warning 'Profil seit Installation geaendert: nicht zurueckgesetzt. Sicherung: profile.ps1' }
$env:CLAUDE_CODE_PLUGIN_DIRS = $state.oldEnv
Write-Host 'V7 zurueckgenommen (V6.x-Dateien wiederhergestellt). Lerndaten im Ordner data bleiben erhalten. PowerShell und Claude Code neu starten.'
'@
    $state = @{ target = $TargetModDir; profile = [string]$PROFILE; profileExisted = $ProfileExisted; installedProfile = $newProfile; oldEnv = $oldEnv; files = $touchedFiles }
    Write-Utf8 (Join-Path $BackupDir 'rollback.json') ($state | ConvertTo-Json -Depth 5)
    Write-Utf8 (Join-Path $BackupDir 'rollback.ps1') $rollback
    Write-Host ''
    Write-Host ("V7 installiert. Tests: $passCount bestanden, $failCount fehlgeschlagen (Claude Code $currentVersion, deterministisch, ohne Modellanfragen).")
    Write-Host "Installationspfad: $TargetModDir"
    Write-Host "Sicherung (V6.x + Lerndaten): $BackupDir"
    Write-Host ('Rollback:  & "' + (Join-Path $BackupDir 'rollback.ps1') + '"')
    Write-Host ('Lerndaten lokal: ' + (Join-Path $TargetModDir 'data'))
    Write-Host 'Start in diesem PowerShell-Fenster (Claude Code vorher beenden):'
    Write-Host ('& "' + $RealClaude + '" --model sonnet')
    Write-Host 'In Claude: /autorouter = Status (und Pausen aufheben), /autorouter status = nur Anzeige, /router-auto /router-model-auto /router-effort-auto /router-reset /router-zu-schwach /router-zu-stark.'
    Write-Host 'Wichtig: Die Wirkung im echten Betrieb (tatsaechlich genutzte Modelle) bitte mit /autorouter pruefen; dieser Installer fuehrt keine echten Modellanfragen aus.'
} catch {
    $failure = $_
    if ($Mutated -and $BackupDir) {
        foreach ($relative in $touchedFiles) {
            $target = Join-Path $TargetModDir $relative
            $old = Join-Path (Join-Path $BackupDir 'mod') $relative
            if (Test-Path -LiteralPath $old) { Copy-Item -LiteralPath $old -Destination $target -Force }
            elseif (Test-Path -LiteralPath $target) { Remove-Item -LiteralPath $target -Force }
        }
        if ($ProfileExisted) { Copy-Item -LiteralPath (Join-Path $BackupDir 'profile.ps1') -Destination $PROFILE -Force }
        elseif (Test-Path -LiteralPath $PROFILE) { Remove-Item -LiteralPath $PROFILE -Force }
        $env:CLAUDE_CODE_PLUGIN_DIRS = $oldEnv
    }
    throw $failure
} finally {
    if (Test-Path -LiteralPath $StageDir) { Remove-Item -LiteralPath $StageDir -Recurse -Force }
}
