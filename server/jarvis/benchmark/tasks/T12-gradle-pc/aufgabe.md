**PC-Aufgabe (`java.build`, Windows-PC mit Java 21): braucht `jarvis-pc.json` und den freigegebenen, gesandboxten PC-Worker. Auf dem Server nicht ausführbar.**

Lege ein minimales Gradle-Projekt an (Gradle-Wrapper wird nicht vorausgesetzt; `build.gradle` mit `java`-Plugin, Quelle unter `src/main/java/`), das eine Klasse `app.Main` mit `public static int quadrat(int x)` enthält (liefert `x * x`) und `main` gibt `quadrat(7)` aus. Dazu ein JUnit-5-Test unter `src/test/java/` für `quadrat` (0, 7, -3). `gradle build` muss grün durchlaufen und `build/libs/*.jar` erzeugen.

Liefere `README.md` mit dem Build-Aufruf.
