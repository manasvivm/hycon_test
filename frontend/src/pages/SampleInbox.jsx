import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import showToast from '../utils/toast';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function SampleInbox() {
  const { token, user } = useAuth();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState('inbox'); // 'inbox' or 'sent'
  const [selectedSubmission, setSelectedSubmission] = useState(null);
  const [replyMessage, setReplyMessage] = useState('');

  // Fetch inbox
  const { data: inboxData = [], isLoading: inboxLoading } = useQuery({
    queryKey: ['inbox'],
    queryFn: async () => {
      const response = await axios.get(`${API_BASE_URL}/samples/inbox`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      return response.data;
    },
    enabled: activeTab === 'inbox',
refetchInterval: 10000, // Auto-refresh every 10 seconds
    staleTime: 5000
  });

  // Fetch sent items
  const { data: sentData = [], isLoading: sentLoading } = useQuery({
    queryKey: ['sent-submissions'],
    queryFn: async () => {
      const response = await axios.get(`${API_BASE_URL}/samples/sent`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      return response.data;
    },
    enabled: activeTab === 'sent'
  });

  // Fetch unread count
  const { data: unreadCount = 0 } = useQuery({
    queryKey: ['unread-count'],
    queryFn: async () => {
      const response = await axios.get(`${API_BASE_URL}/samples/inbox/unread-count`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      return response.data.count;
    },
    refetchInterval: 30000 // Refresh every 30 seconds
  });

  // Mark as read mutation
  const markAsReadMutation = useMutation({
    mutationFn: async (submissionId) => {
      await axios.put(
        `${API_BASE_URL}/samples/${submissionId}/mark-read`,
        {},
        { headers: { 'Authorization': `Bearer ${token}` } }
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['inbox']);
      queryClient.invalidateQueries(['unread-count']);
    }
  });

  const handleSubmissionClick = (submission) => {
    setSelectedSubmission(submission);
    if (!submission.is_read && activeTab === 'inbox') {
      markAsReadMutation.mutate(submission.id);
    }
  };

  // Status change mutation
  const changeStatusMutation = useMutation({
    mutationFn: async ({ submissionId, newStatus, notes }) => {
      await axios.put(
        `${API_BASE_URL}/samples/${submissionId}/status`,
        null,
        { 
          params: { new_status: newStatus, notes },
          headers: { 'Authorization': `Bearer ${token}` }
        }
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['inbox']);
      queryClient.invalidateQueries(['sent-submissions']);
      showToast('Status updated successfully!', 'success');
    },
    onError: (error) => {
      showToast(`Failed to update status: ${error.response?.data?.detail || 'Unknown error'}`, 'error');
    }
  });

  const handleStatusChange = (newStatus) => {
    if (!selectedSubmission) return;
    
    const notes = prompt(`Change status to "${newStatus.toUpperCase()}".\n\nOptional notes:`);
    if (notes === null) return; // User cancelled
    
    changeStatusMutation.mutate({
      submissionId: selectedSubmission.id,
      newStatus,
      notes: notes || undefined
    });
    
    // Update local state optimistically
    setSelectedSubmission({ ...selectedSubmission, status: newStatus });
  };

  // Generate mailto link for forwarding submission
  const handleForwardViaEmail = (submission) => {
    const recipientEmail = activeTab === 'inbox' 
      ? (submission.submitted_by_user?.email || submission.submitted_by)
      : (submission.recipient_user?.email || submission.submitted_to);
    
    const subject = encodeURIComponent(`Re: Sample Submission #${submission.reference_number} - ${submission.project}`);
    
    const body = encodeURIComponent(
`SAMPLE SUBMISSION DETAILS
=========================

Reference Number: ${submission.reference_number}
Status: ${submission.status.toUpperCase()}

1. Project: ${submission.project || ''}
2. Sample Name: ${submission.sample_name || ''}
3. Batch No./Lot No.: ${submission.batch_no || ''}
4. Label Claim: ${submission.label_claim || ''}
5. Sample Quantity: ${submission.sample_quantity || ''}
6. Packaging Configuration: ${submission.packaging_configuration || ''}
7. Recommended Storage: ${submission.recommended_storage || ''}
8. Condition: ${submission.condition || ''}
9. Tests to be Performed:
${submission.tests_to_be_performed || ''}
10. Remarks: ${submission.remarks || 'N/A'}
11. Submitted to: ${submission.submitted_to || ''}
12. Submitted by: ${submission.submitted_by || ''}

Submitted on: ${new Date(submission.created_at).toLocaleString()}

---
This submission was retrieved from HYCON Lab Management System.`
    );
    
    window.location.href = `mailto:${recipientEmail}?subject=${subject}&body=${body}`;
  };

  const getStatusBadge = (status) => {
    const styles = {
      pending: 'bg-yellow-100 text-yellow-800 border-yellow-300',
      received: 'bg-blue-100 text-blue-800 border-blue-300',
      in_review: 'bg-purple-100 text-purple-800 border-purple-300',
      completed: 'bg-green-100 text-green-800 border-green-300',
      rejected: 'bg-red-100 text-red-800 border-red-300',
      archived: 'bg-gray-100 text-gray-800 border-gray-300'
    };
    
    const labels = {
      pending: 'Pending',
      received: 'Received',
      in_review: 'In Review',
      completed: 'Completed',
      rejected: 'Rejected',
      archived: 'Archived'
    };

    return (
      <span className={`px-3 py-1 rounded-full text-xs font-semibold border ${styles[status] || styles.pending}`}>
        {labels[status] || status}
      </span>
    );
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric',
      year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
    });
  };

  const currentData = activeTab === 'inbox' ? inboxData : sentData;
  const isLoading = activeTab === 'inbox' ? inboxLoading : sentLoading;

  return (
    <div className="max-w-7xl mx-auto">
      <div className="bg-white rounded-lg shadow-xl overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-teal-600 to-teal-700 text-white px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold">📬 Sample Submissions</h1>
              <p className="text-teal-100 mt-2">View and manage your sample submissions</p>
            </div>
            {unreadCount > 0 && activeTab === 'inbox' && (
              <div className="bg-white text-teal-700 px-4 py-2 rounded-full font-bold">
                {unreadCount} Unread
              </div>
            )}
          </div>
        </div>

        {/* Tabs */}
        <div className="border-b border-gray-200 bg-gray-50">
          <nav className="flex space-x-8 px-8">
            <button
              onClick={() => setActiveTab('inbox')}
              className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors relative ${
                activeTab === 'inbox'
                  ? 'border-teal-500 text-teal-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              📥 Inbox
              {unreadCount > 0 && (
                <span className="ml-2 bg-red-500 text-white text-xs rounded-full px-2 py-0.5">
                  {unreadCount}
                </span>
              )}
            </button>
            <button
              onClick={() => setActiveTab('sent')}
              className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === 'sent'
                  ? 'border-teal-500 text-teal-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              📤 Sent
            </button>
          </nav>
        </div>

        {/* Content */}
        <div className="flex">
          {/* List */}
          <div className="w-2/5 border-r border-gray-200 h-[calc(100vh-300px)] overflow-y-auto">
            {isLoading ? (
              <div className="p-8 text-center text-gray-500">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-teal-600 mx-auto"></div>
                <p className="mt-4">Loading submissions...</p>
              </div>
            ) : currentData.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                <div className="text-6xl mb-4">📭</div>
                <h3 className="text-lg font-semibold text-gray-700 mb-2">
                  {activeTab === 'inbox' ? 'No submissions in inbox' : 'No sent submissions'}
                </h3>
                <p className="text-sm">
                  {activeTab === 'inbox' 
                    ? 'When someone sends you a submission, it will appear here.'
                    : 'Submissions you send will appear here.'}
                </p>
              </div>
            ) : (
              <div className="divide-y divide-gray-200">
                {currentData.map((submission) => (
                  <div
                    key={submission.id}
                    onClick={() => handleSubmissionClick(submission)}
                    className={`p-4 cursor-pointer hover:bg-gray-50 transition-colors ${
                      selectedSubmission?.id === submission.id ? 'bg-teal-50 border-l-4 border-teal-500' : ''
                    } ${
                      !submission.is_read && activeTab === 'inbox' ? 'bg-blue-50' : ''
                    }`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center space-x-2">
                        {!submission.is_read && activeTab === 'inbox' && (
                          <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                        )}
                        <span className="font-semibold text-gray-900 text-sm">
                          {activeTab === 'inbox' 
                            ? (submission.submitted_by_user?.name || submission.submitted_by)
                            : (submission.recipient_user?.name || submission.submitted_to)
                          }
                        </span>
                      </div>
                      <span className="text-xs text-gray-500">
                        {formatDate(submission.created_at)}
                      </span>
                    </div>
                    <div className="mb-2">
                      <span className="text-xs text-gray-500 font-mono">
                        {submission.reference_number}
                      </span>
                    </div>
                    <h4 className="font-medium text-gray-800 text-sm mb-1">
                      {submission.project}
                    </h4>
                    <p className="text-xs text-gray-600 truncate">
                      {submission.sample_name}
                    </p>
                    <div className="mt-2">
                      {getStatusBadge(submission.status)}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Detail View */}
          <div className="w-3/5 p-8 h-[calc(100vh-300px)] overflow-y-auto">
            {!selectedSubmission ? (
              <div className="flex items-center justify-center h-full text-gray-400">
                <div className="text-center">
                  <div className="text-6xl mb-4">📋</div>
                  <p>Select a submission to view details</p>
                </div>
              </div>
            ) : (
              <div>
                {/* Header */}
                <div className="mb-6 pb-4 border-b border-gray-200">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1">
                      <h2 className="text-2xl font-bold text-gray-900 mb-2">
                        {selectedSubmission.project}
                      </h2>
                      <div className="flex items-center space-x-3">
                        {getStatusBadge(selectedSubmission.status)}
                        <span className="text-sm text-gray-500 font-mono">
                          {selectedSubmission.reference_number}
                        </span>
                      </div>
                    </div>
                    
                    {/* Status Change Dropdown (only for inbox/recipient) */}
                    {activeTab === 'inbox' && (
                      <div className="ml-4">
                        <label className="block text-xs font-semibold text-gray-600 mb-1">
                          Change Status
                        </label>
                        <select
                          value={selectedSubmission.status}
                          onChange={(e) => handleStatusChange(e.target.value)}
                          className="px-3 py-2 border-2 border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
                        >
                          <option value="pending">⏳ Pending</option>
                          <option value="received">✅ Received</option>
                          <option value="in_review">🔍 In Review</option>
                          <option value="completed">✔️ Completed</option>
                          <option value="rejected">❌ Rejected</option>
                          <option value="archived">📦 Archived</option>
                        </select>
                      </div>
                    )}
                  </div>
                  <div className="text-sm text-gray-600">
                    <p>
                      <span className="font-semibold">
                        {activeTab === 'inbox' ? 'From:' : 'To:'}
                      </span>{' '}
                      {activeTab === 'inbox' 
                        ? (selectedSubmission.submitted_by_user?.name || selectedSubmission.submitted_by)
                        : (selectedSubmission.recipient_user?.name || selectedSubmission.submitted_to)
                      }
                      {activeTab === 'inbox' && selectedSubmission.submitted_by_user && (
                        <span className="text-gray-500 ml-1">
                          ({selectedSubmission.submitted_by_user.email})
                        </span>
                      )}
                    </p>
                    <p>
                      <span className="font-semibold">Date:</span>{' '}
                      {new Date(selectedSubmission.created_at).toLocaleString()}
                    </p>
                  </div>
                  
                  {/* Forward via Email Button */}
                  <button
                    onClick={() => handleForwardViaEmail(selectedSubmission)}
                    className="mt-3 inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-green-600 to-green-700 text-white rounded-lg hover:from-green-700 hover:to-green-800 transition-all shadow-md hover:shadow-lg text-sm font-medium"
                    title="Forward this submission via email"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                      <path d="M2.003 5.884L10 9.882l7.997-3.998A2 2 0 0016 4H4a2 2 0 00-1.997 1.884z" />
                      <path d="M18 8.118l-8 4-8-4V14a2 2 0 002 2h12a2 2 0 002-2V8.118z" />
                    </svg>
                    Forward via Email
                  </button>
                </div>

                {/* Details */}
                <div className="space-y-4">
                  <DetailField label="Sample Name" value={selectedSubmission.sample_name} />
                  <DetailField label="Batch No. / Lot No." value={selectedSubmission.batch_no} />
                  <DetailField label="Label Claim" value={selectedSubmission.label_claim} />
                  <DetailField label="Sample Quantity" value={selectedSubmission.sample_quantity} />
                  <DetailField label="Packaging Configuration" value={selectedSubmission.packaging_configuration} />
                  <DetailField label="Recommended Storage" value={selectedSubmission.recommended_storage} />
                  <DetailField label="Condition" value={selectedSubmission.condition} />
                  <DetailField label="Tests to be Performed" value={selectedSubmission.tests_to_be_performed} multiline />
                  {selectedSubmission.remarks && (
                    <DetailField label="Remarks" value={selectedSubmission.remarks} multiline />
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// Helper component
function DetailField({ label, value, multiline }) {
  return (
    <div className="bg-gray-50 p-4 rounded-lg">
      <label className="block text-xs font-semibold text-gray-600 uppercase mb-1">
        {label}
      </label>
      {multiline ? (
        <p className="text-sm text-gray-900 whitespace-pre-wrap">{value}</p>
      ) : (
        <p className="text-sm text-gray-900">{value}</p>
      )}
    </div>
  );
}

export default SampleInbox;
