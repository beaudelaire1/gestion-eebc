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
        var frame = section.querySelector('.journey-scene-frame');
        var stage = section.querySelector('#journeySceneStage');
        var space = section.querySelector('#journeySceneSpace');
        var media = section.querySelector('#journeySceneMedia');
        var title = section.querySelector('#journeyVisualTitle');
        var copy = section.querySelector('#journeyVisualCopy');
        var ref = section.querySelector('#journeyVisualRef');
        var visualCopy = section.querySelector('.journey-visual-copy');
        var verseList = section.querySelector('#journeyVerseList');
        var verseCite = section.querySelector('#journeyVerseCite');
        if (!cards.length || !frame || !stage || !media || !title || !copy || !ref || !visualCopy) return;

        var motionPresets = [
            { panX: '-1.8%', panY: '-1.2%', zoom: '1.12', rotate: '-1.8deg', focusX: '34%', focusY: '28%' },
            { panX: '1.5%', panY: '-0.9%', zoom: '1.09', rotate: '1.2deg', focusX: '66%', focusY: '30%' },
            { panX: '-0.9%', panY: '1.6%', zoom: '1.11', rotate: '-0.8deg', focusX: '42%', focusY: '42%' },
            { panX: '1.9%', panY: '0.8%', zoom: '1.08', rotate: '1.6deg', focusX: '62%', focusY: '38%' },
            { panX: '-1.4%', panY: '0.9%', zoom: '1.13', rotate: '-1.4deg', focusX: '36%', focusY: '33%' }
        ];

        // Passages : liste de versets affichés un par un dans le même cadre
        var verseMap = {
            'Genèse 22': {
                cite: 'Genèse 22.10-12',
                verses: [
                    'Abraham étendit la main, et prit le couteau, pour égorger son fils.',
                    'Alors l\u0027ange de l\u0027Éternel l\u0027appela des cieux, et dit : Abraham ! Abraham ! Et il répondit : Me voici !',
                    'L\u0027ange dit : N\u0027avance pas ta main sur l\u0027enfant, car je sais maintenant que tu crains Dieu, et que tu ne m\u0027as pas refusé ton fils, ton unique.'
                ]
            },
            'Genèse 32': {
                cite: 'Genèse 32.25-27',
                verses: [
                    'Jacob demeura seul. Alors un homme lutta avec lui jusqu\u0027au lever de l\u0027aurore.',
                    'Voyant qu\u0027il ne pouvait le vaincre, cet homme le frappa à l\u0027emboîture de la hanche.',
                    'Il dit : Laisse-moi aller, car l\u0027aurore se lève. Jacob répondit : Je ne te laisserai point aller, que tu ne m\u0027aies béni.'
                ]
            },
            '1 Rois 3': {
                cite: '1 Rois 3.9-10',
                verses: [
                    'Accorde donc à ton serviteur un cœur intelligent pour juger ton peuple.',
                    'Pour discerner le bien du mal. Car qui pourrait juger ton peuple, ce peuple si nombreux ?',
                    'Cette demande de Salomon plut au Seigneur.'
                ]
            },
            'Nombres 22': {
                cite: 'Nombres 22.28-31',
                verses: [
                    'L\u0027Éternel ouvrit la bouche de l\u0027ânesse, et elle dit à Balaam : Que t\u0027ai-je fait, pour que tu m\u0027aies frappée déjà trois fois ?',
                    'Alors l\u0027Éternel ouvrit les yeux de Balaam, et il vit l\u0027ange de l\u0027Éternel sur le chemin, son épée nue dans la main.',
                    'Et il s\u0027inclina, et se prosterna sur son visage.'
                ]
            },
            'Daniel 6': {
                cite: 'Daniel 6.23-24',
                verses: [
                    'Mon Dieu a envoyé son ange et fermé la gueule des lions, qui ne m\u0027ont fait aucun mal.',
                    'Parce que j\u0027ai été trouvé innocent devant lui ; et devant toi non plus, ô roi, je n\u0027ai rien fait de mauvais.',
                    'Alors le roi fut très joyeux, et il ordonna qu\u0027on fît sortir Daniel de la fosse.'
                ]
            },
            'Jonas 2': {
                cite: 'Jonas 2.3-4',
                verses: [
                    'Dans ma détresse, j\u0027ai invoqué l\u0027Éternel, et il m\u0027a exaucé.',
                    'Du sein du séjour des morts j\u0027ai crié, et tu as entendu ma voix.',
                    'Tu m\u0027as jeté dans l\u0027abîme, dans le cœur de la mer, et les courants d\u0027eau m\u0027ont environné.'
                ]
            },
            'Luc 1': {
                cite: 'Luc 1.28,38',
                verses: [
                    'L\u0027ange entra chez elle, et dit : Je te salue, toi à qui une grâce a été faite ; le Seigneur est avec toi.',
                    'Marie dit : Je suis la servante du Seigneur ; qu\u0027il me soit fait selon ta parole !',
                    'Et l\u0027ange la quitta.'
                ]
            },
            'Jean 11': {
                cite: 'Jean 11.25-27',
                verses: [
                    'Jésus lui dit : Je suis la résurrection et la vie.',
                    'Celui qui croit en moi vivra, quand même il serait mort ; et quiconque vit et croit en moi ne mourra jamais. Crois-tu cela ?',
                    'Elle lui dit : Oui, Seigneur, je crois que tu es le Christ, le Fils de Dieu.'
                ]
            },
            'Genèse 7': {
                cite: 'Genèse 7.1,7,16',
                verses: [
                    'L\u0027Éternel dit à Noé : Entre dans l\u0027arche, toi et toute ta maison ; car je t\u0027ai vu juste devant moi parmi cette génération.',
                    'Noé entra dans l\u0027arche avec ses fils, sa femme et les femmes de ses fils, pour échapper aux eaux du déluge.',
                    'Et l\u0027Éternel ferma la porte sur lui.'
                ]
            }
        };

        var verseTimers = [];

        function clearVerseTimers() {
            verseTimers.forEach(function (t) { window.clearTimeout(t); });
            verseTimers = [];
        }

        function typeLine(line, text, onDone) {
            var textSpan = line.querySelector('.text');
            var i = 0;
            var step = function () {
                if (i <= text.length) {
                    textSpan.textContent = text.slice(0, i);
                    i += 1;
                    var delay = 14 + Math.random() * 18;
                    var prev = text.charAt(i - 2);
                    if (prev === ',' || prev === ';') delay += 70;
                    if (prev === '.' || prev === '!' || prev === '?') delay += 160;
                    verseTimers.push(window.setTimeout(step, delay));
                } else {
                    line.classList.add('is-done');
                    if (onDone) onDone();
                }
            };
            step();
        }

        function typePassage(verses, cite) {
            clearVerseTimers();
            if (!verseList) return;
            if (verseCite) verseCite.textContent = '';
            verseList.innerHTML = '';

            // Toujours au moins 3 entrées affichées
            var list = (verses && verses.length) ? verses.slice() : [];
            while (list.length < 3) list.push('');

            var lines = list.map(function (t) {
                var li = document.createElement('li');
                li.className = 'journey-verse-line';
                li.innerHTML = '<span class="text"></span><span class="caret"></span>';
                verseList.appendChild(li);
                return li;
            });

            var done = 0;
            lines.forEach(function (line, idx) {
                var appear = window.setTimeout(function () {
                    line.classList.add('is-visible');
                    typeLine(line, list[idx], function () {
                        done += 1;
                        if (done === lines.length && verseCite) {
                            verseCite.textContent = cite || '';
                        }
                    });
                }, idx * 650);
                verseTimers.push(appear);
            });
        }

        var scenePulseTimer = null;

        media.dataset.currentImage = media.getAttribute('src') || '';

        function pulseScene() {
            frame.classList.remove('is-transitioning');
            stage.classList.remove('is-transitioning');
            visualCopy.classList.remove('is-transitioning');

            void frame.offsetWidth;

            frame.classList.add('is-transitioning');
            stage.classList.add('is-transitioning');
            visualCopy.classList.add('is-transitioning');

            window.clearTimeout(scenePulseTimer);
            scenePulseTimer = window.setTimeout(function () {
                frame.classList.remove('is-transitioning');
                stage.classList.remove('is-transitioning');
                visualCopy.classList.remove('is-transitioning');
            }, 520);
        }

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
            var motionPreset = motionPresets[cardIndex % motionPresets.length];
            var frameTilt = cardIndex % 2 === 0 ? '-1.1deg' : '1.1deg';
            var frameTiltStrong = cardIndex % 2 === 0 ? '-1.6deg' : '1.6deg';

            section.style.setProperty('--journey-pan-x', motionPreset.panX);
            section.style.setProperty('--journey-pan-y', motionPreset.panY);
            section.style.setProperty('--journey-zoom', motionPreset.zoom);
            section.style.setProperty('--journey-rotate', motionPreset.rotate);
            section.style.setProperty('--journey-focus-x', motionPreset.focusX);
            section.style.setProperty('--journey-focus-y', motionPreset.focusY);
            section.style.setProperty('--journey-frame-tilt', frameTilt);
            section.style.setProperty('--journey-frame-tilt-strong', frameTiltStrong);

            title.textContent = nextTitle;
            copy.textContent = nextCopy;
            ref.textContent = nextRef;
            section.style.setProperty('--journey-bible-tilt', cardIndex % 2 === 0 ? '-6deg' : '6deg');
            pulseScene();

            var mapped = verseMap[nextRef];
            if (mapped && mapped.verses) {
                typePassage(mapped.verses, mapped.cite);
            } else {
                typePassage([nextCopy], nextRef);
            }

            if (nextImage && media.dataset.currentImage !== nextImage) {
                media.classList.add('is-switching');
                media.dataset.currentImage = nextImage;
                window.clearTimeout(media.switchTimer);

                var releaseSwitchState = function () {
                    media.classList.remove('is-switching');
                    media.onload = null;
                    media.switchTimer = null;
                };

                media.onload = releaseSwitchState;
                media.switchTimer = window.setTimeout(releaseSwitchState, 900);
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

        // 3D parallax tilt on mouse move over the scene
        if (space && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            var rafId = null;
            var targetMx = 0;
            var targetMy = 0;
            var currentMx = 0;
            var currentMy = 0;

            var applyTilt = function () {
                currentMx += (targetMx - currentMx) * 0.08;
                currentMy += (targetMy - currentMy) * 0.08;
                space.style.setProperty('--journey-mx', currentMx.toFixed(3));
                space.style.setProperty('--journey-my', currentMy.toFixed(3));
                if (Math.abs(targetMx - currentMx) > 0.001 || Math.abs(targetMy - currentMy) > 0.001) {
                    rafId = window.requestAnimationFrame(applyTilt);
                } else {
                    rafId = null;
                }
            };

            var scheduleTilt = function () {
                if (rafId === null) {
                    rafId = window.requestAnimationFrame(applyTilt);
                }
            };

            space.addEventListener('mousemove', function (event) {
                var rect = space.getBoundingClientRect();
                targetMx = ((event.clientX - rect.left) / rect.width - 0.5) * 2;
                targetMy = ((event.clientY - rect.top) / rect.height - 0.5) * 2;
                scheduleTilt();
            });

            space.addEventListener('mouseleave', function () {
                targetMx = 0;
                targetMy = 0;
                scheduleTilt();
            });
        }

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
