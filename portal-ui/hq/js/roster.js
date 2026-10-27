/* MA-HOME HQ — Roster + Raeume (Living HQ). Bewohner = die 18 jarvis-* Profile + 2 Systemakteure.
   Raumzuordnung ist Konfiguration (Schreibtisch), keine Aktivitaetsbehauptung. */

export const W = 1200, Hh = 720;     // virtuelle Weltgroesse

export const ROOMS = {
  zentrale:  { name: 'Zentrale',            x: 400, y: 40,  w: 400, h: 220, color: '#35C4D8' },
  forschung: { name: 'Forschung',           x: 40,  y: 40,  w: 330, h: 220, color: '#B8A892' },
  council:   { name: 'Council-Konferenz',   x: 830, y: 40,  w: 330, h: 220, color: '#D9BFA8' },
  dev:       { name: 'Entwicklerbüro',      x: 40,  y: 290, w: 400, h: 200, color: '#5B8DEF' },
  kreativ:   { name: 'Kreativstudio',       x: 470, y: 290, w: 240, h: 200, color: '#FF5470' },
  qa:        { name: 'QA-Lab',              x: 740, y: 290, w: 420, h: 200, color: '#4ADE80' },
  infra:     { name: 'Infrastruktur',       x: 40,  y: 520, w: 420, h: 170, color: '#22D3EE' },
  server:    { name: 'Serverraum',          x: 490, y: 520, w: 670, h: 170, color: '#FF2E4D' }
};

/* id, Kurzrolle, Raum */
export const ROSTER = [
  ['jarvis-cloud-dev',     'Koordinator Cloud-Council',        'zentrale'],
  ['jarvis-planner',       'Planung & kritischer Pfad',        'zentrale'],
  ['jarvis-context',       'Projektkontext & Quellen',         'zentrale'],
  ['jarvis-architecture',  'Architektur & Schnittstellen',     'council'],
  ['jarvis-integrator',    'Patches & Integration',            'council'],
  ['jarvis-dependencies',  'Abhängigkeiten & Versionen',       'council'],
  ['jarvis-core',          'Core & Integration',               'dev'],
  ['jarvis-server-fix',    'MA-Server Bugs & Betrieb',         'dev'],
  ['jarvis-router',        'MA Auto Router',                   'dev'],
  ['jarvis-portal',        'Webportal & APIs',                 'dev'],
  ['jarvis-research',      'Recherche & Evidenz',              'forschung'],
  ['jarvis-brain',         'Cognitive Brain & Memory',         'forschung'],
  ['jarvis-qa',            'Tests & Abnahme',                  'qa'],
  ['jarvis-recovery',      'Checkpoint & Recovery',            'qa'],
  ['jarvis-security',      'Sicherheit & Datenschutz',         'qa'],
  ['jarvis-worker',        'Worker & Ressourcen',              'infra'],
  ['jarvis-observability', 'Telemetrie & Fehlerkorrelation',   'infra'],
  ['jarvis-design',        'UI/UX & Designqualität',           'kreativ']
];

/* Systemakteure (Heartbeat-Tabelle) im Serverraum; jarvis-core hat zusaetzlich einen Profil-Schreibtisch im Entwicklerbüro */
export const SYSTEM = [['watchdog', 'Watchdog (Systemakteur)', 'server']];

/* Schreibtisch-Slots je Raum (Gitter im Raum, ohne Titelzeile) */
export function slots(room, n) {
  const r = ROOMS[room], padX = 46, top = 74, bottom = 34;
  if (room === 'server') return Array.from({ length: n }, (_, i) => ({ x: r.x + 110 + i * 90, y: r.y + 100 }));   // links neben den Racks
  const cols = Math.max(1, Math.min(n, Math.floor((r.w - padX) / 84)));
  const rows = Math.ceil(n / cols);
  const cw = (r.w - padX) / cols, ch = (r.h - top - bottom) / Math.max(1, rows);
  const out = [];
  for (let i = 0; i < n; i++) {
    const c = i % cols, rr = Math.floor(i / cols);
    out.push({ x: r.x + padX / 2 + cw * (c + 0.5), y: r.y + top + ch * (rr + 0.5) });
  }
  return out;
}
