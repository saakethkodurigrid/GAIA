import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Header from '../components/Header';
import Footer from '../components/Footer';
import { addJob, listJobs, listTodayInterviews } from '../api/recruiter.api';
import type { InterviewResponse } from '../api/recruiter.api';

interface JobDescription {
  id: string;
  jobTitle: string;
  status: 'Active' | 'Closed';
  grade: string;
  jobDescription: string;
}

interface ScheduledInterview {
  jobTitle: string;
  status: 'Scheduled' | 'Completed' | 'In Progress';
  candidateName: string;
  time: string;
}

const Recruiter = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    jobRole: '',
    grade: '',
    jobDescription: '',
  });
  const [jobDescriptions, setJobDescriptions] = useState<JobDescription[]>([]);
  const [isLoadingJobs, setIsLoadingJobs] = useState(true);
  const [jobsError, setJobsError] = useState<string | null>(null);
  const [scheduledInterviews, setScheduledInterviews] = useState<ScheduledInterview[]>([]);
  const [isLoadingInterviews, setIsLoadingInterviews] = useState(true);
  const [interviewsError, setInterviewsError] = useState<string | null>(null);

  const handleLogout = () => {
    logout();
  };

  // Fetch jobs from backend
  useEffect(() => {
    const fetchJobs = async () => {
      setIsLoadingJobs(true);
      setJobsError(null);
      try {
        const response = await listJobs();
        if (response.success && response.jobs) {
          // Map backend jobs to frontend format
          const mappedJobs: JobDescription[] = response.jobs.map((job) => ({
            id: job.job_id,
            jobTitle: job.job_role,
            status: 'Active' as const, // Default status since backend doesn't provide status
            grade: job.grade,
            jobDescription: job.job_description || '',
          }));
          setJobDescriptions(mappedJobs);
          console.log(mappedJobs);
        } else {
          setJobsError('Failed to load jobs');
        }
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to load jobs. Please try again.';
        setJobsError(errorMessage);
        console.error('Error fetching jobs:', err);
      } finally {
        setIsLoadingJobs(false);
      }
    };

    fetchJobs();
  }, []);

  // Map API interview response to component format
  const mapInterviewToScheduled = (interview: InterviewResponse): ScheduledInterview => {
    // Map status from backend to frontend format
    let mappedStatus: 'Scheduled' | 'Completed' | 'In Progress' = 'Scheduled';
    if (interview.status === 'completed' || interview.status === 'selected' || interview.status === 'not selected') {
      mappedStatus = 'Completed';
    } else if (interview.status === 'in progress') {
      mappedStatus = 'In Progress';
    } else {
      mappedStatus = 'Scheduled';
    }

    // Parse scheduled_date and format time
    // Extract time directly from the ISO string to preserve IST timezone
    let timeString = 'TBD';
    if (interview.scheduled_date) {
      try {
        console.log('--- Parsing scheduled_date in mapInterviewToScheduled ---');
        console.log('Input scheduled_date string:', interview.scheduled_date);
        
        // Parse the ISO string - it should be in format like "2024-01-15T12:30:00+05:30"
        // Extract the time part directly from the string to avoid timezone conversion
        const dateMatch = interview.scheduled_date.match(/T(\d{2}):(\d{2}):(\d{2})/);
        if (dateMatch) {
          const hours = parseInt(dateMatch[1], 10);
          const minutes = parseInt(dateMatch[2], 10);
          console.log('Extracted hours from string:', hours);
          console.log('Extracted minutes from string:', minutes);
          const ampm = hours >= 12 ? 'PM' : 'AM';
          const displayHours = hours % 12 || 12;
          const displayMinutes = minutes.toString().padStart(2, '0');
          timeString = `${displayHours}:${displayMinutes} ${ampm}`;
          console.log('Formatted time string (from regex):', timeString);
        } else {
          console.log('Regex match failed, using Date parsing fallback');
          // Fallback to Date parsing if format is different
          const date = new Date(interview.scheduled_date);
          console.log('Date object from parsing:', date);
          const hours = date.getHours();
          const minutes = date.getMinutes();
          console.log('Date.getHours() (local):', hours);
          console.log('Date.getMinutes() (local):', minutes);
          const ampm = hours >= 12 ? 'PM' : 'AM';
          const displayHours = hours % 12 || 12;
          const displayMinutes = minutes.toString().padStart(2, '0');
          timeString = `${displayHours}:${displayMinutes} ${ampm}`;
          console.log('Formatted time string (from Date):', timeString);
        }
      } catch (e) {
        console.error('Error parsing date:', e);
      }
    }

    const mappedInterview = {
      jobTitle: interview.job_role,
      status: mappedStatus,
      candidateName: interview.candidate_name || 'N/A',
      time: timeString,
    };
    
    console.log('Final mapped interview object:', mappedInterview);
    console.log('--- End of mapInterviewToScheduled ---');
    
    return mappedInterview;
  };

  // Fetch interviews from backend
  useEffect(() => {
    const fetchInterviews = async () => {
      setIsLoadingInterviews(true);
      setInterviewsError(null);
      try {
        console.log('=== Fetching Today\'s Interviews ===');
        const response = await listTodayInterviews();
        console.log('Full API Response:', JSON.stringify(response, null, 2));
        console.log('Response success:', response.success);
        console.log('Response count:', response.count);
        console.log('Response message:', response.message);
        
        if (response.success && response.interviews) {
          console.log('Number of interviews:', response.interviews.length);
          console.log('Raw interviews array:', response.interviews);
          
          // Log each interview's scheduled_date in detail
          response.interviews.forEach((interview, index) => {
            console.log(`--- Interview ${index + 1} ---`);
            console.log('Candidate:', interview.candidate_name);
            console.log('Job Role:', interview.job_role);
            console.log('Status:', interview.status);
            console.log('Raw scheduled_date from backend:', interview.scheduled_date);
            console.log('scheduled_date type:', typeof interview.scheduled_date);
            
            if (interview.scheduled_date) {
              // Try parsing it to see what JavaScript sees
              const parsedDate = new Date(interview.scheduled_date);
              console.log('Parsed as Date object:', parsedDate);
              console.log('Date ISO string:', parsedDate.toISOString());
              console.log('Date Local string:', parsedDate.toString());
              console.log('Date Local time:', parsedDate.toLocaleString());
              console.log('Date getHours() (local):', parsedDate.getHours());
              console.log('Date getMinutes() (local):', parsedDate.getMinutes());
              console.log('Date UTC hours:', parsedDate.getUTCHours());
              console.log('Date UTC minutes:', parsedDate.getUTCMinutes());
            }
          });
          
          const mappedInterviews: ScheduledInterview[] = response.interviews.map(mapInterviewToScheduled);
          console.log('Final mapped interviews:', mappedInterviews);
          console.log('===================================');
          setScheduledInterviews(mappedInterviews);
        } else {
          setInterviewsError(response.message || 'Failed to load interviews');
        }
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to load interviews. Please try again.';
        setInterviewsError(errorMessage);
        console.error('Error fetching interviews:', err);
      } finally {
        setIsLoadingInterviews(false);
      }
    };

    fetchInterviews();
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'Active':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'Closed':
        return 'bg-gray-100 text-gray-800 border-gray-200';
      case 'Scheduled':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'Completed':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'In Progress':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getUserName = () => {
    return user?.name?.split(' ')[0] || 'John';
  };

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good Morning';
    if (hour < 17) return 'Good Afternoon';
    return 'Good Evening';
  };

  const handleOpenModal = () => {
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    // Prevent closing modal while saving
    if (isLoading) {
      return;
    }
    setIsModalOpen(false);
    setError(null);
    setSuccessMessage(null);
    setFormData({
      jobRole: '',
      grade: '',
      jobDescription: '',
    });
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value,
    }));
    // Clear error when user starts typing
    if (error) {
      setError(null);
    }
  };

  const handleSave = async () => {
    // Prevent multiple simultaneous saves
    if (isLoading) {
      return;
    }

    // Validate form data
    if (!formData.jobRole.trim()) {
      setError('Job Role is required');
      return;
    }
    if (!formData.grade.trim()) {
      setError('Grade is required');
      return;
    }
    if (!formData.jobDescription.trim()) {
      setError('Job Description is required');
      return;
    }

    setIsLoading(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const response = await addJob({
        job_role: formData.jobRole.trim(),
        grade: formData.grade.trim(),
        job_description: formData.jobDescription.trim(),
      });

      if (response.success) {
        setSuccessMessage('Job created successfully!');
        // Refresh the job list
        const jobsResponse = await listJobs();
        if (jobsResponse.success && jobsResponse.jobs) {
          const mappedJobs: JobDescription[] = jobsResponse.jobs.map((job) => ({
            id: job.job_id,
            jobTitle: job.job_role,
            status: 'Active' as const,
            grade: job.grade,
            jobDescription: job.job_description || '',
          }));
          setJobDescriptions(mappedJobs);
          console.log(mappedJobs);
        }
        // Close modal immediately after successful creation
        setTimeout(() => {
          setIsLoading(false);
          handleCloseModal();
        }, 500);
      } else {
        setError(response.message || 'Failed to create job');
        setIsLoading(false);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to create job. Please try again.';
      setError(errorMessage);
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-br from-[#FFF7E5] to-[#F5FCFF]">
      {/* Header */}
      <Header 
        showUserInfo={true} 
        showLogout={true} 
        showTechInterviewLogo={true} 
        user={user} 
        onLogout={handleLogout} 
      />

      {/* Main Content */}
      <div className="flex-1 p-8">
        <div className="max-w-[95%] mx-auto">
          {/* Greeting */}
          <h1 className="text-4xl font-bold text-gray-900 mb-8">
            {getGreeting()}, {getUserName()}!
          </h1>

          {/* Two Panels Side by Side */}
          <div className="grid grid-cols-1 lg:grid-cols-[2fr_1fr] gap-4">
            {/* Left Panel: Uploaded Job Descriptions */}
            <div className="bg-white rounded-xl shadow-lg border-2 border-gray-200 p-6 flex flex-col max-h-[700px]">
              {/* Panel Header */}
              <div className="flex items-center justify-between mb-6 flex-shrink-0">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                    <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </div>
                  <h2 className="text-xl font-bold text-gray-900">Uploaded Job Descriptions</h2>
                </div>
                <button 
                  onClick={handleOpenModal}
                  className="bg-yellow-400 text-gray-900 px-4 py-2 rounded-lg font-semibold text-sm hover:bg-yellow-500 transition-colors flex items-center gap-2"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                  Upload JD
                </button>
              </div>

              {/* Table */}
              <div className="overflow-x-auto overflow-y-auto flex-1">
                {isLoadingJobs ? (
                  <div className="flex items-center justify-center h-64">
                    <div className="flex flex-col items-center gap-3">
                      <svg className="animate-spin h-8 w-8 text-purple-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      <p className="text-gray-600">Loading jobs...</p>
                    </div>
                  </div>
                ) : jobsError ? (
                  <div className="flex items-center justify-center h-64">
                    <div className="text-center">
                      <p className="text-red-600 mb-2">{jobsError}</p>
                      <button
                        onClick={async () => {
                          setJobsError(null);
                          setIsLoadingJobs(true);
                          try {
                            const response = await listJobs();
                            if (response.success && response.jobs) {
                              const mappedJobs: JobDescription[] = response.jobs.map((job) => ({
                                id: job.job_id,
                                jobTitle: job.job_role,
                                status: 'Active' as const,
                                grade: job.grade,
                                jobDescription: job.job_description || '',
                              }));
                              setJobDescriptions(mappedJobs);
                            } else {
                              setJobsError('Failed to load jobs');
                            }
                          } catch (err) {
                            const errorMessage = err instanceof Error ? err.message : 'Failed to load jobs. Please try again.';
                            setJobsError(errorMessage);
                          } finally {
                            setIsLoadingJobs(false);
                          }
                        }}
                        className="text-blue-600 hover:text-blue-800 underline"
                      >
                        Try again
                      </button>
                    </div>
                  </div>
                ) : jobDescriptions.length === 0 ? (
                  <div className="flex items-center justify-center h-64">
                    <p className="text-gray-600">No jobs found. Create your first job!</p>
                  </div>
                ) : (
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-gray-200">
                        <th className="text-left py-3 px-4 text-base font-bold text-gray-700">ID</th>
                        <th className="text-left py-3 px-4 text-base font-bold text-gray-700">Job Title</th>
                        <th className="text-left py-3 px-4 text-base font-bold text-gray-700">Status</th>
                        <th className="text-left py-3 px-4 text-base font-bold text-gray-700">Grade</th>
                        <th className="text-left py-3 px-4 text-base font-bold text-gray-700">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {jobDescriptions.map((jd) => (
                        <tr key={jd.id} className="border-b border-gray-100 hover:bg-gray-50">
                          <td className="py-3 px-4 text-base text-gray-900">{jd.id}</td>
                          <td className="py-3 px-4 text-base text-gray-900">{jd.jobTitle}</td>
                          <td className="py-3 px-4">
                            <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium border ${getStatusColor(jd.status)}`}>
                              {jd.status}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-base text-gray-900">{jd.grade}</td>
                          <td className="py-3 px-4">
                            <button 
                              onClick={() => navigate('/recruiter/job-details', { 
                                state: { jobId: jd.id, jobTitle: jd.jobTitle, jobDescription: jd.jobDescription } 
                              })}
                              className="text-blue-600 hover:text-blue-800 text-base font-medium"
                            >
                              View
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>

            {/* Right Panel: Scheduled Interviews */}
            <div className="bg-white rounded-xl shadow-lg border-2 border-gray-200 p-6 flex flex-col max-h-[700px]">
              {/* Panel Header */}
              <div className="flex items-center gap-3 mb-6 flex-shrink-0">
                <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                  <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                </div>
                <h2 className="text-xl font-bold text-gray-900">Scheduled Interviews for today</h2>
              </div>

              {/* Interviews List */}
              <div className="space-y-4 overflow-y-auto flex-1">
                {isLoadingInterviews ? (
                  <div className="flex items-center justify-center h-64">
                    <div className="flex flex-col items-center gap-3">
                      <svg className="animate-spin h-8 w-8 text-purple-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      <p className="text-gray-600">Loading interviews...</p>
                    </div>
                  </div>
                ) : interviewsError ? (
                  <div className="flex items-center justify-center h-64">
                    <div className="text-center">
                      <p className="text-red-600 mb-2">{interviewsError}</p>
                      <button
                        onClick={async () => {
                          setInterviewsError(null);
                          setIsLoadingInterviews(true);
                          try {
                            const response = await listTodayInterviews();
                            console.log('API Response from /admin/list-interviews/today (retry):', response);
                            if (response.success && response.interviews) {
                              const mappedInterviews: ScheduledInterview[] = response.interviews.map(mapInterviewToScheduled);
                              setScheduledInterviews(mappedInterviews);
                            } else {
                              setInterviewsError(response.message || 'Failed to load interviews');
                            }
                          } catch (err) {
                            const errorMessage = err instanceof Error ? err.message : 'Failed to load interviews. Please try again.';
                            setInterviewsError(errorMessage);
                          } finally {
                            setIsLoadingInterviews(false);
                          }
                        }}
                        className="text-blue-600 hover:text-blue-800 underline"
                      >
                        Try again
                      </button>
                    </div>
                  </div>
                ) : scheduledInterviews.length === 0 ? (
                  <div className="flex items-center justify-center h-64">
                    <p className="text-gray-600">No interviews scheduled for today.</p>
                  </div>
                ) : (
                  scheduledInterviews.map((interview, index) => (
                    <div key={index} className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <h3 className="text-lg font-semibold text-blue-600 mb-3">{interview.jobTitle}</h3>
                          <div className="text-base text-gray-600">
                            <span>{interview.candidateName || 'N/A'}</span>
                          </div>
                        </div>
                        <div className="flex flex-col items-end">
                          <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium border ${getStatusColor(interview.status)} mb-3`}>
                            {interview.status}
                          </span>
                          {interview.status !== 'Completed' && (
                            <div className="flex items-center gap-1 text-sm text-gray-600">
                              <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                              </svg>
                              <span>{interview.time}</span>
                            </div>
                          )}
                          {interview.status === 'Completed' && (
                            <button className="text-blue-600 hover:text-blue-800 mt-1">
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                              </svg>
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <Footer />

      {/* Modal */}
      {isModalOpen && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
          onClick={isLoading ? undefined : handleCloseModal}
        >
          <div 
            className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-xl font-semibold text-gray-900">Create Job</h2>
            </div>

            {/* Modal Body */}
            <div className="px-6 py-6 space-y-5">
              {/* Error Message */}
              {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                  {error}
                </div>
              )}

              {/* Success Message */}
              {successMessage && (
                <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg text-sm">
                  {successMessage}
                </div>
              )}

              {/* Job Role */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Job Role<span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  name="jobRole"
                  value={formData.jobRole}
                  onChange={handleInputChange}
                  disabled={isLoading}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-yellow-400 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-gray-100"
                  placeholder="Enter job role"
                />
              </div>

              {/* Grade */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Grade<span className="text-red-500">*</span>
                </label>
                <select
                  name="grade"
                  value={formData.grade}
                  onChange={handleInputChange}
                  disabled={isLoading}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-yellow-400 focus:border-transparent appearance-none bg-white bg-[url('data:image/svg+xml;charset=UTF-8,%3csvg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 24 24%27 fill=%27none%27 stroke=%27currentColor%27 stroke-width=%272%27 stroke-linecap=%27round%27 stroke-linejoin=%27round%27%3e%3cpolyline points=%276 9 12 15 18 9%27%3e%3c/polyline%3e%3c/svg%3e')] bg-[length:20px] bg-[right_0.5rem_center] bg-no-repeat pr-10 disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-gray-100"
                >
                  <option value="">Select grade</option>
                  <option value="T1">T1</option>
                  <option value="T2">T2</option>
                  <option value="T3">T3</option>
                  <option value="T4">T4</option>
                </select>
              </div>

              {/* Job Description */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Job Description<span className="text-red-500">*</span>
                </label>
                <textarea
                  name="jobDescription"
                  value={formData.jobDescription}
                  onChange={handleInputChange}
                  rows={6}
                  disabled={isLoading}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-yellow-400 focus:border-transparent resize-none disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-gray-100"
                  placeholder="Enter job description"
                />
              </div>
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-4 border-t border-gray-200 flex justify-end gap-3">
              <button
                onClick={handleCloseModal}
                disabled={isLoading}
                className="px-4 py-2 bg-[#F5E6D3] text-gray-700 rounded-lg font-medium hover:bg-[#E8D4B8] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={isLoading}
                className="px-4 py-2 bg-yellow-400 text-gray-900 rounded-lg font-medium hover:bg-yellow-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {isLoading ? (
                  <>
                    <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Creating JD...
                  </>
                ) : (
                  'Save'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Recruiter;
