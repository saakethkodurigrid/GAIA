import { useState, useRef, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Header from '../components/Header';
import Footer from '../components/Footer';
import { uploadCandidatesBatch, getResumesList, type ResumeCandidateResponse } from '../api/admin.api';

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
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const [resumes, setResumes] = useState<ResumeCandidateResponse[]>([]);
  const [isLoadingResumes, setIsLoadingResumes] = useState(false);
  const [resumesError, setResumesError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

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
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch resumes. Please try again.';
      setResumesError(errorMessage);
      setResumes([]);
    } finally {
      setIsLoadingResumes(false);
    }
  };

  // Fetch resumes on mount and when jobId changes
  useEffect(() => {
    fetchResumes();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);

  const getStatusColor = (status: string) => {
    const statusLower = status.toLowerCase();
    switch (statusLower) {
      case 'shortlisted':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
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

  const getScoreColor = (score: number) => {
    return score >= 60 ? 'text-green-600' : 'text-red-600';
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    
    // Validate file types
    const allowedExtensions = ['pdf', 'docx', 'doc'];
    const validFiles: File[] = [];
    const invalidFiles: string[] = [];
    
    files.forEach((file) => {
      const extension = file.name.toLowerCase().split('.').pop() || '';
      if (allowedExtensions.includes(extension)) {
        validFiles.push(file);
      } else {
        invalidFiles.push(file.name);
      }
    });

    if (invalidFiles.length > 0) {
      setUploadError(`Invalid file types. Only PDF and DOCX are allowed. Invalid files: ${invalidFiles.join(', ')}`);
      setTimeout(() => setUploadError(null), 5000);
    }

    if (validFiles.length > 0) {
      // Check total file count (max 10)
      const totalFiles = selectedFiles.length + validFiles.length;
      if (totalFiles > 10) {
        setUploadError(`Maximum 10 files allowed. You have ${selectedFiles.length} selected and trying to add ${validFiles.length} more.`);
        setTimeout(() => setUploadError(null), 5000);
        return;
      }
      
      setSelectedFiles((prev) => [...prev, ...validFiles]);
      setUploadError(null);
    }

    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleRemoveFile = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleUpload = async () => {
    if (selectedFiles.length === 0) {
      setUploadError('Please select at least one file to upload');
      setTimeout(() => setUploadError(null), 5000);
      return;
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
      const response = await uploadCandidatesBatch(jobId, selectedFiles);
      
      if (response.success) {
        let successMsg = `Successfully uploaded ${response.successful} resume(s)`;
        
        // Add details about failed files if any
        if (response.failed > 0 && response.failed_files && response.failed_files.length > 0) {
          const failedFileNames = response.failed_files.map(f => f.filename).join(', ');
          successMsg += `. ${response.failed} file(s) failed: ${failedFileNames}`;
        }
        
        setUploadSuccess(successMsg);
        setSelectedFiles([]);
        
        // Refresh resumes list after successful upload
        await fetchResumes();
        
        // Clear success message after 7 seconds
        setTimeout(() => {
          setUploadSuccess(null);
        }, 7000);
      } else {
        // Handle partial success or complete failure
        let errorMsg = response.message || 'Failed to upload resumes';
        
        if (response.failed_files && response.failed_files.length > 0) {
          const failedDetails = response.failed_files.map(f => `${f.filename}: ${f.error}`).join('; ');
          errorMsg += `. Failed files: ${failedDetails}`;
        }
        
        setUploadError(errorMsg);
        setTimeout(() => setUploadError(null), 8000);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to upload resumes. Please try again.';
      setUploadError(errorMessage);
      setTimeout(() => setUploadError(null), 5000);
    } finally {
      setIsUploading(false);
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
                      <input
                        ref={fileInputRef}
                        type="file"
                        multiple
                        accept=".pdf,.docx,.doc"
                        onChange={handleFileSelect}
                        className="hidden"
                      />
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
                      {selectedFiles.length > 0 && (
                        <button
                          onClick={handleUpload}
                          disabled={isUploading}
                          className="bg-green-500 text-white px-4 py-2 rounded-lg font-semibold text-base hover:bg-green-600 transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
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
                              Upload {selectedFiles.length} file{selectedFiles.length > 1 ? 's' : ''}
                            </>
                          )}
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Selected Files List */}
                  {selectedFiles.length > 0 && (
                    <div className="mb-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
                      <div className="flex items-center justify-between mb-2">
                        <h3 className="text-sm font-semibold text-gray-700">
                          Selected Files ({selectedFiles.length}/10)
                        </h3>
                        <button
                          onClick={() => setSelectedFiles([])}
                          className="text-sm text-red-600 hover:text-red-800"
                        >
                          Clear All
                        </button>
                      </div>
                      <div className="space-y-2 max-h-40 overflow-y-auto">
                        {selectedFiles.map((file, index) => (
                          <div
                            key={index}
                            className="flex items-center justify-between p-2 bg-white rounded border border-gray-200"
                          >
                            <div className="flex items-center gap-2 flex-1 min-w-0">
                              <svg className="w-5 h-5 text-gray-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                              </svg>
                              <span className="text-sm text-gray-700 truncate">{file.name}</span>
                              <span className="text-xs text-gray-500 flex-shrink-0">
                                ({(file.size / 1024).toFixed(1)} KB)
                              </span>
                            </div>
                            <button
                              onClick={() => handleRemoveFile(index)}
                              className="ml-2 text-red-600 hover:text-red-800 flex-shrink-0"
                            >
                              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                              </svg>
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

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
                              <td className="py-3 px-4 text-base text-gray-900">{resume.candidate_id.substring(0, 8)}...</td>
                              <td className="py-3 px-4 text-base text-gray-900">{resume.name}</td>
                              <td className="py-3 px-4 text-base text-gray-600">{resume.email_id}</td>
                              <td className={`py-3 px-4 text-base font-medium ${getScoreColor(resume.resume_score)}`}>
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
              <div className="text-center py-12 text-gray-500">
                <p className="text-base">Scheduled Interviews content will appear here</p>
              </div>
            )}

            {activeTab === 'completed' && (
              <div className="text-center py-12 text-gray-500">
                <p className="text-base">Completed Interviews content will appear here</p>
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
    </div>
  );
};

export default JobDetailsPage;

