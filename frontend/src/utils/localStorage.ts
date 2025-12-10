export const localStorage = {
  get: (key: string): string | null => {
    if (typeof window === 'undefined') return null;
    try {
      return window.localStorage.getItem(key);
    } catch (error) {
      console.error('Error reading from localStorage:', error);
      return null;
    }
  },

  set: (key: string, value: string): void => {
    if (typeof window === 'undefined') return;
    try {
      window.localStorage.setItem(key, value);
    } catch (error) {
      console.error('Error writing to localStorage:', error);
    }
  },

  remove: (key: string): void => {
    if (typeof window === 'undefined') return;
    try {
      window.localStorage.removeItem(key);
    } catch (error) {
      console.error('Error removing from localStorage:', error);
    }
  },

  hasCompletedTour: (tourType: string): boolean => {
    const key = `tour_completed_${tourType}`;
    return localStorage.get(key) === 'true';
  },

  markTourCompleted: (tourType: string): void => {
    const key = `tour_completed_${tourType}`;
    localStorage.set(key, 'true');
  },

  // Timer localStorage functions
  getTimerEndTime: function(): number | null {
    const stored = this.get('timer_end_time');
    if (stored) {
      const endTime = parseInt(stored, 10);
      if (!isNaN(endTime) && endTime > Date.now()) {
        return endTime;
      }
    }
    return null;
  },

  setTimerEndTime: function(remainingSeconds: number): void {
    const endTime = Date.now() + (remainingSeconds * 1000);
    this.set('timer_end_time', endTime.toString());
  },

  getRemainingTime: function(): number | null {
    const endTime = this.getTimerEndTime();
    if (endTime) {
      const remaining = Math.max(0, Math.floor((endTime - Date.now()) / 1000));
      return remaining;
    }
    return null;
  },

  clearTimer: function(): void {
    this.remove('timer_end_time');
  }
};

