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

    /*
     * Reveal each band as it scrolls into view, staggering its children.
     *
     * The classes are added from here rather than sitting in the markup, so a
     * visitor without JS — or without IntersectionObserver — gets a fully
     * visible page instead of one permanently stuck at opacity 0.
     */
    function initReveal() {
        if (!('IntersectionObserver' in window)) return;

        const bands = document.querySelectorAll('.band:not(.band-hero)');
        bands.forEach(band => {
            band.classList.add('reveal');
            [...band.children].forEach((child, i) => child.style.setProperty('--i', i));
        });

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (!entry.isIntersecting) return;
                entry.target.classList.add('in-view');
                observer.unobserve(entry.target);
            });
        }, { rootMargin: '0px 0px -12% 0px', threshold: 0.08 });

        bands.forEach(band => observer.observe(band));
    }

    // The hero is above the fold and animates immediately.
    [...document.querySelectorAll('.band-hero > *')]
        .forEach((child, i) => child.style.setProperty('--i', i));

    initReveal();

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
