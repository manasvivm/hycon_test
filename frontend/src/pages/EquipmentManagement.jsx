import { useState, useMemo, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { equipmentApi } from '../services/api';
import Pagination from '../components/Pagination';
import axios from 'axios';
import {
  PlusIcon,
  PencilIcon,
  TrashIcon,
  XMarkIcon,
  CheckIcon,
  MagnifyingGlassIcon,
  ArrowUpTrayIcon,
  DocumentArrowDownIcon
} from '@heroicons/react/24/outline';

function EquipmentManagement() {
  const [showAddModal, setShowAddModal] = useState(false);
  const [showBatchUploadModal, setShowBatchUploadModal] = useState(false);
  const [editingEquipment, setEditingEquipment] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage] = useState(10);
  const [uploadFile, setUploadFile] = useState(null);
  const [uploadResult, setUploadResult] = useState(null);
  const fileInputRef = useRef(null);
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

  // Batch upload mutation
  const batchUploadMutation = useMutation(
    async (file) => {
      const token = localStorage.getItem('token');
      const formData = new FormData();
      formData.append('file', file);
      const response = await axios.post('/equipment/batch-upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
          'Authorization': `Bearer ${token}`
        },
      });
      return response.data;
    },
    {
      onSuccess: (data) => {
        queryClient.invalidateQueries('equipment');
        setUploadResult(data);
        setUploadFile(null);
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
      },
      onError: (error) => {
        alert(error.response?.data?.detail || 'Failed to upload file');
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

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (!file.name.endsWith('.csv')) {
        alert('Please select a CSV file');
        return;
      }
      setUploadFile(file);
      setUploadResult(null);
    }
  };

  const handleBatchUpload = () => {
    if (!uploadFile) {
      alert('Please select a file first');
      return;
    }
    batchUploadMutation.mutate(uploadFile);
  };

  const downloadTemplate = () => {
    const template = 'name,equipment_id,location,description\nMicroscope A,MSC-001,Lab Room 101,High-resolution optical microscope\nCentrifuge B,CTF-002,Lab Room 102,Refrigerated centrifuge';
    const blob = new Blob([template], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'equipment_template.csv';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
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
        <div className="flex gap-3">
          <button
            onClick={() => setShowBatchUploadModal(true)}
            className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
          >
            <ArrowUpTrayIcon className="h-5 w-5" />
            Batch Upload
          </button>
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-2 bg-teal-600 text-white px-4 py-2 rounded-lg hover:bg-teal-700 transition-colors"
          >
            <PlusIcon className="h-5 w-5" />
            Add Equipment
          </button>
        </div>
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

      {/* Batch Upload Modal */}
      {showBatchUploadModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center p-6 border-b border-gray-200">
              <h2 className="text-2xl font-bold text-gray-900">Batch Upload Equipment</h2>
              <button
                onClick={() => {
                  setShowBatchUploadModal(false);
                  setUploadFile(null);
                  setUploadResult(null);
                  if (fileInputRef.current) fileInputRef.current.value = '';
                }}
                className="text-gray-400 hover:text-gray-600"
              >
                <XMarkIcon className="h-6 w-6" />
              </button>
            </div>

            <div className="p-6 space-y-6">
              {/* Instructions */}
              <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded">
                <h3 className="font-semibold text-blue-900 mb-2">📋 Instructions</h3>
                <ol className="list-decimal list-inside space-y-1 text-sm text-blue-800">
                  <li>Download the CSV template below</li>
                  <li>Fill in equipment details (name, equipment_id, location, description)</li>
                  <li>Save as CSV file</li>
                  <li>Upload the file using the button below</li>
                </ol>
              </div>

              {/* Template Download */}
              <div className="flex justify-center">
                <button
                  onClick={downloadTemplate}
                  className="flex items-center gap-2 bg-green-600 text-white px-6 py-3 rounded-lg hover:bg-green-700 transition-colors"
                >
                  <DocumentArrowDownIcon className="h-5 w-5" />
                  Download CSV Template
                </button>
              </div>

              {/* File Upload */}
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-6">
                <div className="text-center">
                  <ArrowUpTrayIcon className="mx-auto h-12 w-12 text-gray-400" />
                  <div className="mt-4">
                    <label htmlFor="file-upload" className="cursor-pointer">
                      <span className="mt-2 block text-sm font-medium text-gray-900">
                        {uploadFile ? uploadFile.name : 'Choose a CSV file'}
                      </span>
                      <input
                        id="file-upload"
                        ref={fileInputRef}
                        type="file"
                        accept=".csv"
                        onChange={handleFileChange}
                        className="sr-only"
                      />
                      <span className="mt-1 block text-xs text-gray-500">
                        CSV files only
                      </span>
                    </label>
                  </div>
                  {uploadFile && (
                    <button
                      onClick={handleBatchUpload}
                      disabled={batchUploadMutation.isLoading}
                      className="mt-4 bg-teal-600 text-white px-6 py-2 rounded-lg hover:bg-teal-700 transition-colors disabled:opacity-50"
                    >
                      {batchUploadMutation.isLoading ? 'Uploading...' : 'Upload Equipment'}
                    </button>
                  )}
                </div>
              </div>

              {/* Upload Results */}
              {uploadResult && (
                <div className={`p-4 rounded-lg ${uploadResult.errors && uploadResult.errors.length > 0 ? 'bg-yellow-50 border-l-4 border-yellow-500' : 'bg-green-50 border-l-4 border-green-500'}`}>
                  <h3 className="font-semibold text-gray-900 mb-2">
                    ✅ Upload Complete
                  </h3>
                  <p className="text-sm text-gray-700 mb-2">
                    Successfully created <strong>{uploadResult.created}</strong> equipment entries
                  </p>
                  {uploadResult.errors && uploadResult.errors.length > 0 && (
                    <div className="mt-3">
                      <p className="text-sm font-semibold text-yellow-800 mb-1">
                        ⚠️ Errors ({uploadResult.errors.length}):
                      </p>
                      <div className="bg-white rounded p-2 max-h-40 overflow-y-auto">
                        <ul className="list-disc list-inside text-xs text-gray-700 space-y-1">
                          {uploadResult.errors.map((error, idx) => (
                            <li key={idx}>{error}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* CSV Format Reference */}
              <div className="bg-gray-50 rounded-lg p-4">
                <h3 className="font-semibold text-gray-900 mb-2">📝 CSV Format</h3>
                <div className="text-xs font-mono bg-white p-3 rounded border border-gray-200 overflow-x-auto">
                  <div className="text-gray-600">name,equipment_id,location,description</div>
                  <div className="text-gray-800">Microscope A,MSC-001,Lab Room 101,High-resolution optical microscope</div>
                  <div className="text-gray-800">Centrifuge B,CTF-002,Lab Room 102,Refrigerated centrifuge</div>
                </div>
                <p className="text-xs text-gray-600 mt-2">
                  <strong>Required fields:</strong> name, equipment_id<br/>
                  <strong>Optional fields:</strong> location, description
                </p>
              </div>

              <div className="flex justify-end">
                <button
                  onClick={() => {
                    setShowBatchUploadModal(false);
                    setUploadFile(null);
                    setUploadResult(null);
                    if (fileInputRef.current) fileInputRef.current.value = '';
                  }}
                  className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default EquipmentManagement;
