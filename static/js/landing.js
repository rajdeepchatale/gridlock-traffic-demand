/*
 * Landing page behaviour. Deliberately tiny — the page is server-rendered and
 * needs no data fetching. The theme contract matches the dashboard exactly, so
 * a visitor's choice carries across both pages.
 */
(function () {
    'use strict';

    const STORAGE_KEY = 'btp_theme';

    function readTheme() {
        try {
            return localStorage.getItem(STORAGE_KEY) || 'dark';
        } catch (err) {
            return 'dark';
        }
    }

    function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
    }

    applyTheme(readTheme());

    document.getElementById('themeToggle').addEventListener('click', () => {
        const next = readTheme() === 'dark' ? 'light' : 'dark';
        try {
            localStorage.setItem(STORAGE_KEY, next);
        } catch (err) {
            /* Private browsing — the toggle still works for this page view. */
        }
        applyTheme(next);
    });
})();
