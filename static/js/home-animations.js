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
        var textEl = el && el.querySelector('.verse-text');
        var refEl = el && el.querySelector('.verse-ref');
        if (!el || !textEl || !refEl) return;

        var verses = [
            { text: '\u00ab Car Dieu a tant aim\u00e9 le monde qu\u2019il a donn\u00e9 son Fils unique, afin que quiconque croit en lui ne p\u00e9risse point, mais qu\u2019il ait la vie \u00e9ternelle. \u00bb', ref: '\u2014 Jean 3:16' },
            { text: '\u00ab L\u2019\u00c9ternel est mon berger : je ne manquerai de rien. \u00bb', ref: '\u2014 Psaume 23:1' },
            { text: '\u00ab Je suis le chemin, la v\u00e9rit\u00e9, et la vie. Nul ne vient au P\u00e8re que par moi. \u00bb', ref: '\u2014 Jean 14:6' },
            { text: '\u00ab Confie-toi en l\u2019\u00c9ternel de tout ton c\u0153ur, et ne t\u2019appuie pas sur ta sagesse. \u00bb', ref: '\u2014 Proverbes 3:5' },
            { text: '\u00ab Car je connais les projets que j\u2019ai form\u00e9s sur vous, dit l\u2019\u00c9ternel, projets de paix et non de malheur, afin de vous donner un avenir et de l\u2019esp\u00e9rance. \u00bb', ref: '\u2014 J\u00e9r\u00e9mie 29:11' }
        ];

        var currentVerse = 0;

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

    // --- HERO BIBLE PANEL ---
    function initHeroBiblePanels() {
        if (!window.matchMedia('(hover: hover) and (pointer: fine)').matches) return;

        var stages = document.querySelectorAll('.hero-bible-stage');
        if (!stages.length) return;

        stages.forEach(function (stage) {
            function resetTilt() {
                stage.classList.remove('is-tilting');
                stage.style.setProperty('--hero-bible-rotate-x', '0deg');
                stage.style.setProperty('--hero-bible-rotate-y', '0deg');
            }

            stage.addEventListener('pointerenter', function () {
                stage.classList.add('is-tilting');
            });

            stage.addEventListener('pointermove', function (event) {
                var rect = stage.getBoundingClientRect();
                var offsetX = (event.clientX - rect.left) / rect.width - 0.5;
                var offsetY = (event.clientY - rect.top) / rect.height - 0.5;
                var rotateY = offsetX * 12;
                var rotateX = offsetY * -10;

                stage.style.setProperty('--hero-bible-rotate-x', rotateX.toFixed(2) + 'deg');
                stage.style.setProperty('--hero-bible-rotate-y', rotateY.toFixed(2) + 'deg');
            });

            stage.addEventListener('pointerleave', resetTilt);
            stage.addEventListener('blur', resetTilt, true);
        });
    }

    // --- BIBLICAL JOURNEY ---
    function initBibleJourney() {
        var section = document.querySelector('.bible-journey-section');
        if (!section) return;

        var cards = Array.from(section.querySelectorAll('.journey-story-card'));
        var media = section.querySelector('#journeySceneMedia');
        var title = section.querySelector('#journeyVisualTitle');
        var copy = section.querySelector('#journeyVisualCopy');
        var ref = section.querySelector('#journeyVisualRef');
        if (!cards.length || !media || !title || !copy || !ref) return;

        function activateCard(card) {
            if (!card) return;

            cards.forEach(function (item) {
                item.classList.toggle('is-active', item === card);
            });

            var nextTitle = card.dataset.journeyTitle || '';
            var nextCopy = card.dataset.journeyCopy || '';
            var nextRef = card.dataset.journeyRef || '';
            var nextImage = card.dataset.journeyImage || '';
            var cardIndex = cards.indexOf(card);

            title.textContent = nextTitle;
            copy.textContent = nextCopy;
            ref.textContent = nextRef;
            section.style.setProperty('--journey-bible-tilt', cardIndex % 2 === 0 ? '-6deg' : '6deg');

            if (nextImage && media.dataset.currentImage !== nextImage) {
                media.classList.add('is-switching');
                media.dataset.currentImage = nextImage;
                media.onload = function () {
                    media.classList.remove('is-switching');
                    media.onload = null;
                };
                media.src = nextImage;
                media.alt = nextTitle;
            }
        }

        var observer = new IntersectionObserver(function (entries) {
            var visibleEntries = entries.filter(function (entry) {
                return entry.isIntersecting;
            }).sort(function (left, right) {
                return right.intersectionRatio - left.intersectionRatio;
            });

            if (visibleEntries.length) {
                activateCard(visibleEntries[0].target);
            }
        }, {
            threshold: [0.35, 0.55, 0.75],
            rootMargin: '-10% 0px -18% 0px'
        });

        cards.forEach(function (card) {
            observer.observe(card);
            card.addEventListener('mouseenter', function () {
                activateCard(card);
            });
            card.addEventListener('focusin', function () {
                activateCard(card);
            });
        });

        activateCard(cards[0]);
    }

    // --- INIT ---
    document.addEventListener('DOMContentLoaded', function () {
        initTypewriter();
        initScrollReveal();
        initCounters();
        initScrollDown();
        initHeroBiblePanels();
        initBibleJourney();
    });
})();
