/**
 * Utility function to check if an error is a token expiration error
 * and handle it by logging out the user
 */
export const isTokenExpiredError = (error: unknown): boolean => {
  if (!error) return false;
  
  // Handle string errors
  if (typeof error === 'string') {
    const errorMessage = error.toLowerCase();
    return (
      errorMessage.includes('invalid or expired token') ||
      errorMessage.includes('expired token') ||
      errorMessage.includes('invalid token') ||
      errorMessage.includes('unauthorized') ||
      errorMessage.includes('authentication failed')
    );
  }
  
  // Handle Error objects and objects with message/detail properties
  if (error instanceof Error || (typeof error === 'object' && error !== null)) {
    const errorObj = error as { message?: string; detail?: string; status?: number };
    const errorMessage = (
      errorObj.message?.toLowerCase() || 
      errorObj.detail?.toLowerCase() || 
      ''
    );
    
    // Check status code first (401 or 403)
    if (errorObj.status === 401 || errorObj.status === 403) {
      return true;
    }
    
    // Check error message content
    return (
      errorMessage.includes('invalid or expired token') ||
      errorMessage.includes('expired token') ||
      errorMessage.includes('invalid token') ||
      errorMessage.includes('unauthorized') ||
      errorMessage.includes('authentication failed')
    );
  }
  
  return false;
};

/**
 * Check if a response status indicates token expiration
 */
export const isTokenExpiredStatus = (status: number): boolean => {
  return status === 401 || status === 403;
};

/**
 * Handle API error response and check for token expiration
 * Returns true if token is expired and logout should be triggered
 */
export const handleApiError = async (response: Response): Promise<boolean> => {
  if (isTokenExpiredStatus(response.status)) {
    try {
      const errorData = await response.json().catch(() => ({}));
      const errorDetail = errorData.detail || errorData.message || '';
      
      if (isTokenExpiredError(errorDetail)) {
        return true; // Token expired, should logout
      }
    } catch {
      // If we can't parse the error, but status is 401/403, assume token expired
      return true;
    }
  }
  return false;
};

