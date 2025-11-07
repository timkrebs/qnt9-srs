/**
 * Client-side logging utility for browser console.
 * 
 * Provides structured logging for frontend debugging in Chrome Developer Console.
 * All logs include timestamps, request IDs, and structured context.
 */

class FrontendLogger {
    constructor(config = {}) {
        this.enabled = config.enabled !== false;
        this.level = config.level || 'INFO';
        this.serviceName = config.serviceName || 'frontend-service';
        this.levels = {
            DEBUG: 0,
            INFO: 1,
            WARNING: 2,
            ERROR: 3
        };
        
        this.currentLevel = this.levels[this.level] || this.levels.INFO;
        
        // Generate session ID for tracking
        this.sessionId = this.generateId();
        
        this.log('INFO', 'Logger initialized', {
            sessionId: this.sessionId,
            logLevel: this.level,
            userAgent: navigator.userAgent
        });
    }
    
    generateId() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }
    
    formatMessage(level, message, context = {}) {
        const timestamp = new Date().toISOString();
        const requestId = context.requestId || this.getRequestIdFromHeaders();
        
        return {
            timestamp,
            level,
            service: this.serviceName,
            message,
            sessionId: this.sessionId,
            requestId,
            ...context
        };
    }
    
    getRequestIdFromHeaders() {
        // Try to extract request ID from last response
        return window._lastRequestId || null;
    }
    
    log(level, message, context = {}) {
        if (!this.enabled) return;
        if (this.levels[level] < this.currentLevel) return;
        
        const logData = this.formatMessage(level, message, context);
        const consoleMethod = level === 'ERROR' ? 'error' : 
                             level === 'WARNING' ? 'warn' : 
                             level === 'DEBUG' ? 'debug' : 'log';
        
        // Styled console output
        const style = this.getStyle(level);
        console[consoleMethod](
            `%c[${level}]%c ${message}`,
            style,
            'color: inherit',
            logData
        );
        
        // Store in session for export
        this.storeLog(logData);
    }
    
    getStyle(level) {
        const styles = {
            DEBUG: 'color: #6366f1; font-weight: bold',
            INFO: 'color: #10b981; font-weight: bold',
            WARNING: 'color: #f59e0b; font-weight: bold',
            ERROR: 'color: #ef4444; font-weight: bold'
        };
        return styles[level] || styles.INFO;
    }
    
    storeLog(logData) {
        if (!window.sessionStorage) return;
        
        try {
            const logs = JSON.parse(sessionStorage.getItem('frontend_logs') || '[]');
            logs.push(logData);
            
            // Keep only last 100 logs
            if (logs.length > 100) {
                logs.shift();
            }
            
            sessionStorage.setItem('frontend_logs', JSON.stringify(logs));
        } catch (e) {
            // Silently fail if storage is full
        }
    }
    
    debug(message, context) {
        this.log('DEBUG', message, context);
    }
    
    info(message, context) {
        this.log('INFO', message, context);
    }
    
    warning(message, context) {
        this.log('WARNING', message, context);
    }
    
    error(message, context) {
        this.log('ERROR', message, context);
    }
    
    exportLogs() {
        if (!window.sessionStorage) return [];
        
        try {
            return JSON.parse(sessionStorage.getItem('frontend_logs') || '[]');
        } catch (e) {
            return [];
        }
    }
    
    clearLogs() {
        if (!window.sessionStorage) return;
        sessionStorage.removeItem('frontend_logs');
        this.info('Logs cleared');
    }
    
    downloadLogs() {
        const logs = this.exportLogs();
        const blob = new Blob([JSON.stringify(logs, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `frontend-logs-${new Date().toISOString()}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        this.info('Logs downloaded');
    }
}

// Initialize global logger
window.logger = new FrontendLogger({
    enabled: true,
    level: 'INFO'  // Change to 'DEBUG' for more verbose logging
});

// Log page load
window.logger.info('Page loaded', {
    url: window.location.href,
    referrer: document.referrer
});

// Print usage instructions to console
console.log('%c===========================================', 'color: #10b981; font-weight: bold');
console.log('%cQNT9 Frontend Logger Initialized', 'color: #10b981; font-weight: bold; font-size: 16px');
console.log('%c===========================================', 'color: #10b981; font-weight: bold');
console.log('');
console.log('%cAvailable Commands:', 'color: #6366f1; font-weight: bold');
console.log('  logger.info("message", {context})     - Log info message');
console.log('  logger.debug("message", {context})    - Log debug message');
console.log('  logger.warning("message", {context})  - Log warning message');
console.log('  logger.error("message", {context})    - Log error message');
console.log('');
console.log('%cUtility Functions:', 'color: #6366f1; font-weight: bold');
console.log('  logger.exportLogs()                   - Export all logs as JSON');
console.log('  logger.downloadLogs()                 - Download logs as file');
console.log('  logger.clearLogs()                    - Clear all stored logs');
console.log('  getHTMXStats()                        - Show HTMX request statistics');
console.log('');
console.log('%cTo change log level:', 'color: #6366f1; font-weight: bold');
console.log('  logger.level = "DEBUG"                - Show debug logs');
console.log('  logger.currentLevel = logger.levels.DEBUG');
console.log('');
console.log('%cTip:', 'color: #f59e0b; font-weight: bold');
console.log('  All HTMX requests are automatically logged with timing and status');
console.log('  Request IDs correlate with backend server logs');
console.log('');

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FrontendLogger;
}
