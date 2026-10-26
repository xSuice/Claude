Schreibe eine kleine Python-Bibliothek `ringpuffer.py` (nur Standardbibliothek) mit der Klasse `RingPuffer(kapazitaet)`:

1. `kapazitaet` ist eine ganze Zahl >= 1. Sonst `ValueError` (auch für `bool`, `float`, `str`).
2. `append(x)` fügt am Ende ein; ist der Puffer voll, wird das älteste Element überschrieben.
3. `extend(iterable)` ruft `append` für jedes Element der Reihe nach auf.
4. `len(p)` ist die Zahl der gespeicherten Elemente (höchstens `kapazitaet`). `p.kapazitaet` liefert die Kapazität.
5. `iter(p)` und `list(p)` liefern die Elemente vom ältesten zum neuesten. `p[i]` indiziert in dieser Reihenfolge, auch mit negativen Indizes (`p[-1]` ist das neueste); außerhalb des Bereichs `IndexError`. Slices werden nicht unterstützt (`TypeError`).
6. `p.voll` ist `True`, wenn `len(p) == kapazitaet`. `p.leeren()` entfernt alle Elemente.
7. `p.entnehmen()` entfernt und liefert das **älteste** Element; bei leerem Puffer `IndexError`.
8. `repr(p)` ist `RingPuffer(kapazitaet=3, elemente=[1, 2, 3])`.
9. Zwei Puffer sind gleich, wenn Kapazität und Elementfolge gleich sind.

Liefere außerdem `test_ringpuffer.py` (unittest, deckt Kantenfälle ab: Kapazität 1, Überlauf, negative Indizes, Entnehmen bis leer) und `README.md` mit Beispiel.
