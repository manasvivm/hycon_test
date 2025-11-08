import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { equipmentApi, sessionApi } from '../services/api';
import { SearchBar, FilterDropdown, EquipmentTable } from '../components/EquipmentTable';
import StartSessionModal from '../components/StartSessionModal';
import EquipmentDetailsModal from '../components/EquipmentDetailsModal';
import { useAuth } from '../contexts/AuthContext';
import Pagination from '../components/Pagination';

const STATUS_OPTIONS = [
  { value: 'available', label: 'Available' },
  { value: 'in_use', label: 'In Use' },
  { value: 'maintenance', label: 'Maintenance' }
];

function EquipmentList() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState(null);
  const [selectedEquipment, setSelectedEquipment] = useState(null);
  const [isDetailsModalOpen, setIsDetailsModalOpen] = useState(false);
  const [isSessionModalOpen, setIsSessionModalOpen] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const ITEMS_PER_PAGE = 15;

  // Fetch equipment list
  const { data: equipment, isLoading } = useQuery(
    'equipment',
    equipmentApi.getAll,
    {
      select: (data) => data.data.map(item => ({
        ...item,
        current_status: item.current_status?.toLowerCase() || 'maintenance'
      })),
      refetchInterval: 30000 // Refresh every 30 seconds
    }
  );

  // Fetch user's active sessions
  const { data: activeSessions } = useQuery(
    'activeSessions',
    sessionApi.getMyActiveSessions,
    {
      select: (data) => data.data?.active_sessions || [],
      retry: 1,
      refetchOnWindowFocus: false
    }
  );

  // Filter equipment based on search and status
  const filteredEquipment = equipment?.filter(item => {
    const matchesSearch = search === '' || 
      item.name.toLowerCase().includes(search.toLowerCase()) ||
      item.equipment_id.toLowerCase().includes(search.toLowerCase());
    
    const matchesStatus = !statusFilter || item.current_status === statusFilter;
    
    return matchesSearch && matchesStatus;
  }) || [];

  const handleSearch = (e) => {
    e.preventDefault();
    // Search is already handled by the filter
  };

  const handleEquipmentSelect = (equipment) => {
    setSelectedEquipment(equipment);
    setIsDetailsModalOpen(true);
  };

  const handleStartSession = (equipment) => {
    console.log('handleStartSession called with:', equipment);
    setSelectedEquipment(equipment);
    setIsDetailsModalOpen(false); // Close details modal first
    setIsSessionModalOpen(true);
  };

  // Start session mutation
  const startSessionMutation = useMutation(sessionApi.startSession, {
    onSuccess: (data) => {
      console.log('startSessionMutation success:', data);
      queryClient.invalidateQueries('activeSessions');
      queryClient.invalidateQueries('equipment');
      setIsSessionModalOpen(false);
      setSelectedEquipment(null);
      alert('Session started successfully!');
    },
    onError: (error) => {
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message || 'Unknown error';
      alert('Failed to start session: ' + errorMessage);
      console.error('Session start error:', error.response?.data || error);
    }
  });

  // Log past usage mutation
  const logPastUsageMutation = useMutation(sessionApi.logPastUsage, {
    onSuccess: async (data) => {
      // Invalidate and refetch equipment list
      await queryClient.invalidateQueries('equipment');
      await queryClient.refetchQueries('equipment');
      
      // Update the selected equipment with fresh data if it's still selected
      if (selectedEquipment) {
        const updatedEquipment = await equipmentApi.getById(selectedEquipment.id);
        setSelectedEquipment(updatedEquipment.data);
      }
      
      alert('Past usage logged successfully!');
    },
    onError: (error) => {
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message || 'Unknown error';
      alert('Failed to log past usage: ' + errorMessage);
      console.error('Log past usage error:', error.response?.data || error);
    }
  });

  const handleLogPastUsage = async (data) => {
    await logPastUsageMutation.mutateAsync(data);
  };

  if (isLoading) {
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
          <h1 className="text-xl font-semibold text-gray-900">Equipment List</h1>
          <p className="mt-2 text-sm text-gray-700">
            A list of all available equipment in the facility.
          </p>
        </div>
        {user?.role === 'admin' && (
          <div className="mt-4 sm:mt-0 sm:ml-16 sm:flex-none">
            <button
              type="button"
              className="inline-flex items-center justify-center rounded-md border border-transparent bg-teal-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-teal-700 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 sm:w-auto"
            >
              Add Equipment
            </button>
          </div>
        )}
      </div>

      {/* Filters */}
      <div className="flex items-center space-x-4">
        <SearchBar
          value={search}
          onChange={setSearch}
          onSubmit={handleSearch}
        />
        <FilterDropdown
          value={statusFilter}
          onChange={setStatusFilter}
          options={STATUS_OPTIONS}
        />
      </div>

      {/* Equipment Table with Pagination */}
      <div>
        <EquipmentTable
          equipment={filteredEquipment.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE)}
          onSelectEquipment={handleEquipmentSelect}
        />
        {filteredEquipment.length > ITEMS_PER_PAGE && (
          <div className="mt-6">
            <Pagination
              totalItems={filteredEquipment.length}
              itemsPerPage={ITEMS_PER_PAGE}
              currentPage={currentPage}
              onPageChange={setCurrentPage}
            />
          </div>
        )}
      </div>

      {/* Equipment Details Modal */}
      <EquipmentDetailsModal
        isOpen={isDetailsModalOpen}
        onClose={() => {
          setIsDetailsModalOpen(false);
          setSelectedEquipment(null);
        }}
        equipment={selectedEquipment}
        onStartSession={handleStartSession}
        onLogPastUsage={handleLogPastUsage}
      />

      {/* Start Session Modal */}
      <StartSessionModal
        isOpen={isSessionModalOpen}
        onClose={() => {
          setIsSessionModalOpen(false);
          setSelectedEquipment(null);
        }}
        equipment={selectedEquipment}
        onSubmit={(data) => startSessionMutation.mutate(data)}
        isLoading={startSessionMutation.isLoading}
        allEquipment={equipment}
        activeSessions={activeSessions}
      />
    </div>
  );
}

export default EquipmentList;