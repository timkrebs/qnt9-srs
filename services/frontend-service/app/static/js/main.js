/**
 * QNT9 Frontend Service - Main JavaScript
 * Handles additional interactivity beyond HTMX
 */

// Debounce utility function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('QNT9 Frontend Service initialized');
    
    // Add keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Focus search input with Ctrl+K or Cmd+K
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            const searchInput = document.getElementById('query');
            if (searchInput) {
                searchInput.focus();
                searchInput.select();
            }
        }
        
        // Clear search with Escape
        if (e.key === 'Escape') {
            const searchInput = document.getElementById('query');
            const suggestions = document.getElementById('suggestions');
            
            if (suggestions && suggestions.innerHTML) {
                suggestions.innerHTML = '';
            } else if (searchInput && document.activeElement === searchInput) {
                searchInput.blur();
            }
        }
    });
    
    // Track analytics (if needed later)
    trackPageView();
});

// Simple analytics tracking
function trackPageView() {
    // Placeholder for analytics
    console.log('Page view:', window.location.pathname);
}

// Export for use in inline scripts if needed
window.QNT9 = {
    debounce,
    trackPageView
};
