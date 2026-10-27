#!/usr/bin/env python3
"""Erzeugt js/port.js aus dem Bestands-app.js (Logik 1:1 uebernommen, nur Adapter drumherum).
Bereiche: Neu, Musik, Einstellungen, Wissen (Graph), Vault (Editor), JARVIS-Auftraege (V16)."""
import io, re, sys, pathlib

SRC = pathlib.Path("legacy/app.js")
OUT = pathlib.Path("js/port.js")
L = SRC.read_text(encoding="utf-8").split("\n")
seg = lambda a, b: "\n".join(L[a - 1:b])          # 1-basiert, inklusiv

# Plausibilitaetsanker: die Schnittgrenzen muessen auf Top-Level-Deklarationen liegen
def expect(n, start):
    assert L[n - 1].startswith(start), f"Zeile {n}: erwartet '{start}', ist '{L[n-1][:60]}'"
expect(6, "const ICONS = {"); expect(40, "const ico = ")
expect(958, "function mdDoc("); expect(993, "}")
expect(1081, "let graphCache"); expect(1110, "async function wissen()")
expect(1226, "const V = {"); expect(1451, "}")
expect(1511, "async function neu()"); expect(1701, "async function jarvis()")

# Ende des jarvis()-Blocks: Zeile vor 'async function route()'
end_j = next(i for i, l in enumerate(L, 1) if l.startswith("const ROUTES = ")) - 1
while not L[end_j - 1].strip() or L[end_j - 1].startswith("//"):
    end_j -= 1
assert L[end_j - 1].strip() == "}", f"jarvis() endet nicht auf '}}': {L[end_j-1][:60]!r}"

PRE = """/* MA-HOME HQ — Port der Bestandsbereiche Neu, Musik, Einstellungen, Wissen (Graph), Vault (Editor), JARVIS-Auftraege.
   GENERIERT von build_port.py aus legacy/app.js: Logik und API-Vertraege 1:1 uebernommen (nur Adapter: view/head/ico/me). */
import { $, esc, api, cop, toast, mdLite, items, fmtBytes, fmtDate, fmtTok, fmtUp, fmtAgo, today } from './api.js';
import { openViewer, pushLayer, closeViewer } from './viewer.js';

let view = null;                              // aktuelles Wurzelelement (#view der Shell)
let me = { user: '', admin: false, domain: '' };
export const setMe = m => { me = m || me; };
const VERSION = '2026-10-27';
const CTX_MAX = 200000;
const head = (title, sub, extra = '') => '<div class="top"><div><h1>' + title + '</h1><div class="sub">' + (sub || '') + '</div></div>' + extra + '</div>';
"""

body = "\n".join([
    seg(6, 40),                                   # ICONS + ico
    "",
    seg(958, 993),                                # mdDoc (mit V.att fuer Vault-Anhaenge)
    "",
    seg(1081, 1096),                              # Graph-Cache, loadGraph, openNote, Wikilink-Klick, GCOL
    "",
    seg(1110, 1451),                              # wissen() + Vault (V, vnote, vindex, ..., vdraw)
    "",
    seg(1511, end_j),                             # neu, Musik, einstellungen, JARVIS V16
])

POST = """

/* ---- Exporte: je Ansicht das Wurzelelement setzen, dann die Bestandsfunktion starten ---- */
export const renderNeu = r => { view = r; return neu(); };
export const renderMusik = r => { view = r; return musik(); };
export const renderEinstellungen = r => { view = r; return einstellungen(); };
export const renderWissen = r => { view = r; return wissen(); };
export const renderVault = r => { view = r; return vault(); };
export const renderJarvis = r => { view = r; return jarvis(); };
"""

code = PRE + "\n" + body + POST
# Das Altportal prueft Hash-Routen mit '#/jarvis' – identisch zur neuen Shell, keine Anpassung noetig.
A = "  const w = e.target.closest('.wl'); if (!w) return;\n  try { const g = await loadGraph();"
assert code.count(A) == 1, 'globaler Wikilink-Handler nicht gefunden'
code = code.replace(A, "  const w = e.target.closest('.wl'); if (!w || w.closest('#vread')) return;   // Vault-Leser navigiert selbst\n  try { const g = await loadGraph();")
OUT.write_text(code, encoding="utf-8", newline="\n")
print("geschrieben:", OUT, len(code), "Zeichen,", code.count("\n"), "Zeilen; jarvis endet bei Altzeile", end_j)
