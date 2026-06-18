// Sidebar toggle — persists in localStorage
function initSidebar() {
    return {
        sidebarCollapsed: localStorage.getItem('sidebarCollapsed') === 'true',
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
