/* MA-HOME HQ — Öffnet dieses Element die Bildschirmtastatur? Nur dann setzt app.js body.kb (Platz für die Tastatur).
   Auswahllisten, Häkchen, Schalter, Regler usw. öffnen keine Tastatur. Würden sie body.kb setzen, blendet
   „body.kb .copt-fold { display: none }“ ihr eigenes Optionsfeld aus – das Auswahlfeld klappt sofort wieder zu. */
const NO_KB = /^(?:checkbox|radio|button|submit|reset|image|file|range|color|hidden)$/i;
export function raisesKeyboard(t) {
  if (!t || !t.tagName) return false;
  if (t.isContentEditable) return true;
  if (t.tagName === 'TEXTAREA') return !t.readOnly && !t.disabled;
  if (t.tagName === 'INPUT') return !NO_KB.test(t.type || 'text') && !t.readOnly && !t.disabled;
  return false;
}
