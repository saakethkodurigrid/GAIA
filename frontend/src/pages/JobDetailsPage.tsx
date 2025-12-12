import { useState, useRef, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Header from '../components/Header';
import Footer from '../components/Footer';
import { uploadCandidatesBatch, getResumesList, getScheduledInterviews, getCompletedInterviews, type ResumeCandidateResponse, type ScheduledInterviewCandidateResponse, type CompletedInterviewCandidateResponse, type CandidateEntry } from '../api/recruiter.api';
import { isTokenExpiredError } from '../utils/apiErrorHandler';

const JobDetailsPage = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  
  // Get job details from location state or use defaults
  const jobId = location.state?.jobId || 'JD-000000';
  const jobTitle = location.state?.jobTitle || 'Senior Software Engineer';
  const jobDescription = location.state?.jobDescription || '';
  
  const [activeTab, setActiveTab] = useState<'resumes' | 'scheduled' | 'completed'>('resumes');
  const [showJobDescriptionModal, setShowJobDescriptionModal] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [candidates, setCandidates] = useState<Array<Omit<CandidateEntry, 'file'> & { file: File | null }>>([
    { name: '', email: '', file: null }
  ]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const [resumes, setResumes] = useState<ResumeCandidateResponse[]>([]);
  const [isLoadingResumes, setIsLoadingResumes] = useState(false);
  const [resumesError, setResumesError] = useState<string | null>(null);
  const [scheduledInterviews, setScheduledInterviews] = useState<ScheduledInterviewCandidateResponse[]>([]);
  const [isLoadingScheduledInterviews, setIsLoadingScheduledInterviews] = useState(false);
  const [scheduledInterviewsError, setScheduledInterviewsError] = useState<string | null>(null);
  const [completedInterviews, setCompletedInterviews] = useState<CompletedInterviewCandidateResponse[]>([]);
  const [isLoadingCompletedInterviews, setIsLoadingCompletedInterviews] = useState(false);
  const [completedInterviewsError, setCompletedInterviewsError] = useState<string | null>(null);
  const fileInputRefs = useRef<(HTMLInputElement | null)[]>([]);

  const handleLogout = () => {
    logout();
  };

  // Fetch resumes list
  const fetchResumes = async () => {
    // Validate jobId is in the format JD-XXXXXX (e.g., JD-783901)
    const jobIdPattern = /^JD-\d{6}$/;
    if (!jobIdPattern.test(jobId)) {
      // If not a valid job ID format, don't fetch (might be mock data)
      setResumes([]);
      return;
    }

    setIsLoadingResumes(true);
    setResumesError(null);

    try {
      const response = await getResumesList(jobId);
      if (response.success) {
        setResumes(response.candidates);
      } else {
        setResumesError(response.message || 'Failed to fetch resumes');
      }
    } catch (err) {
      // Check if it's a token expiration error - logout immediately
      if (isTokenExpiredError(err)) {
        console.log('Token expired, logging out...');
        logout();
        return;
      }
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch resumes. Please try again.';
      setResumesError(errorMessage);
      setResumes([]);
    } finally {
      setIsLoadingResumes(false);
    }
  };

  // Fetch scheduled interviews list
  const fetchScheduledInterviews = async () => {
    // Validate jobId is in the format JD-XXXXXX (e.g., JD-783901)
    const jobIdPattern = /^JD-\d{6}$/;
    if (!jobIdPattern.test(jobId)) {
      // If not a valid job ID format, don't fetch (might be mock data)
      setScheduledInterviews([]);
      return;
    }

    setIsLoadingScheduledInterviews(true);
    setScheduledInterviewsError(null);

    try {
      const response = await getScheduledInterviews(jobId);
      if (response.success) {
        setScheduledInterviews(response.candidates);
      } else {
        setScheduledInterviewsError(response.message || 'Failed to fetch scheduled interviews');
      }
    } catch (err) {
      // Check if it's a token expiration error - logout immediately
      if (isTokenExpiredError(err)) {
        console.log('Token expired, logging out...');
        logout();
        return;
      }
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch scheduled interviews. Please try again.';
      setScheduledInterviewsError(errorMessage);
      setScheduledInterviews([]);
    } finally {
      setIsLoadingScheduledInterviews(false);
    }
  };

  // Fetch resumes on mount and when jobId changes
  useEffect(() => {
    fetchResumes();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);

  // Fetch completed interviews list
  const fetchCompletedInterviews = async () => {
    // Validate jobId is in the format JD-XXXXXX (e.g., JD-783901)
    const jobIdPattern = /^JD-\d{6}$/;
    if (!jobIdPattern.test(jobId)) {
      // If not a valid job ID format, don't fetch (might be mock data)
      setCompletedInterviews([]);
      return;
    }

    setIsLoadingCompletedInterviews(true);
    setCompletedInterviewsError(null);

    try {
      const response = await getCompletedInterviews(jobId);
      if (response.success) {
        setCompletedInterviews(response.candidates);
      } else {
        setCompletedInterviewsError(response.message || 'Failed to fetch completed interviews');
      }
    } catch (err) {
      // Check if it's a token expiration error - logout immediately
      if (isTokenExpiredError(err)) {
        console.log('Token expired, logging out...');
        logout();
        return;
      }
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch completed interviews. Please try again.';
      setCompletedInterviewsError(errorMessage);
      setCompletedInterviews([]);
    } finally {
      setIsLoadingCompletedInterviews(false);
    }
  };

  // Fetch scheduled interviews when scheduled tab is active
  useEffect(() => {
    if (activeTab === 'scheduled') {
      fetchScheduledInterviews();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, jobId]);

  // Fetch completed interviews when completed tab is active
  useEffect(() => {
    if (activeTab === 'completed') {
      fetchCompletedInterviews();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, jobId]);

  const getStatusColor = (status: string) => {
    const statusLower = status.toLowerCase();
    switch (statusLower) {
      case 'shortlisted':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'rejected':
        return 'bg-red-100 text-red-800 border-red-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const formatStatus = (status: string) => {
    // Capitalize first letter
    return status.charAt(0).toUpperCase() + status.slice(1).toLowerCase();
  };

  const getScoreColor = (status: string) => {
    // If rejected, show red
    if (status.toLowerCase() === 'rejected') {
      return 'text-red-600';
    }
    // For all other statuses (shortlisted, pending, etc.), show green
    return 'text-green-600';
  };

  const getInterviewStatusColor = (status: string) => {
    const statusLower = status.toLowerCase();
    switch (statusLower) {
      case 'shortlisted':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'scheduled':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'in progress':
        return 'bg-purple-100 text-purple-800 border-purple-200';
      case 'completed':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'selected':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'not selected':
        return 'bg-red-100 text-red-800 border-red-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const formatInterviewDate = (dateString: string | null) => {
    if (!dateString) return 'Not scheduled';
    try {
      const date = new Date(dateString);
      return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return 'Invalid date';
    }
  };

  const formatInterviewScore = (score: number | null) => {
    if (score === null) return 'N/A';
    return score.toFixed(1);
  };

  const getCompletedStatusColor = (status: string) => {
    const statusLower = status.toLowerCase();
    switch (statusLower) {
      case 'selected':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'not selected':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'completed':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const handleUploadClick = () => {
    setShowUploadModal(true);
    setCandidates([{ name: '', email: '', file: null }]);
    setUploadError(null);
    fileInputRefs.current = [null];
  };

  const handleAddCandidate = () => {
    if (candidates.length < 10) {
      setCandidates([...candidates, { name: '', email: '', file: null }]);
      fileInputRefs.current.push(null);
    }
  };

  const handleRemoveCandidate = (index: number) => {
    if (candidates.length > 1) {
      setCandidates(candidates.filter((_, i) => i !== index));
      // Clean up file input ref
      fileInputRefs.current = fileInputRefs.current.filter((_, i) => i !== index);
    }
  };

  const handleCandidateNameChange = (index: number, name: string) => {
    const updated = [...candidates];
    updated[index].name = name;
    setCandidates(updated);
  };

  const handleCandidateEmailChange = (index: number, email: string) => {
    const updated = [...candidates];
    updated[index].email = email;
    setCandidates(updated);
  };

  const handleCandidateFileChange = (index: number, e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      // Validate file type
      const allowedExtensions = ['pdf', 'docx', 'doc'];
      const extension = file.name.toLowerCase().split('.').pop() || '';
      
      if (!allowedExtensions.includes(extension)) {
        setUploadError(`Invalid file type for candidate ${index + 1}. Only PDF and DOCX are allowed.`);
        setTimeout(() => setUploadError(null), 5000);
        return;
      }

      const updated = [...candidates];
      updated[index].file = file;
      setCandidates(updated);
      setUploadError(null);
    }
  };

  const handleModalSubmit = async () => {
    // Validate all candidates and filter out invalid ones
    const validCandidates: CandidateEntry[] = [];
    for (const candidate of candidates) {
      if (candidate.name.trim() && candidate.email.trim() && candidate.file !== null) {
        validCandidates.push({
          name: candidate.name.trim(),
          email: candidate.email.trim(),
          file: candidate.file
        });
      }
    }
    
    if (validCandidates.length === 0) {
      setUploadError('Please add at least one candidate with name, email, and resume file.');
      setTimeout(() => setUploadError(null), 5000);
      return;
    }

    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    for (let i = 0; i < validCandidates.length; i++) {
      if (!emailRegex.test(validCandidates[i].email)) {
        setUploadError(`Invalid email format for candidate ${i + 1}.`);
        setTimeout(() => setUploadError(null), 5000);
        return;
      }
    }

    // Validate jobId is in the format JD-XXXXXX (e.g., JD-783901)
    const jobIdPattern = /^JD-\d{6}$/;
    if (!jobIdPattern.test(jobId)) {
      setUploadError('Invalid job ID. Please navigate from the jobs list to upload resumes.');
      setTimeout(() => setUploadError(null), 5000);
      return;
    }

    setIsUploading(true);
    setUploadError(null);
    setUploadSuccess(null);

    try {
      const response = await uploadCandidatesBatch(jobId, validCandidates);
      
      if (response.success) {
        let successMsg = `Successfully uploaded ${response.successful} candidate(s)`;
        
        // Add details about failed files if any
        if (response.failed > 0 && response.failed_files && response.failed_files.length > 0) {
          const failedFileNames = response.failed_files.map(f => f.filename).join(', ');
          successMsg += `. ${response.failed} candidate(s) failed: ${failedFileNames}`;
        }
        
        setUploadSuccess(successMsg);
        setShowUploadModal(false);
        setCandidates([{ name: '', email: '', file: null }]);
        fileInputRefs.current = [];
        
        // Refresh resumes list after successful upload
        await fetchResumes();
        
        // Clear success message after 7 seconds
        setTimeout(() => {
          setUploadSuccess(null);
        }, 7000);
      } else {
        // Handle partial success or complete failure
        let errorMsg = response.message || 'Failed to upload candidates';
        
        if (response.failed_files && response.failed_files.length > 0) {
          const failedDetails = response.failed_files.map(f => `${f.filename}: ${f.error}`).join('; ');
          errorMsg += `. Failed candidates: ${failedDetails}`;
        }
        
        setUploadError(errorMsg);
        setTimeout(() => setUploadError(null), 8000);
      }
    } catch (err) {
      // Check if it's a token expiration error - logout immediately
      if (isTokenExpiredError(err)) {
        console.log('Token expired, logging out...');
        logout();
        return;
      }
      const errorMessage = err instanceof Error ? err.message : 'Failed to upload candidates. Please try again.';
      setUploadError(errorMessage);
      setTimeout(() => setUploadError(null), 5000);
    } finally {
      setIsUploading(false);
    }
  };

  const handleModalClose = () => {
    if (!isUploading) {
      setShowUploadModal(false);
      setCandidates([{ name: '', email: '', file: null }]);
      setUploadError(null);
      fileInputRefs.current = [];
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
          {/* Back Button and Job Title - Outside Card */}
          <div className="mb-6">
            <button
              onClick={() => navigate('/recruiter')}
              className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4 transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              <span className="text-base font-medium">Job Title</span>
            </button>
            <div className="flex items-center gap-4">
              <h1 className="text-2xl font-bold text-gray-900">
                {jobId} {jobTitle}
              </h1>
              <button
                onClick={() => setShowJobDescriptionModal(true)}
                className="flex items-center gap-2 text-blue-600 hover:text-blue-800 text-base font-medium"
              >
                View job description
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </button>
            </div>
          </div>

          {/* Tabs - Outside Card with reduced height */}
          <div className="mb-6">
            <div className="bg-white rounded-xl shadow-lg border-2 border-gray-200 p-1.5 w-fit">
              <div className="bg-[#FFF7E5] rounded-lg p-1 flex gap-1">
                <button
                  onClick={() => setActiveTab('resumes')}
                  className={`px-5 py-2 rounded-lg text-base font-medium transition-all ${
                    activeTab === 'resumes'
                      ? 'bg-white text-gray-900 shadow-sm font-semibold'
                      : 'bg-transparent text-gray-700 hover:text-gray-900'
                  }`}
                >
                  Resumes
                </button>
                <button
                  onClick={() => setActiveTab('scheduled')}
                  className={`px-5 py-2 rounded-lg text-base font-medium transition-all ${
                    activeTab === 'scheduled'
                      ? 'bg-white text-gray-900 shadow-sm font-semibold'
                      : 'bg-transparent text-gray-700 hover:text-gray-900'
                  }`}
                >
                  Scheduled Interviews
                </button>
                <button
                  onClick={() => setActiveTab('completed')}
                  className={`px-5 py-2 rounded-lg text-base font-medium transition-all ${
                    activeTab === 'completed'
                      ? 'bg-white text-gray-900 shadow-sm font-semibold'
                      : 'bg-transparent text-gray-700 hover:text-gray-900'
                  }`}
                >
                  Completed Interviews
                </button>
              </div>
            </div>
          </div>

          {/* Main Card - Only Content Inside */}
          <div className="bg-white rounded-xl shadow-lg border-2 border-gray-200 p-8">
            {/* Tab Content */}
            {activeTab === 'resumes' && (
              <div>
                {/* Uploaded Resumes Section */}
                <div className="mb-6">
                  <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                        <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                      </div>
                      <h2 className="text-xl font-bold text-gray-900">Uploaded Resumes</h2>
                    </div>
                    <div className="flex items-center gap-3">
                      <button
                        onClick={handleUploadClick}
                        disabled={isUploading}
                        className="bg-yellow-400 text-gray-900 px-4 py-2 rounded-lg font-semibold text-base hover:bg-yellow-500 transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                        </svg>
                        Upload Resume
                      </button>
                    </div>
                  </div>

                  {/* Upload Messages */}
                  {uploadError && (
                    <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
                      {uploadError}
                    </div>
                  )}

                  {uploadSuccess && (
                    <div className="mb-4 p-3 bg-green-50 border border-green-200 text-green-700 rounded-lg text-sm">
                      {uploadSuccess}
                    </div>
                  )}

                  {resumesError && (
                    <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
                      {resumesError}
                    </div>
                  )}

                  {/* Table */}
                  <div className="overflow-x-auto">
                    {isLoadingResumes ? (
                      <div className="text-center py-12 text-gray-500">
                        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
                        <p className="mt-4 text-base">Loading resumes...</p>
                      </div>
                    ) : resumes.length === 0 ? (
                      <div className="text-center py-12 text-gray-500">
                        <p className="text-base">No resumes found. Upload resumes to get started.</p>
                      </div>
                    ) : (
                      <table className="w-full">
                        <thead>
                          <tr className="border-b border-gray-200">
                            <th className="text-left py-3 px-4 text-base font-semibold text-gray-700">ID</th>
                            <th className="text-left py-3 px-4 text-base font-semibold text-gray-700">Candidate Name</th>
                            <th className="text-left py-3 px-4 text-base font-semibold text-gray-700">Email</th>
                            <th className="text-left py-3 px-4 text-base font-semibold text-gray-700">Resume Score</th>
                            <th className="text-left py-3 px-4 text-base font-semibold text-gray-700">Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {resumes.map((resume) => (
                            <tr key={resume.candidate_id} className="border-b border-gray-100 hover:bg-gray-50">
                              <td className="py-3 px-4 text-base text-gray-900 font-mono text-sm">{resume.candidate_id}</td>
                              <td className="py-3 px-4 text-base text-gray-900">{resume.name}</td>
                              <td className="py-3 px-4 text-base text-gray-600">{resume.email_id}</td>
                              <td className={`py-3 px-4 text-base font-medium ${getScoreColor(resume.status)}`}>
                                {resume.resume_score.toFixed(1)}
                              </td>
                              <td className="py-3 px-4">
                                <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium border ${getStatusColor(resume.status)}`}>
                                  {formatStatus(resume.status)}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>

                  {/* Note */}
                  <p className="text-sm text-gray-600 mt-4 italic">
                    * The invitation link will be sent to the shortlisted candidates automatically.
                  </p>
                </div>
              </div>
            )}

            {activeTab === 'scheduled' && (
              <div>
                {/* Scheduled Interviews Section */}
                <div className="mb-6">
                  <div className="flex items-center gap-3 mb-6">
                    <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                      <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                      </svg>
                    </div>
                    <h2 className="text-xl font-bold text-gray-900">Scheduled Interviews</h2>
                  </div>

                  {/* Error Message */}
                  {scheduledInterviewsError && (
                    <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
                      {scheduledInterviewsError}
                    </div>
                  )}

                  {/* Table */}
                  <div className="overflow-x-auto">
                    {isLoadingScheduledInterviews ? (
                      <div className="text-center py-12 text-gray-500">
                        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
                        <p className="mt-4 text-base">Loading scheduled interviews...</p>
                      </div>
                    ) : scheduledInterviews.length === 0 ? (
                      <div className="text-center py-12 text-gray-500">
                        <p className="text-base">No scheduled interviews found.</p>
                      </div>
                    ) : (
                      <table className="w-full">
                        <thead>
                          <tr className="border-b border-gray-200">
                            <th className="text-left py-3 px-4 text-base font-semibold text-gray-700">ID</th>
                            <th className="text-left py-3 px-4 text-base font-semibold text-gray-700">Candidate Name</th>
                            <th className="text-left py-3 px-4 text-base font-semibold text-gray-700">Email</th>
                            <th className="text-left py-3 px-4 text-base font-semibold text-gray-700">Interview Date</th>
                            <th className="text-left py-3 px-4 text-base font-semibold text-gray-700">Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {scheduledInterviews.map((interview) => (
                            <tr key={interview.candidate_id} className="border-b border-gray-100 hover:bg-gray-50">
                              <td className="py-3 px-4 text-base text-gray-900 font-mono text-sm">{interview.candidate_id}</td>
                              <td className="py-3 px-4 text-base text-gray-900">{interview.name}</td>
                              <td className="py-3 px-4 text-base text-gray-600">{interview.email_id}</td>
                              <td className="py-3 px-4 text-base text-gray-700">{formatInterviewDate(interview.interview_date)}</td>
                              <td className="py-3 px-4">
                                <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium border ${getInterviewStatusColor(interview.interview_status)}`}>
                                  {formatStatus(interview.interview_status)}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'completed' && (
              <div>
                {/* Completed Interviews Section */}
                <div className="mb-6">
                  <div className="flex items-center gap-3 mb-6">
                    <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                      <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                    <h2 className="text-xl font-bold text-gray-900">Completed Interviews</h2>
                  </div>

                  {/* Error Message */}
                  {completedInterviewsError && (
                    <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
                      {completedInterviewsError}
                    </div>
                  )}

                  {/* Table */}
                  <div className="overflow-x-auto">
                    {isLoadingCompletedInterviews ? (
                      <div className="text-center py-12 text-gray-500">
                        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
                        <p className="mt-4 text-base">Loading completed interviews...</p>
                      </div>
                    ) : completedInterviews.length === 0 ? (
                      <div className="text-center py-12 text-gray-500">
                        <p className="text-base">No completed interviews found.</p>
                      </div>
                    ) : (
                      <table className="w-full">
                        <thead>
                          <tr className="border-b border-gray-200">
                            <th className="text-left py-3 px-4 text-base font-semibold text-gray-700">ID</th>
                            <th className="text-left py-3 px-4 text-base font-semibold text-gray-700">Candidate Name</th>
                            <th className="text-left py-3 px-4 text-base font-semibold text-gray-700">Email</th>
                            <th className="text-left py-3 px-4 text-base font-semibold text-gray-700">Interview Score</th>
                            <th className="text-left py-3 px-4 text-base font-semibold text-gray-700">Status</th>
                            <th className="text-left py-3 px-4 text-base font-semibold text-gray-700">Report</th>
                          </tr>
                        </thead>
                        <tbody>
                          {completedInterviews.map((interview) => (
                            <tr key={interview.candidate_id} className="border-b border-gray-100 hover:bg-gray-50">
                              <td className="py-3 px-4 text-base text-gray-900 font-mono text-sm">{interview.candidate_id}</td>
                              <td className="py-3 px-4 text-base text-gray-900">{interview.name}</td>
                              <td className="py-3 px-4 text-base text-gray-600">{interview.email_id}</td>
                              <td className={`py-3 px-4 text-base font-medium ${interview.interview_score !== null && interview.interview_score >= 60 ? 'text-green-600' : 'text-gray-600'}`}>
                                {formatInterviewScore(interview.interview_score)}
                              </td>
                              <td className="py-3 px-4">
                                <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium border ${getCompletedStatusColor(interview.status)}`}>
                                  {formatStatus(interview.status)}
                                </span>
                              </td>
                              <td className="py-3 px-4">
                                <button
                                  onClick={() => navigate('/candidate/analysis', { 
                                    state: { 
                                      candidateId: interview.candidate_id,
                                      candidateName: interview.name,
                                      candidateEmail: interview.email_id
                                    } 
                                  })}
                                  className="text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1"
                                >
                                  View Report
                                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                                  </svg>
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Footer */}
      <Footer />

      {/* Job Description Modal */}
      {showJobDescriptionModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-[#FFF7E5] rounded-lg shadow-2xl max-w-5xl w-full max-h-[85vh] overflow-y-auto relative border-4 border-white">
            {/* Close Button */}
            <button
              onClick={() => setShowJobDescriptionModal(false)}
              className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 transition-colors z-10"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>

            {/* Modal Content */}
            <div className="p-8">
              {/* Job Title */}
              <h2 className="text-3xl font-bold text-gray-900 mb-6">{jobTitle}</h2>

              {/* Job Description */}
              <div className="mb-6">
                {jobDescription ? (
                  <div className="text-base text-gray-700 leading-relaxed whitespace-pre-wrap">
                    {jobDescription}
                  </div>
                ) : (
                  <div className="text-base text-gray-500 italic">
                    No job description available.
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Upload Candidates Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto relative border-2 border-gray-200">
            {/* Close Button */}
            <button
              onClick={handleModalClose}
              disabled={isUploading}
              className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 transition-colors z-10 disabled:opacity-50"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>

            {/* Modal Content */}
            <div className="p-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">Add Candidates</h2>
              <p className="text-sm text-gray-600 mb-6">Add up to 10 candidates with their name, email, and resume file.</p>

              {/* Error Message */}
              {uploadError && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
                  {uploadError}
                </div>
              )}

              {/* Candidates List */}
              <div className="space-y-4 mb-6">
                {candidates.map((candidate, index) => (
                  <div key={index} className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-base font-semibold text-gray-700">Candidate {index + 1}</h3>
                      {candidates.length > 1 && (
                        <button
                          onClick={() => handleRemoveCandidate(index)}
                          disabled={isUploading}
                          className="text-red-600 hover:text-red-800 disabled:opacity-50"
                        >
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      )}
                    </div>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-3">
                      {/* Name Input */}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Name <span className="text-red-500">*</span>
                        </label>
                        <input
                          type="text"
                          value={candidate.name}
                          onChange={(e) => handleCandidateNameChange(index, e.target.value)}
                          disabled={isUploading}
                          placeholder="Enter candidate name"
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-400 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
                        />
                      </div>

                      {/* Email Input */}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Email <span className="text-red-500">*</span>
                        </label>
                        <input
                          type="email"
                          value={candidate.email}
                          onChange={(e) => handleCandidateEmailChange(index, e.target.value)}
                          disabled={isUploading}
                          placeholder="Enter candidate email"
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-400 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
                        />
                      </div>
                    </div>

                    {/* File Input */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Resume File <span className="text-red-500">*</span>
                      </label>
                      <div className="flex items-center gap-3">
                        <input
                          ref={(el) => {
                            fileInputRefs.current[index] = el;
                          }}
                          type="file"
                          accept=".pdf,.docx,.doc"
                          onChange={(e) => handleCandidateFileChange(index, e)}
                          disabled={isUploading}
                          className="hidden"
                        />
                        <button
                          type="button"
                          onClick={() => fileInputRefs.current[index]?.click()}
                          disabled={isUploading}
                          className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {candidate.file ? 'Change File' : 'Select File'}
                        </button>
                        {candidate.file && (
                          <span className="text-sm text-gray-600 flex items-center gap-2">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                            {candidate.file.name}
                            <span className="text-xs text-gray-500">
                              ({(candidate.file.size / 1024).toFixed(1)} KB)
                            </span>
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Add More Button */}
              {candidates.length < 10 && (
                <button
                  onClick={handleAddCandidate}
                  disabled={isUploading}
                  className="mb-6 w-full py-2 border-2 border-dashed border-gray-300 rounded-lg text-gray-600 hover:border-gray-400 hover:text-gray-700 transition-colors flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  Add Another Candidate ({candidates.length}/10)
                </button>
              )}

              {/* Submit Button */}
              <div className="flex gap-3 justify-end">
                <button
                  onClick={handleModalClose}
                  disabled={isUploading}
                  className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Cancel
                </button>
                <button
                  onClick={handleModalSubmit}
                  disabled={isUploading}
                  className="px-6 py-2 bg-yellow-400 text-gray-900 rounded-lg hover:bg-yellow-500 transition-colors font-semibold flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isUploading ? (
                    <>
                      <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Uploading...
                    </>
                  ) : (
                    <>
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      Submit
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default JobDetailsPage;

