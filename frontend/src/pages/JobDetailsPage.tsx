import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Header from '../components/Header';
import Footer from '../components/Footer';

interface Resume {
  id: string;
  candidateName: string;
  resumeScore: number;
  status: 'Shortlisted' | 'Rejected';
}

const JobDetailsPage = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  
  // Get job details from location state or use defaults
  const jobId = location.state?.jobId || 'JD-001';
  const jobTitle = location.state?.jobTitle || 'Senior Software Engineer';
  
  const [activeTab, setActiveTab] = useState<'resumes' | 'scheduled' | 'completed'>('resumes');
  const [showJobDescriptionModal, setShowJobDescriptionModal] = useState(false);

  const handleLogout = () => {
    logout();
  };

  // Mock data for resumes
  const resumes: Resume[] = [
    { id: '001', candidateName: 'Alex Johnson', resumeScore: 82, status: 'Shortlisted' },
    { id: '002', candidateName: 'Sarah Mitchell', resumeScore: 75, status: 'Shortlisted' },
    { id: '003', candidateName: 'Pradeep Kumar', resumeScore: 54, status: 'Rejected' },
    { id: '004', candidateName: 'Pradeep Kumar', resumeScore: 87, status: 'Shortlisted' },
    { id: '005', candidateName: 'Sarah Mitchell', resumeScore: 43, status: 'Rejected' },
  ];

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'Shortlisted':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'Rejected':
        return 'bg-red-100 text-red-800 border-red-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getScoreColor = (score: number) => {
    return score >= 60 ? 'text-green-600' : 'text-red-600';
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
                    <button className="bg-yellow-400 text-gray-900 px-4 py-2 rounded-lg font-semibold text-base hover:bg-yellow-500 transition-colors flex items-center gap-2">
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                      </svg>
                      Upload Resume
                    </button>
                  </div>

                  {/* Table */}
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b border-gray-200">
                          <th className="text-left py-3 px-4 text-base font-semibold text-gray-700">ID</th>
                          <th className="text-left py-3 px-4 text-base font-semibold text-gray-700">Candidate Name</th>
                          <th className="text-left py-3 px-4 text-base font-semibold text-gray-700">Resume Score</th>
                          <th className="text-left py-3 px-4 text-base font-semibold text-gray-700">Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {resumes.map((resume) => (
                          <tr key={resume.id} className="border-b border-gray-100 hover:bg-gray-50">
                            <td className="py-3 px-4 text-base text-gray-900">{resume.id}</td>
                            <td className="py-3 px-4 text-base text-gray-900">{resume.candidateName}</td>
                            <td className={`py-3 px-4 text-base font-medium ${getScoreColor(resume.resumeScore)}`}>
                              {resume.resumeScore}
                            </td>
                            <td className="py-3 px-4">
                              <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium border ${getStatusColor(resume.status)}`}>
                                {resume.status}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
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

              {/* Company/Role Overview */}
              <div className="mb-6">
                <h3 className="text-xl font-semibold text-gray-900 mb-3">Company Overview</h3>
                <p className="text-base text-gray-700 leading-relaxed mb-3">
                  We provide innovative tech solutions to drive operational efficiency across the Globe.
                </p>
                <p className="text-base text-gray-700 leading-relaxed mb-3">
                  We are exploring innovative GenAI applications to enhance consumer engagement on retail platforms.
                </p>
                <p className="text-base text-gray-700 leading-relaxed mb-3">
                  We are creating a Party Planner experience within a Tesco replica site hosted on MDSL.
                </p>
                <p className="text-base text-gray-700 leading-relaxed mb-3">
                  This effort aims to showcase how AI-driven tools can improve product discovery and event-based shopping journeys.
                </p>
                <p className="text-base text-gray-700 leading-relaxed">
                  The solution is expected to drive long-term value by enabling scalable, brand-aligned digital experiences while adhering to budget, security, and compliance constraints.
                </p>
              </div>

              {/* Essential Functions */}
              <div className="mb-6">
                <h3 className="text-xl font-semibold text-gray-900 mb-3">Essential Functions</h3>
                <ul className="list-disc list-inside space-y-2 text-base text-gray-700">
                  <li>Strong programming skills in Python, including popular libraries such as LangChain, Transformers, FastAPI, or similar.</li>
                  <li>Design, develop, and deploy applications utilizing Large Language Models (LLMs) such as GPT, LLaMA, Claude, etc.</li>
                  <li>Build and optimize AI agent frameworks, leveraging prompt engineering best practices.</li>
                  <li>Develop and integrate vector databases (e.g., FAISS, Pinecone, Weaviate) for efficient semantic search and retrieval.</li>
                  <li>Collaborate with data scientists and ML engineers to operationalize NLP and generative AI models.</li>
                  <li>Optimize inference and fine-tuning workflows for performance, reliability, and scalability.</li>
                  <li>Work closely with DevOps and Cloud Engineering teams to deploy and monitor applications on Microsoft Azure (experience with Azure ML, Azure OpenAI, or Cognitive Services preferred).</li>
                  <li>Stay current with advancements in the LLM and GenAI space and apply them to solve real-world business problems.</li>
                  <li>Write clean, maintainable code and contribute to internal knowledge sharing.</li>
                </ul>
              </div>

              {/* Qualifications */}
              <div>
                <h3 className="text-xl font-semibold text-gray-900 mb-3">Qualifications</h3>
                <ul className="list-disc list-inside space-y-2 text-base text-gray-700">
                  <li>Experience with open-source LLMs (e.g., LLaMA, Mistral, Falcon, or Mixtral).</li>
                  <li>Familiarity with agent frameworks such as LangChain Agents, AutoGPT, or Semantic Kernel.</li>
                  <li>Prior work on Retrieval-Augmented Generation (RAG) pipelines.</li>
                  <li>Understanding of MLOps principles and model lifecycle management.</li>
                </ul>
                <p className="text-base text-gray-600 mt-3 italic">Would be a plus</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default JobDetailsPage;

