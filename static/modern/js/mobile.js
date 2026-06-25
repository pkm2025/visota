/* PMKetoan mobile interactions: pull-to-refresh + swipe gestures.

Auto-activates on touch devices. Safe to load on desktop (no-op).
 */

(function () {
    'use strict';

    // Only enable on touch devices
    const isTouch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
    if (!isTouch) return;

    // Highlight active bottom nav item
    function highlightActiveNav() {
        const path = window.location.pathname;
        document.querySelectorAll('.mobile-bottom-nav-item').forEach(item => {
            const href = item.getAttribute('href');
            if (href && href !== '#' && path === href) {
                item.classList.add('active');
            }
        });
    }

    // ---------- Pull to refresh ----------

    function setupPullToRefresh() {
        let touchStartY = 0;
        let pulling = false;
        let pullDistance = 0;
        const THRESHOLD = 70;
        const indicator = document.getElementById('ptr-indicator');
        if (!indicator) return;

        // Only on list-like pages
        const isListPage = document.querySelector('table tbody, .list-group');
        if (!isListPage) return;

        document.addEventListener('touchstart', (e) => {
            if (window.scrollY === 0) {
                touchStartY = e.touches[0].clientY;
                pulling = true;
                pullDistance = 0;
            } else {
                pulling = false;
            }
        }, { passive: true });

        document.addEventListener('touchmove', (e) => {
            if (!pulling) return;
            const currentY = e.touches[0].clientY;
            pullDistance = Math.max(0, currentY - touchStartY);
            if (pullDistance > 0 && pullDistance < 120) {
                const progress = Math.min(pullDistance / THRESHOLD, 1);
                indicator.style.top = `${(progress * 60) - 60}px`;
                const icon = indicator.querySelector('i');
                if (icon) icon.style.transform = `rotate(${progress * 360}deg)`;
            }
        }, { passive: true });

        document.addEventListener('touchend', () => {
            if (!pulling) return;
            pulling = false;
            if (pullDistance >= THRESHOLD) {
                // Trigger refresh
                indicator.classList.add('refreshing', 'visible');
                indicator.style.top = '0';
                setTimeout(() => {
                    window.location.reload();
                }, 500);
            } else {
                // Snap back
                indicator.style.top = '-60px';
            }
            pullDistance = 0;
        });
    }

    // ---------- Swipe to delete on rows ----------

    function setupSwipeToDelete() {
        let startX = 0;
        let currentX = 0;
        let swiping = false;
        let activeRow = null;

        document.querySelectorAll('table tbody tr[data-swipe-delete]').forEach(row => {
            row.classList.add('swipe-row');

            // Add delete button if not exists
            if (!row.querySelector('.swipe-row-delete')) {
                const delBtn = document.createElement('div');
                delBtn.className = 'swipe-row-delete';
                delBtn.innerHTML = '<i class="bi bi-trash"></i>';
                delBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    if (confirm('Xóa dòng này?')) {
                        const url = row.dataset.swipeDelete;
                        fetch(url, { method: 'POST', headers: { 'X-CSRFToken': getCsrf() } })
                            .then(() => row.remove());
                    }
                });
                row.appendChild(delBtn);
            }

            row.addEventListener('touchstart', (e) => {
                startX = e.touches[0].clientX;
                currentX = startX;
                swiping = true;
                activeRow = row;
                // Close other open rows
                document.querySelectorAll('.swipe-row.swiped').forEach(r => {
                    if (r !== row) r.classList.remove('swiped');
                });
            }, { passive: true });

            row.addEventListener('touchmove', (e) => {
                if (!swiping || activeRow !== row) return;
                currentX = e.touches[0].clientX;
                const diff = currentX - startX;
                if (diff < 0 && diff > -100) {
                    e.preventDefault();
                    row.style.transform = `translateX(${diff}px)`;
                }
            });

            row.addEventListener('touchend', () => {
                if (!swiping || activeRow !== row) return;
                swiping = false;
                const diff = currentX - startX;
                if (diff < -60) {
                    row.classList.add('swiped');
                } else {
                    row.classList.remove('swiped');
                }
                row.style.transform = '';
                activeRow = null;
            });
        });
    }

    function getCsrf() {
        const input = document.querySelector('[name=csrfmiddlewaretoken]');
        return input ? input.value : '';
    }

    // ---------- Long-press for context menu ----------

    function setupLongPress() {
        let pressTimer = null;
        document.querySelectorAll('[data-long-press]').forEach(el => {
            el.addEventListener('touchstart', () => {
                pressTimer = setTimeout(() => {
                    const url = el.dataset.longPress;
                    if (url) window.location.href = url;
                }, 600);
            });
            el.addEventListener('touchend', () => clearTimeout(pressTimer));
            el.addEventListener('touchmove', () => clearTimeout(pressTimer));
        });
    }

    // ---------- Init ----------

    document.addEventListener('DOMContentLoaded', () => {
        highlightActiveNav();
        setupPullToRefresh();
        setupSwipeToDelete();
        setupLongPress();
    });

    // Re-init after HTMX swaps
    document.body.addEventListener('htmx:afterSwap', () => {
        setupSwipeToDelete();
    });
})();
