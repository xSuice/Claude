"""Chat-Weiche in die Claude-Bruecke einbauen (Anker-Patch, idempotent, Marker CHAT-ROUTE). Pfad als Argument."""
import sys
P = sys.argv[1]
s = open(P, encoding='utf-8').read()
if 'CHAT-ROUTE' in s:
    print('schon gepatcht'); sys.exit(0)


def rep(old, new):
    global s
    assert s.count(old) == 1, (old[:80], s.count(old))
    s = s.replace(old, new)


rep("""    import router_core
except ImportError:
    router_core = None""", """    import router_core
except ImportError:
    router_core = None
try:                                   # CHAT-ROUTE 29.10.: Fachfragen -> Hermes-Rollen/Supervisor, Claude nur fuer Werkzeug-Auftraege
    import ma_chat_route
except ImportError:
    ma_chat_route = None""")

rep("""                sid = req.get('session')
                if isinstance(sid, str) and SESSION.fullmatch(sid):
                    args += ['--resume', sid]
        except Exception:""", """                sid = req.get('session')
                if isinstance(sid, str) and SESSION.fullmatch(sid):
                    args += ['--resume', sid]
            route_env, route_label = {}, None   # CHAT-ROUTE: nur normale Chat-Auftraege; jeder Fehler -> Claude unveraendert
            if ma_chat_route and cat == 'chat' and req.get('mode') != 'gespraech':
                args, route_env, route_label, _rd = ma_chat_route.wrap(args, prompt, req, bool(img_paths), bool(file_paths))
        except Exception:""")

rep("""            if req.get('mode') == 'voll_senden':
                env['MA_ALLOW_SEND'] = '1'
            proc = subprocess.Popen(args, cwd=cwd, env=env,""", """            if req.get('mode') == 'voll_senden':
                env['MA_ALLOW_SEND'] = '1'
            env.update(route_env)   # CHAT-ROUTE
            proc = subprocess.Popen(args, cwd=cwd, env=env,""")

rep("""            job = {'proc': proc, 'start': time.time(), 'prompt': ' '.join(prompt.split())[:60], 'model': model, 'mode': str(req.get('mode')),""",
    """            job = {'proc': proc, 'start': time.time(), 'prompt': ' '.join(prompt.split())[:60], 'model': route_label or model, 'mode': str(req.get('mode')),""")

rep("""            usage_add(cat, jobs=1)
            job_push(job, {'type': 'bridge_model', 'model': model})
            job_push(job, {'type': 'bridge_job', 'id': jid})""", """            usage_add(cat, jobs=1)
            job_push(job, {'type': 'bridge_model', 'model': route_label or model})   # CHAT-ROUTE: zeigt, wer antwortet
            job_push(job, {'type': 'bridge_job', 'id': jid})""")

rep("""            if op == 'usage':""", """            if op == 'route_report' and ma_chat_route:   # CHAT-ROUTE: Tageszaehler fuer das Command Center (ohne Inhalte)
                return self.reply({'type': 'route_report', 'data': ma_chat_route.State().report(), 'mode': ma_chat_route.MODE})
            if op == 'usage':""")
open(P, 'w', encoding='utf-8').write(s)
print('gepatcht')
