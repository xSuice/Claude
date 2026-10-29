"""Tests für die Chat-Weiche (ma_chat_route): wer beantwortet eine Portal-Chat-Nachricht?
Regeln (Andrew 29.10.): automatisch, nicht auf Claude festgefahren; Fachfragen an die passende Hermes-Rolle;
„Spezialisten“ und schwierige Entscheidungen an den Supervisor; Claude nur, wenn Werkzeuge/Daten auf dem Server nötig sind.
Sicherheit: private Inhalte und alles mit Werkzeugbedarf bleiben bei Claude; jeder Fehler -> Claude (bisheriges Verhalten)."""
import json, os, sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, os.environ.get('ROUTE_DIR', str(Path(__file__).resolve().parent.parent)))
import ma_chat_route as R  # noqa: E402


class FakeFach:
    def __init__(self, fach='allgemein', fail=False):
        self.fach, self.fail, self.calls = fach, fail, []

    def __call__(self, text):
        self.calls.append(text)
        if self.fail:
            raise OSError('PC aus')
        return self.fach


def decide(prompt, fach='allgemein', fail=False, **kw):
    f = FakeFach(fach, fail)
    st = R.State(Path(tempfile.mkdtemp()) / 'route-state.json')
    req = {'mode': 'auto', 'model': 'auto', **kw.pop('req', {})}
    d = R.decide(prompt, req, has_images=kw.pop('img', False), has_files=kw.pop('files', False),
                 fach_of=f, state=st, alive=kw.pop('alive', lambda: True))
    return d, f


class Rules(unittest.TestCase):
    def test_fachfrage_geht_an_passende_rolle(self):
        for fach, role in (('sicherheit', 'jarvis-security'), ('entwicklung', 'jarvis-cloud-dev'), ('architektur', 'jarvis-architecture'),
                           ('betrieb', 'jarvis-server-fix'), ('design', 'jarvis-design'), ('planung', 'jarvis-planner'),
                           ('test', 'jarvis-qa'), ('abhaengigkeiten', 'jarvis-dependencies'), ('recherche', 'jarvis-research'),
                           ('allgemein', 'jarvis-research')):
            d, _ = decide('Wie sichere ich SSH am besten ab, was empfiehlst du?', fach)
            self.assertEqual(d['target'], role, fach)

    def test_entscheidung_und_spezialisten_gehen_an_supervisor(self):
        self.assertEqual(decide('Soll ich den Server aufrüsten oder einen Mini-PC kaufen?', 'entscheidung')[0]['target'], 'kimi-supervisor')
        d, f = decide('Frag mal die Spezialisten, ob Kotlin oder Java besser ist', 'entwicklung')
        self.assertEqual(d['target'], 'kimi-supervisor')
        self.assertEqual(decide('Was meint der Supervisor zu meinem Plan?', 'allgemein')[0]['target'], 'kimi-supervisor')
        self.assertEqual(decide('AI-Council: Prüfe diese Idee aus fünf Rollen ...\nIdee:\nEigenes Netzwerk', 'entscheidung')[0]['target'], 'kimi-supervisor')

    def test_pruefende_auftraege_gehen_an_den_hermes_ausfuehrer(self):
        for p in ('Prüf mal, wie voll die Festplatte auf dem Server ist', 'Zeig mir die Auslastung von CPU und RAM',
                  'Check, ob alle Dienste laufen', 'Analysiere die letzten Fehler im Portal-Log'):
            d, f = decide(p, 'ausfuehren')
            self.assertEqual(d['target'], 'jarvis-server', p)
            self.assertEqual(f.calls, [], 'Regel entscheidet vor dem Modell: ' + p)
        self.assertEqual(R.label({'target': 'jarvis-server', 'fach': None}), 'jarvis-server · Hermes-Ausführer (Nexum, Sandbox)')

    def test_ausfuehrer_nicht_fuer_dateien_daten_private_und_schreibrechte(self):
        for p in ('Prüf meine Notizen auf Tippfehler', 'Prüf die PDFs im Eingang', 'Zeig mir die Fotos von gestern',
                  'Prüf mein Passwort für das NAS', 'Check die Datei config.yaml'):
            self.assertEqual(decide(p, 'ausfuehren')[0]['target'], 'claude', p)
        for m in ('voll', 'voll_senden', 'notizen', 'plan', 'konnektoren', 'gespraech'):
            self.assertEqual(decide('Prüf mal die Festplatte', 'ausfuehren', req={'mode': m})[0]['target'], 'claude', m)
        self.assertEqual(decide('Prüf mal die Festplatte', 'ausfuehren', alive=lambda: False)[0]['target'], 'claude')

    def test_ausfuehrer_tageslimit_und_wrap_mit_eigenem_arbeitsordner(self):
        tmp = Path(tempfile.mkdtemp())
        runner = tmp / 'network_runner.py'
        runner.write_text('#', encoding='utf-8')
        old = (R.ROLE_RUNNER, R.EXEC_WORK)
        R.ROLE_RUNNER, R.EXEC_WORK = str(runner), str(tmp / 'jobs')
        try:
            st = R.State(tmp / 's.json')
            dec = lambda *a, **k: {'target': 'jarvis-server', 'why': 't', 'fach': None}
            a, env, lab, d = R.wrap(['claude'], 'Prüf die Festplatte', {}, decide_fn=dec, state=st, log_file=str(tmp / 'l'))
            cmd = json.loads(env['MA_ROUTE_LOCAL_CMD'])
            work = cmd[cmd.index('--') - 1]
            self.assertTrue(work.startswith(str(tmp / 'jobs')) and os.path.isdir(work), work)
            self.assertIn('terminal', env['MA_ROUTE_TOOLSETS'])
            self.assertEqual(env['MA_ROUTE_KIND'], 'exec')
            self.assertEqual(a[2:], ['jarvis-server', 'jarvis-server · Hermes-Ausführer (Nexum, Sandbox)'])
            for _ in range(R.LIMIT_EXEC):
                st.count('jarvis-server')
            c = R.decide('Prüf die Festplatte', {'mode': 'auto'}, fach_of=lambda t: 'ausfuehren', state=st, alive=lambda: True)
            self.assertEqual(c['target'], 'claude')
        finally:
            R.ROLE_RUNNER, R.EXEC_WORK = old

    def test_auftraege_und_eigene_daten_bleiben_bei_claude_ohne_modellfrage(self):
        for p in ('Sortier mir die Screenshots in einen Ordner',
                  'Was steht in meinen Notizen zu Java?', 'Schau in meinen Kalender', 'lösch die alten logs',
                  'kannste ma die PDFs im Eingang umbenennen', 'Durchsuche meine Notizen im Vault nach „x“',
                  'Nutze den Skill „uebergabe“.', 'Erstelle nur einen Plan (nichts ausführen, nichts ändern):\nx', '/status'):
            d, f = decide(p, 'allgemein')
            self.assertEqual(d['target'], 'claude', p)
            self.assertEqual(f.calls, [], 'Regel entscheidet vor dem Modell: ' + p)

    def test_modell_sagt_ausfuehren_dann_claude(self):
        self.assertEqual(decide('Kannst du dich mal um das Backup kümmern?', 'ausfuehren')[0]['target'], 'claude')

    def test_privates_bleibt_bei_claude(self):
        for p in ('Mein Passwort für das NAS ist vergessen, was tun?', 'Wie hoch ist mein Gehalt im Vergleich?',
                  'Ich habe eine Diagnose vom Arzt bekommen, was bedeutet sie?', 'Meine IBAN ist DE89370400440532013000, ist das gültig?'):
            self.assertEqual(decide(p, 'allgemein')[0]['target'], 'claude', p)

    def test_bilder_dateien_modi_und_gespraechsmodus_bleiben_bei_claude(self):
        q = 'Was hältst du von dieser Architektur, ist das sinnvoll?'
        self.assertEqual(decide(q, 'architektur', img=True)[0]['target'], 'claude')
        self.assertEqual(decide(q, 'architektur', files=True)[0]['target'], 'claude')
        for m in ('voll', 'voll_senden', 'notizen', 'plan', 'konnektoren', 'gespraech'):
            self.assertEqual(decide(q, 'architektur', req={'mode': m})[0]['target'], 'claude', m)
        self.assertEqual(decide(q, 'architektur', req={'model': 'opus'})[0]['target'], 'claude')   # Andrew hat Modell gewählt
        self.assertEqual(decide(q, 'architektur', req={'mode': 'lesen'})[0]['target'], 'jarvis-architecture')

    def test_ausdruecklich_claude_oder_ohne_router(self):
        self.assertEqual(decide('Frag Claude: was ist Docker?', 'allgemein')[0]['target'], 'claude')
        self.assertEqual(decide('ohne router: was ist Docker?', 'allgemein')[0]['target'], 'claude')

    def test_fehler_und_pc_aus_bedeuten_claude(self):
        self.assertEqual(decide('Wie sichere ich SSH ab?', fail=True)[0]['target'], 'claude')
        self.assertEqual(decide('Wie sichere ich SSH ab?', None)[0]['target'], 'claude')
        self.assertEqual(decide('Wie sichere ich SSH ab?', 'kochen')[0]['target'], 'claude')
        d, f = decide('Wie sichere ich SSH ab?', 'sicherheit', alive=lambda: False)
        self.assertEqual((d['target'], f.calls), ('claude', []))

    def test_tageslimits(self):
        st = R.State(Path(tempfile.mkdtemp()) / 's.json')
        f = FakeFach('entscheidung')
        for i in range(R.LIMIT_SUPERVISOR):
            self.assertEqual(R.decide('Soll ich A oder B nehmen, was meinst du?', {'mode': 'auto'}, fach_of=f, state=st, alive=lambda: True)['target'], 'kimi-supervisor')
            st.count('kimi-supervisor')
        d = R.decide('Soll ich A oder B nehmen, was meinst du?', {'mode': 'auto'}, fach_of=f, state=st, alive=lambda: True)
        self.assertEqual(d['target'], 'jarvis-planner', 'Supervisor-Limit erreicht -> Planer statt Claude')

    def test_aus_schalter(self):
        d, _ = decide('Wie sichere ich SSH ab?', 'sicherheit')
        self.assertEqual(d['target'], 'jarvis-security')
        old = R.MODE
        try:
            R.MODE = 'off'
            self.assertEqual(decide('Wie sichere ich SSH ab?', 'sicherheit')[0]['target'], 'claude')
        finally:
            R.MODE = old

    def test_entscheidung_hat_begruendung_und_label(self):
        d, _ = decide('Wie sichere ich SSH ab?', 'sicherheit')
        self.assertIn('sicherheit', d['why'])
        self.assertEqual(R.label(d), 'jarvis-security · Nexum (Fachrolle Sicherheit)')
        self.assertEqual(R.label({'target': 'kimi-supervisor', 'fach': 'entscheidung'}), 'kimi-supervisor · Supervisor')

    def test_server_modus_setzt_lokalen_runner_und_alive_ohne_pc(self):
        tmp = Path(tempfile.mkdtemp())
        runner = tmp / 'network_runner.py'
        runner.write_text('#', encoding='utf-8')
        old = R.ROLE_RUNNER
        R.ROLE_RUNNER = str(runner)
        try:
            self.assertTrue(R.receiver_alive())
            st = R.State(tmp / 's.json')
            dec = lambda *a, **k: {'target': 'jarvis-security', 'why': 't', 'fach': 'sicherheit'}
            a, env, lab, d = R.wrap(['claude'], 'Frage', {}, decide_fn=dec, state=st, log_file=str(tmp / 'l'))
            cmd = json.loads(env['MA_ROUTE_LOCAL_CMD'])
            self.assertEqual(cmd[0], 'systemd-run')                 # Benutzer-Dienstmanager: richtige Gruppe, Zeitlimit, control-group-Kill
            self.assertIn('--user', cmd)
            self.assertIn('KillMode=control-group', cmd)
            self.assertTrue(any(c.startswith('RuntimeMaxSec=') for c in cmd))
            self.assertIn(str(runner), cmd)
            self.assertEqual(env['XDG_RUNTIME_DIR'], '/run/user/1000')
            self.assertIn('--', cmd)
            R.ROLE_RUNNER = str(tmp / 'fehlt.py')
            self.assertFalse(R.receiver_alive())
        finally:
            R.ROLE_RUNNER = old

    def test_wrap_fuer_die_bruecke(self):
        tmp = Path(tempfile.mkdtemp())
        st, logf = R.State(tmp / 's.json'), str(tmp / 'log.jsonl')
        claude_args = ['claude', '-p', '--model', 'sonnet']
        dec = lambda target: (lambda *a, **k: {'target': target, 'why': 'test', 'fach': 'sicherheit'})
        a, env, lab, d = R.wrap(claude_args, 'Frage', {'ctx': 'vorher  X'}, decide_fn=dec('jarvis-security'), state=st, log_file=logf)
        self.assertEqual(a, ['/usr/bin/python3', R.ASK, 'jarvis-security', 'jarvis-security · Nexum (Fachrolle Sicherheit)'])
        self.assertEqual(json.loads(env['MA_ROUTE_CLAUDE_ARGS']), claude_args)
        self.assertEqual(env['MA_ROUTE_CTX'], 'vorher X')
        self.assertEqual((st.used('jarvis-security'), st.used('rollen')), (1, 1))
        a, env, lab, d = R.wrap(claude_args, 'Sortier X', {}, decide_fn=dec('claude'), state=st, log_file=logf)
        self.assertEqual((a, env, lab), (claude_args, {}, None))
        boom = lambda *a, **k: 1 / 0
        self.assertEqual(R.wrap(claude_args, 'x', {}, decide_fn=boom, state=st, log_file=logf)[0], claude_args)   # Weiche-Fehler -> Claude
        lines = [json.loads(l) for l in open(logf, encoding='utf-8')]
        self.assertEqual([l['target'] for l in lines], ['jarvis-security', 'claude', 'claude'])
        self.assertNotIn('Frage', open(logf, encoding='utf-8').read())   # keine Inhalte im Protokoll


if __name__ == '__main__':
    unittest.main()
