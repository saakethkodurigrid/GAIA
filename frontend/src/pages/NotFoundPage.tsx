import { useNavigate } from 'react-router-dom';
import Header from '../components/Header';
import Footer from '../components/Footer';

const NotFoundPage = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex flex-col">
      {/* Header */}
      <Header showTechInterviewLogo={true} />

      {/* Main Content */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="max-w-2xl w-full text-center">
          <div className="bg-white rounded-2xl shadow-2xl p-12">
            {/* 404 Icon */}
            <div className="mb-8">
              <div className="text-9xl font-bold text-gray-300 mb-4">404</div>
              <div className="w-24 h-1 bg-gradient-to-r from-blue-500 to-indigo-500 mx-auto rounded-full"></div>
            </div>

            {/* Message */}
            <h1 className="text-4xl font-bold text-gray-900 mb-4">
              Page Not Found
            </h1>
            <p className="text-xl text-gray-600 mb-2">
              Oops! It looks like you've navigated to a page that doesn't exist.
            </p>
            <p className="text-lg text-gray-500 mb-8">
              The page you're looking for may have been moved, deleted, or the URL might be incorrect.
            </p>

            {/* Action Button */}
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <button
                onClick={() => navigate('/')}
                className="px-8 py-3 bg-blue-600 text-white rounded-lg font-semibold text-lg hover:bg-blue-700 transition-colors shadow-md"
              >
                Go to Home
              </button>
              <button
                onClick={() => navigate(-1)}
                className="px-8 py-3 bg-gray-200 text-gray-700 rounded-lg font-semibold text-lg hover:bg-gray-300 transition-colors shadow-md"
              >
                Go Back
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <Footer />
    </div>
  );
};

export default NotFoundPage;

