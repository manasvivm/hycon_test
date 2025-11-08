import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { useNavigate } from 'react-router-dom';
import { equipmentApi, sessionApi } from '../services/api';
import { ActiveSessionCard, EquipmentCard } from '../components/Equipment';
import { SearchBar } from '../components/EquipmentTable';
import StartSessionModal from '../components/StartSessionModal';
import LogPastUsageModal from '../components/LogPastUsageModal';
import Pagination from '../components/Pagination';

function Dashboard() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [selectedEquipment, setSelectedEquipment] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isLogModalOpen, setIsLogModalOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [sessionsPage, setSessionsPage] = useState(1);
  const [historyPage, setHistoryPage] = useState(1);
  const ITEMS_PER_PAGE = 3;  // Show only 3 equipment cards
  const SESSIONS_PER_PAGE = 5;  // Show 5 active sessions per page
  const HISTORY_PER_PAGE = 10;  // Show 10 history items per page

  // Fetch equipment list
  const { data: equipment, isLoading: isLoadingEquipment, error: equipmentError } = useQuery(
    'equipment',
    equipmentApi.getAll,
    {
      select: (data) => {
        // Ensure equipment status is properly normalized
        return data.data.map(eq => ({
          ...eq,
          current_status: eq.current_status?.toUpperCase() || 'MAINTENANCE'
        }));
      },
      retry: 1,
      refetchOnWindowFocus: false
    }
  );

  // Fetch user's active sessions
  const { data: activeSessions, isLoading: isLoadingSession, error: sessionError } = useQuery(
    'activeSessions',
    sessionApi.getMyActiveSessions,
    {
      select: (data) => data.data?.active_sessions || [],
      retry: 1,
      refetchOnWindowFocus: false,
      refetchInterval: 30000 // Refresh every 30 seconds
    }
  );

  // Fetch user's session history
  const { data: sessionHistory, isLoading: isLoadingHistory } = useQuery(
    'mySessionHistory',
    sessionApi.getMySessions,
    {
      select: (data) => data.data || [],
      retry: 1,
      refetchOnWindowFocus: false
    }
  );

  // Start session mutation
  const startSessionMutation = useMutation(sessionApi.startSession, {
    onSuccess: (data) => {
      console.log('startSessionMutation success:', data);
      queryClient.invalidateQueries('activeSessions');
      queryClient.invalidateQueries('equipment');
      queryClient.invalidateQueries('mySessionHistory');
      setIsModalOpen(false);
      setSelectedEquipment(null);
      alert('Session started successfully!');
    },
    onError: (error) => {
      // Show detailed error message from the backend
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message || 'Unknown error';
      alert('Failed to start session: ' + errorMessage);
      console.error('Session start error:', error.response?.data || error);
    }
  });

  // Log past usage mutation
  const logPastUsageMutation = useMutation(sessionApi.logPastUsage, {
    onSuccess: async (data) => {
      console.log('logPastUsageMutation success:', data);
      
      // Invalidate and refetch equipment list and session history
      await queryClient.invalidateQueries('equipment');
      await queryClient.invalidateQueries('mySessionHistory');
      await queryClient.refetchQueries('equipment');
      await queryClient.refetchQueries('mySessionHistory');
      
      setIsLogModalOpen(false);
      setSelectedEquipment(null);
      alert('Past usage logged successfully!');
    },
    onError: (error) => {
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message || 'Unknown error';
      alert('Failed to log past usage: ' + errorMessage);
      console.error('Log past usage error:', error.response?.data || error);
    }
  });

  // End session mutation
  const endSessionMutation = useMutation(
    (sessionId) => {
      // Create end time in UTC
      const now = new Date();
      const endTime = new Date(now.getTime() - (now.getTimezoneOffset() * 60000)).toISOString();
      return sessionApi.endSession(sessionId, { end_time: endTime });
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries('activeSessions');
        queryClient.invalidateQueries('equipment');
        queryClient.invalidateQueries('mySessionHistory');
        alert('Session ended successfully!');
      },
      onError: (error) => {
        const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message || 'Unknown error';
        alert('Failed to end session: ' + errorMessage);
        console.error('Session end error:', error.response?.data || error);
      }
    }
  );

  const handleEquipmentSelect = (action) => {
    console.log('handleEquipmentSelect called with:', action);
    
    switch (action.type) {
      case 'START_SESSION': {
        const existingSession = activeSessions?.find(session => session.equipment.id === action.equipment.id);
        
        if (existingSession) {
          alert('You already have an active session with ' + action.equipment.name);
          return;
        }

        setSelectedEquipment(action.equipment);
        setIsModalOpen(true);
        setIsLogModalOpen(false);
        break;
      }

      case 'LOG_PAST_USAGE': {
        setSelectedEquipment(action.equipment);
        setIsModalOpen(false);
        setIsLogModalOpen(true);
        break;
      }

      case 'CLOSE': {
        setSelectedEquipment(null);
        setIsModalOpen(false);
        setIsLogModalOpen(false);
        break;
      }

      default:
        console.warn('Unknown equipment action:', action);
    }
  };

  const handleNewSession = () => {
    setSelectedEquipment(null);
    setIsModalOpen(true);
  };

  const handleEndSession = (sessionId) => {
    if (window.confirm('Are you sure you want to end this session?')) {
      endSessionMutation.mutate(sessionId);
    }
  };

  if (isLoadingEquipment || isLoadingSession) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-teal-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header with New Session button */}
      <div className="sm:flex sm:items-center sm:justify-between">
        <div className="sm:flex-auto">
          <h1 className="text-xl font-semibold text-gray-900">Equipment Dashboard</h1>
        </div>
        <div className="mt-4 sm:mt-0 sm:ml-16 sm:flex-none">
          <button
            onClick={handleNewSession}
            className="inline-flex items-center justify-center rounded-md border border-transparent bg-teal-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-teal-700 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 sm:w-auto"
          >
            New Session
          </button>
        </div>
      </div>

      {/* Active Session Section */}
      <div className="bg-white shadow sm:rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h2 className="text-lg font-medium text-gray-900">Active Sessions</h2>
          {activeSessions?.length > 0 ? (
            <div className="mt-4 space-y-4">
              {activeSessions
                .slice((sessionsPage - 1) * SESSIONS_PER_PAGE, sessionsPage * SESSIONS_PER_PAGE)
                .map(session => (
                  <div key={session.id} className="border-b pb-4 last:border-b-0">
                    <ActiveSessionCard session={session} />
                    <div className="mt-4">
                      <button
                        onClick={() => handleEndSession(session.id)}
                        className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700"
                      >
                        End Session
                      </button>
                    </div>
                  </div>
                ))}
              {activeSessions.length > SESSIONS_PER_PAGE && (
                <Pagination
                  totalItems={activeSessions.length}
                  itemsPerPage={SESSIONS_PER_PAGE}
                  currentPage={sessionsPage}
                  onPageChange={setSessionsPage}
                />
              )}
            </div>
          ) : (
            <p className="mt-2 text-sm text-gray-500">No active sessions. Select equipment below to start a new session.</p>
          )}
        </div>
      </div>

      {/* Equipment Section */}
      <div>
        <div className="mb-6">
          <h2 className="text-lg font-medium text-gray-900 mb-3">Available Equipment</h2>
          <div className="flex items-center gap-3 flex-wrap">
            <div className="flex-1 min-w-[250px]">
              <SearchBar
                value={search}
                onChange={setSearch}
                onSubmit={(e) => e.preventDefault()}
                className="shadow-lg"
              />
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => navigate('/equipment')}
                className="inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-teal-600 hover:bg-teal-700 hover:shadow-lg whitespace-nowrap transition-all duration-200"
              >
                View All
              </button>
              <button
                onClick={() => navigate('/sessions')}
                className="inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-teal-600 hover:bg-teal-700 hover:shadow-lg whitespace-nowrap transition-all duration-200"
              >
                Sessions
              </button>
            </div>
            {equipment && equipment.length > ITEMS_PER_PAGE && (
              <div className="ml-auto">
                <Pagination
                  totalItems={equipment.filter(item => 
                    search === '' || 
                    item.name.toLowerCase().includes(search.toLowerCase()) ||
                    item.equipment_id.toLowerCase().includes(search.toLowerCase())
                  ).length}
                  itemsPerPage={ITEMS_PER_PAGE}
                  currentPage={currentPage}
                  onPageChange={setCurrentPage}
                />
              </div>
            )}
          </div>
        </div>
        <div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {equipment
              ?.filter(item => 
                search === '' || 
                item.name.toLowerCase().includes(search.toLowerCase()) ||
                item.equipment_id.toLowerCase().includes(search.toLowerCase())
              )
              .slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE)
              .map((item) => (
                <EquipmentCard
                  key={item.id}
                  equipment={item}
                  onSelect={handleEquipmentSelect}
                  activeSessions={activeSessions}
                />
              ))}
          </div>
        </div>
      </div>

      {/* Recent Session History */}
      <div className="bg-white shadow sm:rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-medium text-gray-900">My Recent History</h2>
            <button
              onClick={() => navigate('/sessions')}
              className="text-sm font-medium text-teal-600 hover:text-teal-500"
            >
              View All →
            </button>
          </div>
          {sessionHistory && sessionHistory.length > 0 ? (
            <div className="mt-4">
              <div className="overflow-x-auto border-2 border-teal-500 rounded-lg">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th scope="col" className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Equipment</th>
                      <th scope="col" className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Start Time</th>
                      <th scope="col" className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">End Time</th>
                      <th scope="col" className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                      <th scope="col" className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Description</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {sessionHistory
                      .slice((historyPage - 1) * HISTORY_PER_PAGE, historyPage * HISTORY_PER_PAGE)
                      .map((session) => (
                        <tr key={session.id}>
                          <td className="px-3 py-4 text-sm text-gray-900">{session.equipment?.name || 'N/A'}</td>
                          <td className="px-3 py-4 text-sm text-gray-900">
                            {new Date(session.start_time).toLocaleString('en-US', {
                              month: 'short',
                              day: 'numeric',
                              year: 'numeric',
                              hour: 'numeric',
                              minute: '2-digit',
                              hour12: true
                            })}
                          </td>
                          <td className="px-3 py-4 text-sm text-gray-900">
                            {session.end_time ? new Date(session.end_time).toLocaleString('en-US', {
                              month: 'short',
                              day: 'numeric',
                              year: 'numeric',
                              hour: 'numeric',
                              minute: '2-digit',
                              hour12: true
                            }) : '-'}
                          </td>
                          <td className="px-3 py-4 text-sm">
                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                              session.status === 'ACTIVE' 
                                ? 'bg-green-100 text-green-800' 
                                : 'bg-gray-100 text-gray-800'
                            }`}>
                              {session.status}
                            </span>
                          </td>
                          <td className="px-3 py-4 text-sm text-gray-900">
                            {session.description ? (
                              session.description.length > 50 
                                ? session.description.substring(0, 50) + '...' 
                                : session.description
                            ) : '-'}
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
              {sessionHistory.length > HISTORY_PER_PAGE && (
                <div className="mt-4">
                  <Pagination
                    totalItems={sessionHistory.length}
                    itemsPerPage={HISTORY_PER_PAGE}
                    currentPage={historyPage}
                    onPageChange={setHistoryPage}
                  />
                </div>
              )}
            </div>
          ) : (
            <p className="mt-2 text-sm text-gray-500">No session history available.</p>
          )}
        </div>
      </div>

      {/* Start Session Modal */}
      <StartSessionModal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setSelectedEquipment(null);
        }}
        equipment={selectedEquipment}
        onSubmit={(data) => startSessionMutation.mutate(data)}
        isLoading={startSessionMutation.isLoading}
        allEquipment={equipment}
        activeSessions={activeSessions}
      />

      {/* Log Past Usage Modal */}
      {selectedEquipment && (
        <LogPastUsageModal
          isOpen={isLogModalOpen}
          onClose={() => {
            console.log('Closing log modal');
            setIsLogModalOpen(false);
            setSelectedEquipment(null);
          }}
          equipment={selectedEquipment}
          isLoading={logPastUsageMutation.isLoading}
          onSubmit={async (data) => {
            console.log('Dashboard - Log Past Usage submit handler:', {
              data,
              selectedEquipment: selectedEquipment
            });

            await logPastUsageMutation.mutateAsync(data);
          }}
        />
      )}
    </div>
  );
}

export default Dashboard;