// Sidebar toggle — persists in localStorage
// Mobile default: viewport < 768px starts collapsed unless user explicitly expanded.
function initSidebar() {
    // Detect mobile (matches the @media (max-width: 768px) CSS breakpoint)
    const isMobile = window.matchMedia('(max-width: 768px)').matches;
    const userPref = localStorage.getItem('sidebarCollapsed');
    const sidebarCollapsed = userPref !== null
        ? userPref === 'true'
        : isMobile; // default: collapsed on mobile, expanded on desktop

    return {
        sidebarCollapsed: sidebarCollapsed,
        rightCollapsed: localStorage.getItem('rightCollapsed') !== 'false', // default: collapsed

        toggleSidebar() {
            this.sidebarCollapsed = !this.sidebarCollapsed;
            localStorage.setItem('sidebarCollapsed', this.sidebarCollapsed);
            if (this.sidebarCollapsed) {
                document.body.classList.add('sidebar-collapsed');
            } else {
                document.body.classList.remove('sidebar-collapsed');
            }
        },
        toggleRight() {
            this.rightCollapsed = !this.rightCollapsed;
            localStorage.setItem('rightCollapsed', this.rightCollapsed);
            if (this.rightCollapsed) {
                document.body.classList.add('right-collapsed');
            } else {
                document.body.classList.remove('right-collapsed');
            }
        },
        init() {
            if (this.sidebarCollapsed) document.body.classList.add('sidebar-collapsed');
            if (this.rightCollapsed) document.body.classList.add('right-collapsed');
        }
    };
}

// Tab system — uses normal browser navigation, not HTMX swap
// This prevents the sidebar from being duplicated inside the content area
function initTabs() {
    return {
        tabs: [],
        activeTabId: null,

        init() {
            // Restore tabs from sessionStorage
            const saved = sessionStorage.getItem('openTabs');
            if (saved) {
                try {
                    const data = JSON.parse(saved);
                    this.tabs = data.tabs || [];
                    this.activeTabId = data.activeTabId;
                } catch (e) {
                    this.tabs = [];
                    this.activeTabId = null;
                }
            }
            // Always ensure dashboard tab exists
            if (!this.tabs || this.tabs.length === 0) {
                this.tabs = [{ id: 'dashboard', title: 'Trang chủ', url: '/modern/' }];
                this.activeTabId = 'dashboard';
                this.saveState();
            }
            // Mark current page as active tab based on URL
            this.syncActiveFromUrl();
        },

        syncActiveFromUrl() {
            const path = window.location.pathname;
            // Find matching tab
            const match = this.tabs.find(t => path.startsWith(t.url.replace(/\/$/, '')));
            if (match) {
                this.activeTabId = match.id;
            }
            this.saveState();
        },

        openTab(id, title, url) {
            // Check if tab already exists
            const existing = this.tabs.find(t => t.id === id);
            if (existing) {
                this.activeTabId = id;
            } else {
                this.tabs.push({ id, title, url });
                this.activeTabId = id;
            }
            this.saveState();
            // Navigate normally — no HTMX content swap
            window.location.href = url;
        },

        closeTab(id) {
            const idx = this.tabs.findIndex(t => t.id === id);
            if (idx === -1) return;
            this.tabs.splice(idx, 1);
            if (this.activeTabId === id) {
                // Switch to previous tab or first
                if (this.tabs.length > 0) {
                    const prevIdx = Math.max(0, idx - 1);
                    this.activeTabId = this.tabs[prevIdx].id;
                    window.location.href = this.tabs[prevIdx].url;
                }
            }
            this.saveState();
        },

        switchTab(id) {
            this.activeTabId = id;
            const tab = this.tabs.find(t => t.id === id);
            if (tab) {
                // Navigate normally — no HTMX content swap
                window.location.href = tab.url;
            }
            this.saveState();
        },

        saveState() {
            try {
                sessionStorage.setItem('openTabs', JSON.stringify({
                    tabs: this.tabs,
                    activeTabId: this.activeTabId,
                }));
            } catch (e) {
                // sessionStorage might be full or unavailable
            }
        }
    };
}

// Auto-open links marked with data-tab in new tabs
document.addEventListener('click', function (e) {
    const link = e.target.closest('a[data-tab]');
    if (!link) return;
    e.preventDefault();
    const url = link.href;
    const title = link.dataset.tabTitle || link.textContent.trim();
    const id = link.dataset.tab || 'tab_' + Date.now();

    // Find Alpine tabs component
    const el = document.querySelector('[x-data*="initTabs"]');
    if (el && el._x_dataStack) {
        el._x_dataStack[0].openTab(id, title, url);
    } else {
        // Fallback: just navigate
        window.location.href = url;
    }
});

// ===== Sidebar nav enhancements: active state, a11y, pins, expand/collapse =====
(function () {
    var PINS_KEY = 'nav_pins';
    var nav;

    function readPins() {
        try { return JSON.parse(localStorage.getItem(PINS_KEY)) || []; }
        catch (e) { return []; }
    }
    function writePins(arr) {
        try { localStorage.setItem(PINS_KEY, JSON.stringify(arr)); } catch (e) {}
    }

    function setSectionOpen(sectionEl, value) {
        if (!sectionEl || !sectionEl._x_dataStack) return;
        sectionEl._x_dataStack[0].open = value;
    }

    function syncAriaExpanded(titleEl) {
        var section = titleEl.closest('.nav-section');
        if (!section) return;
        var body = section.querySelector('[x-show]');
        var open = body && getComputedStyle(body).display !== 'none';
        titleEl.setAttribute('aria-expanded', open ? 'true' : 'false');
    }

    function markActive() {
        var here = window.location.pathname;
        var items = nav.querySelectorAll('.nav-item');
        var activeSection = null;
        items.forEach(function (a) {
            var href = a.getAttribute('href');
            if (!href) return;
            var isActive = here === href
                || (href !== '/modern/' && href.indexOf('/modern/') === 0 && here.indexOf(href) === 0);
            if (isActive) {
                a.classList.add('active');
                a.setAttribute('aria-current', 'page');
                var sec = a.closest('.nav-section');
                if (sec) activeSection = sec;
            }
        });
        if (activeSection) setSectionOpen(activeSection, true);
    }

    function setupA11y() {
        nav.querySelectorAll('.nav-section-title').forEach(function (title) {
            if (title.classList.contains('nav-pins-title')) return;
            title.setAttribute('role', 'button');
            title.setAttribute('tabindex', '0');
            title.setAttribute('aria-expanded', 'false');
            title.addEventListener('keydown', function (e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    title.click();
                }
            });
            title.addEventListener('click', function () {
                setTimeout(function () { syncAriaExpanded(title); }, 60);
            });
            syncAriaExpanded(title);
        });
        // Title tooltips for collapsed mode
        nav.querySelectorAll('.nav-item').forEach(function (a) {
            if (a.hasAttribute('title')) return;
            var span = a.querySelector('span');
            if (span) a.setAttribute('title', span.textContent.trim());
        });
    }

    function itemData(a) {
        var span = a.querySelector('span:not(.nav-badge)');
        var icon = a.querySelector('i');
        return {
            href: a.getAttribute('href'),
            label: span ? span.textContent.trim() : '',
            icon: icon ? icon.className : '',
        };
    }

    function renderPins() {
        var section = document.getElementById('ss-pins-section');
        var list = document.getElementById('ss-pins-list');
        if (!section || !list) return;
        var pins = readPins();
        list.innerHTML = '';
        if (!pins.length) { section.setAttribute('hidden', ''); return; }
        section.removeAttribute('hidden');
        pins.forEach(function (p) {
            var a = document.createElement('a');
            a.className = 'nav-item';
            a.href = p.href;
            a.title = p.label;
            a.innerHTML = (p.icon ? '<i class="' + p.icon + '"></i> ' : '')
                + '<span>' + p.label + '</span>'
                + '<button type="button" class="nav-pin pinned" aria-label="Bỏ ghim" data-unpin="' + p.href + '"><i class="bi bi-x-lg"></i></button>';
            list.appendChild(a);
        });
    }

    function addPinButtons() {
        nav.querySelectorAll('.nav-section .nav-item').forEach(function (a) {
            if (a.closest('#ss-pins-list')) return;
            if (a.querySelector('.nav-pin')) return;
            var d = itemData(a);
            var btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'nav-pin';
            btn.setAttribute('aria-label', 'Ghim ' + d.label);
            btn.innerHTML = '<i class="bi bi-pin"></i>';
            btn.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                var pins = readPins();
                var href = a.getAttribute('href');
                var exists = pins.find(function (p) { return p.href === href; });
                if (exists) {
                    pins = pins.filter(function (p) { return p.href !== href; });
                    btn.classList.remove('pinned');
                    btn.querySelector('i').className = 'bi bi-pin';
                } else {
                    pins.push(d);
                    btn.classList.add('pinned');
                    btn.querySelector('i').className = 'bi bi-pin-fill';
                }
                writePins(pins);
                renderPins();
            });
            // Reflect pinned state on load
            var pins = readPins();
            if (pins.find(function (p) { return p.href === d.href; })) {
                btn.classList.add('pinned');
                btn.innerHTML = '<i class="bi bi-pin-fill"></i>';
            }
            a.appendChild(btn);
        });
    }

    function setupTools() {
        var exp = document.getElementById('ss-expand-all');
        var col = document.getElementById('ss-collapse-all');
        if (exp) exp.addEventListener('click', function () {
            nav.querySelectorAll('.nav-section').forEach(function (s) {
                setSectionOpen(s, true);
                var key = s.querySelector('[x-show]');
            });
            nav.querySelectorAll('.nav-section-title').forEach(syncAriaExpanded);
        });
        if (col) col.addEventListener('click', function () {
            nav.querySelectorAll('.nav-section').forEach(function (s) {
                setSectionOpen(s, false);
            });
            nav.querySelectorAll('.nav-section-title').forEach(syncAriaExpanded);
        });
        var clearBtn = document.getElementById('ss-pins-clear');
        if (clearBtn) clearBtn.addEventListener('click', function () {
            writePins([]);
            renderPins();
            nav.querySelectorAll('.nav-pin.pinned').forEach(function (b) {
                b.classList.remove('pinned');
                b.innerHTML = '<i class="bi bi-pin"></i>';
            });
        });
        // Unpin from within pinned list
        document.addEventListener('click', function (e) {
            var btn = e.target.closest('[data-unpin]');
            if (!btn) return;
            e.preventDefault();
            var href = btn.getAttribute('data-unpin');
            writePins(readPins().filter(function (p) { return p.href !== href; }));
            renderPins();
            // Update the source pin button if visible
            var src = nav.querySelector('.nav-item[href="' + href + '"] .nav-pin');
            if (src) { src.classList.remove('pinned'); src.innerHTML = '<i class="bi bi-pin"></i>'; }
        });
    }

    function init() {
        nav = document.querySelector('.sidebar nav');
        if (!nav) return;
        renderPins();
        addPinButtons();
        markActive();
        setupA11y();
        setupTools();
    }

    if (document.readyState !== 'loading') {
        // Alpine may still be initializing; defer to next tick.
        requestAnimationFrame(init);
    } else {
        document.addEventListener('DOMContentLoaded', function () { requestAnimationFrame(init); });
    }
})();

