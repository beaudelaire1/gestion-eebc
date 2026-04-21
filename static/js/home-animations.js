/* =============================================================================
   HOME ANIMATIONS JS — "Divine Experience"
   Particles, typewriter, scroll reveals, counters, mouse glow
   ============================================================================= */

(function () {
    'use strict';

    // --- PARTICLES SYSTEM ---
    function initParticles() {
        const canvas = document.getElementById('particles-canvas');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');

        function resize() {
            canvas.width = canvas.offsetWidth * (window.devicePixelRatio || 1);
            canvas.height = canvas.offsetHeight * (window.devicePixelRatio || 1);
            ctx.scale(window.devicePixelRatio || 1, window.devicePixelRatio || 1);
        }
        resize();
        window.addEventListener('resize', resize);

        const particles = [];
        const PARTICLE_COUNT = Math.min(60, Math.floor(window.innerWidth / 25));

        class Particle {
            constructor() { this.reset(); }
            reset() {
                this.x = Math.random() * canvas.offsetWidth;
                this.y = Math.random() * canvas.offsetHeight;
                this.size = Math.random() * 3 + 1;
                this.speedX = (Math.random() - 0.5) * 0.4;
                this.speedY = (Math.random() - 0.5) * 0.4 - 0.2;
                this.opacity = Math.random() * 0.5 + 0.2;
                this.opacityDir = Math.random() > 0.5 ? 0.005 : -0.005;
                // 30% chance to be a tiny cross, rest are circles
                this.isCross = Math.random() < 0.3;
                this.rotation = Math.random() * Math.PI;
                this.rotSpeed = (Math.random() - 0.5) * 0.01;
                // Gold or white
                this.color = Math.random() < 0.3
                    ? 'rgba(248, 181, 0, OPACITY)'
                    : 'rgba(255, 255, 255, OPACITY)';
            }
            update() {
                this.x += this.speedX;
                this.y += this.speedY;
                this.rotation += this.rotSpeed;
                this.opacity += this.opacityDir;
                if (this.opacity <= 0.1 || this.opacity >= 0.7) this.opacityDir *= -1;

                const w = canvas.offsetWidth;
                const h = canvas.offsetHeight;
                if (this.x < -20 || this.x > w + 20 || this.y < -20 || this.y > h + 20) {
                    this.reset();
                    this.y = h + 10;
                }
            }
            draw() {
                const c = this.color.replace('OPACITY', this.opacity.toFixed(2));
                ctx.save();
                ctx.translate(this.x, this.y);
                ctx.rotate(this.rotation);

                if (this.isCross) {
                    const s = this.size * 2;
                    ctx.strokeStyle = c;
                    ctx.lineWidth = 1;
                    ctx.beginPath();
                    ctx.moveTo(0, -s);
                    ctx.lineTo(0, s);
                    ctx.moveTo(-s * 0.6, -s * 0.3);
                    ctx.lineTo(s * 0.6, -s * 0.3);
                    ctx.stroke();
                } else {
                    ctx.fillStyle = c;
                    ctx.beginPath();
                    ctx.arc(0, 0, this.size, 0, Math.PI * 2);
                    ctx.fill();
                }
                ctx.restore();
            }
        }

        for (let i = 0; i < PARTICLE_COUNT; i++) particles.push(new Particle());

        let animFrame;
        function animate() {
            ctx.clearRect(0, 0, canvas.offsetWidth, canvas.offsetHeight);
            particles.forEach(p => { p.update(); p.draw(); });
            animFrame = requestAnimationFrame(animate);
        }

        // Only animate when hero is visible
        const hero = document.querySelector('.aurora-hero');
        if (!hero) return;
        const observer = new IntersectionObserver(entries => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    animate();
                } else {
                    cancelAnimationFrame(animFrame);
                }
            });
        }, { threshold: 0.1 });
        observer.observe(hero);
    }

    // --- TYPEWRITER EFFECT ---
    function initTypewriter() {
        const el = document.querySelector('.verse-typewriter');
        if (!el) return;

        const verses = [
            { text: '« Car Dieu a tant aimé le monde qu\'il a donné son Fils unique, afin que quiconque croit en lui ne périsse point, mais qu\'il ait la vie éternelle. »', ref: '— Jean 3:16' },
            { text: '« L\'Éternel est mon berger : je ne manquerai de rien. »', ref: '— Psaume 23:1' },
            { text: '« Je suis le chemin, la vérité, et la vie. Nul ne vient au Père que par moi. »', ref: '— Jean 14:6' },
            { text: '« Confie-toi en l\'Éternel de tout ton cœur, et ne t\'appuie pas sur ta sagesse. »', ref: '— Proverbes 3:5' },
            { text: '« Car je connais les projets que j\'ai formés sur vous, dit l\'Éternel, projets de paix et non de malheur, afin de vous donner un avenir et de l\'espérance. »', ref: '— Jérémie 29:11' }
        ];

        let currentVerse = 0;
        const textEl = el.querySelector('.verse-text');
        const refEl = el.querySelector('.verse-ref');
        if (!textEl || !refEl) return;

        function typeVerse(verse) {
            textEl.textContent = '';
            refEl.textContent = '';
            refEl.style.opacity = '0';
            let i = 0;
            const cursor = document.createElement('span');
            cursor.className = 'typewriter-cursor';
            textEl.appendChild(cursor);

            const interval = setInterval(() => {
                if (i < verse.text.length) {
                    cursor.before(document.createTextNode(verse.text[i]));
                    i++;
                } else {
                    clearInterval(interval);
                    refEl.textContent = verse.ref;
                    refEl.style.opacity = '1';
                    refEl.style.transition = 'opacity 0.6s ease';

                    // After display time, erase and type next
                    setTimeout(() => {
                        cursor.remove();
                        textEl.style.transition = 'opacity 0.5s ease';
                        textEl.style.opacity = '0';
                        refEl.style.opacity = '0';

                        setTimeout(() => {
                            textEl.style.opacity = '1';
                            currentVerse = (currentVerse + 1) % verses.length;
                            typeVerse(verses[currentVerse]);
                        }, 600);
                    }, 6000);
                }
            }, 35);
        }

        // Start after a delay
        setTimeout(() => typeVerse(verses[0]), 2000);
    }

    // --- SCROLL REVEAL ---
    function initScrollReveal() {
        const targets = document.querySelectorAll(
            '.reveal-section, .reveal-left, .reveal-right, .reveal-scale, .stagger-children'
        );
        if (!targets.length) return;

        const obs = new IntersectionObserver(entries => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('revealed');
                    obs.unobserve(entry.target);
                }
            });
        }, { threshold: 0.15, rootMargin: '0px 0px -50px 0px' });

        targets.forEach(t => obs.observe(t));
    }

    // --- ANIMATED COUNTERS ---
    function initCounters() {
        const counters = document.querySelectorAll('[data-counter]');
        if (!counters.length) return;

        const obs = new IntersectionObserver(entries => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    animateCounter(entry.target);
                    obs.unobserve(entry.target);
                }
            });
        }, { threshold: 0.5 });

        counters.forEach(c => obs.observe(c));

        function animateCounter(el) {
            const target = parseInt(el.dataset.counter, 10);
            const suffix = el.dataset.counterSuffix || '';
            const duration = 2000;
            const start = performance.now();

            function update(now) {
                const elapsed = now - start;
                const progress = Math.min(elapsed / duration, 1);
                // Ease-out cubic
                const eased = 1 - Math.pow(1 - progress, 3);
                const current = Math.floor(eased * target);
                el.textContent = current.toLocaleString('fr-FR');
                if (suffix) {
                    const span = document.createElement('span');
                    span.className = 'counter-suffix';
                    span.textContent = suffix;
                    el.appendChild(span);
                }
                if (progress < 1) requestAnimationFrame(update);
            }
            requestAnimationFrame(update);
        }
    }

    // --- SCROLL PROGRESS BAR ---
    function initScrollProgress() {
        const bar = document.querySelector('.scroll-progress');
        if (!bar) return;

        function update() {
            const scrollTop = window.scrollY;
            const docHeight = document.documentElement.scrollHeight - window.innerHeight;
            const progress = docHeight > 0 ? (scrollTop / docHeight) * 100 : 0;
            bar.style.width = progress + '%';
        }

        window.addEventListener('scroll', update, { passive: true });
        update();
    }

    // --- MOUSE GLOW ---
    function initMouseGlow() {
        const glow = document.querySelector('.mouse-glow');
        if (!glow) return;

        // Only on non-touch devices
        if ('ontouchstart' in window) {
            glow.style.display = 'none';
            return;
        }

        document.addEventListener('mousemove', e => {
            glow.style.left = e.clientX + 'px';
            glow.style.top = e.clientY + 'px';
        }, { passive: true });
    }

    // --- SCROLL DOWN CLICK ---
    function initScrollDown() {
        const btn = document.querySelector('.scroll-down-indicator');
        if (!btn) return;
        btn.addEventListener('click', () => {
            const nextSection = document.querySelector('.aurora-hero + section, .aurora-hero ~ section');
            if (nextSection) {
                nextSection.scrollIntoView({ behavior: 'smooth' });
            }
        });
    }

    // --- NAVBAR SHRINK ON SCROLL ---
    function initNavbarShrink() {
        const nav = document.querySelector('.navbar');
        if (!nav) return;

        window.addEventListener('scroll', () => {
            if (window.scrollY > 100) {
                nav.style.boxShadow = '0 4px 20px rgba(0,0,0,0.15)';
                nav.style.padding = '0.3rem 0';
            } else {
                nav.style.boxShadow = '0 2px 10px rgba(0,0,0,0.1)';
                nav.style.padding = '';
            }
        }, { passive: true });
    }

    // --- INIT ALL ---
    document.addEventListener('DOMContentLoaded', () => {
        initParticles();
        initTypewriter();
        initScrollReveal();
        initCounters();
        initScrollProgress();
        initMouseGlow();
        initScrollDown();
        initNavbarShrink();
    });
})();
