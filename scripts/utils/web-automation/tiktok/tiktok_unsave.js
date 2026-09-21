(function(){
/* TikTok Favoriten-Aufräumer
   Anleitung:
   1. Gehe auf dein Profil -> Favoriten.
   2. Klicke das ERSTE Video an, das du behalten oder entfernen willst (öffnet den Player).
   3. Öffne die Konsole (F12 -> Tab "Console").
   4. Diesen Code einfügen, Enter drücken. Unten rechts erscheint ein kleines Panel.
   5. Steuerung per Taste:
        s = Start/Weiter (Automatik: entspeichern -> nächstes Video -> wiederholen)
        p = Pause (stoppt vor der nächsten Aktion)
        k = "Keep" -> dieses eine Video behalten, nur zum nächsten springen, NICHT entspeichern
        u = Undo  -> letzten Entfernen-Klick rückgängig machen (geht zurück + speichert erneut)
   Tipp: nicht alle 3000 in einem Rutsch laufen lassen. Alle paar hundert Videos
   mit "p" pausieren und eine Pause machen, damit TikTok das nicht als Bot-Verhalten wertet.
*/
if (window.__tiktokCleanerRunning !== undefined) {
  console.log('Cleaner läuft bereits.');
  return;
}
window.__tiktokCleanerRunning = false;
window.__tiktokCleanerStop = false;

const DELAY_MS = 1100;       // Basis-Pause zwischen Aktionen
const JITTER_MS = 500;       // + zufällige Streuung, wirkt weniger robotisch
let removedCount = 0;
let lastAction = null;       // 'removed' | 'kept' | null, für Undo

const panel = document.createElement('div');
panel.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:999999;background:#161823;color:#fff;font:14px sans-serif;padding:14px 18px;border-radius:10px;box-shadow:0 4px 20px rgba(0,0,0,.5);width:230px;';
panel.innerHTML = `
  <div style="font-weight:600;margin-bottom:6px;">TikTok Aufräumer</div>
  <div id="tc-status" style="margin-bottom:6px;color:#fe2c55;">Pausiert</div>
  <div id="tc-count" style="margin-bottom:10px;">Entfernt: 0</div>
  <div style="font-size:12px;line-height:1.5;color:#aaa;">
    <b>s</b> Start/Weiter<br>
    <b>p</b> Pause<br>
    <b>k</b> Behalten (skip)<br>
    <b>u</b> Undo letzte Aktion
  </div>
`;
document.body.appendChild(panel);

function setStatus(text, color) {
  panel.querySelector('#tc-status').textContent = text;
  panel.querySelector('#tc-status').style.color = color;
}
function updateCount() {
  panel.querySelector('#tc-count').textContent = 'Entfernt: ' + removedCount;
}

function getVisibleFavoriteIcon() {
  const icons = Array.from(document.querySelectorAll('[data-e2e="favorite-icon"]'));
  return icons.find(el => {
    const r = el.getBoundingClientRect();
    return r.top >= 0 && r.top < window.innerHeight && r.width > 0;
  }) || null;
}
function getButtonByLabel(label) {
  return document.querySelector(`[aria-label="${label}"]`);
}

function clickNext() {
  const next = getButtonByLabel('Next video');
  if (!next || next.getAttribute('aria-disabled') === 'true') return false;
  next.click();
  return true;
}
function clickPrev() {
  const prev = getButtonByLabel('Previous video');
  if (!prev) return false;
  prev.click();
  return true;
}
function clickFavoriteIcon() {
  const icon = getVisibleFavoriteIcon();
  if (!icon) return false;
  icon.click();
  return true;
}

function randomDelay() {
  return DELAY_MS + Math.random() * JITTER_MS;
}

function loop() {
  if (window.__tiktokCleanerStop || !window.__tiktokCleanerRunning) return;

  const removedOk = clickFavoriteIcon();
  if (!removedOk) {
    setStatus('Kein Video gefunden - gestoppt', '#fe2c55');
    window.__tiktokCleanerRunning = false;
    return;
  }
  removedCount++;
  lastAction = 'removed';
  updateCount();

  setTimeout(() => {
    if (window.__tiktokCleanerStop || !window.__tiktokCleanerRunning) return;
    const nextOk = clickNext();
    if (!nextOk) {
      setStatus('Ende der Liste erreicht', '#f5a623');
      window.__tiktokCleanerRunning = false;
      return;
    }
    setTimeout(loop, randomDelay());
  }, 350 + Math.random() * 200);
}

function start() {
  if (window.__tiktokCleanerRunning) return;
  window.__tiktokCleanerRunning = true;
  window.__tiktokCleanerStop = false;
  setStatus('Läuft...', '#25d366');
  loop();
}
function pause() {
  window.__tiktokCleanerRunning = false;
  setStatus('Pausiert', '#fe2c55');
}
function keepAndAdvance() {
  window.__tiktokCleanerRunning = false;
  setStatus('Pausiert', '#fe2c55');
  lastAction = 'kept';
  clickNext();
}
function undoLast() {
  if (lastAction !== 'removed') {
    console.log('Nichts zum Rückgängig-Machen.');
    return;
  }
  window.__tiktokCleanerRunning = false;
  setStatus('Pausiert (Undo)', '#f5a623');
  clickPrev();
  setTimeout(() => {
    clickFavoriteIcon(); // erneut speichern
    removedCount = Math.max(0, removedCount - 1);
    updateCount();
    lastAction = null;
  }, 500);
}

window.addEventListener('keydown', (e) => {
  if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable)) return;
  const key = (e.key || '').toLowerCase();
  if (!['s','p','k','u'].includes(key)) return;
  // capture-phase + stop, damit TikToks eigene Tastatur-Shortcuts das Event nicht vorher wegschnappen
  e.preventDefault();
  e.stopPropagation();
  e.stopImmediatePropagation();
  switch (key) {
    case 's': start(); break;
    case 'p': pause(); break;
    case 'k': keepAndAdvance(); break;
    case 'u': undoLast(); break;
  }
}, true); // true = capture phase, läuft VOR TikToks eigenen Listenern

console.log('TikTok Aufräumer geladen. Panel unten rechts. s=Start p=Pause k=Behalten u=Undo');
})();
