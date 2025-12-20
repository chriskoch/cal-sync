/**
 * Utility functions for parsing and formatting API error messages
 */

interface ValidationError {
  loc: (string | number)[];
  msg: string;
  type: string;
}

interface ApiError {
  response?: {
    status?: number;
    data?: {
      detail?: string | ValidationError[];
    };
  };
  message?: string;
}

/**
 * Parse API error and return user-friendly message
 */
export function getErrorMessage(error: ApiError, fallbackMessage: string): string {
  // Network error
  if (!error.response) {
    return 'Network error. Please check your connection and try again.';
  }

  const { data } = error.response;
  const detail = data?.detail;

  // No detail provided
  if (!detail) {
    return fallbackMessage;
  }

  // Validation errors (array of error objects)
  if (Array.isArray(detail)) {
    // Get the first validation error and make it user-friendly
    const firstError = detail[0];
    if (firstError?.msg) {
      // Extract field name from location array
      const field = firstError.loc[firstError.loc.length - 1];
      const fieldName = typeof field === 'string' ? formatFieldName(field) : 'Field';

      return `${fieldName}: ${firstError.msg}`;
    }
    return 'Validation error. Please check your input.';
  }

  // Simple string error message
  if (typeof detail === 'string') {
    return detail;
  }

  return fallbackMessage;
}

/**
 * Format field name to be more readable
 */
function formatFieldName(field: string): string {
  // Convert snake_case to Title Case
  return field
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

/**
 * Get user-friendly error message for login failures
 */
export function getLoginErrorMessage(error: ApiError): string {
  const status = error.response?.status;

  // Specific status code handling
  if (status === 401) {
    return 'Invalid email or password. Please try again.';
  }

  if (status === 422) {
    return getErrorMessage(error, 'Please enter a valid email and password.');
  }

  if (status === 500) {
    return 'Server error. Please try again later.';
  }

  return getErrorMessage(error, 'Login failed. Please try again.');
}

/**
 * Get user-friendly error message for registration failures
 */
export function getRegistrationErrorMessage(error: ApiError): string {
  const status = error.response?.status;

  // Specific status code handling
  if (status === 400) {
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string' && detail.toLowerCase().includes('already registered')) {
      return 'This email is already registered. Please sign in instead.';
    }
    return getErrorMessage(error, 'Registration failed. Please check your information.');
  }

  if (status === 422) {
    return getErrorMessage(error, 'Please check your input and try again.');
  }

  if (status === 500) {
    return 'Server error. Please try again later.';
  }

  return getErrorMessage(error, 'Registration failed. Please try again.');
}
