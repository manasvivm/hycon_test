import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import showToast from '../utils/toast';

const API_BASE_URL = 'http://localhost:8000';

function SampleSubmission() {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const [searchQuery, setSearchQuery] = useState('');  // Add search state
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
    recipient_emails: []  // Changed to array for multiple recipients
  });

  // Fetch all users (employees) for the dropdown
  const { data: users = [], isLoading: usersLoading } = useQuery({
    queryKey: ['all-users'],
    queryFn: async () => {
      const response = await axios.get(`${API_BASE_URL}/auth/users`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      return response.data;
    }
  });

  // Fetch additional email recipients (admin-added external emails)
  const { data: customRecipients = [], isLoading: recipientsLoading } = useQuery({
    queryKey: ['email-recipients'],
    queryFn: async () => {
      const response = await axios.get(`${API_BASE_URL}/samples/recipients`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      return response.data;
    }
  });

  // Combine both lists for the dropdown
  const allRecipients = [
    ...users.map(user => ({
      id: `user-${user.id}`,
      name: user.name,
      email: user.email,
      department: user.role === 'admin' ? '🔑 Admin' : '👤 Employee',
      source: 'employee'
    })),
    ...customRecipients.map(recipient => ({
      id: `custom-${recipient.id}`,
      name: recipient.name,
      email: recipient.email,
      department: recipient.department || '📧 Custom Recipient',
      source: 'custom'
    }))
  ];

  // Filter recipients based on search query
  const filteredRecipients = allRecipients.filter(recipient => 
    recipient.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    recipient.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
    recipient.department.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const isLoadingRecipients = usersLoading || recipientsLoading;

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
      const recipientCount = formData.recipient_emails.length;
      const recipientList = formData.recipient_emails.join(', ');
      
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
        recipient_emails: []
      });
      setSearchQuery('');  // Reset search
      
      // Show success message with toast
      showToast(
        `Sample submission successful! Sent to ${recipientCount} recipient${recipientCount > 1 ? 's' : ''}!`,
        'success'
      );
      
      // Also show an alert for important confirmation
      setTimeout(() => {
        alert(`✅ Sample Submission Successful!\n\n� Sent to ${recipientCount} recipient${recipientCount > 1 ? 's' : ''}:\n${recipientList}\n\nProject: ${formData.project}\nSample: ${formData.sample_name}\n\n${recipientCount} submission${recipientCount > 1 ? 's' : ''} created with unique reference numbers.`);
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
      'condition', 'tests_to_be_performed', 'submitted_to', 'submitted_by'
    ];
    
    for (const field of requiredFields) {
      if (!formData[field].trim()) {
        alert(`Please fill in: ${field.replace(/_/g, ' ').toUpperCase()}`);
        return;
      }
    }
    
    if (formData.recipient_emails.length === 0) {
      alert('Please select at least one recipient!');
      return;
    }
    
    submitMutation.mutate(formData);
  };

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  // Generate mailto link for email client
  const generateMailtoLink = (recipientEmail, data) => {
    const subject = encodeURIComponent(`Sample Submission: ${data.project || 'New Sample'}`);
    
    const body = encodeURIComponent(
`INTERNAL SAMPLE SUBMISSION FORM
================================

1. Project: ${data.project || ''}
2. Sample Name: ${data.sample_name || ''}
3. Batch No./Lot No.: ${data.batch_no || ''}
4. Label Claim: ${data.label_claim || ''}
5. Sample Quantity: ${data.sample_quantity || ''}
6. Packaging Configuration: ${data.packaging_configuration || ''}
7. Recommended Storage: ${data.recommended_storage || ''}
8. Condition: ${data.condition || ''}
9. Tests to be Performed:
${data.tests_to_be_performed || ''}
10. Remarks: ${data.remarks || 'N/A'}
11. Submitted to: ${data.submitted_to || ''}
12. Submitted by: ${data.submitted_by || ''}

---
This submission was created using HYCON Lab Management System.
Please review and process accordingly.`
    );
    
    return `mailto:${recipientEmail}?subject=${subject}&body=${body}`;
  };

  const handleSendViaEmail = () => {
    if (formData.recipient_emails.length === 0) {
      alert('Please select at least one recipient!');
      return;
    }
    
    // For multiple recipients, open email for the first one
    // (Browser limitation: mailto can't handle multiple recipients well with pre-filled body)
    const recipientEmail = formData.recipient_emails[0];
    const mailtoLink = generateMailtoLink(recipientEmail, formData);
    
    window.location.href = mailtoLink;
    
    if (formData.recipient_emails.length > 1) {
      alert(`Email client opened for ${recipientEmail}.\n\nNote: You selected ${formData.recipient_emails.length} recipients. Please send separate emails to:\n${formData.recipient_emails.slice(1).join('\n')}`);
    }
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
          <p className="text-teal-100 mt-2">Fill out all required fields and send to recipients</p>
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

            {/* Email Recipient Multi-Select with Search */}
            <div className="group">
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Send To (Select One or More Recipients)
                <span className="text-red-500 ml-1">*</span>
              </label>
              {isLoadingRecipients ? (
                <div className="text-gray-500">Loading recipients...</div>
              ) : (
                <>
                  {/* Search Box */}
                  <div className="mb-3">
                    <input
                      type="text"
                      placeholder="🔍 Search by name, email, or department..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="w-full px-4 py-2 border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
                    />
                    {searchQuery && (
                      <p className="text-xs text-gray-500 mt-1">
                        Found {filteredRecipients.length} recipient{filteredRecipients.length !== 1 ? 's' : ''}
                      </p>
                    )}
                  </div>

                  <select
                    multiple
                    size="8"
                    value={formData.recipient_emails}
                    onChange={(e) => {
                      const selected = Array.from(e.target.selectedOptions, option => option.value);
                      setFormData({ ...formData, recipient_emails: selected });
                    }}
                    className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500 transition-all"
                  >
                    {filteredRecipients.length === 0 ? (
                      <option disabled>No recipients found</option>
                    ) : (
                      filteredRecipients.map((recipient) => (
                        <option key={recipient.id} value={recipient.email} className="py-2">
                          {recipient.source === 'employee' ? '👤' : '📧'} {recipient.name} ({recipient.email}) {recipient.source === 'employee' && recipient.department.includes('Admin') ? '🔑' : ''}
                        </option>
                      ))
                    )}
                  </select>
                  <p className="text-sm text-gray-500 mt-2">
                    💡 Hold <kbd className="px-2 py-1 bg-gray-100 border rounded">Cmd/Ctrl</kbd> to select multiple recipients
                    {formData.recipient_emails.length > 0 && (
                      <span className="ml-2 text-teal-600 font-semibold">
                        ({formData.recipient_emails.length} selected)
                      </span>
                    )}
                  </p>
                  
                  {/* Selected recipients tags */}
                  {formData.recipient_emails.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {formData.recipient_emails.map((email) => {
                        const recipient = allRecipients.find(r => r.email === email);
                        return (
                          <span
                            key={email}
                            className="inline-flex items-center gap-1 px-3 py-1 bg-teal-100 text-teal-800 rounded-full text-sm"
                          >
                            {recipient?.name || email}
                            <button
                              type="button"
                              onClick={() => {
                                setFormData({
                                  ...formData,
                                  recipient_emails: formData.recipient_emails.filter(e => e !== email)
                                });
                              }}
                              className="ml-1 text-teal-600 hover:text-teal-900 font-bold"
                            >
                              ×
                            </button>
                          </span>
                        );
                      })}
                    </div>
                  )}
                </>
              )}
              <p className="text-xs text-gray-500 mt-2">
                💡 Choose any employee or custom recipient. Admins can add more custom recipients via Email Recipients Management.
              </p>
            </div>
          </div>

          {/* Submit Button */}
          <div className="mt-8 flex gap-4">
            <button
              type="submit"
              disabled={submitMutation.isPending}
              className="flex-1 bg-gradient-to-r from-teal-600 to-teal-700 text-white px-8 py-4 rounded-lg font-semibold text-lg hover:from-teal-700 hover:to-teal-800 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-xl transition-all duration-200"
            >
              {submitMutation.isPending ? '⏳ Sending...' : '📨 Send'}
            </button>
            <button
              type="button"
              onClick={handleSendViaEmail}
              disabled={formData.recipient_emails.length === 0}
              className="flex-1 bg-gradient-to-r from-green-600 to-green-700 text-white px-8 py-4 rounded-lg font-semibold text-lg hover:from-green-700 hover:to-green-800 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-xl transition-all duration-200 flex items-center justify-center gap-2"
              title="Open in your email client with pre-filled form"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" viewBox="0 0 20 20" fill="currentColor">
                <path d="M2.003 5.884L10 9.882l7.997-3.998A2 2 0 0016 4H4a2 2 0 00-1.997 1.884z" />
                <path d="M18 8.118l-8 4-8-4V14a2 2 0 002 2h12a2 2 0 002-2V8.118z" />
              </svg>
              Send via Email
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
