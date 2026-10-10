"""Einmaliger GMX-IMAP-Login-Test: Passwort verdeckt eingeben, wird nicht gespeichert/ausgegeben.
Liest nichts aus dem Postfach, zeigt nur die Server-Antwort auf den Login.
Aufruf:  python -I gmx-imap-login-check.py
"""
import getpass
import imaplib

user = input("GMX-Adresse: ").strip()
pw = getpass.getpass("App-Passwort (verdeckt): ").strip()
print(f"Passwortlaenge: {len(pw)} Zeichen (App-Passwoerter haben meist 20)")
m = imaplib.IMAP4_SSL("imap.gmx.net", 993, timeout=20)
try:
    typ, data = m.login(user, pw)
    print("LOGIN OK:", typ)
    m.logout()
except imaplib.IMAP4.error as e:
    print("Server-Antwort:", e)
