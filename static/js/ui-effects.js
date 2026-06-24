/**
 * ExpenseWise UI Effects - Professional Fintech Dashboard Animations
 * Lightweight vanilla JavaScript for smooth, production-ready animations
 */

(function() {
    'use strict';

    // ================= CONFIGURATION =================
    const CONFIG = {
        numberAnimationDuration: 1000,    // ms for counter animation
        numberAnimationEasing: 'easeOutQuart',
        chartAnimationDuration: 1200,
        skeletonDelay: 2000,               // ms before removing skeletons
        scrollRevealThreshold: 0.1
    };

    // ================= UTILITY FUNCTIONS =================
    
    /**
     * Easing function - easeOutQuart
     * @param {number} t - Current time
     * @returns {number} Eased value
     */
    function easeOutQuart(t) {
        return 1 - Math.pow(1 - t, 4);
    }

    /**
     * Check if element is in viewport
     * @param {HTMLElement} element - Element to check
     * @returns {boolean}
     */
    function isInViewport(element) {
        const rect = element.getBoundingClientRect();
        return (
            rect.top < (window.innerHeight || document.documentElement.clientHeight) &&
            rect.bottom > 0 &&
            rect.left < (window.innerWidth || document.documentElement.clientWidth) &&
            rect.right > 0
        );
    }

    // ================= ANIMATED NUMBER COUNTERS =================
    
    /**
     * Animate number from 0 to value
     * @param {HTMLElement} element - Target element
     * @param {number} endValue - Final value
     * @param {string} prefix - Prefix (e.g., '$')
     * @param {string} suffix - Suffix (e.g., ',')
     * @param {number} duration - Animation duration in ms
     */
    function animateNumber(element, endValue, prefix = '', suffix = '', duration = CONFIG.numberAnimationDuration) {
        if (!element) return;
        
        const startTime = performance.now();
        const startValue = 0;
        
        // Format number with commas
        const formatNumber = (num) => {
            return Math.floor(num).toLocaleString();
        };
        
        // Animation loop
        function update(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const easedProgress = easeOutQuart(progress);
            const currentValue = startValue + (endValue - startValue) * easedProgress;
            
            element.textContent = prefix + formatNumber(currentValue) + suffix;
            
            if (progress < 1) {
                requestAnimationFrame(update);
            } else {
                // Ensure final value is exact
                element.textContent = prefix + formatNumber(endValue) + suffix;
            }
        }
        
        requestAnimationFrame(update);
    }

    /**
     * Initialize all animated counters on page
     */
    function initCounters() {
        const counters = document.querySelectorAll('[data-counter]');
        
        counters.forEach(counter => {
            const value = parseFloat(counter.dataset.counter);
            const prefix = counter.dataset.prefix || '';
            const suffix = counter.dataset.suffix || '';
            
            // Only animate if element is visible
            if (isInViewport(counter)) {
                animateNumber(counter, value, prefix, suffix);
            }
        });
    }

    // ================= SKELETON LOADING =================
    
    /**
     * Hide skeleton loaders and show actual content
     */
    function hideSkeletons() {
        const skeletons = document.querySelectorAll('.skeleton');
        
        skeletons.forEach(skeleton => {
            skeleton.classList.add('fade-out');
            
            // Find and show content
            const content = skeleton.nextElementSibling;
            if (content && content.classList.contains('skeleton-content')) {
                content.style.display = '';
            }
        });
        
        // Remove skeleton classes after animation
        setTimeout(() => {
            skeletons.forEach(skeleton => {
                skeleton.style.display = 'none';
            });
        }, 300);
    }

    /**
     * Initialize skeleton loading with delay
     */
    function initSkeletons() {
        // Delay hiding skeletons to simulate loading
        setTimeout(hideSkeletons, CONFIG.skeletonDelay);
    }

    // ================= SCROLL REVEAL ANIMATIONS =================
    
    /**
     * Initialize scroll reveal animations using Intersection Observer
     */
    function initScrollReveal() {
        const revealElements = document.querySelectorAll('.reveal');
        
        if (!revealElements.length) return;
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                    observer.unobserve(entry.target);
                }
            });
        }, {
            threshold: CONFIG.scrollRevealThreshold
        });
        
        revealElements.forEach(element => {
            observer.observe(element);
        });
    }

    // ================= CHART.JS ANIMATIONS =================
    
    /**
     * Get enhanced Chart.js configuration for smooth animations
     * @returns {object} Chart.js default options
     */
    function getChartAnimationConfig() {
        return {
            duration: CONFIG.chartAnimationDuration,
            easing: 'easeOutQuart'
        };
    }

    /**
     * Apply animation to existing Chart.js charts
     */
    function animateCharts() {
        // Wait for Chart.js to be loaded
        if (typeof Chart === 'undefined') {
            // Retry after a short delay
            setTimeout(animateCharts, 100);
            return;
        }
        
        // Override default Chart.js animation
        Chart.defaults.animation = getChartAnimationConfig();
        
        // Animate any existing charts - Chart.js v3+ uses Chart.getChart()
        try {
            // Try to get all charts using Chart.js v3+ API
            const chartElements = document.querySelectorAll('canvas[id^="chart-"], canvas[id^="expense"]');
            if (chartElements && chartElements.length > 0) {
                console.log('Found chart canvases:', chartElements.length);
            }
        } catch (e) {
            console.log('Chart animation skipped:', e.message);
        }
    }

    // ================= NOTIFICATION BELL ANIMATION =================
    
    /**
     * Trigger shake animation on notification bell
     */
    function triggerBellShake() {
        const bell = document.querySelector('.notification-bell');
        if (!bell) return;
        
        // Remove existing animation class
        bell.classList.remove('shake');
        
        // Force reflow to restart animation
        void bell.offsetWidth;
        
        // Add animation class
        bell.classList.add('shake');
        
        // Remove class after animation completes
        setTimeout(() => {
            bell.classList.remove('shake');
        }, 500);
    }

    /**
     * Listen for new notifications and trigger bell animation
     * Call this function when a new notification arrives
     */
    window.triggerNotificationBell = triggerBellShake;

    // ================= PROGRESS BAR ANIMATIONS =================
    
    /**
     * Animate progress bars on page load
     */
    function animateProgressBars() {
        const progressBars = document.querySelectorAll('.progress-bar[data-width]');
        
        progressBars.forEach(bar => {
            const targetWidth = bar.dataset.width;
            
            // Reset to 0 first
            bar.style.width = '0%';
            
            // Animate to target
            requestAnimationFrame(() => {
                bar.style.transition = 'width 1.2s cubic-bezier(0.4, 0, 0.2, 1)';
                bar.style.width = targetWidth + '%';
            });
        });
    }

    // ================= CARD STAGGERED ANIMATION =================
    
    /**
     * Initialize staggered card animations
     */
    function initCardAnimations() {
        const cards = document.querySelectorAll('.card-animate');
        
        cards.forEach((card, index) => {
            card.style.animationDelay = (index * 0.05) + 's';
        });
    }

    // ================= DARK MODE TRANSITIONS =================
    
    /**
     * Enhanced dark mode toggle with smooth transitions
     */
    function initDarkModeEnhancements() {
        const darkToggle = document.getElementById('darkModeToggle');
        
        if (!darkToggle) return;
        
        // The base template already handles dark mode toggle
        // This adds additional smoothness enhancements
        
        darkToggle.addEventListener('click', () => {
            // Add transition overlay for smoother experience
            document.body.style.transition = 'background-color 0.3s, color 0.3s';
        });
    }

    // ================= HEALTH SCORE CIRCLE =================
    
    /**
     * Animate health score circle
     */
    function animateHealthScore() {
        const circles = document.querySelectorAll('.health-score-circle[data-score]');
        
        circles.forEach(circle => {
            const score = parseInt(circle.dataset.score);
            const valueElement = circle.querySelector('.score-value');
            
            if (!valueElement) return;
            
            // Animate the number
            animateNumber(valueElement, score, '', '', 1200);
            
            // Animate the circle
            const circumference = 2 * Math.PI * 45;
            const offset = circumference - (score / 100) * circumference;
            
            // Set color based on score
            let color;
            if (score >= 80) color = '#1cc88a';
            else if (score >= 60) color = '#f6c23e';
            else color = '#e74a3b';
            
            // Apply gradient
            circle.style.background = `conic-gradient(${color} ${score}%, #e9ecef 0%)`;
            
            // Inner circle color
            setTimeout(() => {
                if (circle.querySelector('.score-value')) {
                    circle.style.background = `${color} ${score}%, #1e2228 ${score}%`;
                }
            }, 1200);
        });
    }

    // ================= TOOLTIP INITIALIZATION =================
    
    /**
     * Initialize Bootstrap tooltips
     */
    function initTooltips() {
        // Check if Bootstrap tooltips are available
        if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
            const tooltipElements = document.querySelectorAll('[data-bs-toggle="tooltip"]');
            tooltipElements.forEach(element => {
                new bootstrap.Tooltip(element, {
                    animation: true,
                    trigger: 'hover focus',
                    delay: { show: 200, hide: 100 }
                });
            });
        }
    }

    // ================= PAGE TRANSITION =================
    
    /**
     * Handle page transitions
     */
    function initPageTransition() {
        // Add fade-in class to page content
        const pageContent = document.querySelector('.page-content');
        if (pageContent) {
            pageContent.classList.add('page-fade-in');
        }
    }

    // ================= INITIALIZATION =================
    
    /**
     * Initialize all UI effects when DOM is ready
     */
    function init() {
        // Wait for DOM to be fully loaded
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', init);
            return;
        }
        
        // Initialize all effects
        initCounters();
        initSkeletons();
        initScrollReveal();
        initCardAnimations();
        animateProgressBars();
        animateHealthScore();
        initDarkModeEnhancements();
        initTooltips();
        animateCharts();
        
        console.log('✓ UI Effects initialized');
    }

    // Auto-initialize
    init();

    // ================= PUBLIC API =================
    
    // Expose functions for manual control if needed
    window.UIEffects = {
        animateNumber: animateNumber,
        triggerBellShake: triggerBellShake,
        hideSkeletons: hideSkeletons,
        animateCharts: animateCharts,
        CONFIG: CONFIG
    };

})();
