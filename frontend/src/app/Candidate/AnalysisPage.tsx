import { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import { useAuth } from '../../context/AuthContext';
import Header from '../../components/Header';
import Footer from '../../components/Footer';
import { getInterviewAnalysis, type InterviewAnalysisResponse } from '../../api/admin.api';
import { isTokenExpiredError } from '../../utils/apiErrorHandler';

const AnalysisPage = () => {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());
  const [analysisData, setAnalysisData] = useState<InterviewAnalysisResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const candidateId = location.state?.candidateId;
  const candidateName = location.state?.candidateName || 'Unknown';
  const candidateEmail = location.state?.candidateEmail || '';

  useEffect(() => {
    if (!candidateId) {
      setError('No candidate ID provided');
      setIsLoading(false);
      return;
    }

    const fetchAnalysis = async () => {
      try {
        setIsLoading(true);
        const data = await getInterviewAnalysis(candidateId);
        // Log exact response received from API function
        console.log('=== EXACT RESPONSE FROM API FUNCTION ===');
        console.log('Full Response:', JSON.stringify(data, null, 2));
        console.log('Response Type:', typeof data);
        console.log('========================================');
        // Debug logging (only log non-null values with helpful messages)
        console.log('Interview Analysis Data:', data);
        if (data.mcq_analysis) {
          console.log('MCQ Analysis:', data.mcq_analysis);
        }
        if (data.coding_analysis) {
          console.log('Coding Analysis:', data.coding_analysis);
        } else {
          console.log('Coding Analysis: Not available (coding section may not be completed)');
        }
        if (data.system_design_analysis) {
          console.log('System Design Analysis:', data.system_design_analysis);
        }
        if (data.cheat_metrics) {
          console.log('Cheat Metrics:', data.cheat_metrics);
        }
        if (data.overall_summary) {
          console.log('Overall Summary:', data.overall_summary);
        }
        setAnalysisData(data);
        setError(null);
      } catch (err) {
        if (isTokenExpiredError(err)) {
          console.log('Token expired, logging out...');
          logout();
          return;
        }
        const errorMessage = err instanceof Error ? err.message : 'Failed to fetch analysis data';
        console.error('Error fetching analysis:', err);
        setError(errorMessage);
      } finally {
        setIsLoading(false);
      }
    };

    fetchAnalysis();
  }, [candidateId, logout]);

  const handleLogout = () => {
    logout();
  };

  // Helper function to get candidate initials
  const getInitials = (name: string) => {
    const parts = name.split(' ');
    if (parts.length >= 2) {
      return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    }
    return name.substring(0, 2).toUpperCase();
  };

  // Helper function to determine integrity level
  const getIntegrityLevel = (metrics?: { tab_change?: number; full_screen_exits?: number; multiple_face?: number } | null) => {
    if (!metrics) return 'Unknown';
    
    const totalViolations = (metrics.tab_change || 0) + (metrics.full_screen_exits || 0) + (metrics.multiple_face || 0);
    
    if (totalViolations === 0) return 'Very High';
    if (totalViolations <= 3) return 'High';
    if (totalViolations <= 6) return 'Medium';
    return 'Low';
  };

  const handleSectionClick = (section: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(section)) {
      newExpanded.delete(section);
    } else {
      newExpanded.add(section);
    }
    setExpandedSections(newExpanded);
  };

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case 'easy': return '#10B981'; // green
      case 'medium': return '#F59E0B'; // orange
      case 'hard': return '#EF4444'; // red
      default: return '#6B7280';
    }
  };

  // Helper function to format duration from seconds
  const formatDurationFromSeconds = (seconds: number | null | undefined): string => {
    if (seconds === null || seconds === undefined) return 'N/A';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    if (hours > 0) {
      return `${hours}h ${minutes}m ${secs}s`;
    } else if (minutes > 0) {
      return `${minutes}m ${secs}s`;
    }
    return `${secs}s`;
  };

  const renderDonutChart = (data: { easy: number; medium: number; hard: number }, label: string) => {
    const total = data.easy + data.medium + data.hard;
    if (total === 0) return null;

    const chartData = [
      { name: 'Easy', value: data.easy, color: getDifficultyColor('easy') },
      { name: 'Medium', value: data.medium, color: getDifficultyColor('medium') },
      { name: 'Hard', value: data.hard, color: getDifficultyColor('hard') }
    ].filter(item => item.value > 0);

    const COLORS = chartData.map(item => item.color);

    return (
      <div className="flex flex-col items-center">
        <div className="relative w-48 h-48">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={80}
                paddingAngle={2}
                dataKey="value"
                startAngle={90}
                endAngle={-270}
              >
                {chartData.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index]} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <span className="text-2xl font-semibold text-gray-700">{total}</span>
          </div>
        </div>
        <p className="text-sm text-gray-600 mt-2 text-center font-semibold">{label}</p>
        <div className="flex gap-4 mt-2">
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: getDifficultyColor('easy') }}></div>
            <span className="text-xs text-gray-600">Easy</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: getDifficultyColor('medium') }}></div>
            <span className="text-xs text-gray-600">Medium</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: getDifficultyColor('hard') }}></div>
            <span className="text-xs text-gray-600">Hard</span>
          </div>
        </div>
      </div>
    );
  };

  const renderSectionContent = (section: string) => {
    if (!analysisData) return null;

    switch (section) {
      case 'mcq': {
        const mcqData = analysisData.mcq_analysis;
        if (!mcqData) return <p className="text-gray-500">No MCQ data available</p>;
        
        // Use the actual data structure: attempted and correct objects
        const mcqAttempted = mcqData.attempted || { easy: 0, medium: 0, hard: 0 };
        const mcqCorrect = mcqData.correct || { easy: 0, medium: 0, hard: 0 };
        
        // Calculate totals
        const totalAttempted = mcqAttempted.easy + mcqAttempted.medium + mcqAttempted.hard;
        const totalCorrect = mcqCorrect.easy + mcqCorrect.medium + mcqCorrect.hard;
        const totalQuestions = mcqData.total_questions || 25; // Default to 25 if not provided
        
        // Get timing from section_timings if available, otherwise fall back to mcqData.time_taken
        const mcqTimeTaken = analysisData.section_timings?.mcq !== undefined 
          ? formatDurationFromSeconds(analysisData.section_timings.mcq)
          : (mcqData.time_taken ? `${mcqData.time_taken} mins` : 'N/A');
        
        return (
          <div className="space-y-6">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
                <span className="text-lg font-semibold text-gray-700">Total Score: {mcqData.score ?? 'N/A'}</span>
              </div>
              <div className="flex items-center gap-2">
                <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="text-lg font-semibold text-gray-700">Time Taken: {mcqTimeTaken}</span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-6">
              {renderDonutChart(
                mcqAttempted,
                `Total attempted questions: ${totalAttempted}/${totalQuestions}`
              )}
              {renderDonutChart(
                mcqCorrect,
                `Correct answers: ${totalCorrect}`
              )}
            </div>

            {/* Correct answers breakdown by difficulty */}
            <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
              <div className="flex items-center gap-2 mb-3">
                <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="text-base font-semibold text-gray-700">Correct Answers Breakdown:</span>
              </div>
              <div className="flex items-center gap-6">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: getDifficultyColor('easy') }}></div>
                  <span className="text-sm text-gray-700">
                    <span className="font-semibold">Easy:</span> {mcqCorrect.easy}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: getDifficultyColor('medium') }}></div>
                  <span className="text-sm text-gray-700">
                    <span className="font-semibold">Medium:</span> {mcqCorrect.medium}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: getDifficultyColor('hard') }}></div>
                  <span className="text-sm text-gray-700">
                    <span className="font-semibold">Hard:</span> {mcqCorrect.hard}
                  </span>
                </div>
              </div>
            </div>
          </div>
        );
      }

      case 'coding': {
        const codingData = analysisData.coding_analysis;
        if (!codingData) return <p className="text-gray-500">No coding data available</p>;
        
        // Get timing from section_timings if available, otherwise fall back to codingData.time_taken
        const codingTimeTaken = analysisData.section_timings?.coding !== undefined 
          ? formatDurationFromSeconds(analysisData.section_timings.coding)
          : (codingData.time_taken ? `${codingData.time_taken} mins` : 'N/A');
        
        return (
          <div className="space-y-6">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <div className="w-10 h-10 bg-yellow-100 rounded-full flex items-center justify-center flex-shrink-0">
                  <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                </div>
                <span className="text-lg font-semibold text-gray-700">Total Score: {codingData.total_score ?? 'N/A'}</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-10 h-10 bg-yellow-100 rounded-full flex items-center justify-center flex-shrink-0">
                  <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <span className="text-lg font-semibold text-gray-700">Time Taken: {codingTimeTaken}</span>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div>
                <span className="text-base font-semibold text-gray-700">Submitted questions: </span>
                <span className="text-base text-gray-900">{codingData.total_submitted ?? 0}{codingData.total_questions ? `/${codingData.total_questions}` : ''}</span>
              </div>
              <div>
                <span className="text-base font-semibold text-gray-700">Total correct answers: </span>
                <span className="text-base text-gray-900">{codingData.total_correct ?? 0}</span>
              </div>
              <div>
                <span className="text-base font-semibold text-gray-700">Partially correct answers: </span>
                <span className="text-base text-gray-900">{codingData.partially_correct ?? 0}</span>
              </div>
            </div>
          </div>
        );
      }

      case 'system-design': {
        const sdData = analysisData.system_design_analysis;
        if (!sdData) return <p className="text-gray-500">No system design data available</p>;
        
        // Get timing from section_timings if available, otherwise fall back to sdData.time_taken
        const sdTimeTaken = analysisData.section_timings?.system_design !== undefined 
          ? formatDurationFromSeconds(analysisData.section_timings.system_design)
          : (sdData.time_taken ? `${sdData.time_taken} mins` : 'N/A');
        
        return (
          <div className="space-y-6">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
                <span className="text-lg font-semibold text-gray-700">Total Score: {sdData.score ?? 'N/A'}</span>
              </div>
              <div className="flex items-center gap-2">
                <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="text-lg font-semibold text-gray-700">Time Taken: {sdTimeTaken}</span>
              </div>
            </div>

            {sdData.summary && (
              <div className="bg-yellow-50 rounded-lg p-6 shadow-sm">
                <div className="flex items-start gap-3 mb-4">
                  <div className="w-10 h-10 bg-orange-500 rounded-full flex items-center justify-center flex-shrink-0">
                    <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                    </svg>
                  </div>
                  <h3 className="text-lg font-bold text-gray-900">Summary</h3>
                </div>
                <p className="text-gray-700 leading-relaxed">{sdData.summary}</p>
              </div>
            )}

            {/* Strengths and Things to Improve */}
            <div className="grid grid-cols-2 gap-6">
              {sdData.key_strengths && sdData.key_strengths.length > 0 && (
                <div className="bg-white rounded-lg p-6 shadow-sm">
                  <div className="flex items-start gap-3 mb-4">
                    <div className="w-10 h-10 bg-green-500 rounded-full flex items-center justify-center flex-shrink-0">
                      <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                    <h3 className="text-lg font-bold text-gray-900">Strengths</h3>
                  </div>
                  <ul className="space-y-2">
                    {sdData.key_strengths.map((strength, index) => (
                      <li key={index} className="flex items-start gap-2">
                        <svg className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                        <span className="text-gray-700">{strength}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {sdData.things_to_improve && sdData.things_to_improve.length > 0 && (
                <div className="bg-white rounded-lg p-6 shadow-sm">
                  <div className="flex items-start gap-3 mb-4">
                    <div className="w-10 h-10 bg-yellow-500 rounded-full flex items-center justify-center flex-shrink-0">
                      <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                      </svg>
                    </div>
                    <h3 className="text-lg font-bold text-gray-900">Things to Improve</h3>
                  </div>
                  <ul className="space-y-2">
                    {sdData.things_to_improve.map((item, index) => (
                      <li key={index} className="flex items-start gap-2">
                        <svg className="w-5 h-5 text-yellow-500 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <span className="text-gray-700">{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        );
      }

      case 'integrity': {
        const cheatData = analysisData.cheat_metrics;
        if (!cheatData) return <p className="text-gray-500">No integrity data available</p>;
        
        return (
          <div className="space-y-6">
            <div className="bg-white rounded-lg p-6 shadow-sm">
              <div className="space-y-3">
                <div>
                  <span className="text-base font-semibold text-gray-700">Tab changes: </span>
                  <span className="text-base text-gray-900">{cheatData.tab_change ?? 0}</span>
                </div>
                <div>
                  <span className="text-base font-semibold text-gray-700">Fullscreen exits: </span>
                  <span className="text-base text-gray-900">{cheatData.full_screen_exits ?? 0}</span>
                </div>
                <div>
                  <span className="text-base font-semibold text-gray-700">Multiple face detection: </span>
                  <span className="text-base text-gray-900">{(cheatData.multiple_face ?? 0) > 0 ? 'yes' : 'no'}</span>
                </div>
              </div>
            </div>
          </div>
        );
      }

      default:
        return null;
    }
  };


  // Show loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-[#FFF7E5] to-[#F5FCFF] flex flex-col">
        <Header 
          showUserInfo={true} 
          showLogout={true} 
          showTechInterviewLogo={true} 
          user={user} 
          onLogout={handleLogout} 
        />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mb-4"></div>
            <p className="text-lg text-gray-700">Loading interview analysis...</p>
          </div>
        </div>
        <Footer />
      </div>
    );
  }

  // Show error state
  if (error || !analysisData) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-[#FFF7E5] to-[#F5FCFF] flex flex-col">
        <Header 
          showUserInfo={true} 
          showLogout={true} 
          showTechInterviewLogo={true} 
          user={user} 
          onLogout={handleLogout} 
        />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <p className="text-lg text-red-600 mb-4">{error || 'No analysis data available'}</p>
            <button
              onClick={() => navigate(-1)}
              className="px-4 py-2 bg-yellow-400 text-gray-900 rounded-lg hover:bg-yellow-500 font-semibold"
            >
              Go Back
            </button>
          </div>
        </div>
        <Footer />
      </div>
    );
  }

  const integrityLevel = getIntegrityLevel(analysisData.cheat_metrics);
  const overallScore = analysisData.overall_percentage ?? 0;

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#FFF7E5] to-[#F5FCFF] flex flex-col">
      <Header 
        showUserInfo={true} 
        showLogout={true} 
        showTechInterviewLogo={true} 
        user={user} 
        onLogout={handleLogout} 
      />

      <div className="flex-1 flex gap-8 px-8 py-8 max-w-7xl mx-auto w-full">
        {/* Main Content */}
        <div className="flex-1">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-3xl font-semibold text-gray-900">Interview Analysis Report</h1>
            <button
              onClick={() => navigate(-1)}
              className="text-blue-600 hover:text-blue-800 font-medium flex items-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              Back
            </button>
          </div>
          
          {/* Separator Line */}
          <div className="border-t border-gray-300 mb-4"></div>

          {/* Result */}
          <div className="mb-6">
            <span className="text-lg font-semibold text-gray-700">Result: </span>
            <span className={`text-lg font-bold ${analysisData.result === 'PASS' ? 'text-green-600' : 'text-red-600'}`}>
              {analysisData.result || 'Pending'}
            </span>
          </div>

          {/* Summary */}
          {analysisData.overall_summary && (
            <div className="bg-white rounded-lg p-6 mb-6 shadow-sm">
              <div className="flex items-start gap-3 mb-4">
                <div className="w-10 h-10 bg-orange-500 rounded-full flex items-center justify-center flex-shrink-0">
                  <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                  </svg>
                </div>
                <h2 className="text-xl font-bold text-gray-900">Summary</h2>
              </div>
              <p className="text-gray-700 leading-relaxed">
                {analysisData.overall_summary.replace(/^\*\*Interview Performance Summary:\*\*\s*/i, '')}
              </p>
            </div>
          )}

          {/* Section Analysis */}
          <div className="mb-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Section Analysis</h2>

            {/* Section 1: Multiple Choice */}
            {analysisData.mcq_analysis && (
              <div className="bg-white rounded-lg shadow-sm mb-3">
                <button
                  onClick={() => handleSectionClick('mcq')}
                  className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
                >
                  <span className="text-lg font-semibold text-gray-900">Section 1: Multiple Choice</span>
                  <svg 
                    className={`w-5 h-5 text-gray-500 transition-transform ${expandedSections.has('mcq') ? 'rotate-90' : ''}`} 
                    fill="none" 
                    stroke="currentColor" 
                    viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </button>
                {expandedSections.has('mcq') && (
                  <div className="px-4 pb-4 border-t border-gray-200">
                    <div className="pt-4">
                      {renderSectionContent('mcq')}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Section 2: Coding Challenge */}
            {analysisData.coding_analysis && (
              <div className="bg-white rounded-lg shadow-sm mb-3">
                <button
                  onClick={() => handleSectionClick('coding')}
                  className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
                >
                  <span className="text-lg font-semibold text-gray-900">Section 2: Coding Challenge</span>
                  <svg 
                    className={`w-5 h-5 text-gray-500 transition-transform ${expandedSections.has('coding') ? 'rotate-90' : ''}`} 
                    fill="none" 
                    stroke="currentColor" 
                    viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </button>
                {expandedSections.has('coding') && (
                  <div className="px-4 pb-4 border-t border-gray-200">
                    <div className="pt-4">
                      {renderSectionContent('coding')}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Section 3: System Design */}
            {analysisData.system_design_analysis && (
              <div className="bg-white rounded-lg shadow-sm mb-3">
                <button
                  onClick={() => handleSectionClick('system-design')}
                  className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
                >
                  <span className="text-lg font-semibold text-gray-900">Section 3: System Design</span>
                  <svg 
                    className={`w-5 h-5 text-gray-500 transition-transform ${expandedSections.has('system-design') ? 'rotate-90' : ''}`} 
                    fill="none" 
                    stroke="currentColor" 
                    viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </button>
                {expandedSections.has('system-design') && (
                  <div className="px-4 pb-4 border-t border-gray-200">
                    <div className="pt-4">
                      {renderSectionContent('system-design')}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Integrity */}
            {analysisData.cheat_metrics && (
              <div className="bg-white rounded-lg shadow-sm">
                <button
                  onClick={() => handleSectionClick('integrity')}
                  className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-lg font-semibold text-gray-900">Integrity: </span>
                    <span className={`text-lg font-semibold ${integrityLevel === 'High' || integrityLevel === 'Very High' ? 'text-green-600' : integrityLevel === 'Medium' ? 'text-yellow-600' : 'text-red-600'}`}>
                      {integrityLevel}
                    </span>
                  </div>
                  <svg 
                    className={`w-5 h-5 text-gray-500 transition-transform ${expandedSections.has('integrity') ? 'rotate-90' : ''}`} 
                    fill="none" 
                    stroke="currentColor" 
                    viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </button>
                {expandedSections.has('integrity') && (
                  <div className="px-4 pb-4 border-t border-gray-200">
                    <div className="pt-4">
                      {renderSectionContent('integrity')}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Candidate Info Panel */}
        <div className="w-80 bg-white rounded-lg p-6 shadow-sm h-fit">
          <div className="flex flex-col items-center mb-6">
            <div className="w-full h-64 bg-yellow-400 rounded-lg flex items-center justify-center mb-4 relative overflow-hidden">
              {analysisData?.image_data ? (
                <img 
                  src={analysisData.image_data} 
                  alt={candidateName}
                  className="w-full h-full object-cover"
                />
              ) : (
                <span className="text-5xl font-bold text-gray-800">{getInitials(candidateName)}</span>
              )}
              <div className="absolute bottom-2 right-2 w-6 h-6 bg-green-500 rounded-full border-2 border-white"></div>
            </div>
          </div>
          <div className="space-y-3">
            <div>
              <span className="text-sm font-semibold text-gray-600">Name: </span>
              <span className="text-base font-bold text-gray-900">{candidateName}</span>
            </div>
            {candidateEmail && (
              <div>
                <span className="text-sm font-semibold text-gray-600">Email: </span>
                <span className="text-base text-gray-700">{candidateEmail}</span>
              </div>
            )}
            <div>
              <span className="text-sm font-semibold text-gray-600">Overall Score: </span>
              <span className="text-base font-bold text-gray-900">{overallScore}%</span>
            </div>
            <div>
              <span className="text-sm font-semibold text-gray-600">Integrity: </span>
              <span className={`text-base font-bold ${integrityLevel === 'High' || integrityLevel === 'Very High' ? 'text-green-600' : integrityLevel === 'Medium' ? 'text-yellow-600' : 'text-red-600'}`}>
                {integrityLevel}
              </span>
            </div>
            <div>
              <span className="text-sm font-semibold text-gray-600">Candidate ID: </span>
              <span className="text-xs text-gray-600 break-all">{candidateId}</span>
            </div>
          </div>
        </div>
      </div>

      <Footer />
    </div>
  );
};

export default AnalysisPage;

