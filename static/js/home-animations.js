/* =============================================================================
   HOME ANIMATIONS JS — "Divine Experience" LITE
   Léger : typewriter, scroll reveal (IntersectionObserver), counters
   Pas de canvas, pas de mouse tracking, pas de scroll progress
   ============================================================================= */

(function () {
    'use strict';

    // --- TYPEWRITER VERSE ---
    function initTypewriter() {
        var el = document.querySelector('.verse-typewriter');
        if (!el) return;

        var verses = [
            { text: '\u00ab Car Dieu a tant aim\u00e9 le monde qu\u2019il a donn\u00e9 son Fils unique, afin que quiconque croit en lui ne p\u00e9risse point, mais qu\u2019il ait la vie \u00e9ternelle. \u00bb', ref: '\u2014 Jean 3:16' },
            { text: '\u00ab L\u2019\u00c9ternel est mon berger : je ne manquerai de rien. \u00bb', ref: '\u2014 Psaume 23:1' },
            { text: '\u00ab Je suis le chemin, la v\u00e9rit\u00e9, et la vie. Nul ne vient au P\u00e8re que par moi. \u00bb', ref: '\u2014 Jean 14:6' },
            { text: '\u00ab Confie-toi en l\u2019\u00c9ternel de tout ton c\u0153ur, et ne t\u2019appuie pas sur ta sagesse. \u00bb', ref: '\u2014 Proverbes 3:5' },
            { text: '\u00ab Car je connais les projets que j\u2019ai form\u00e9s sur vous, dit l\u2019\u00c9ternel, projets de paix et non de malheur, afin de vous donner un avenir et de l\u2019esp\u00e9rance. \u00bb', ref: '\u2014 J\u00e9r\u00e9mie 29:11' }
        ];

        var currentVerse = 0;
        var textEl = el.querySelector('.verse-text');
        var refEl = el.querySelector('.verse-ref');
        if (!textEl || !refEl) return;

        function typeVerse(verse) {
            textEl.textContent = '';
            refEl.textContent = '';
            refEl.style.opacity = '0';
            var i = 0;
            var cursor = document.createElement('span');
            cursor.className = 'typewriter-cursor';
            textEl.appendChild(cursor);

            var interval = setInterval(function () {
                if (i < verse.text.length) {
                    cursor.before(document.createTextNode(verse.text[i]));
                    i++;
                } else {
                    clearInterval(interval);
                    refEl.textContent = verse.ref;
                    refEl.style.opacity = '1';
                    refEl.style.transition = 'opacity 0.6s ease';

                    setTimeout(function () {
                        cursor.remove();
                        textEl.style.transition = 'opacity 0.5s ease';
                        textEl.style.opacity = '0';
                        refEl.style.opacity = '0';

                        setTimeout(function () {
                            textEl.style.opacity = '1';
                            currentVerse = (currentVerse + 1) % verses.length;
                            typeVerse(verses[currentVerse]);
                        }, 600);
                    }, 6000);
                }
            }, 40);
        }

        setTimeout(function () { typeVerse(verses[0]); }, 1500);
    }

    // --- SCROLL REVEAL (IntersectionObserver — no library) ---
    function initScrollReveal() {
        var targets = document.querySelectorAll(
            '.reveal-section, .reveal-left, .reveal-right, .reveal-scale, .stagger-children'
        );
        if (!targets.length) return;

        var obs = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('revealed');
                    obs.unobserve(entry.target);
                }
            });
        }, { threshold: 0.15, rootMargin: '0px 0px -40px 0px' });

        targets.forEach(function (t) { obs.observe(t); });
    }

    // --- ANIMATED COUNTERS ---
    function initCounters() {
        var counters = document.querySelectorAll('[data-counter]');
        if (!counters.length) return;

        var obs = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    animateCounter(entry.target);
                    obs.unobserve(entry.target);
                }
            });
        }, { threshold: 0.5 });

        counters.forEach(function (c) { obs.observe(c); });

        function animateCounter(el) {
            var target = parseInt(el.dataset.counter, 10);
            var suffix = el.dataset.counterSuffix || '';
            var duration = 2000;
            var start = performance.now();

            function update(now) {
                var elapsed = now - start;
                var progress = Math.min(elapsed / duration, 1);
                var eased = 1 - Math.pow(1 - progress, 3);
                var current = Math.floor(eased * target);
                el.textContent = current.toLocaleString('fr-FR');
                if (suffix) {
                    var span = document.createElement('span');
                    span.className = 'counter-suffix';
                    span.textContent = suffix;
                    el.appendChild(span);
                }
                if (progress < 1) requestAnimationFrame(update);
            }
            requestAnimationFrame(update);
        }
    }

    // --- SCROLL DOWN CLICK ---
    function initScrollDown() {
        var btn = document.querySelector('.scroll-down-indicator');
        if (!btn) return;
        btn.addEventListener('click', function () {
            var next = document.querySelector('.aurora-hero ~ section');
            if (next) next.scrollIntoView({ behavior: 'smooth' });
        });
    }

    // --- INIT ---
    document.addEventListener('DOMContentLoaded', function () {
        initTypewriter();
        initScrollReveal();
        initCounters();
        initScrollDown();
    });
})();
