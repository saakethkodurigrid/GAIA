import { useState } from 'react';
import { addRecruiterAdmin } from '../api/admin.api';
import { isTokenExpiredError } from '../utils/apiErrorHandler';
import { useAuth } from '../context/AuthContext';

interface AddRecruiterAdminModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

const AddRecruiterAdminModal = ({ isOpen, onClose, onSuccess }: AddRecruiterAdminModalProps) => {
  const { logout } = useAuth();
  const [formData, setFormData] = useState({
    email_id: '',
    name: '',
    role_id: 1, // Default to Recruiter
    phone_number: '',
    location: '',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  if (!isOpen) return null;

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: name === 'role_id' ? parseInt(value, 10) : value,
    }));
    // Clear error when user starts typing
    if (error) setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);
    setSuccess(false);

    // Validate required fields
    if (!formData.email_id || !formData.name) {
      setError('Email and Name are required fields.');
      setIsSubmitting(false);
      return;
    }

    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(formData.email_id)) {
      setError('Please enter a valid email address.');
      setIsSubmitting(false);
      return;
    }

    try {
      const requestData = {
        email_id: formData.email_id.trim(),
        name: formData.name.trim(),
        role_id: formData.role_id,
        phone_number: formData.phone_number.trim() || undefined,
        location: formData.location.trim() || undefined,
      };

      const response = await addRecruiterAdmin(requestData);

      if (response.success) {
        setSuccess(true);
        // Reset form
        setFormData({
          email_id: '',
          name: '',
          role_id: 1,
          phone_number: '',
          location: '',
        });
        // Call onSuccess callback if provided
        if (onSuccess) {
          setTimeout(() => {
            onSuccess();
            onClose();
            setSuccess(false);
          }, 1500);
        } else {
          setTimeout(() => {
            onClose();
            setSuccess(false);
          }, 1500);
        }
      } else {
        setError(response.message || 'Failed to add recruiter/admin');
      }
    } catch (err) {
      // Check if it's a token expiration error
      if (isTokenExpiredError(err)) {
        console.log('Token expired, logging out...');
        logout();
        return;
      }

      const errorMessage = err instanceof Error ? err.message : 'Failed to add recruiter/admin. Please try again.';
      setError(errorMessage);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    if (!isSubmitting) {
      setFormData({
        email_id: '',
        name: '',
        role_id: 1,
        phone_number: '',
        location: '',
      });
      setError(null);
      setSuccess(false);
      onClose();
    }
  };

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[1000]"
      onClick={handleClose}
    >
      <div
        className="bg-white rounded-xl p-8 max-w-[600px] w-[90%] max-h-[90vh] overflow-y-auto shadow-[0_10px_25px_rgba(0,0,0,0.2)]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 bg-purple-100 rounded-full flex items-center justify-center flex-shrink-0">
            <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
          </div>
          <h2 className="text-2xl font-semibold text-gray-800">Add Recruiter/Admin</h2>
        </div>

        {/* Success Message */}
        {success && (
          <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-lg text-green-700">
            <div className="flex items-center gap-2">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <span>Recruiter/Admin added successfully!</span>
            </div>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            <div className="flex items-center gap-2">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>{error}</span>
            </div>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Email */}
          <div>
            <label htmlFor="email_id" className="block text-sm font-medium text-gray-700 mb-1">
              Email <span className="text-red-500">*</span>
            </label>
            <input
              type="email"
              id="email_id"
              name="email_id"
              value={formData.email_id}
              onChange={handleInputChange}
              required
              disabled={isSubmitting}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
              placeholder="recruiter@example.com"
            />
          </div>

          {/* Name */}
          <div>
            <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
              Full Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              id="name"
              name="name"
              value={formData.name}
              onChange={handleInputChange}
              required
              disabled={isSubmitting}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
              placeholder="John Doe"
            />
          </div>

          {/* Role */}
          <div>
            <label htmlFor="role_id" className="block text-sm font-medium text-gray-700 mb-1">
              Role <span className="text-red-500">*</span>
            </label>
            <select
              id="role_id"
              name="role_id"
              value={formData.role_id}
              onChange={handleInputChange}
              required
              disabled={isSubmitting}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
            >
              <option value={1}>Recruiter</option>
              <option value={2}>Admin</option>
            </select>
          </div>

          {/* Phone Number */}
          <div>
            <label htmlFor="phone_number" className="block text-sm font-medium text-gray-700 mb-1">
              Phone Number <span className="text-gray-400 text-xs">(Optional)</span>
            </label>
            <input
              type="tel"
              id="phone_number"
              name="phone_number"
              value={formData.phone_number}
              onChange={handleInputChange}
              disabled={isSubmitting}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
              placeholder="+1234567890"
            />
          </div>

          {/* Location */}
          <div>
            <label htmlFor="location" className="block text-sm font-medium text-gray-700 mb-1">
              Location <span className="text-gray-400 text-xs">(Optional)</span>
            </label>
            <input
              type="text"
              id="location"
              name="location"
              value={formData.location}
              onChange={handleInputChange}
              disabled={isSubmitting}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
              placeholder="New York, USA"
            />
          </div>

          {/* Action Buttons */}
          <div className="flex justify-end gap-4 pt-4">
            <button
              type="button"
              onClick={handleClose}
              disabled={isSubmitting}
              className="px-6 py-3 bg-gray-100 border border-gray-300 rounded-lg text-base font-medium cursor-pointer transition-all hover:bg-gray-200 text-gray-900 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || success}
              className="px-6 py-3 bg-yellow-400 text-gray-900 rounded-lg text-base font-medium cursor-pointer transition-colors hover:bg-yellow-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? 'Adding...' : success ? 'Added!' : 'Add Recruiter/Admin'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default AddRecruiterAdminModal;

