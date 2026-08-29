/**
 * Check-list — listes de cases à cocher avec filtre et compteur.
 * Remplace les <select multiple> (plus de « Maintenez Ctrl »).
 *
 * Structure attendue :
 *   <div class="check-list" data-check-list>
 *     <input ... data-check-list-search>
 *     <div class="check-list__items"> …checkboxes… </div>
 *     <div class="check-list__footer"><span data-check-list-count></span></div>
 *   </div>
 *
 * Le JS est dégradé : sans lui, les cases à cocher restent pleinement fonctionnelles.
 */
(function () {
    'use strict';

    function items(container) {
        // Cases rendues à la main (.form-check) ou par un widget Django (li)
        return container.querySelectorAll('.check-list__items .form-check, .check-list__items li');
    }

    function updateCount(container) {
        var countEl = container.querySelector('[data-check-list-count]');
        if (!countEl) return;
        var checked = container.querySelectorAll('.check-list__items input[type="checkbox"]:checked').length;
        countEl.textContent = checked === 0
            ? 'Aucune sélection'
            : checked + (checked > 1 ? ' sélectionnés' : ' sélectionné');
    }

    function filter(container) {
        var search = container.querySelector('[data-check-list-search]');
        if (!search) return;
        var query = search.value.trim().toLowerCase();
        var visible = 0;
        items(container).forEach(function (item) {
            var match = !query || item.textContent.toLowerCase().indexOf(query) !== -1;
            item.classList.toggle('d-none', !match);
            if (match) visible++;
        });
        container.classList.toggle('is-filtered-empty', visible === 0);
    }

    document.addEventListener('input', function (event) {
        var container = event.target.closest('[data-check-list]');
        if (container && event.target.matches('[data-check-list-search]')) {
            filter(container);
        }
    });

    document.addEventListener('change', function (event) {
        var container = event.target.closest('[data-check-list]');
        if (container && event.target.matches('input[type="checkbox"]')) {
            updateCount(container);
        }
    });

    document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('[data-check-list]').forEach(function (container) {
            updateCount(container);
            filter(container);
        });
    });
})();
