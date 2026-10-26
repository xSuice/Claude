[ .[] | select(.status == "bezahlt") ]
| group_by(.kunde)
| map({kunde: .[0].kunde, bestellungen: length,
      umsatz: ((map(.positionen | map(.menge * .preis) | add) | add) * 100 | round / 100)})
| sort_by([-.umsatz, .kunde])
