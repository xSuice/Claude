"""Generates design-varianten.html (static mockups with sample data, clearly labeled) and prints WCAG contrast ratios."""
import json,sys
def lum(h):
    h=h.lstrip('#');r,g,b=[int(h[i:i+2],16)/255 for i in (0,2,4)]
    f=lambda c:c/12.92 if c<=0.03928 else ((c+0.055)/1.055)**2.4
    return 0.2126*f(r)+0.7152*f(g)+0.0722*f(b)
def cr(a,b):
    la,lb=sorted((lum(a),lum(b)),reverse=True);return round((la+0.05)/(lb+0.05),2)
V={
 'A':dict(name='A · Headquarters Slate (live)',desc='Der heutige Stand: Schiefer, Cyan-Akzent, Crimson für Alarm. Ruhig, hohe Informationsdichte, Underglow nur als Dekor.',bg='#0E1116',card='#151920',line='#262C36',text='#E6EAF0',muted='#8A93A0',acc='#3DD6E0',acc2='#7AA2F7',bad='#FF6B6B',glow='rgba(61,214,224,.10)'),
 'B':dict(name='B · Arc Reactor',desc='Iron-Man-Anmutung: tiefes Blau, zentraler „Reaktor“-Kern mit Ringen, Gold als zweiter Akzent. Stärkster Wiedererkennungswert, etwas mehr Dekor (nur bei erlaubter Bewegung animiert).',bg='#070B14',card='#0D1626',line='#1E3350',text='#EAF4FF',muted='#93A9C6',acc='#5CE1FF',acc2='#FFB547',bad='#FF7A85',glow='rgba(92,225,255,.16)'),
 'C':dict(name='C · Quiet Console (hell)',desc='Ruhige helle Konsole: warmes Papier, Petrol-Akzent, sehr hoher Kontrast, kaum Dekor. Beste Lesbarkeit draußen/auf dem Handy, geringste Last. Dunkelmodus wäre eine Ableitung von A.',bg='#F5F2EC',card='#FFFFFF',line='#D9D3C7',text='#1B1F24',muted='#4B525C',acc='#0A6C70',acc2='#8A5A00',bad='#B42318',glow='rgba(10,108,112,.06)'),
}
rows={}
for k,v in V.items():
    rows[k]=dict(text=cr(v['text'],v['card']),muted=cr(v['muted'],v['card']),acc=cr(v['acc'],v['card']),acc2=cr(v['acc2'],v['card']),bad=cr(v['bad'],v['card']))
print(json.dumps(rows,indent=1))
agents=[('qa','prüft','TASK-114 Regressionslauf',1),('core','arbeitet','TASK-117 Persistenz',1),('security','Planung','TASK-121 Review',0),('portal','ohne Auftrag','–',0),('router','arbeitet','TASK-118 Quoten',1),('worker','offline','PC aus',-1)]
def frame_main(v):
    return f'''<div class=frame><div class=tag>Entwurf · Beispieldaten</div><div class=side><b class=logo>JARVIS HQ</b><i class=on>Zentrale</i><i>Aufträge</i><i>Agenten</i><i>Council</i><i>Freigaben</i><i>Einstellungen</i></div>
<div class=main><h4>Guten Tag, Andre</h4><div class=hero><div class=core><span></span><span></span><span></span><em>JARVIS<br><small>bereit</small></em></div><div class=herotxt><p class=big>3 Aufträge laufen, 1 wartet auf deine Freigabe.</p><p class=mut>Letzte Meldung: „TASK-114 bestanden“ vor 4 min</p><button>Freigabe prüfen</button></div></div>
<div class=kpis><div><small>Agenten aktiv</small><b>3 / 18</b></div><div><small>Offene Aufträge</small><b>8</b></div><div class=badk><small>Incidents</small><b>1</b></div><div><small>Heute (Ledger)</small><b>46 Aufrufe</b></div></div>
<ul class=feed><li><i class=d ok></i>TASK-114 abgeschlossen (qa)</li><li><i class=d warn></i>Heartbeat veraltet: worker</li><li><i class=d></i>TASK-118 gestartet (router)</li></ul></div></div>'''
def frame_tasks(v):
    rws=''.join(f'<tr><td><i class="d {"ok" if s==1 else "warn" if s==-1 else ""}"></i> {a}</td><td>{st}</td><td>{t}</td></tr>' for a,st,t,s in agents)
    return f'''<div class=frame><div class=tag>Entwurf · Beispieldaten</div><div class=side><b class=logo>JARVIS HQ</b><i>Zentrale</i><i>Aufträge</i><i class=on>Agenten</i><i>Council</i><i>Freigaben</i><i>Einstellungen</i></div>
<div class=main><h4>Aufträge &amp; Agenten</h4><div class=cols><div class=panel><h5>Agenten</h5><table><thead><tr><th>Agent</th><th>Status</th><th>Auftrag</th></tr></thead><tbody>{rws}</tbody></table></div>
<div class=panel><h5>Auftrag TASK-117</h5><ol class=steps><li class=done>Gespeichert &amp; geplant</li><li class=done>Council-Beschluss dokumentiert</li><li class=now>Ausführung (core) – Checkpoint 2/4</li><li>Unabhängige Prüfung (qa)</li><li>Abschluss &amp; Meldung</li></ol><p class=mut>Status „läuft“ nur bei echtem Start-Nachweis.</p></div></div></div></div>'''
def frame_mobile(v):
    return f'''<div class="frame phone"><div class=tag>Entwurf · Beispieldaten</div><div class=main><div class=top><b class=logo>JARVIS</b><span class=chip>● verbunden</span></div><div class="hero m"><div class="core s"><span></span><span></span><em>JARVIS<br><small>bereit</small></em></div><p class=big>1 Freigabe wartet.</p><button>Prüfen</button></div>
<div class=kpis m><div><small>Aktiv</small><b>3</b></div><div><small>Offen</small><b>8</b></div><div class=badk><small>Incidents</small><b>1</b></div></div><ul class=feed><li><i class="d ok"></i>TASK-114 fertig</li><li><i class="d warn"></i>worker offline</li></ul></div><nav class=tab><span class=on>Zentrale</span><span>Aufträge</span><span>Agenten</span><span>Mehr</span></nav></div>'''
css_tpl='''.v{display:none}.v.show{display:block}
.v[data-v="%(k)s"]{--bg:%(bg)s;--card:%(card)s;--line:%(line)s;--text:%(text)s;--muted:%(muted)s;--acc:%(acc)s;--acc2:%(acc2)s;--bad:%(bad)s;--glow:%(glow)s}'''
css=''.join(css_tpl%dict(k=k,**v) for k,v in V.items())
html=f'''<!doctype html><html lang=de><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>JARVIS HQ – Designvarianten (Entwurf)</title>
<style>
body{{margin:0;font:14px/1.5 system-ui,Segoe UI,sans-serif;background:#1a1d23;color:#e6eaf0}}
header.page{{padding:18px 24px;border-bottom:1px solid #333}}header.page h1{{margin:0 0 4px;font-size:20px}}header.page p{{margin:0;color:#b4bcc8;max-width:900px}}
.tabs{{display:flex;gap:8px;padding:12px 24px;flex-wrap:wrap}}.tabs button{{background:#252a33;color:#e6eaf0;border:1px solid #3a4150;border-radius:8px;padding:8px 14px;cursor:pointer;font:inherit}}.tabs button[aria-selected=true]{{background:#e6eaf0;color:#14171c;font-weight:600}}
.v{{padding:0 24px 40px}}.vh h2{{margin:8px 0 2px;font-size:17px}}.vh p{{margin:0 0 6px;color:#b4bcc8;max-width:900px}}.ratio{{font-size:12px;color:#b4bcc8}}
.grid{{display:grid;grid-template-columns:minmax(0,3fr) minmax(0,3fr) 300px;gap:16px;align-items:start}}@media(max-width:1200px){{.grid{{grid-template-columns:1fr}}}}
.frame{{position:relative;display:flex;min-height:420px;background:var(--bg);color:var(--text);border:1px solid var(--line);border-radius:12px;overflow:hidden;background-image:radial-gradient(circle at 70% 0,var(--glow),transparent 55%)}}
.frame .tag{{position:absolute;right:8px;bottom:6px;font-size:10px;color:var(--muted);border:1px dashed var(--line);padding:1px 6px;border-radius:10px;z-index:2;background:var(--bg)}}
.side{{width:128px;border-right:1px solid var(--line);padding:12px 8px;display:flex;flex-direction:column;gap:2px;font-size:12px}}.side i{{font-style:normal;padding:6px 8px;border-radius:6px;color:var(--muted)}}.side i.on{{background:var(--card);color:var(--acc);border-left:2px solid var(--acc)}}.logo{{color:var(--acc);letter-spacing:.08em;font-size:12px;margin-bottom:8px}}
.main{{flex:1;padding:14px;min-width:0}}h4{{margin:0 0 10px;font-size:15px}}h5{{margin:0 0 8px;font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em}}
.hero{{display:flex;gap:14px;align-items:center;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px;margin-bottom:10px}}.hero.m{{flex-direction:column;text-align:center}}
.core{{position:relative;width:96px;height:96px;flex:none;display:grid;place-items:center}}.core.s{{width:72px;height:72px}}.core span{{position:absolute;inset:0;border:2px solid var(--acc);border-radius:50%;opacity:.8}}.core span:nth-child(2){{inset:10px;border-color:var(--acc2);opacity:.55}}.core span:nth-child(3){{inset:22px;border-style:dashed;opacity:.5}}.core em{{font-style:normal;font-size:11px;text-align:center;color:var(--text);line-height:1.2}}.core small{{color:var(--acc)}}
.big{{margin:0 0 4px;font-size:15px;font-weight:600}}.mut{{margin:0 0 8px;color:var(--muted);font-size:12px}}button.cta,.hero button{{background:var(--acc);color:var(--bg);border:0;border-radius:8px;padding:7px 12px;font:inherit;font-weight:600}}
.kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:10px}}.kpis[m]{{grid-template-columns:repeat(3,1fr)}}.kpis div{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:8px}}.kpis small{{display:block;color:var(--muted);font-size:11px}}.kpis b{{font-size:15px}}.kpis .badk b{{color:var(--bad)}}
.feed{{list-style:none;margin:0;padding:0;font-size:12px}}.feed li{{padding:5px 0;border-top:1px solid var(--line);display:flex;gap:8px;align-items:center}}
.d{{width:8px;height:8px;border-radius:50%;background:var(--muted);display:inline-block}}.d[ok],.d.ok{{background:var(--acc)}}.d.warn,.d[warn]{{background:var(--bad)}}
.cols{{display:grid;grid-template-columns:1.3fr 1fr;gap:10px}}.panel{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px}}table{{width:100%;border-collapse:collapse;font-size:12px}}th{{text-align:left;color:var(--muted);font-weight:500;border-bottom:1px solid var(--line);padding:4px}}td{{padding:5px 4px;border-bottom:1px solid var(--line)}}td:first-child{{white-space:nowrap}}
.steps{{margin:0;padding-left:18px;font-size:12px;color:var(--muted)}}.steps .done{{color:var(--text)}}.steps .done::marker{{color:var(--acc)}}.steps .now{{color:var(--acc);font-weight:600}}
.phone .tag{{bottom:56px}}.phone{{width:300px;min-height:520px;flex-direction:column;border-radius:26px}}.phone .main{{padding:14px 12px}}.top{{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}}.chip{{font-size:11px;color:var(--acc);border:1px solid var(--line);border-radius:12px;padding:1px 8px}}
.tab{{display:flex;justify-content:space-around;border-top:1px solid var(--line);padding:10px 4px;font-size:11px;color:var(--muted);background:var(--card)}}.tab .on{{color:var(--acc);font-weight:600}}
.vote{{margin-top:10px;font-size:12px;color:#b4bcc8}}
@media (prefers-reduced-motion:no-preference){{.v[data-v=B] .core span:nth-child(1){{animation:spin 18s linear infinite}}}}@keyframes spin{{to{{transform:rotate(360deg)}}}}
{css}
</style>
<header class=page><h1>JARVIS Headquarters – Designvarianten (Entwurf zur Abnahme)</h1><p>Drei Richtungen, jeweils Hauptansicht, Aufträge/Agenten und Mobil. <b>Alle Inhalte sind Beispieldaten zur Veranschaulichung, keine Live-Werte.</b> Der Kern „JARVIS bereit“ und die Statuspunkte würden im echten Portal nur reale Backend-Ereignisse zeigen; Bewegung nur bei erlaubter Animation (reduzierte Bewegung wird respektiert).</p></header>
<div class=tabs role=tablist>{''.join(f'<button role=tab aria-selected={"true" if k=="A" else "false"} data-k={k}>{v["name"]}</button>' for k,v in V.items())}</div>
{''.join(f'<section class="v{" show" if k=="A" else ""}" data-v={k}><div class=vh><h2>{v["name"]}</h2><p>{v["desc"]}</p><p class=ratio>Kontrast (WCAG 1.4.3, Mindestwert 4,5:1) auf Kartenfläche: Text {rows[k]["text"]}:1 · gedämpfter Text {rows[k]["muted"]}:1 · Akzent {rows[k]["acc"]}:1 · Zweitakzent {rows[k]["acc2"]}:1 · Alarm {rows[k]["bad"]}:1</p></div><div class=grid>{frame_main(v)}{frame_tasks(v)}{frame_mobile(v)}</div></section>' for k,v in V.items())}
<script>document.querySelectorAll('.tabs button').forEach(b=>b.onclick=()=>{{document.querySelectorAll('.tabs button').forEach(x=>x.setAttribute('aria-selected',x===b));document.querySelectorAll('.v').forEach(s=>s.classList.toggle('show',s.dataset.v===b.dataset.k))}})</script></html>'''
out=sys.argv[1]
open(out,'w',encoding='utf-8').write(html)
print('written',len(html))
