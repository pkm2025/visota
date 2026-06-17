// Sidebar toggle — persists in localStorage
function initSidebar() {
    return {
        sidebarCollapsed: localStorage.getItem('sidebarCollapsed') === 'true',
        rightCollapsed: localStorage.getItem('rightCollapsed') === 'true',

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

// Multi-tab system
function initTabs() {
    return {
        tabs: [],
        activeTabId: null,

        init() {
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
            if (!this.tabs || this.tabs.length === 0) {
                this.openTab('dashboard', 'Trang chủ', '/modern/');
            }
        },

        openTab(id, title, url) {
            const existing = this.tabs.find(t => t.id === id);
            if (existing) {
                this.activeTabId = id;
            } else {
                this.tabs.push({ id, title, url });
                this.activeTabId = id;
            }
            this.saveState();
            if (typeof htmx !== 'undefined') {
                htmx.ajax('GET', url, { target: '#tab-content', swap: 'innerHTML' });
            }
        },

        closeTab(id) {
            const idx = this.tabs.findIndex(t => t.id === id);
            if (idx === -1) return;
            this.tabs.splice(idx, 1);
            if (this.activeTabId === id) {
                if (this.tabs.length > 0) {
                    const prevIdx = Math.max(0, idx - 1);
                    this.activeTabId = this.tabs[prevIdx].id;
                    if (typeof htmx !== 'undefined') {
                        htmx.ajax('GET', this.tabs[prevIdx].url, { target: '#tab-content', swap: 'innerHTML' });
                    }
                } else {
                    this.openTab('dashboard', 'Trang chủ', '/modern/');
                    return;
                }
            }
            this.saveState();
        },

        switchTab(id) {
            this.activeTabId = id;
            const tab = this.tabs.find(t => t.id === id);
            if (tab && typeof htmx !== 'undefined') {
                htmx.ajax('GET', tab.url, { target: '#tab-content', swap: 'innerHTML' });
            }
            this.saveState();
        },

        saveState() {
            sessionStorage.setItem('openTabs', JSON.stringify({
                tabs: this.tabs,
                activeTabId: this.activeTabId,
            }));
        }
    };
}

// Auto-open links marked with data-tab in tabs
document.addEventListener('click', function (e) {
    const link = e.target.closest('a[data-tab]');
    if (!link) return;
    e.preventDefault();
    const url = link.href;
    const title = link.dataset.tabTitle || link.textContent.trim();
    const id = link.dataset.tab || 'tab_' + Date.now();

    const tabsComp = document.querySelector('[x-data*="initTabs"]');
    if (tabsComp && tabsComp._x_dataStack) {
        tabsComp._x_dataStack[0].openTab(id, title, url);
    }
});
