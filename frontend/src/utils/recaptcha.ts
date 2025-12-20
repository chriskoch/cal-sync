/**
 * Google reCAPTCHA Enterprise utility functions
 */

declare global {
  interface Window {
    grecaptcha: {
      enterprise: {
        ready: (callback: () => void) => void;
        execute: (siteKey: string, options: { action: string }) => Promise<string>;
      };
    };
  }
}

const RECAPTCHA_SITE_KEY = import.meta.env.VITE_RECAPTCHA_SITE_KEY || '';

let scriptLoaded = false;
let scriptLoading = false;
let loadPromise: Promise<void> | null = null;

/**
 * Load the reCAPTCHA Enterprise script
 */
export function loadRecaptchaScript(): Promise<void> {
  if (scriptLoaded) {
    return Promise.resolve();
  }

  if (scriptLoading && loadPromise) {
    return loadPromise;
  }

  scriptLoading = true;

  loadPromise = new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = `https://www.google.com/recaptcha/enterprise.js?render=${RECAPTCHA_SITE_KEY}`;
    script.async = true;
    script.defer = true;

    script.onload = () => {
      scriptLoaded = true;
      scriptLoading = false;
      resolve();
    };

    script.onerror = () => {
      scriptLoading = false;
      loadPromise = null;
      reject(new Error('Failed to load reCAPTCHA script'));
    };

    document.head.appendChild(script);
  });

  return loadPromise;
}

/**
 * Execute reCAPTCHA and get a token
 */
export async function executeRecaptcha(action: string): Promise<string> {
  // Ensure script is loaded
  await loadRecaptchaScript();

  // Wait for reCAPTCHA to be ready and execute
  return new Promise((resolve, reject) => {
    if (!window.grecaptcha?.enterprise) {
      reject(new Error('reCAPTCHA not loaded'));
      return;
    }

    window.grecaptcha.enterprise.ready(async () => {
      try {
        const token = await window.grecaptcha.enterprise.execute(
          RECAPTCHA_SITE_KEY,
          { action }
        );
        resolve(token);
      } catch (error) {
        reject(error);
      }
    });
  });
}
