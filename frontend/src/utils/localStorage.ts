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
  },

  // Section timing localStorage functions
  // Uses timer values (timeRemaining in seconds) instead of Date.now()
  startSectionTiming: function(sectionName: 'mcq' | 'coding' | 'systemDesign', timeRemainingSeconds: number): void {
    const key = `section_timing_${sectionName}`;
    const timing = {
      startTimeRemaining: timeRemainingSeconds, // Timer value when section was entered
      endTimeRemaining: null as number | null, // Timer value when section was submitted
      durationMinutes: null as number | null
    };
    this.set(key, JSON.stringify(timing));
  },

  endSectionTiming: function(sectionName: 'mcq' | 'coding' | 'systemDesign', timeRemainingSeconds: number): number | null {
    const key = `section_timing_${sectionName}`;
    const stored = this.get(key);
    if (!stored) return null;
    
    try {
      const timing = JSON.parse(stored);
      if (timing.startTimeRemaining === null || timing.startTimeRemaining === undefined) return null;
      
      // Calculate duration: time spent = startTimeRemaining - endTimeRemaining (both in seconds)
      const durationSeconds = timing.startTimeRemaining - timeRemainingSeconds;
      const durationMinutes = Math.round((durationSeconds / 60) * 100) / 100; // Round to 2 decimal places
      
      timing.endTimeRemaining = timeRemainingSeconds;
      timing.durationMinutes = durationMinutes;
      this.set(key, JSON.stringify(timing));
      
      return durationMinutes;
    } catch (error) {
      console.error(`Error ending section timing for ${sectionName}:`, error);
      return null;
    }
  },

  getSectionTiming: function(sectionName: 'mcq' | 'coding' | 'systemDesign'): { startTimeRemaining: number; endTimeRemaining: number | null; durationMinutes: number | null } | null {
    const key = `section_timing_${sectionName}`;
    const stored = this.get(key);
    if (!stored) return null;
    
    try {
      return JSON.parse(stored);
    } catch (error) {
      console.error(`Error getting section timing for ${sectionName}:`, error);
      return null;
    }
  },

  getAllSectionTimings: function(): { mcq: number | null; coding: number | null; systemDesign: number | null } {
    const mcqTiming = this.getSectionTiming('mcq');
    const codingTiming = this.getSectionTiming('coding');
    const systemDesignTiming = this.getSectionTiming('systemDesign');
    
    return {
      mcq: mcqTiming?.durationMinutes ?? null,
      coding: codingTiming?.durationMinutes ?? null,
      systemDesign: systemDesignTiming?.durationMinutes ?? null
    };
  },

  // Calculate current time spent in a section based on timer
  calculateCurrentSectionTime: function(sectionName: 'mcq' | 'coding' | 'systemDesign', currentTimeRemainingSeconds: number): number | null {
    const timing = this.getSectionTiming(sectionName);
    if (!timing || timing.startTimeRemaining === null || timing.startTimeRemaining === undefined) return null;
    
    // If already ended, return the stored duration
    if (timing.durationMinutes !== null) {
      return timing.durationMinutes;
    }
    
    // Calculate current duration: time spent = startTimeRemaining - currentTimeRemaining
    const durationSeconds = timing.startTimeRemaining - currentTimeRemainingSeconds;
    const durationMinutes = Math.round((durationSeconds / 60) * 100) / 100; // Round to 2 decimal places
    
    return durationMinutes;
  }
};

