// The project detail panel: a native <dialog> (focus trap, Esc, backdrop for
// free) filled from public/data/projects.json when a gallery card is clicked.

const GITHUB = 'https://github.com/ashikhub23';
let data = null;
let loading = null;

function load() {
  if (!loading) {
    loading = fetch('public/data/projects.json')
      .then((r) => r.json())
      .then((j) => { data = new Map(j.projects.map((p) => [p.id, p])); })
      .catch((e) => console.warn('[ashik] projects.json unavailable:', e.message));
  }
  return loading;
}

const el = (id) => document.getElementById(id);
const li = (text) => { const n = document.createElement('li'); n.textContent = text; return n; };

function link(href, label, ghost) {
  const a = document.createElement('a');
  a.className = ghost ? 'btn btn--ghost' : 'btn';
  a.href = href;
  a.target = '_blank';
  a.rel = 'noopener';
  a.textContent = label;
  return a;
}

export async function openProject(id) {
  await load();
  const p = data && data.get(id);
  const dlg = el('projDialog');
  if (!p || !dlg || typeof dlg.showModal !== 'function') return;

  el('projKicker').textContent = p.kicker;
  el('projTitle').textContent = p.title;
  el('projSum').textContent = p.summary;
  el('projFeat').replaceChildren(...p.features.map(li));
  const tech = el('projTech');
  tech.replaceChildren(...p.tech.map(li));
  tech.hidden = p.tech.length === 0;

  const links = el('projLinks');
  links.replaceChildren();
  if (p.live) links.append(link(p.live, 'Live demo \u2197', false));
  if (p.repo) links.append(link(p.repo, 'Source on GitHub \u2197', !!p.live));
  links.append(link(GITHUB, 'GitHub profile \u2197', true));

  dlg.showModal();
}

export function initPanel() {
  const dlg = el('projDialog');
  if (!dlg) return;
  el('projClose')?.addEventListener('click', () => dlg.close());
  // a click on the backdrop (the dialog element itself) closes it
  dlg.addEventListener('click', (e) => { if (e.target === dlg) dlg.close(); });
  load();
}
