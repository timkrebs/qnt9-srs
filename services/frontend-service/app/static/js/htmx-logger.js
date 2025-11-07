/**
 * HTMX Request Logging Integration.
 * 
 * Intercepts and logs all HTMX requests to the browser console
 * for debugging frontend-backend communication.
 */

(function() {
    'use strict';
    
    if (!window.logger) {
        console.error('Logger not initialized. Include logger.js before htmx-logger.js');
        return;
    }
    
    // Track active requests
    const activeRequests = new Map();
    
    // Log HTMX configuration
    document.addEventListener('DOMContentLoaded', function() {
        window.logger.info('HTMX initialized', {
            version: htmx.version || 'unknown',
            timeout: htmx.config.timeout,
            historyCacheSize: htmx.config.historyCacheSize
        });
    });
    
    // Before request is sent
    document.body.addEventListener('htmx:beforeRequest', function(evt) {
        const detail = evt.detail;
        const requestId = window.logger.generateId();
        
        // Store request info
        activeRequests.set(detail.xhr, {
            requestId,
            startTime: performance.now(),
            method: detail.verb || 'GET',
            url: detail.path,
            target: detail.target?.id || 'unknown'
        });
        
        // Store for later reference
        window._lastRequestId = requestId;
        
        window.logger.info('HTMX request started', {
            requestId,
            method: detail.verb || 'GET',
            url: detail.path,
            target: detail.target?.id,
            trigger: detail.triggeringEvent?.type
        });
    });
    
    // After request completes successfully
    document.body.addEventListener('htmx:afterRequest', function(evt) {
        const detail = evt.detail;
        const requestInfo = activeRequests.get(detail.xhr);
        
        if (!requestInfo) return;
        
        const duration = (performance.now() - requestInfo.startTime).toFixed(2);
        const success = detail.successful;
        
        if (success) {
            window.logger.info('HTMX request completed', {
                requestId: requestInfo.requestId,
                method: requestInfo.method,
                url: requestInfo.url,
                statusCode: detail.xhr.status,
                duration: `${duration}ms`,
                target: requestInfo.target
            });
        } else {
            window.logger.error('HTMX request failed', {
                requestId: requestInfo.requestId,
                method: requestInfo.method,
                url: requestInfo.url,
                statusCode: detail.xhr.status,
                duration: `${duration}ms`,
                error: detail.xhr.statusText
            });
        }
        
        activeRequests.delete(detail.xhr);
    });
    
    // After content swap
    document.body.addEventListener('htmx:afterSwap', function(evt) {
        const detail = evt.detail;
        
        window.logger.debug('HTMX content swapped', {
            target: detail.target?.id,
            swapStyle: detail.swapStyle,
            contentLength: detail.xhr.responseText?.length || 0
        });
    });
    
    // Handle response errors
    document.body.addEventListener('htmx:responseError', function(evt) {
        const detail = evt.detail;
        const requestInfo = activeRequests.get(detail.xhr);
        
        window.logger.error('HTMX response error', {
            requestId: requestInfo?.requestId,
            method: requestInfo?.method,
            url: requestInfo?.url,
            statusCode: detail.xhr.status,
            statusText: detail.xhr.statusText,
            responseText: detail.xhr.responseText?.substring(0, 200)
        });
        
        if (requestInfo) {
            activeRequests.delete(detail.xhr);
        }
    });
    
    // Handle timeout
    document.body.addEventListener('htmx:timeout', function(evt) {
        const detail = evt.detail;
        const requestInfo = activeRequests.get(detail.xhr);
        
        window.logger.error('HTMX request timeout', {
            requestId: requestInfo?.requestId,
            method: requestInfo?.method,
            url: requestInfo?.url,
            timeout: htmx.config.timeout
        });
        
        if (requestInfo) {
            activeRequests.delete(detail.xhr);
        }
    });
    
    // Handle validation errors
    document.body.addEventListener('htmx:validation:failed', function(evt) {
        window.logger.warning('HTMX validation failed', {
            target: evt.detail.elt?.id,
            message: evt.detail.message
        });
    });
    
    // Log when loading indicator shows/hides
    document.body.addEventListener('htmx:beforeSend', function(evt) {
        window.logger.debug('HTMX sending request', {
            xhr: 'XMLHttpRequest initiated'
        });
    });
    
    window.logger.info('HTMX logger initialized');
    
})();

// Helper function to get current request stats
window.getHTMXStats = function() {
    const logs = window.logger.exportLogs();
    const htmxLogs = logs.filter(log => log.message.includes('HTMX'));
    
    const stats = {
        totalRequests: 0,
        successful: 0,
        failed: 0,
        averageDuration: 0,
        errors: []
    };
    
    const durations = [];
    
    htmxLogs.forEach(log => {
        if (log.message === 'HTMX request completed') {
            stats.totalRequests++;
            stats.successful++;
            if (log.duration) {
                durations.push(parseFloat(log.duration));
            }
        } else if (log.message === 'HTMX request failed' || log.message === 'HTMX response error') {
            stats.totalRequests++;
            stats.failed++;
            stats.errors.push({
                url: log.url,
                statusCode: log.statusCode,
                error: log.error || log.statusText
            });
        }
    });
    
    if (durations.length > 0) {
        stats.averageDuration = (durations.reduce((a, b) => a + b, 0) / durations.length).toFixed(2) + 'ms';
    }
    
    console.table(stats);
    return stats;
};
