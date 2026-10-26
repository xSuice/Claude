printf '#!/bin/sh\njq -f auswertung.jq bestellungen.json > ergebnis.json\n' > pruefen.sh
printf '# auswertung\n\n    jq -f auswertung.jq bestellungen.json\n' > README.md
sh pruefen.sh
