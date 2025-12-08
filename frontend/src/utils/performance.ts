/**
 * NyayamGPT Performance Monitoring
 * =================================
 * Core Web Vitals tracking and API performance monitoring
 */

import { onCLS, onINP, onFCP, onLCP, onTTFB, type Metric } from 'web-vitals';

// API endpoint for metrics
const METRICS_ENDPOINT = '/api/metrics';

// Metric types
interface PerformanceMetric {
  name: string;
  value: number;
  delta: number;
  id: string;
  navigationType: string;
  rating: 'good' | 'needs-improvement' | 'poor';
}

interface APIMetric {
  endpoint: string;
  method: string;
  duration: number;
  status: number;
  timestamp: number;
  success: boolean;
}

// Queue for batching metrics
let metricsQueue: (PerformanceMetric | APIMetric)[] = [];
let flushTimeout: ReturnType<typeof setTimeout> | null = null;

/**
 * Send metrics to backend using sendBeacon for reliability
 */
function sendMetrics(metrics: (PerformanceMetric | APIMetric)[]) {
  if (metrics.length === 0) return;

  const payload = JSON.stringify({
    metrics,
    timestamp: Date.now(),
    url: window.location.href,
    userAgent: navigator.userAgent,
  });

  // Use sendBeacon for reliability (works even on page unload)
  if (navigator.sendBeacon) {
    navigator.sendBeacon(METRICS_ENDPOINT, payload);
  } else {
    // Fallback to fetch
    fetch(METRICS_ENDPOINT, {
      method: 'POST',
      body: payload,
      headers: { 'Content-Type': 'application/json' },
      keepalive: true,
    }).catch(() => {
      // Silently fail
    });
  }
}

/**
 * Flush metrics queue
 */
function flushMetrics() {
  if (metricsQueue.length > 0) {
    sendMetrics([...metricsQueue]);
    metricsQueue = [];
  }
  flushTimeout = null;
}

/**
 * Queue a metric for sending
 */
function queueMetric(metric: PerformanceMetric | APIMetric) {
  metricsQueue.push(metric);

  // Batch metrics - flush every 5 seconds or when queue reaches 10
  if (metricsQueue.length >= 10) {
    flushMetrics();
  } else if (!flushTimeout) {
    flushTimeout = setTimeout(flushMetrics, 5000);
  }
}

/**
 * Convert web-vitals Metric to our format
 */
function formatWebVitalMetric(metric: Metric): PerformanceMetric {
  return {
    name: metric.name,
    value: metric.value,
    delta: metric.delta,
    id: metric.id,
    navigationType: metric.navigationType,
    rating: metric.rating,
  };
}

/**
 * Report Core Web Vital
 */
function reportWebVital(metric: Metric) {
  // Log to console in development
  if (import.meta.env.DEV) {
    console.log(`[WebVital] ${metric.name}:`, {
      value: Math.round(metric.value),
      rating: metric.rating,
    });
  }

  queueMetric(formatWebVitalMetric(metric));
}

/**
 * Initialize Core Web Vitals monitoring
 */
export function initWebVitals() {
  // Cumulative Layout Shift
  onCLS(reportWebVital);

  // Interaction to Next Paint (replaces FID)
  onINP(reportWebVital);

  // First Contentful Paint
  onFCP(reportWebVital);

  // Largest Contentful Paint
  onLCP(reportWebVital);

  // Time to First Byte
  onTTFB(reportWebVital);

  // Flush remaining metrics on page unload
  window.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') {
      flushMetrics();
    }
  });

  // Also flush on beforeunload for older browsers
  window.addEventListener('beforeunload', flushMetrics);
}

/**
 * Track API call performance
 */
export async function trackAPICall<T>(
  endpoint: string,
  fetchFn: () => Promise<Response>
): Promise<T> {
  const startTime = performance.now();
  let status = 0;
  let success = false;

  try {
    const response = await fetchFn();
    status = response.status;
    success = response.ok;

    const duration = performance.now() - startTime;

    // Log to console in development
    if (import.meta.env.DEV) {
      console.log(
        `[API] ${endpoint}:`,
        `${Math.round(duration)}ms`,
        success ? '✓' : '✗'
      );
    }

    // Queue metric
    queueMetric({
      endpoint,
      method: 'POST', // Most API calls are POST
      duration,
      status,
      timestamp: Date.now(),
      success,
    });

    if (!response.ok) {
      throw new Error(`HTTP ${status}`);
    }

    return response.json() as Promise<T>;
  } catch (error) {
    const duration = performance.now() - startTime;

    queueMetric({
      endpoint,
      method: 'POST',
      duration,
      status: status || 0,
      timestamp: Date.now(),
      success: false,
    });

    throw error;
  }
}

/**
 * Measure custom performance mark
 */
export function measurePerformance(name: string, fn: () => void) {
  const startMark = `${name}-start`;
  const endMark = `${name}-end`;

  performance.mark(startMark);
  fn();
  performance.mark(endMark);

  performance.measure(name, startMark, endMark);

  const measure = performance.getEntriesByName(name, 'measure')[0];

  if (import.meta.env.DEV) {
    console.log(`[Perf] ${name}:`, `${Math.round(measure.duration)}ms`);
  }

  // Cleanup
  performance.clearMarks(startMark);
  performance.clearMarks(endMark);
  performance.clearMeasures(name);

  return measure.duration;
}

/**
 * Get navigation timing metrics
 */
export function getNavigationTiming() {
  const timing = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;

  if (!timing) return null;

  return {
    dns: timing.domainLookupEnd - timing.domainLookupStart,
    tcp: timing.connectEnd - timing.connectStart,
    ssl: timing.secureConnectionStart > 0
      ? timing.connectEnd - timing.secureConnectionStart
      : 0,
    ttfb: timing.responseStart - timing.requestStart,
    download: timing.responseEnd - timing.responseStart,
    domInteractive: timing.domInteractive - timing.fetchStart,
    domComplete: timing.domComplete - timing.fetchStart,
    loadComplete: timing.loadEventEnd - timing.fetchStart,
  };
}

/**
 * Log performance summary
 */
export function logPerformanceSummary() {
  const timing = getNavigationTiming();

  if (timing && import.meta.env.DEV) {
    console.group('[Performance Summary]');
    console.table({
      'DNS Lookup': `${Math.round(timing.dns)}ms`,
      'TCP Connection': `${Math.round(timing.tcp)}ms`,
      'SSL Handshake': `${Math.round(timing.ssl)}ms`,
      'Time to First Byte': `${Math.round(timing.ttfb)}ms`,
      'Content Download': `${Math.round(timing.download)}ms`,
      'DOM Interactive': `${Math.round(timing.domInteractive)}ms`,
      'DOM Complete': `${Math.round(timing.domComplete)}ms`,
      'Page Load': `${Math.round(timing.loadComplete)}ms`,
    });
    console.groupEnd();
  }
}

export default {
  initWebVitals,
  trackAPICall,
  measurePerformance,
  getNavigationTiming,
  logPerformanceSummary,
};
