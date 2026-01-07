// Custom logger that respects environment variables
const isDevelopment = import.meta.env.MODE === 'development';
const enableLogs = import.meta.env.VITE_ENABLE_CONSOLE_LOGS === 'true';

// Enable logs in development by default, or if explicitly enabled
const shouldLog = isDevelopment || enableLogs;

export const logger = {
  log: (...args: any[]) => {
    if (shouldLog) {
      console.log(...args);
    }
  },
  
  error: (...args: any[]) => {
    // Always log errors, even in production
    console.error(...args);
  },
  
  warn: (...args: any[]) => {
    if (shouldLog) {
      console.warn(...args);
    }
  },
  
  info: (...args: any[]) => {
    if (shouldLog) {
      console.info(...args);
    }
  },
  
  debug: (...args: any[]) => {
    if (shouldLog) {
      console.debug(...args);
    }
  },
  
  table: (...args: any[]) => {
    if (shouldLog) {
      console.table(...args);
    }
  }
};

// For backwards compatibility, export a default function
export default logger.log;

