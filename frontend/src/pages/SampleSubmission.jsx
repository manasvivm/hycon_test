import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import showToast from '../utils/toast';

const API_BASE_URL = 'http://localhost:8000';

function SampleSubmission() {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState({
    project: '',
    sample_name: '',
    batch_no: '',
    label_claim: '',
    sample_quantity: '',
    packaging_configuration: '',
    recommended_storage: '',
    condition: '',
    tests_to_be_performed: '',
    remarks: '',
    submitted_to: '',
    submitted_by: '',
    recipient_email: ''
  });

  // Fetch email recipients
  const { data: recipients = [], isLoading: recipientsLoading } = useQuery({
    queryKey: ['email-recipients'],
    queryFn: async () => {
      const response = await axios.get(`${API_BASE_URL}/samples/recipients`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      return response.data;
    }
  });

  // Submit mutation
  const submitMutation = useMutation({
    mutationFn: async (data) => {
      const response = await axios.post(`${API_BASE_URL}/samples/submit`, data, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries(['sample-submissions']);
      // Reset form
      setFormData({
        project: '',
        sample_name: '',
        batch_no: '',
        label_claim: '',
        sample_quantity: '',
        packaging_configuration: '',
        recommended_storage: '',
        condition: '',
        tests_to_be_performed: '',
        remarks: '',
        submitted_to: '',
        submitted_by: '',
        recipient_email: ''
      });
      
      // Show success message with toast
      showToast(
        `Sample submission successful! Email sent to ${formData.recipient_email}. Submission ID: ${data.id}`,
        'success'
      );
      
      // Also show an alert for important confirmation
      setTimeout(() => {
        alert(`✅ Sample Submission Successful!\n\n📧 Email sent successfully to: ${formData.recipient_email}\n\nSubmission ID: ${data.id}\nProject: ${data.project}\nSample: ${data.sample_name}`);
      }, 500);
    },
    onError: (error) => {
      const errorDetail = error.response?.data?.detail || 'Failed to submit sample';
      
      // Check if it's an email sending error
      if (errorDetail.includes('email') || errorDetail.includes('SMTP')) {
        showToast('Submission saved but email failed to send. Check email configuration.', 'warning');
        setTimeout(() => {
          alert(`⚠️ Submission Saved but Email Failed!\n\nThe sample submission was saved to the database, but the email could not be sent.\n\nError: ${errorDetail}\n\nPlease check your email configuration or contact the administrator.`);
        }, 500);
      } else {
        showToast(`Submission failed: ${errorDetail}`, 'error');
        setTimeout(() => {
          alert(`❌ Submission Failed!\n\nError: ${errorDetail}\n\nPlease try again or contact the administrator.`);
        }, 500);
      }
    }
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    
    // Validation
    const requiredFields = [
      'project', 'sample_name', 'batch_no', 'label_claim', 
      'sample_quantity', 'packaging_configuration', 'recommended_storage',
      'condition', 'tests_to_be_performed', 'submitted_to', 'submitted_by', 'recipient_email'
    ];
    
    for (const field of requiredFields) {
      if (!formData[field].trim()) {
        alert(`Please fill in: ${field.replace(/_/g, ' ').toUpperCase()}`);
        return;
      }
    }
    
    submitMutation.mutate(formData);
  };

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const formFields = [
    { name: 'project', label: '1. Project', placeholder: 'e.g., mCMR215', required: true },
    { name: 'sample_name', label: '2. Sample Name', placeholder: 'e.g., 215/MS-06 & 215/MS-07', required: true },
    { name: 'batch_no', label: '3. Batch No./ Lot No.', placeholder: 'e.g., CBR-001-861-151-3', required: true },
    { name: 'label_claim', label: '4. Label claim', placeholder: 'e.g., 215/MS-06: 10 mg/mL', required: true },
    { name: 'sample_quantity', label: '5. Sample Quantity', placeholder: 'e.g., 1.5 mL each', required: true },
    { name: 'packaging_configuration', label: '6. Packaging configuration', placeholder: 'e.g., Glass vial with screw cap', required: true },
    { name: 'recommended_storage', label: '7. Recommended storage', placeholder: 'e.g., RT, 2-8°C, -20°C', required: true },
    { name: 'condition', label: '8. Condition', placeholder: 'e.g., Initial, Accelerated, Long-term', required: true },
    { name: 'tests_to_be_performed', label: '9. Tests to be performed', placeholder: 'e.g., 1. Solubility 2. RS', required: true, multiline: true },
    { name: 'remarks', label: '10. Remarks (if any)', placeholder: 'Optional remarks', required: false, multiline: true },
    { name: 'submitted_to', label: '11. Submitted to (Name & Dept)', placeholder: 'e.g., Shruti & ARD', required: true },
    { name: 'submitted_by', label: '12. Submitted by (Name & Dept)', placeholder: 'e.g., Rudransh & PFD', required: true },
  ];

  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-white rounded-lg shadow-xl overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-teal-600 to-teal-700 text-white px-8 py-6">
          <h1 className="text-3xl font-bold">📋 INTERNAL SAMPLE SUBMISSION FORM</h1>
          <p className="text-teal-100 mt-2">Fill out all required fields and submit to send email notification</p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-8">
          <div className="space-y-6">
            {formFields.map((field) => (
              <div key={field.name} className="group">
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  {field.label}
                  {field.required && <span className="text-red-500 ml-1">*</span>}
                </label>
                {field.multiline ? (
                  <textarea
                    name={field.name}
                    value={formData[field.name]}
                    onChange={handleChange}
                    placeholder={field.placeholder}
                    rows="3"
                    className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500 transition-all"
                    required={field.required}
                  />
                ) : (
                  <input
                    type="text"
                    name={field.name}
                    value={formData[field.name]}
                    onChange={handleChange}
                    placeholder={field.placeholder}
                    className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500 transition-all"
                    required={field.required}
                  />
                )}
              </div>
            ))}

            {/* Email Recipient Dropdown */}
            <div className="group">
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Send Email To
                <span className="text-red-500 ml-1">*</span>
              </label>
              {recipientsLoading ? (
                <div className="text-gray-500">Loading recipients...</div>
              ) : (
                <select
                  name="recipient_email"
                  value={formData.recipient_email}
                  onChange={handleChange}
                  className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500 transition-all"
                  required
                >
                  <option value="">-- Select Recipient --</option>
                  {recipients.map((recipient) => (
                    <option key={recipient.id} value={recipient.email}>
                      {recipient.name} {recipient.department && `(${recipient.department})`}
                    </option>
                  ))}
                </select>
              )}
            </div>
          </div>

          {/* Submit Button */}
          <div className="mt-8 flex gap-4">
            <button
              type="submit"
              disabled={submitMutation.isPending}
              className="flex-1 bg-gradient-to-r from-teal-600 to-teal-700 text-white px-8 py-4 rounded-lg font-semibold text-lg hover:from-teal-700 hover:to-teal-800 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-xl transition-all duration-200"
            >
              {submitMutation.isPending ? '📧 Sending...' : '📧 Submit & Send Email'}
            </button>
            <button
              type="button"
              onClick={() => setFormData({
                project: '',
                sample_name: '',
                batch_no: '',
                label_claim: '',
                sample_quantity: '',
                packaging_configuration: '',
                recommended_storage: '',
                condition: '',
                tests_to_be_performed: '',
                remarks: '',
                submitted_to: '',
                submitted_by: '',
                recipient_email: ''
              })}
              className="px-6 py-4 border-2 border-gray-300 text-gray-700 rounded-lg font-semibold hover:bg-gray-50 transition-all"
            >
              Clear Form
            </button>
          </div>
        </form>
      </div>

      {/* Info Box */}
      <div className="mt-6 bg-blue-50 border-l-4 border-blue-500 p-4 rounded-r-lg">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <p className="text-sm text-blue-700">
              <strong>Note:</strong> Upon submission, a beautifully formatted email will be sent to the selected recipient with all form details. 
              The submission will also be saved in the database for record-keeping.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default SampleSubmission;
