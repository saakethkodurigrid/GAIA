import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Header from '../components/Header';
import Footer from '../components/Footer';

interface JobDescription {
  id: string;
  jobTitle: string;
  status: 'Active' | 'Closed';
  grade: string;
}

interface ScheduledInterview {
  jobTitle: string;
  status: 'Scheduled' | 'Completed' | 'In Progress';
  interviewer: string;
  time: string;
}

const Recruiter = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [selectedDate, setSelectedDate] = useState(new Date(2025, 10, 5)); // Nov 5, 2025

  const handleLogout = () => {
    logout();
  };

  // Mock data for job descriptions
  const jobDescriptions: JobDescription[] = [
    { id: 'JD-001', jobTitle: 'Senior Software Engineer', status: 'Active', grade: 'T2' },
    { id: 'JD-002', jobTitle: 'Frontend Engineer', status: 'Closed', grade: 'T3' },
    { id: 'JD-003', jobTitle: 'Backend Engineer', status: 'Active', grade: 'T2' },
    { id: 'JD-004', jobTitle: 'Senior Software Engineer', status: 'Active', grade: 'T2' },
    { id: 'JD-005', jobTitle: 'Devops Engineer', status: 'Active', grade: 'T2' },
    { id: 'JD-006', jobTitle: 'Senior Software Engineer', status: 'Active', grade: 'T2' },
    { id: 'JD-007', jobTitle: 'Frontend Engineer', status: 'Closed', grade: 'T3' },
    { id: 'JD-008', jobTitle: 'Frontend Engineer', status: 'Closed', grade: 'T3' },
    { id: 'JD-009', jobTitle: 'Frontend Engineer', status: 'Closed', grade: 'T3' },
  ];

  // Mock data for scheduled interviews
  const scheduledInterviews: ScheduledInterview[] = [
    { jobTitle: 'Backend Engineer', status: 'Scheduled', interviewer: 'Alex Johnson', time: '9:00 AM' },
    { jobTitle: 'Frontend Engineer', status: 'Completed', interviewer: 'Alex Johnson', time: '9:00 AM' },
    { jobTitle: 'Senior Software Engineer', status: 'Completed', interviewer: 'Alex Johnson', time: '9:00 AM' },
    { jobTitle: 'Backend Engineer', status: 'Scheduled', interviewer: 'Alex Johnson', time: '9:00 AM' },
    { jobTitle: 'Backend Engineer', status: 'In Progress', interviewer: 'Alex Johnson', time: '9:00 AM' },
    { jobTitle: 'Backend Engineer', status: 'In Progress', interviewer: 'Alex Johnson', time: '9:00 AM' },
  ];

  const formatDate = (date: Date) => {
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return `${months[date.getMonth()]} ${date.getDate()}, ${date.getFullYear()}`;
  };

  const navigateDate = (direction: 'prev' | 'next') => {
    const newDate = new Date(selectedDate);
    if (direction === 'prev') {
      newDate.setDate(newDate.getDate() - 1);
    } else {
      newDate.setDate(newDate.getDate() + 1);
    }
    setSelectedDate(newDate);
  };

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
                <button className="bg-yellow-400 text-gray-900 px-4 py-2 rounded-lg font-semibold text-sm hover:bg-yellow-500 transition-colors flex items-center gap-2">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                  Upload JD
                </button>
              </div>

              {/* Table */}
              <div className="overflow-x-auto overflow-y-auto flex-1">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-gray-200">
                      <th className="text-left py-3 px-4 text-base font-semibold text-gray-700">ID</th>
                      <th className="text-left py-3 px-4 text-base font-semibold text-gray-700">Job Title</th>
                      <th className="text-left py-3 px-4 text-base font-semibold text-gray-700">Status</th>
                      <th className="text-left py-3 px-4 text-base font-semibold text-gray-700">Grade</th>
                      <th className="text-left py-3 px-4 text-base font-semibold text-gray-700">Actions</th>
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
                              state: { jobId: jd.id, jobTitle: jd.jobTitle } 
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
                <h2 className="text-xl font-bold text-gray-900">Scheduled Interviews</h2>
              </div>

              {/* Date Navigation */}
              <div className="flex items-center justify-center gap-4 mb-6 flex-shrink-0">
                <button
                  onClick={() => navigateDate('prev')}
                  className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                  </svg>
                </button>
                <span className="text-lg font-semibold text-gray-900">
                  {formatDate(selectedDate)}
                </span>
                <button
                  onClick={() => navigateDate('next')}
                  className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </button>
              </div>

              {/* Interviews List */}
              <div className="space-y-4 overflow-y-auto flex-1">
                {scheduledInterviews.map((interview, index) => (
                  <div key={index} className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                    <div className="flex items-start justify-between mb-2">
                      <h3 className="text-lg font-semibold text-gray-900">{interview.jobTitle}</h3>
                      <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium border ${getStatusColor(interview.status)}`}>
                        {interview.status}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-base text-gray-600">
                      <span>Interviewer: {interview.interviewer}</span>
                      <span>•</span>
                      <span>Time: {interview.time}</span>
                      {interview.status === 'Completed' && (
                        <>
                          <span>•</span>
                          <button className="text-blue-600 hover:text-blue-800">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                            </svg>
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <Footer />
    </div>
  );
};

export default Recruiter;
