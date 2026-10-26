// Everything outside the cinematic scenes: nav links, scroll reveals and the
// project panel.

import { initPanel } from './panel.js';
import { initSkills } from './skills.js';

const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;

function scrollToHash(hash) {
  if (!hash || hash === '#') {
    window.scrollTo({ top: 0, behavior: reduced ? 'auto' : 'smooth' });
    return;
  }
  const target = document.querySelector(hash);
  if (target) target.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'start' });
}

export function initContent() {
  // header, mobile menu, footer and in-page buttons all carry [data-nav]
  document.addEventListener('click', (e) => {
    const a = e.target.closest('a[data-nav]');
    if (!a) return;
    const hash = a.getAttribute('href');
    if (!hash || !hash.startsWith('#')) return;
    e.preventDefault();
    scrollToHash(hash);
    if (hash && hash !== '#') history.replaceState(null, '', hash);
    else history.replaceState(null, '', location.pathname + location.search);
  });

  // fade-up as sections arrive; without IntersectionObserver everything simply shows
  if ('IntersectionObserver' in window) {
    document.documentElement.classList.add('has-reveal');
    const io = new IntersectionObserver((entries) => {
      for (const en of entries) {
        if (en.isIntersecting) { en.target.classList.add('is-in'); io.unobserve(en.target); }
      }
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });
    document.querySelectorAll('.reveal').forEach((n, i) => {
      n.style.transitionDelay = `${(i % 4) * 70}ms`;
      io.observe(n);
    });
  }

  initPanel();
  initSkills();
}
