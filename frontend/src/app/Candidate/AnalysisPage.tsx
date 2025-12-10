import { useState } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import { useAuth } from '../../context/AuthContext';
import Header from '../../components/Header';
import Footer from '../../components/Footer';

// Hardcoded data
const analysisData = {
  candidate: {
    name: 'Jhil Kumari',
    role: 'Backend',
    score: 76,
    integrity: 'High',
    testTime: 132,
    avatar: 'JK'
  },
  assessment: {
    date: 'November 5, 2025',
    time: '3:45 PM',
    verdict: 'Recommended',
    summary: 'Strong architectural thinking with attention to scalability. Consider exploring more microservices patterns. Strong architectural thinking with attention to scalability. Consider exploring more microservices patterns. Strong architectural thinking with attention to scalability. Consider exploring more microservices patterns.'
  },
  sections: {
    mcq: {
      title: 'Section 1: Multiple Choice',
      totalScore: 16,
      timeTaken: 72,
      totalAttempted: 15,
      totalQuestions: 25,
      correctAnswers: 10,
      difficultyBreakdown: {
        attempted: { easy: 6, medium: 2, hard: 2 },
        correct: { easy: 6, medium: 2, hard: 2 }
      }
    },
    coding: {
      title: 'Section 2: Coding Challenge',
      totalScore: 32,
      timeTaken: 103,
      submittedQuestions: 3,
      totalQuestions: 4,
      totalCorrect: 2,
      partiallyCorrect: 1,
      result: 'Power coder'
    },
    systemDesign: {
      title: 'Section 3: System Design',
      totalScore: 32,
      timeTaken: 103,
      summary: 'Strong architectural thinking with attention to scalability. Consider exploring more microservices patterns.',
      strengths: [
        'Well-structured system architecture',
        'Good understanding of database design patterns'
      ],
      improvements: [
        'Explore more advanced caching strategies',
        'Deep dive into event-driven architecture patterns'
      ]
    }
  },
  integrity: {
    level: 'High',
    fullscreenExits: 3,
    multipleFaceDetection: 0,
    noFaceDetected: 2,
    objectDetection: 1
  }
};

const AnalysisPage = () => {
  const { user, logout } = useAuth();
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());

  const handleLogout = () => {
    logout();
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
    switch (section) {
      case 'mcq':
        return (
          <div className="space-y-6">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
                <span className="text-lg font-semibold text-gray-700">Total Score: {analysisData.sections.mcq.totalScore}</span>
              </div>
              <div className="flex items-center gap-2">
                <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="text-lg font-semibold text-gray-700">Time Taken: {analysisData.sections.mcq.timeTaken} mins</span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-6">
              {renderDonutChart(
                analysisData.sections.mcq.difficultyBreakdown.attempted,
                `Total attempted questions: ${analysisData.sections.mcq.totalAttempted}/${analysisData.sections.mcq.totalQuestions}`
              )}
              {renderDonutChart(
                analysisData.sections.mcq.difficultyBreakdown.correct,
                `Correct answers: ${analysisData.sections.mcq.correctAnswers}`
              )}
            </div>
          </div>
        );

      case 'coding':
        return (
          <div className="space-y-6">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <div className="w-10 h-10 bg-yellow-100 rounded-full flex items-center justify-center flex-shrink-0">
                  <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                </div>
                <span className="text-lg font-semibold text-gray-700">Total Score: {analysisData.sections.coding.totalScore}</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-10 h-10 bg-yellow-100 rounded-full flex items-center justify-center flex-shrink-0">
                  <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <span className="text-lg font-semibold text-gray-700">Time Taken: {analysisData.sections.coding.timeTaken} mins</span>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div>
                <span className="text-base font-semibold text-gray-700">Submitted questions: </span>
                <span className="text-base text-gray-900">{analysisData.sections.coding.submittedQuestions}/{analysisData.sections.coding.totalQuestions}</span>
              </div>
              <div>
                <span className="text-base font-semibold text-gray-700">Total correct answers: </span>
                <span className="text-base text-gray-900">{analysisData.sections.coding.totalCorrect}</span>
              </div>
              <div>
                <span className="text-base font-semibold text-gray-700">Partially correct answers: </span>
                <span className="text-base text-gray-900">{analysisData.sections.coding.partiallyCorrect}</span>
              </div>
            </div>

            <div>
              <span className="text-base font-semibold text-gray-700">Result: </span>
              <span className="text-lg font-bold text-green-600">{analysisData.sections.coding.result}</span>
            </div>
          </div>
        );

      case 'system-design':
        return (
          <div className="space-y-6">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
                <span className="text-lg font-semibold text-gray-700">Total Score: {analysisData.sections.systemDesign.totalScore}</span>
              </div>
              <div className="flex items-center gap-2">
                <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="text-lg font-semibold text-gray-700">Time Taken: {analysisData.sections.systemDesign.timeTaken} mins</span>
              </div>
            </div>

            <div className="bg-purple-100 rounded-lg p-6 shadow-sm">
              <div className="flex items-start gap-3 mb-4">
                <div className="w-10 h-10 bg-orange-500 rounded-full flex items-center justify-center flex-shrink-0">
                  <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                  </svg>
                </div>
                <h3 className="text-lg font-bold text-gray-900">Summary</h3>
              </div>
              <p className="text-gray-700 leading-relaxed">{analysisData.sections.systemDesign.summary}</p>
            </div>

            <div className="grid grid-cols-2 gap-6">
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
                  {analysisData.sections.systemDesign.strengths.map((strength, index) => (
                    <li key={index} className="flex items-start gap-2">
                      <svg className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      <span className="text-gray-700">{strength}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="bg-white rounded-lg p-6 shadow-sm">
                <div className="flex items-start gap-3 mb-4">
                  <div className="w-10 h-10 bg-orange-500 rounded-full flex items-center justify-center flex-shrink-0">
                    <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                  </div>
                  <h3 className="text-lg font-bold text-gray-900">Areas for Improvement</h3>
                </div>
                <ul className="space-y-2">
                  {analysisData.sections.systemDesign.improvements.map((improvement, index) => (
                    <li key={index} className="flex items-start gap-2">
                      <svg className="w-5 h-5 text-orange-500 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <span className="text-gray-700">{improvement}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        );

      case 'integrity':
        return (
          <div className="space-y-6">
            <div className="bg-white rounded-lg p-6 shadow-sm">
              <div className="flex items-center gap-2 mb-4">
                <span className="text-lg font-semibold text-gray-700">Integrity: </span>
                <span className="text-lg font-bold text-green-600">{analysisData.integrity.level}</span>
              </div>
              <div className="space-y-3">
                <div>
                  <span className="text-base font-semibold text-gray-700">Fullscreen exits: </span>
                  <span className="text-base text-gray-900">{analysisData.integrity.fullscreenExits}</span>
                </div>
                <div>
                  <span className="text-base font-semibold text-gray-700">Multiple face detection: </span>
                  <span className="text-base text-gray-900">{analysisData.integrity.multipleFaceDetection}</span>
                </div>
                <div>
                  <span className="text-base font-semibold text-gray-700">No face detected: </span>
                  <span className="text-base text-gray-900">{analysisData.integrity.noFaceDetected}</span>
                </div>
                <div>
                  <span className="text-base font-semibold text-gray-700">Object detection: </span>
                  <span className="text-base text-gray-900">{analysisData.integrity.objectDetection}</span>
                </div>
              </div>
            </div>
          </div>
        );

      default:
        return null;
    }
  };


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
            <p className="text-base text-gray-600">
              Assessment completed on {analysisData.assessment.date} at {analysisData.assessment.time}
            </p>
          </div>
          
          {/* Separator Line */}
          <div className="border-t border-gray-300 mb-4"></div>

          {/* Result */}
          <div className="mb-6">
            <span className="text-lg font-semibold text-gray-700">Result: </span>
            <span className="text-lg font-bold text-green-600">{analysisData.assessment.verdict}</span>
          </div>

          {/* Summary */}
          <div className="bg-white rounded-lg p-6 mb-6 shadow-sm">
            <div className="flex items-start gap-3 mb-4">
              <div className="w-10 h-10 bg-orange-500 rounded-full flex items-center justify-center flex-shrink-0">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                </svg>
              </div>
              <h2 className="text-xl font-bold text-gray-900">Summary</h2>
            </div>
            <p className="text-gray-700 leading-relaxed">{analysisData.assessment.summary}</p>
          </div>

          {/* Section Analysis */}
          <div className="mb-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Section Analysis</h2>

            {/* Section 1: Multiple Choice */}
            <div className="bg-white rounded-lg shadow-sm mb-3">
              <button
                onClick={() => handleSectionClick('mcq')}
                className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
              >
                <span className="text-lg font-semibold text-gray-900">{analysisData.sections.mcq.title}</span>
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

            {/* Section 2: Coding Challenge */}
            <div className="bg-white rounded-lg shadow-sm mb-3">
              <button
                onClick={() => handleSectionClick('coding')}
                className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
              >
                <span className="text-lg font-semibold text-gray-900">{analysisData.sections.coding.title}</span>
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

            {/* Section 3: System Design */}
            <div className="bg-white rounded-lg shadow-sm mb-3">
              <button
                onClick={() => handleSectionClick('system-design')}
                className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
              >
                <span className="text-lg font-semibold text-gray-900">{analysisData.sections.systemDesign.title}</span>
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

            {/* Integrity */}
            <div className="bg-white rounded-lg shadow-sm">
              <button
                onClick={() => handleSectionClick('integrity')}
                className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <span className="text-lg font-semibold text-gray-900">Integrity: </span>
                  <span className="text-lg font-semibold text-green-600">{analysisData.integrity.level}</span>
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
          </div>
        </div>

        {/* Candidate Info Panel */}
        <div className="w-80 bg-white rounded-lg p-6 shadow-sm h-fit">
          <div className="flex flex-col items-center mb-6">
            <div className="w-24 h-24 bg-yellow-400 rounded-full flex items-center justify-center mb-4 relative">
              <span className="text-3xl font-bold text-gray-800">{analysisData.candidate.avatar}</span>
              <div className="absolute bottom-0 right-0 w-6 h-6 bg-green-500 rounded-full border-2 border-white"></div>
            </div>
          </div>
          <div className="space-y-3">
            <div>
              <span className="text-sm font-semibold text-gray-600">Name: </span>
              <span className="text-base font-bold text-gray-900">{analysisData.candidate.name}</span>
            </div>
            <div>
              <span className="text-sm font-semibold text-gray-600">Role: </span>
              <span className="text-base font-bold text-gray-900">{analysisData.candidate.role}</span>
            </div>
            <div>
              <span className="text-sm font-semibold text-gray-600">Score: </span>
              <span className="text-base font-bold text-gray-900">{analysisData.candidate.score}</span>
            </div>
            <div>
              <span className="text-sm font-semibold text-gray-600">Integrity: </span>
              <span className="text-base font-bold text-green-600">{analysisData.candidate.integrity}</span>
            </div>
            <div>
              <span className="text-sm font-semibold text-gray-600">Test time: </span>
              <span className="text-base font-bold text-gray-900">{analysisData.candidate.testTime} mins</span>
            </div>
          </div>
        </div>
      </div>

      <Footer />
    </div>
  );
};

export default AnalysisPage;

