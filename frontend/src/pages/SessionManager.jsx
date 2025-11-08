import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { format, startOfDay, endOfDay, subDays } from 'date-fns';
import { sessionApi } from '../services/api';
import { SessionTable, SessionDetailsModal } from '../components/SessionComponents';
import Pagination from '../components/Pagination';
import { useAuth } from '../contexts/AuthContext';

function SessionManager() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [selectedSession, setSelectedSession] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const ITEMS_PER_PAGE = 15;
  const [dateRange, setDateRange] = useState({
    startDate: format(subDays(startOfDay(new Date()), 7), 'yyyy-MM-dd'),
    endDate: format(endOfDay(new Date()), 'yyyy-MM-dd')
  });

  // Function to export all sessions to CSV
  const exportToCSV = (allSessions) => {
    // Add BOM for Excel to recognize UTF-8
    const BOM = "\uFEFF";
    
    // Prepare the data
    const headers = ['Equipment Name', 'Equipment ID', 'Start Time', 'End Time', 'Status', 'Description'];
    const rows = allSessions.map(session => ({
      'Equipment Name': session.equipment?.name || '',
      'Equipment ID': session.equipment?.equipment_id || '',
      'Start Time': format(new Date(session.start_time), 'yyyy-MM-dd HH:mm:ss'),
      'End Time': session.end_time ? format(new Date(session.end_time), 'yyyy-MM-dd HH:mm:ss') : '',
      'Status': session.status || '',
      'Description': session.description || ''
    }));

    // Convert to CSV
    const csvRows = [
      headers.join(','),
      ...rows.map(row => headers.map(header => 
        JSON.stringify(row[header] || '').replace(/\\"/g, '""')
      ).join(','))
    ];

    const csvContent = BOM + csvRows.join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `session_history_${format(new Date(), 'yyyy-MM-dd')}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Fetch sessions
  const { data: sessions, isLoading } = useQuery(
    ['sessions', dateRange],
    () => sessionApi.getMySessions(),
    {
      select: (data) => {
        // Sort sessions by start time, most recent first
        return [...data.data].sort((a, b) => 
          new Date(b.start_time).getTime() - new Date(a.start_time).getTime()
        );
      },
      refetchInterval: 30000 // Refresh every 30 seconds
    }
  );

  // End session mutation
  const endSessionMutation = useMutation(
    (sessionId) => {
      const now = new Date();
      const endTime = new Date(now.getTime() - (now.getTimezoneOffset() * 60000)).toISOString();
      return sessionApi.endSession(sessionId, { end_time: endTime });
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries('sessions');
        queryClient.invalidateQueries('activeSessions');
        queryClient.invalidateQueries('equipment');
        setIsModalOpen(false);
        setSelectedSession(null);
      }
    }
  );

  const handleViewDetails = (session) => {
    setSelectedSession(session);
    setIsModalOpen(true);
  };

  const handleEndSession = () => {
    if (!selectedSession) return;
    if (window.confirm('Are you sure you want to end this session?')) {
      endSessionMutation.mutate(selectedSession.id);
    }
  };

  const handleDateRangeChange = (field, value) => {
    setDateRange(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handlePrint = () => {
    // Create a new window for printing
    const printWindow = window.open('', '_blank');
    const allSessions = sessions || [];
    
    // Generate the print content with all sessions
    const printContent = `
      <!DOCTYPE html>
      <html>
        <head>
          <title>Session History Report</title>
          <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f4f4f4; }
            .header { margin-bottom: 20px; }
            .title { font-size: 24px; margin-bottom: 10px; }
            .subtitle { font-size: 14px; color: #666; }
            @media print {
              table { page-break-inside: auto; }
              tr { page-break-inside: avoid; page-break-after: auto; }
              th { background-color: #f4f4f4 !important; -webkit-print-color-adjust: exact; }
            }
          </style>
        </head>
        <body>
          <div class="header">
            <div class="title">Session History Report</div>
            <div class="subtitle">User: ${user?.name || 'Unknown'}</div>
            <div class="subtitle">Role: ${user?.role || 'Unknown'}</div>
            <div class="subtitle">Generated on ${format(new Date(), 'MMMM d, yyyy h:mm a')}</div>
          </div>
          <table>
            <thead>
              <tr>
                <th>Equipment</th>
                <th>Equipment ID</th>
                <th>Start Time</th>
                <th>End Time</th>
                <th>Status</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
              ${allSessions.map(session => `
                <tr>
                  <td>${session.equipment?.name || ''}</td>
                  <td>${session.equipment?.equipment_id || ''}</td>
                  <td>${format(new Date(session.start_time), 'MMM d, yyyy h:mm a')}</td>
                  <td>${session.end_time ? format(new Date(session.end_time), 'MMM d, yyyy h:mm a') : '-'}</td>
                  <td>${session.status || ''}</td>
                  <td>${session.description || ''}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </body>
      </html>
    `;

      // Write the content to the new window and print it
    printWindow.document.write(printContent);
    printWindow.document.close();
    
    // Wait for images and styles to load before printing
    printWindow.onload = function() {
      printWindow.print();
      // Only close the window after printing is done or cancelled
      printWindow.onafterprint = function() {
        printWindow.close();
      };
    };
  };  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-teal-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="sm:flex sm:items-center">
        <div className="sm:flex-auto">
          <h1 className="text-xl font-semibold text-gray-900">Session History</h1>
          <p className="mt-2 text-sm text-gray-700">
            View and manage your equipment usage sessions.
          </p>
        </div>
        <div className="mt-4 sm:mt-0 sm:ml-16 sm:flex-none space-x-4">
          <button
            onClick={() => exportToCSV(sessions || [])}
            className="inline-flex items-center justify-center rounded-md border border-transparent bg-blue-500 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 sm:w-auto"
          >
            Export All Sessions
          </button>
          <button
            onClick={handlePrint}
            className="inline-flex items-center justify-center rounded-md border border-transparent bg-teal-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-teal-700 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 sm:w-auto"
          >
            Print Report
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <label htmlFor="start-date" className="block text-sm font-medium text-gray-700">
            Start Date
          </label>
          <input
            type="date"
            id="start-date"
            value={dateRange.startDate}
            onChange={(e) => handleDateRangeChange('startDate', e.target.value)}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-teal-500 focus:ring-teal-500 sm:text-sm"
          />
        </div>
        <div>
          <label htmlFor="end-date" className="block text-sm font-medium text-gray-700">
            End Date
          </label>
          <input
            type="date"
            id="end-date"
            value={dateRange.endDate}
            onChange={(e) => handleDateRangeChange('endDate', e.target.value)}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-teal-500 focus:ring-teal-500 sm:text-sm"
          />
        </div>
      </div>

      {/* Session Table */}
      <div className="mt-8">
        <SessionTable
          sessions={(sessions || []).slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE)}
          onViewDetails={handleViewDetails}
          currentPage={currentPage}
          totalSessions={(sessions || []).length}
          itemsPerPage={ITEMS_PER_PAGE}
          onPageChange={setCurrentPage}
          onExport={exportToCSV}
        />
      </div>

      {/* Session Details Modal */}
      <SessionDetailsModal
        session={selectedSession}
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setSelectedSession(null);
        }}
        onEndSession={handleEndSession}
        isLoading={endSessionMutation.isLoading}
      />

      {/* Hidden Print Table with All Sessions */}
      <div className="hidden">
        <table id="print-table" className="print-only">
          <thead>
            <tr>
              <th>Equipment</th>
              <th>Start Time</th>
              <th>End Time</th>
              <th>Status</th>
              <th>Description</th>
            </tr>
          </thead>
          <tbody>
            {(sessions || []).map(session => (
              <tr key={session.id}>
                <td>{session.equipment.name}</td>
                <td>{format(new Date(session.start_time), 'MMM d, yyyy h:mm a')}</td>
                <td>{session.end_time ? format(new Date(session.end_time), 'MMM d, yyyy h:mm a') : '-'}</td>
                <td>{session.status}</td>
                <td>
                  {session.description 
                    ? (session.description.length > 15 
                      ? session.description.substring(0, 15) + '...' 
                      : session.description)
                    : '-'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Print Styles */}
      <style type="text/css" dangerouslySetInnerHTML={{
        __html: `
          @media print {
            /* Reset page margins */
            @page {
              margin: 0.5cm;
              size: landscape;
            }
            
            /* Hide non-printable elements */
            .no-print {
              display: none !important;
            }
            
            /* Show print-only table */
            .print-only {
              display: table !important;
              width: 100%;
              font-size: 10pt;
              border-collapse: collapse;
              table-layout: fixed;
            }
            
            /* Table cell styling */
            .print-only th,
            .print-only td {
              padding: 4px 8px;
              text-align: left;
              border: 1px solid #ddd;
              word-wrap: break-word;
              max-width: 150px;
              overflow: hidden;
              text-overflow: ellipsis;
            }
            
            /* Column widths */
            .print-only th:nth-child(1),
            .print-only td:nth-child(1) { width: 20%; } /* Equipment */
            .print-only th:nth-child(2),
            .print-only td:nth-child(2) { width: 15%; } /* Start Time */
            .print-only th:nth-child(3),
            .print-only td:nth-child(3) { width: 15%; } /* End Time */
            .print-only th:nth-child(4),
            .print-only td:nth-child(4) { width: 10%; } /* Status */
            .print-only th:nth-child(5),
            .print-only td:nth-child(5) { width: 40%; } /* Description */
            
            /* Header styling */
            .print-only th {
              background-color: #f3f4f6 !important;
              font-weight: 600;
              -webkit-print-color-adjust: exact;
              print-color-adjust: exact;
            }
            
            /* Page break handling */
            #print-table {
              break-inside: auto;
            }
            
            tr {
              break-inside: avoid;
            }
            
            /* General print settings */
            body {
              -webkit-print-color-adjust: exact;
              print-color-adjust: exact;
              width: 100%;
              margin: 0;
              padding: 0;
            }
          }
          
          /* Hide print-only elements in normal view */
          .print-only {
            display: none;
          }
        `
      }} />
    </div>
  );
}

export default SessionManager;