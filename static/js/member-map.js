(function () {
    'use strict';

    const root = document.querySelector('[data-member-map]');
    if (!root) return;

    const mapElement = document.getElementById('members-map');
    const form = document.getElementById('member-map-filters');
    const siteFilter = document.getElementById('filter-site');
    const statusFilter = document.getElementById('filter-status');
    const cityFilter = document.getElementById('filter-city');
    const refreshButton = document.getElementById('member-map-refresh');
    const resetButton = document.getElementById('member-map-reset');
    const statePanel = document.getElementById('member-map-state');
    const stateIcon = document.getElementById('member-map-state-icon');
    const stateTitle = document.getElementById('member-map-state-title');
    const stateMessage = document.getElementById('member-map-state-message');
    const retryButton = document.getElementById('member-map-retry');
    const resultStatus = document.getElementById('member-map-result-status');
    const statTotal = document.getElementById('stat-total');
    const statLocated = document.getElementById('stat-located');
    const statLocations = document.getElementById('stat-locations');
    const statUnlocated = document.getElementById('stat-unlocated');

    if (!mapElement || typeof window.L === 'undefined') {
        showState(
            'error',
            'Carte indisponible',
            'Le composant cartographique n’a pas pu être chargé. Rechargez la page.'
        );
        return;
    }

    const map = window.L.map(mapElement, {
        preferCanvas: true,
        zoomControl: false,
    }).setView([4.9225, -52.3058], 11);

    window.L.control.zoom({ position: 'bottomright' }).addTo(map);

    window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap',
        maxZoom: 19,
    }).addTo(map);

    const siteLayer = window.L.layerGroup().addTo(map);
    const memberLayer = typeof window.L.markerClusterGroup === 'function'
        ? window.L.markerClusterGroup({
            chunkedLoading: true,
            maxClusterRadius: 48,
            showCoverageOnHover: false,
            spiderfyOnMaxZoom: true,
            iconCreateFunction(cluster) {
                const memberCount = cluster.getAllChildMarkers().reduce(
                    (total, marker) => total + (marker.memberCount || 1),
                    0
                );
                const sizeClass = memberCount >= 25
                    ? 'member-map-cluster--large'
                    : memberCount >= 10
                        ? 'member-map-cluster--medium'
                        : '';
                const size = memberCount >= 25 ? 54 : memberCount >= 10 ? 48 : 42;
                return window.L.divIcon({
                    className: 'member-map-cluster-wrap',
                    html: `<div class="member-map-cluster ${sizeClass}">${memberCount}</div>`,
                    iconSize: [size, size],
                });
            },
        }).addTo(map)
        : window.L.layerGroup().addTo(map);

    let activeRequest = null;

    function escapeHtml(value) {
        return String(value ?? '')
            .replaceAll('&', '&amp;')
            .replaceAll('<', '&lt;')
            .replaceAll('>', '&gt;')
            .replaceAll('"', '&quot;')
            .replaceAll("'", '&#039;');
    }

    function safeInternalUrl(value) {
        try {
            const url = new URL(String(value || ''), window.location.origin);
            if (url.origin !== window.location.origin) return '#';
            return escapeHtml(`${url.pathname}${url.search}${url.hash}`);
        } catch (_error) {
            return '#';
        }
    }

    function plural(value, singular, pluralForm) {
        return `${value} ${value > 1 ? pluralForm : singular}`;
    }

    function showState(type, title, message) {
        if (!statePanel) return;
        stateTitle.textContent = title;
        stateMessage.textContent = message;
        stateIcon.classList.toggle('is-spinning', type === 'loading');
        stateIcon.innerHTML = type === 'loading'
            ? '<i class="bi bi-arrow-repeat" aria-hidden="true"></i>'
            : type === 'error'
                ? '<i class="bi bi-exclamation-triangle" aria-hidden="true"></i>'
                : '<i class="bi bi-geo-alt" aria-hidden="true"></i>';
        retryButton.hidden = type !== 'error';
        statePanel.classList.add('is-visible');
        statePanel.setAttribute('aria-hidden', 'false');
    }

    function hideState() {
        if (!statePanel) return;
        statePanel.classList.remove('is-visible');
        statePanel.setAttribute('aria-hidden', 'true');
    }

    function setLoading(isLoading) {
        root.setAttribute('aria-busy', String(isLoading));
        refreshButton.disabled = isLoading;
        refreshButton.classList.toggle('is-loading', isLoading);
        if (isLoading) {
            showState('loading', 'Chargement de la carte', 'Les positions sont en cours de préparation…');
        }
    }

    function buildUrl() {
        const url = new URL(root.dataset.mapDataUrl, window.location.origin);
        if (siteFilter.value) url.searchParams.set('site', siteFilter.value);
        if (statusFilter.value) url.searchParams.set('status', statusFilter.value);
        if (cityFilter.value) url.searchParams.set('city', cityFilter.value);
        return url;
    }

    function syncPageUrl(dataUrl) {
        const pageUrl = new URL(window.location.href);
        pageUrl.search = dataUrl.search;
        window.history.replaceState({}, '', pageUrl);
    }

    function updateCityOptions(cities) {
        const selectedCity = cityFilter.value;
        cityFilter.replaceChildren(new Option('Toutes les villes', ''));
        (cities || []).forEach(city => {
            cityFilter.add(new Option(city, city, false, city === selectedCity));
        });
    }

    function groupMembers(members) {
        const groups = new Map();
        (members || []).forEach(member => {
            const fallbackKey = `${Number(member.lat).toFixed(6)},${Number(member.lng).toFixed(6)}`;
            const key = member.location_key || fallbackKey;
            if (!groups.has(key)) groups.set(key, []);
            groups.get(key).push(member);
        });
        return Array.from(groups.values());
    }

    function addressMarkup(member) {
        const address = escapeHtml(member.address);
        const city = escapeHtml(member.city);
        if (address && city) return `${address}<br>${city}`;
        return address || city || 'Adresse non renseignée';
    }

    function qualityBadge(group) {
        const isApproximate = group.some(member => member.location_quality === 'approximate');
        if (isApproximate) {
            return '<span class="member-map-popup__badge member-map-popup__badge--warning">Position approximative</span>';
        }
        return '<span class="member-map-popup__badge">Position localisée</span>';
    }

    function personMarkup(member) {
        const details = [member.status_label || member.status, member.family, member.site]
            .filter(Boolean)
            .map(escapeHtml)
            .join(' · ');
        return `
            <div class="member-map-popup__person">
                <span>
                    <span class="member-map-popup__person-name">${escapeHtml(member.name)}</span>
                    <span class="member-map-popup__person-status">${details}</span>
                </span>
                <a class="member-map-popup__link" href="${safeInternalUrl(member.detail_url)}">Profil</a>
            </div>`;
    }

    function popupMarkup(group) {
        const first = group[0];
        if (group.length === 1) {
            const details = [first.status_label || first.status, first.family, first.site]
                .filter(Boolean)
                .map(escapeHtml)
                .join(' · ');
            return `
                <div class="member-map-popup">
                    <div class="member-map-popup__title">${escapeHtml(first.name)}</div>
                    <p class="member-map-popup__meta">${addressMarkup(first)}</p>
                    ${details ? `<p class="member-map-popup__meta">${details}</p>` : ''}
                    ${first.phone ? `<p class="member-map-popup__meta">${escapeHtml(first.phone)}</p>` : ''}
                    ${qualityBadge(group)}
                    <div class="member-map-popup__list">${personMarkup(first)}</div>
                </div>`;
        }

        return `
            <div class="member-map-popup">
                <div class="member-map-popup__title">${plural(group.length, 'membre', 'membres')} à cette adresse</div>
                <p class="member-map-popup__meta">${addressMarkup(first)}</p>
                ${qualityBadge(group)}
                <div class="member-map-popup__list">${group.map(personMarkup).join('')}</div>
            </div>`;
    }

    function memberIcon(group) {
        const isApproximate = group.some(member => member.location_quality === 'approximate');
        const isMultiple = group.length > 1;
        const markerClass = [
            'member-map-marker',
            isMultiple ? 'member-map-marker--multiple' : '',
            isApproximate ? 'member-map-marker--approximate' : '',
        ].filter(Boolean).join(' ');
        const label = isMultiple ? Math.min(group.length, 99) : '<i class="bi bi-person-fill" aria-hidden="true"></i>';
        return window.L.divIcon({
            className: 'member-map-marker-wrap',
            html: `<div class="${markerClass}"><span>${label}</span></div>`,
            iconAnchor: [17, 34],
            iconSize: [34, 34],
            popupAnchor: [0, -31],
        });
    }

    function siteIcon() {
        return window.L.divIcon({
            className: 'member-map-site-wrap',
            html: '<div class="member-map-site-marker"><i class="bi bi-building" aria-hidden="true"></i></div>',
            iconAnchor: [18, 18],
            iconSize: [36, 36],
            popupAnchor: [0, -20],
        });
    }

    function renderSites(sites) {
        siteLayer.clearLayers();
        (sites || []).forEach(site => {
            const popup = `
                <div class="member-map-popup">
                    <div class="member-map-popup__title">${escapeHtml(site.name)}</div>
                    <p class="member-map-popup__meta">${escapeHtml(site.address)}${site.address && site.city ? '<br>' : ''}${escapeHtml(site.city)}</p>
                    <span class="member-map-popup__badge">${plural(site.member_count, 'membre rattaché', 'membres rattachés')}</span>
                </div>`;
            window.L.marker([site.lat, site.lng], {
                icon: siteIcon(),
                title: site.name,
                zIndexOffset: 500,
            }).bindPopup(popup, { maxWidth: 310 }).addTo(siteLayer);
        });
    }

    function renderMembers(groups) {
        memberLayer.clearLayers();
        groups.forEach(group => {
            const first = group[0];
            const title = group.length === 1
                ? first.name
                : plural(group.length, 'membre', 'membres');
            const marker = window.L.marker([first.lat, first.lng], {
                icon: memberIcon(group),
                title,
            }).bindPopup(popupMarkup(group), {
                maxHeight: 340,
                maxWidth: 360,
                minWidth: 230,
            });
            marker.memberCount = group.length;
            memberLayer.addLayer(marker);
        });
    }

    function fitResults(groups, sites) {
        const memberPoints = groups.map(group => [group[0].lat, group[0].lng]);
        const sitePoints = (sites || []).map(site => [site.lat, site.lng]);
        const points = memberPoints.length ? memberPoints : sitePoints;
        if (!points.length) return;
        if (points.length === 1) {
            map.setView(points[0], 15);
            return;
        }
        map.fitBounds(window.L.latLngBounds(points), {
            animate: false,
            maxZoom: 15,
            padding: [55, 55],
        });
    }

    function updateStats(stats, locationCount) {
        statTotal.textContent = stats.total_members ?? 0;
        statLocated.textContent = stats.members_geocoded ?? 0;
        statLocations.textContent = locationCount;
        statUnlocated.textContent = stats.members_unlocated ?? 0;
    }

    function renderData(data) {
        const groups = groupMembers(data.members);
        renderSites(data.sites);
        renderMembers(groups);
        updateCityOptions(data.cities);
        updateStats(data.stats || {}, groups.length);
        fitResults(groups, data.sites);

        const memberCount = (data.members || []).length;
        resultStatus.textContent = `${plural(memberCount, 'membre affiché', 'membres affichés')} · ${plural(groups.length, 'lieu', 'lieux')}`;

        if (!memberCount && !(data.sites || []).length) {
            showState('empty', 'Aucun résultat', 'Modifiez les filtres pour afficher d’autres positions.');
        } else {
            hideState();
        }
    }

    async function loadMapData() {
        if (activeRequest) activeRequest.abort();
        const requestController = new AbortController();
        activeRequest = requestController;
        const dataUrl = buildUrl();
        setLoading(true);

        try {
            const response = await fetch(dataUrl, {
                credentials: 'same-origin',
                headers: { Accept: 'application/json' },
                signal: requestController.signal,
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            renderData(data);
            syncPageUrl(dataUrl);
        } catch (error) {
            if (error.name === 'AbortError') return;
            console.error('Impossible de charger la carte des membres.', error);
            showState(
                'error',
                'Chargement impossible',
                'Les données cartographiques ne répondent pas. Vous pouvez réessayer.'
            );
            resultStatus.textContent = 'Carte indisponible';
        } finally {
            if (activeRequest === requestController) {
                setLoading(false);
                activeRequest = null;
            }
        }
    }

    form.addEventListener('change', loadMapData);
    form.addEventListener('submit', event => {
        event.preventDefault();
        loadMapData();
    });
    resetButton.addEventListener('click', () => {
        siteFilter.value = '';
        statusFilter.value = '';
        cityFilter.value = '';
        loadMapData();
    });
    retryButton.addEventListener('click', loadMapData);

    loadMapData();
})();
