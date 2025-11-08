import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { equipmentApi } from '../services/api';
import Pagination from '../components/Pagination';
import {
  PlusIcon,
  PencilIcon,
  TrashIcon,
  XMarkIcon,
  CheckIcon,
  MagnifyingGlassIcon
} from '@heroicons/react/24/outline';

function EquipmentManagement() {
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingEquipment, setEditingEquipment] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage] = useState(10);
  const [formData, setFormData] = useState({
    name: '',
    equipment_id: '',
    location: '',
    description: ''
  });

  const queryClient = useQueryClient();

  // Fetch all equipment
  const { data: equipment, isLoading } = useQuery('equipment', equipmentApi.getAll, {
    select: (data) => data.data
  });

  // Create equipment mutation
  const createMutation = useMutation(
    (data) => equipmentApi.create(data),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('equipment');
        setShowAddModal(false);
        resetForm();
      },
      onError: (error) => {
        alert(error.response?.data?.detail || 'Failed to create equipment');
      }
    }
  );

  // Update equipment mutation
  const updateMutation = useMutation(
    ({ id, data }) => equipmentApi.update(id, data),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('equipment');
        setEditingEquipment(null);
        resetForm();
      },
      onError: (error) => {
        alert(error.response?.data?.detail || 'Failed to update equipment');
      }
    }
  );

  // Delete equipment mutation
  const deleteMutation = useMutation(
    (id) => equipmentApi.delete(id),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('equipment');
      },
      onError: (error) => {
        alert(error.response?.data?.detail || 'Failed to delete equipment');
      }
    }
  );

  const resetForm = () => {
    setFormData({
      name: '',
      equipment_id: '',
      location: '',
      description: ''
    });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (editingEquipment) {
      updateMutation.mutate({ id: editingEquipment.id, data: formData });
    } else {
      createMutation.mutate(formData);
    }
  };

  const handleEdit = (equipment) => {
    setEditingEquipment(equipment);
    setFormData({
      name: equipment.name,
      equipment_id: equipment.equipment_id,
      location: equipment.location || '',
      description: equipment.description || ''
    });
    setShowAddModal(true);
  };

  const handleDelete = (equipment) => {
    if (window.confirm(`Are you sure you want to delete ${equipment.name}?`)) {
      deleteMutation.mutate(equipment.id);
    }
  };

  const handleCancel = () => {
    setShowAddModal(false);
    setEditingEquipment(null);
    resetForm();
  };

  // Filter equipment based on search term
  const filteredEquipment = useMemo(() => {
    if (!equipment) return [];
    
    return equipment.filter(eq => 
      eq.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      eq.equipment_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      eq.location?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      eq.description?.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [equipment, searchTerm]);

  // Paginate filtered equipment
  const paginatedEquipment = useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage;
    return filteredEquipment.slice(startIndex, startIndex + itemsPerPage);
  }, [filteredEquipment, currentPage, itemsPerPage]);

  const totalPages = Math.ceil(filteredEquipment.length / itemsPerPage);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-gray-600">Loading...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Equipment Management</h1>
          <p className="text-gray-600 mt-1">Add, edit, and manage laboratory equipment</p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 bg-teal-600 text-white px-4 py-2 rounded-lg hover:bg-teal-700 transition-colors"
        >
          <PlusIcon className="h-5 w-5" />
          Add Equipment
        </button>
      </div>

      {/* Search Bar */}
      <div className="bg-white shadow-md rounded-lg p-4">
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <MagnifyingGlassIcon className="h-5 w-5 text-gray-400" />
          </div>
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setCurrentPage(1); // Reset to first page on search
            }}
            placeholder="Search by name, ID, location, or description..."
            className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 sm:text-sm"
          />
        </div>
        {searchTerm && (
          <div className="mt-2 text-sm text-gray-600">
            Found {filteredEquipment.length} result{filteredEquipment.length !== 1 ? 's' : ''}
          </div>
        )}
      </div>

      {/* Equipment List */}
      <div className="bg-white shadow-lg rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Equipment ID
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Name
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Location
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Description
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {paginatedEquipment.length > 0 ? (
              paginatedEquipment.map((eq) => (
                <tr key={eq.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {eq.equipment_id}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {eq.name}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                    {eq.location || '-'}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600 max-w-xs truncate">
                    {eq.description || '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <span
                      className={`px-2 py-1 rounded-full text-xs font-medium ${
                        eq.current_status === 'available'
                          ? 'bg-green-100 text-green-800'
                          : eq.current_status === 'in_use'
                          ? 'bg-blue-100 text-blue-800'
                          : 'bg-yellow-100 text-yellow-800'
                      }`}
                    >
                      {eq.current_status?.replace('_', ' ').toUpperCase()}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <button
                      onClick={() => handleEdit(eq)}
                      className="text-teal-600 hover:text-teal-900 mr-4"
                    >
                      <PencilIcon className="h-5 w-5" />
                    </button>
                    <button
                      onClick={() => handleDelete(eq)}
                      className="text-red-600 hover:text-red-900"
                    >
                      <TrashIcon className="h-5 w-5" />
                    </button>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan="6" className="px-6 py-8 text-center text-sm text-gray-500">
                  {searchTerm ? 'No equipment found matching your search.' : 'No equipment available.'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {filteredEquipment.length > 0 && (
        <Pagination
          totalItems={filteredEquipment.length}
          itemsPerPage={itemsPerPage}
          currentPage={currentPage}
          onPageChange={setCurrentPage}
        />
      )}

      {/* Add/Edit Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center p-6 border-b border-gray-200">
              <h2 className="text-2xl font-bold text-gray-900">
                {editingEquipment ? 'Edit Equipment' : 'Add New Equipment'}
              </h2>
              <button
                onClick={handleCancel}
                className="text-gray-400 hover:text-gray-600"
              >
                <XMarkIcon className="h-6 w-6" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Equipment ID <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={formData.equipment_id}
                  onChange={(e) => setFormData({ ...formData, equipment_id: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
                  placeholder="e.g., EQ-001"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Equipment Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
                  placeholder="e.g., Microscope"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Location
                </label>
                <input
                  type="text"
                  value={formData.location}
                  onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
                  placeholder="e.g., Lab A, Room 101"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Description
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  rows={4}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
                  placeholder="Enter equipment description, specifications, or notes..."
                />
              </div>

              <div className="flex justify-end gap-3 pt-4">
                <button
                  type="button"
                  onClick={handleCancel}
                  className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isLoading || updateMutation.isLoading}
                  className="flex items-center gap-2 bg-teal-600 text-white px-4 py-2 rounded-lg hover:bg-teal-700 transition-colors disabled:opacity-50"
                >
                  <CheckIcon className="h-5 w-5" />
                  {editingEquipment ? 'Update Equipment' : 'Add Equipment'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default EquipmentManagement;
