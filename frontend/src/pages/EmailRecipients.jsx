import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import showToast from '../utils/toast';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function EmailRecipients() {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const [isAddingNew, setIsAddingNew] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    department: '',
    is_active: true
  });

  // Fetch recipients
  const { data: recipients = [], isLoading } = useQuery({
    queryKey: ['email-recipients-admin'],
    queryFn: async () => {
      const response = await axios.get(`${API_BASE_URL}/samples/recipients?active_only=false`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      return response.data;
    }
  });

  // Create mutation
  const createMutation = useMutation({
    mutationFn: async (data) => {
      const response = await axios.post(`${API_BASE_URL}/samples/recipients`, data, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries(['email-recipients-admin']);
      queryClient.invalidateQueries(['email-recipients']);
      resetForm();
      showToast(`Email recipient "${data.name}" added successfully!`, 'success');
    },
    onError: (error) => {
      showToast(error.response?.data?.detail || 'Failed to add recipient', 'error');
    }
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: async ({ id, data }) => {
      const response = await axios.put(`${API_BASE_URL}/samples/recipients/${id}`, data, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries(['email-recipients-admin']);
      queryClient.invalidateQueries(['email-recipients']);
      resetForm();
      showToast(`Email recipient "${data.name}" updated successfully!`, 'success');
    },
    onError: (error) => {
      showToast(error.response?.data?.detail || 'Failed to update recipient', 'error');
    }
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: async (id) => {
      await axios.delete(`${API_BASE_URL}/samples/recipients/${id}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['email-recipients-admin']);
      queryClient.invalidateQueries(['email-recipients']);
      showToast('Email recipient deleted successfully!', 'success');
    },
    onError: (error) => {
      showToast(error.response?.data?.detail || 'Failed to delete recipient', 'error');
    }
  });

  const resetForm = () => {
    setFormData({ name: '', email: '', department: '', is_active: true });
    setIsAddingNew(false);
    setEditingId(null);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (editingId) {
      updateMutation.mutate({ id: editingId, data: formData });
    } else {
      createMutation.mutate(formData);
    }
  };

  const handleEdit = (recipient) => {
    setFormData({
      name: recipient.name,
      email: recipient.email,
      department: recipient.department || '',
      is_active: recipient.is_active
    });
    setEditingId(recipient.id);
    setIsAddingNew(true);
  };

  const handleDelete = (id) => {
    if (window.confirm('Are you sure you want to delete this email recipient?')) {
      deleteMutation.mutate(id);
    }
  };

  if (isLoading) {
    return <div className="text-center py-12">Loading...</div>;
  }

  return (
    <div className="max-w-6xl mx-auto">
      <div className="bg-white rounded-lg shadow-xl overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-teal-600 to-teal-700 text-white px-8 py-6 flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold">✉️ Email Recipients Management</h1>
            <p className="text-teal-100 mt-2">Manage email addresses for sample submission notifications</p>
          </div>
          {!isAddingNew && (
            <button
              onClick={() => setIsAddingNew(true)}
              className="bg-white text-teal-700 px-6 py-3 rounded-lg font-semibold hover:bg-teal-50 transition-all shadow-lg"
            >
              + Add New Recipient
            </button>
          )}
        </div>

        {/* Add/Edit Form */}
        {isAddingNew && (
          <div className="p-8 bg-gray-50 border-b-2 border-teal-200">
            <h3 className="text-xl font-bold mb-4">{editingId ? 'Edit Recipient' : 'Add New Recipient'}</h3>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    Name <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="e.g., Shruti & ARD"
                    className="w-full px-4 py-2 border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    Email <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    placeholder="e.g., shruti.ard@company.com"
                    className="w-full px-4 py-2 border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
                    required
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    Department
                  </label>
                  <input
                    type="text"
                    value={formData.department}
                    onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                    placeholder="e.g., ARD Department"
                    className="w-full px-4 py-2 border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    Status
                  </label>
                  <select
                    value={formData.is_active}
                    onChange={(e) => setFormData({ ...formData, is_active: e.target.value === 'true' })}
                    className="w-full px-4 py-2 border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
                  >
                    <option value="true">Active</option>
                    <option value="false">Inactive</option>
                  </select>
                </div>
              </div>
              <div className="flex gap-3">
                <button
                  type="submit"
                  disabled={createMutation.isPending || updateMutation.isPending}
                  className="bg-teal-600 text-white px-6 py-2 rounded-lg font-semibold hover:bg-teal-700 disabled:opacity-50 transition-all"
                >
                  {editingId ? 'Update Recipient' : 'Add Recipient'}
                </button>
                <button
                  type="button"
                  onClick={resetForm}
                  className="bg-gray-300 text-gray-700 px-6 py-2 rounded-lg font-semibold hover:bg-gray-400 transition-all"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Recipients Table */}
        <div className="p-8">
          <table className="w-full">
            <thead>
              <tr className="border-b-2 border-gray-200">
                <th className="text-left py-3 px-4 font-semibold text-gray-700">Name</th>
                <th className="text-left py-3 px-4 font-semibold text-gray-700">Email</th>
                <th className="text-left py-3 px-4 font-semibold text-gray-700">Department</th>
                <th className="text-left py-3 px-4 font-semibold text-gray-700">Status</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">Actions</th>
              </tr>
            </thead>
            <tbody>
              {recipients.length === 0 ? (
                <tr>
                  <td colSpan="5" className="text-center py-8 text-gray-500">
                    No email recipients found. Add one to get started!
                  </td>
                </tr>
              ) : (
                recipients.map((recipient) => (
                  <tr key={recipient.id} className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
                    <td className="py-4 px-4 font-medium">{recipient.name}</td>
                    <td className="py-4 px-4 text-gray-600">{recipient.email}</td>
                    <td className="py-4 px-4 text-gray-600">{recipient.department || '-'}</td>
                    <td className="py-4 px-4">
                      <span className={`inline-block px-3 py-1 rounded-full text-xs font-semibold ${
                        recipient.is_active 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-gray-100 text-gray-800'
                      }`}>
                        {recipient.is_active ? '✓ Active' : '✗ Inactive'}
                      </span>
                    </td>
                    <td className="py-4 px-4 text-right">
                      <button
                        onClick={() => handleEdit(recipient)}
                        className="text-blue-600 hover:text-blue-800 font-semibold mr-4"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDelete(recipient.id)}
                        className="text-red-600 hover:text-red-800 font-semibold"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Info Box */}
      <div className="mt-6 bg-yellow-50 border-l-4 border-yellow-500 p-4 rounded-r-lg">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <p className="text-sm text-yellow-700">
              <strong>Note:</strong> These email addresses will appear in the dropdown when submitting samples. 
              Make sure to use valid email addresses. Inactive recipients won't appear in the dropdown but are kept for records.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default EmailRecipients;
