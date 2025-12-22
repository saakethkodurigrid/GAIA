import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Header from '../components/Header';
import Footer from '../components/Footer';
import AddRecruiterAdminModal from '../components/AddRecruiterAdminModal';
import { listJobs, listTodayInterviews } from '../api/admin.api';
import type { InterviewResponse } from '../api/admin.api';
import { isTokenExpiredError } from '../utils/apiErrorHandler';

interface JobDescription {
  id: string;
  jobTitle: string;
  status: 'Active' | 'Closed';
  grade: string;
  jobDescription: string;
  recruiterName: string;
}

interface ScheduledInterview {
  jobTitle: string;
  status: 'Scheduled' | 'Completed' | 'In Progress';
  candidateName: string;
  time: string;
}

const Admin = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [jobDescriptions, setJobDescriptions] = useState<JobDescription[]>([]);
  const [isLoadingJobs, setIsLoadingJobs] = useState(true);
  const [jobsError, setJobsError] = useState<string | null>(null);
  const [scheduledInterviews, setScheduledInterviews] = useState<ScheduledInterview[]>([]);
  const [isLoadingInterviews, setIsLoadingInterviews] = useState(true);
  const [interviewsError, setInterviewsError] = useState<string | null>(null);
  const [isAddRecruiterModalOpen, setIsAddRecruiterModalOpen] = useState(false);

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
          const mappedJobs: JobDescription[] = response.jobs.map((job) => ({
            id: job.job_id,
            jobTitle: job.job_role,
            status: 'Active' as const,
            grade: job.grade,
            jobDescription: job.job_description || '',
            recruiterName: job.recruiter_name || 'Unknown',
          }));
          setJobDescriptions(mappedJobs);
        } else {
          setJobsError('Failed to load jobs');
        }
      } catch (err) {
        // Check if it's a token expiration error - logout immediately without setting error state
        if (isTokenExpiredError(err)) {
          console.log('Token expired, logging out...');
          logout();
          return;
        }
        
        const errorMessage = err instanceof Error ? err.message : 'Failed to load jobs. Please try again.';
        setJobsError(errorMessage);
        console.error('Error fetching jobs:', err);
      } finally {
        setIsLoadingJobs(false);
      }
    };

    fetchJobs();
  }, [logout]);

  // Map API interview response to component format
  const mapInterviewToScheduled = (interview: InterviewResponse): ScheduledInterview => {
    let mappedStatus: 'Scheduled' | 'Completed' | 'In Progress' = 'Scheduled';
    if (interview.status === 'completed' || interview.status === 'selected' || interview.status === 'not selected') {
      mappedStatus = 'Completed';
    } else if (interview.status === 'in progress') {
      mappedStatus = 'In Progress';
    } else {
      mappedStatus = 'Scheduled';
    }

    let timeString = 'TBD';
    if (interview.scheduled_date) {
      try {
        const dateMatch = interview.scheduled_date.match(/T(\d{2}):(\d{2}):(\d{2})/);
        if (dateMatch) {
          const hours = parseInt(dateMatch[1], 10);
          const minutes = parseInt(dateMatch[2], 10);
          const ampm = hours >= 12 ? 'PM' : 'AM';
          const displayHours = hours % 12 || 12;
          const displayMinutes = minutes.toString().padStart(2, '0');
          timeString = `${displayHours}:${displayMinutes} ${ampm}`;
        } else {
          const date = new Date(interview.scheduled_date);
          const hours = date.getHours();
          const minutes = date.getMinutes();
          const ampm = hours >= 12 ? 'PM' : 'AM';
          const displayHours = hours % 12 || 12;
          const displayMinutes = minutes.toString().padStart(2, '0');
          timeString = `${displayHours}:${displayMinutes} ${ampm}`;
        }
      } catch (e) {
        console.error('Error parsing date:', e);
      }
    }

    return {
      jobTitle: interview.job_role,
      status: mappedStatus,
      candidateName: interview.candidate_name || 'N/A',
      time: timeString,
    };
  };

  // Fetch interviews from backend
  useEffect(() => {
    const fetchInterviews = async () => {
      setIsLoadingInterviews(true);
      setInterviewsError(null);
      try {
        const response = await listTodayInterviews();
        if (response.success && response.interviews) {
          const mappedInterviews: ScheduledInterview[] = response.interviews.map(mapInterviewToScheduled);
          setScheduledInterviews(mappedInterviews);
        } else {
          setInterviewsError(response.message || 'Failed to load interviews');
        }
      } catch (err) {
        // Check if it's a token expiration error - logout immediately without setting error state
        if (isTokenExpiredError(err)) {
          console.log('Token expired, logging out...');
          logout();
          return;
        }
        
        const errorMessage = err instanceof Error ? err.message : 'Failed to load interviews. Please try again.';
        setInterviewsError(errorMessage);
        console.error('Error fetching interviews:', err);
      } finally {
        setIsLoadingInterviews(false);
      }
    };

    fetchInterviews();
  }, [logout]);

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
    return user?.name?.split(' ')[0] || 'Admin';
  };

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good Morning';
    if (hour < 17) return 'Good Afternoon';
    return 'Good Evening';
  };

  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-br from-[#FFF7E5] to-[#F5FCFF]">
      <Header 
        showUserInfo={true} 
        showLogout={true} 
        showTechInterviewLogo={true} 
        user={user} 
        onLogout={handleLogout} 
      />

      <div className="flex-1 p-8">
        <div className="max-w-[95%] mx-auto">
          <div className="flex items-center justify-between mb-8">
            <h1 className="text-4xl font-bold text-gray-900">
              {getGreeting()}, {getUserName()}!
            </h1>
            <button
              onClick={() => setIsAddRecruiterModalOpen(true)}
              className="flex items-center gap-2 px-6 py-3 bg-yellow-400 text-gray-900 rounded-lg text-base font-medium hover:bg-yellow-500 transition-colors shadow-md"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              Add Recruiter/Admin
            </button>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-[2fr_1fr] gap-4">
            {/* Left Panel: Uploaded Job Descriptions */}
            <div className="bg-white rounded-xl shadow-lg border-2 border-gray-200 p-6 flex flex-col max-h-[700px]">
              <div className="flex items-center justify-between mb-6 flex-shrink-0">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                    <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </div>
                  <h2 className="text-xl font-bold text-gray-900">Uploaded Job Descriptions</h2>
                </div>
              </div>

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
                                recruiterName: job.recruiter_name || 'Unknown',
                              }));
                              setJobDescriptions(mappedJobs);
                            } else {
                              setJobsError('Failed to load jobs');
                            }
                          } catch (err) {
                            // Check if it's a token expiration error - logout immediately
                            if (isTokenExpiredError(err)) {
                              logout();
                              return;
                            }
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
                    <p className="text-gray-600">No jobs found.</p>
                  </div>
                ) : (
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-gray-200">
                        <th className="text-left py-3 px-4 text-base font-bold text-gray-700">ID</th>
                        <th className="text-left py-3 px-4 text-base font-bold text-gray-700">Job Title</th>
                        <th className="text-left py-3 px-4 text-base font-bold text-gray-700">Recruiter</th>
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
                          <td className="py-3 px-4 text-base text-gray-900">{jd.recruiterName}</td>
                          <td className="py-3 px-4">
                            <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium border ${getStatusColor(jd.status)}`}>
                              {jd.status}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-base text-gray-900">{jd.grade}</td>
                          <td className="py-3 px-4">
                            <button 
                              onClick={() => navigate('/recruiter/job-details', { 
                                state: { jobId: jd.id, jobTitle: jd.jobTitle, jobDescription: jd.jobDescription, from: 'admin' } 
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
              <div className="flex items-center gap-3 mb-6 flex-shrink-0">
                <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                  <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                </div>
                <h2 className="text-xl font-bold text-gray-900">Scheduled Interviews for today</h2>
              </div>

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
                            if (response.success && response.interviews) {
                              const mappedInterviews: ScheduledInterview[] = response.interviews.map(mapInterviewToScheduled);
                              setScheduledInterviews(mappedInterviews);
                            } else {
                              setInterviewsError(response.message || 'Failed to load interviews');
                            }
                          } catch (err) {
                            // Check if it's a token expiration error - logout immediately
                            if (isTokenExpiredError(err)) {
                              logout();
                              return;
                            }
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
                          <div className="flex items-center gap-1 text-sm text-gray-600">
                            <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            <span>{interview.time}</span>
                          </div>
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

      {/* Add Recruiter/Admin Modal */}
      <AddRecruiterAdminModal
        isOpen={isAddRecruiterModalOpen}
        onClose={() => setIsAddRecruiterModalOpen(false)}
        onSuccess={() => {
          // Optionally refresh data or show success message
          console.log('Recruiter/Admin added successfully');
        }}
      />

      <Footer />
    </div>
  );
};

export default Admin;
