import { useState, useRef, useEffect } from 'react';
import { useQuery } from 'react-query';
import { format, startOfMonth, endOfMonth, subDays } from 'date-fns';
import { analyticsApi, sessionApi, equipmentApi } from '../services/api';
import axios from 'axios';
import {
  ClockIcon,
  UserGroupIcon,
  BeakerIcon,
  DocumentTextIcon,
  ArrowDownTrayIcon,
  FunnelIcon,
  PrinterIcon,
  ChevronDownIcon,
  XMarkIcon
} from '@heroicons/react/24/outline';
import Pagination from '../components/Pagination';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

// Custom Multiselect Component
function MultiSelect({ label, options, selected, onChange, placeholder = "Select...", searchable = false }) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const dropdownRef = useRef(null);
  const searchInputRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
        setSearchTerm('');
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    if (isOpen && searchable && searchInputRef.current) {
      searchInputRef.current.focus();
    }
  }, [isOpen, searchable]);

  const handleToggle = (value) => {
    const newSelected = selected.includes(value)
      ? selected.filter(v => v !== value)
      : [...selected, value];
    onChange(newSelected);
  };

  const handleClear = (e) => {
    e.stopPropagation();
    onChange([]);
  };

  const selectedLabels = selected
    .map(val => options.find(opt => opt.value === val)?.label)
    .filter(Boolean);

  // Filter options based on search term
  const filteredOptions = searchTerm
    ? options.filter(opt => opt.label.toLowerCase().includes(searchTerm.toLowerCase()))
    : options;

  return (
    <div ref={dropdownRef} className="relative">
      <label className="block text-sm font-bold text-gray-700 mb-2">
        {label}
      </label>
      <div
        onClick={() => setIsOpen(!isOpen)}
        className="block w-full rounded-lg border-2 border-teal-600 shadow-sm focus:border-teal-700 bg-white px-4 py-3 cursor-pointer flex items-center justify-between"
      >
        <span className={selected.length === 0 ? 'text-gray-400' : 'text-gray-900'}>
          {selected.length === 0
            ? placeholder
            : `${selected.length} selected`}
        </span>
        <div className="flex items-center gap-2">
          {selected.length > 0 && (
            <XMarkIcon
              className="h-5 w-5 text-gray-400 hover:text-gray-600"
              onClick={handleClear}
            />
          )}
          <ChevronDownIcon
            className={`h-5 w-5 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}
          />
        </div>
      </div>
      
      {selected.length > 0 && (
        <div className="mt-2 max-h-28 overflow-y-auto flex flex-wrap gap-2 p-1 border border-gray-200 rounded-lg bg-gray-50">
          {selectedLabels.map((label, idx) => (
            <span
              key={idx}
              className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-teal-100 text-teal-800 flex-shrink-0"
            >
              {label}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleToggle(selected[idx]);
                }}
                className="ml-1 inline-flex items-center hover:bg-teal-200 rounded-full p-0.5"
              >
                <XMarkIcon className="h-3 w-3" />
              </button>
            </span>
          ))}
        </div>
      )}

      {isOpen && (
        <div className="absolute z-10 mt-1 w-full bg-white border-2 border-teal-600 rounded-lg shadow-lg">
          {searchable && (
            <div className="p-3 border-b border-gray-200 sticky top-0 bg-white">
              <input
                ref={searchInputRef}
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                onClick={(e) => e.stopPropagation()}
                placeholder="Search..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-sm"
              />
            </div>
          )}
          <div className="max-h-60 overflow-auto">
            {filteredOptions.length > 0 ? (
              filteredOptions.map((option) => (
                <div
                  key={option.value}
                  onClick={() => handleToggle(option.value)}
                  className="px-4 py-2 hover:bg-teal-50 cursor-pointer flex items-center gap-2"
                >
                  <input
                    type="checkbox"
                    checked={selected.includes(option.value)}
                    onChange={() => {}}
                    className="h-4 w-4 text-teal-600 border-gray-300 rounded focus:ring-teal-500"
                  />
                  <span className="text-sm text-gray-900">{option.label}</span>
                </div>
              ))
            ) : (
              <div className="px-4 py-3 text-sm text-gray-500 text-center">
                No results found
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function AdminDashboard() {
  const [dateRange, setDateRange] = useState({
    startDate: format(subDays(new Date(), 30), 'yyyy-MM-dd'),
    endDate: format(new Date(), 'yyyy-MM-dd')
  });
  
  const [filters, setFilters] = useState({
    equipment: [],
    user: [],
    status: []
  });
  
  const [currentPage, setCurrentPage] = useState(1);
  const ITEMS_PER_PAGE = 15;

  // Fetch all sessions with date range only
  const { data: sessionsData, isLoading: loadingSessions } = useQuery(
    ['allSessions', dateRange],
    async () => {
      const params = {
        start_date: dateRange.startDate,
        end_date: dateRange.endDate
      };
      
      const response = await axios.get('/sessions', { params });
      return response.data;
    }
  );

  // Apply filters client-side for multiselect support
  const allSessions = sessionsData?.filter(session => {
    // Equipment filter
    if (filters.equipment.length > 0 && !filters.equipment.includes(String(session.equipment_id))) {
      return false;
    }
    
    // User filter
    if (filters.user.length > 0 && !filters.user.includes(String(session.user_id))) {
      return false;
    }
    
    // Status filter
    if (filters.status.length > 0 && !filters.status.includes(session.status?.toUpperCase())) {
      return false;
    }
    
    return true;
  }) || [];

  // Fetch all equipment for filters
  const { data: equipment } = useQuery('equipment', equipmentApi.getAll, {
    select: (data) => data.data
  });

  // Fetch all users for filters
  const { data: users } = useQuery('users', async () => {
    const response = await axios.get('/auth/users');
    return response.data;
  });

  const handleFilterChange = (field, value) => {
    setFilters(prev => ({
      ...prev,
      [field]: value
    }));
    setCurrentPage(1);
  };

  const handleDateRangeChange = (field, value) => {
    const newDateRange = {
      ...dateRange,
      [field]: value
    };
    
    // Validate that end date is not before start date
    if (newDateRange.startDate && newDateRange.endDate) {
      if (new Date(newDateRange.endDate) < new Date(newDateRange.startDate)) {
        alert('End date must be after start date');
        return;
      }
    }
    
    setDateRange(newDateRange);
  };

  const downloadCSV = () => {
    if (!allSessions || allSessions.length === 0) {
      alert('No data to export');
      return;
    }

    const headers = ['Equipment', 'Equipment ID', 'User', 'Start Time', 'End Time', 'Duration (hours)', 'Status', 'Description'];
    const csvData = allSessions.map(session => {
      const duration = session.end_time 
        ? ((new Date(session.end_time) - new Date(session.start_time)) / (1000 * 60 * 60)).toFixed(2)
        : '-';
      
      return [
        session.equipment?.name || '',
        session.equipment?.equipment_id || '',
        session.user?.name || '',
        format(new Date(session.start_time), 'MMM d, yyyy h:mm a'),
        session.end_time ? format(new Date(session.end_time), 'MMM d, yyyy h:mm a') : '-',
        duration,
        session.status || '',
        (session.description || '').replace(/,/g, ';')
      ];
    });

    const csvContent = [
      headers.join(','),
      ...csvData.map(row => row.join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `sessions-export-${format(new Date(), 'yyyy-MM-dd')}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handlePrint = () => {
    if (!allSessions || allSessions.length === 0) {
      alert('No data to print');
      return;
    }

    // Create printable content
    const printWindow = window.open('', '_blank');
    const printContent = `
      <!DOCTYPE html>
      <html>
      <head>
        <title>Sessions Report - ${format(new Date(), 'MMM d, yyyy')}</title>
        <style>
          body {
            font-family: Arial, sans-serif;
            padding: 20px;
            color: #333;
          }
          h1 {
            color: #0d9488;
            border-bottom: 3px solid #0d9488;
            padding-bottom: 10px;
          }
          .filters {
            background: #f0fdfa;
            padding: 15px;
            margin: 20px 0;
            border-radius: 8px;
            border: 2px solid #0d9488;
          }
          table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
          }
          th, td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
            font-size: 12px;
          }
          th {
            background-color: #0d9488;
            color: white;
          }
          tr:nth-child(even) {
            background-color: #f9fafb;
          }
          .active {
            color: #059669;
            font-weight: bold;
          }
          .completed {
            color: #6b7280;
          }
          @media print {
            button { display: none; }
          }
        </style>
      </head>
      <body>
        <h1>Equipment Usage Sessions Report</h1>
        <div class="filters">
          <strong>Date Range:</strong> ${format(new Date(dateRange.startDate), 'MMM d, yyyy')} to ${format(new Date(dateRange.endDate), 'MMM d, yyyy')}<br/>
          ${filters.equipment.length > 0 ? `<strong>Equipment:</strong> ${filters.equipment.map(id => equipment?.find(e => e.id == id)?.name).filter(Boolean).join(', ')}<br/>` : ''}
          ${filters.user.length > 0 ? `<strong>User:</strong> ${filters.user.map(id => users?.find(u => u.id == id)?.name).filter(Boolean).join(', ')}<br/>` : ''}
          ${filters.status.length > 0 ? `<strong>Status:</strong> ${filters.status.join(', ')}<br/>` : ''}
          <strong>Total Sessions:</strong> ${allSessions.length}
        </div>
        <table>
          <thead>
            <tr>
              <th>Equipment</th>
              <th>Equipment ID</th>
              <th>User</th>
              <th>Start Time</th>
              <th>End Time</th>
              <th>Duration</th>
              <th>Status</th>
              <th>Description</th>
            </tr>
          </thead>
          <tbody>
            ${allSessions.slice(0, 500).map(session => {
              const duration = session.end_time 
                ? ((new Date(session.end_time) - new Date(session.start_time)) / (1000 * 60 * 60)).toFixed(2)
                : '-';
              
              return `
                <tr>
                  <td>${session.equipment?.name || ''}</td>
                  <td>${session.equipment?.equipment_id || ''}</td>
                  <td>${session.user?.name || ''}</td>
                  <td>${format(new Date(session.start_time), 'MMM d, h:mm a')}</td>
                  <td>${session.end_time ? format(new Date(session.end_time), 'MMM d, h:mm a') : '-'}</td>
                  <td>${duration}h</td>
                  <td class="${session.status === 'ACTIVE' ? 'active' : 'completed'}">${session.status}</td>
                  <td>${session.description || '-'}</td>
                </tr>
              `;
            }).join('')}
          </tbody>
        </table>
        ${allSessions.length > 500 ? '<p style="margin-top: 20px; color: #dc2626;"><strong>Note:</strong> Only showing first 500 sessions for performance. Use CSV export for complete data.</p>' : ''}
        <p style="margin-top: 30px; color: #6b7280; font-size: 12px;">Generated on ${format(new Date(), 'MMM d, yyyy h:mm a')}</p>
      </body>
      </html>
    `;
    
    printWindow.document.write(printContent);
    printWindow.document.close();
    printWindow.focus();
    setTimeout(() => {
      printWindow.print();
    }, 250);
  };

  // Calculate statistics (only showing active sessions, unique users, and unique equipment)
  const stats = {
    active_sessions: allSessions?.filter(s => s.status?.toUpperCase() === 'ACTIVE').length || 0,
    completed_sessions: allSessions?.filter(s => s.status?.toUpperCase() === 'COMPLETED').length || 0,
    unique_users: new Set(allSessions?.map(s => s.user?.id)).size || 0,
    unique_equipment: new Set(allSessions?.map(s => s.equipment?.id)).size || 0
  };

  // Pagination
  const paginatedSessions = allSessions?.slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE
  ) || [];

  if (loadingSessions) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-teal-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="sm:flex sm:items-center sm:justify-between">
        <div className="sm:flex-auto">
          <h1 className="text-2xl font-semibold text-gray-900">Admin Dashboard</h1>
          <p className="mt-2 text-sm text-gray-700">
            Monitor all equipment usage, users, and sessions in real-time
          </p>
        </div>
      </div>

      {/* Stats Cards - Only 2 cards on top */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
        <div className="bg-white overflow-hidden shadow-lg rounded-lg border-2 border-transparent hover:border-teal-500 transition-all duration-300">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <UserGroupIcon className="h-8 w-8 text-green-600" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Unique Users</dt>
                  <dd className="text-3xl font-semibold text-gray-900">{stats.unique_users}</dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow-lg rounded-lg border-2 border-transparent hover:border-teal-500 transition-all duration-300">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <BeakerIcon className="h-8 w-8 text-purple-600" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Equipment Used</dt>
                  <dd className="text-3xl font-semibold text-gray-900">{stats.unique_equipment}</dd>
                </dl>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Filters - More Prominent */}
      <div className="bg-gradient-to-r from-teal-50 to-blue-50 shadow-xl rounded-xl p-8">
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-5">
          <div>
            <label htmlFor="start-date" className="block text-sm font-bold text-gray-700 mb-2">
              Start Date *
            </label>
            <input
              type="date"
              id="start-date"
              value={dateRange.startDate}
              onChange={(e) => handleDateRangeChange('startDate', e.target.value)}
              className="block w-full rounded-lg border-2 border-teal-600 shadow-sm focus:border-teal-700 focus:ring-teal-600 sm:text-sm px-4 py-3"
            />
          </div>
          <div>
            <label htmlFor="end-date" className="block text-sm font-bold text-gray-700 mb-2">
              End Date *
            </label>
            <input
              type="date"
              id="end-date"
              value={dateRange.endDate}
              onChange={(e) => handleDateRangeChange('endDate', e.target.value)}
              className="block w-full rounded-lg border-2 border-teal-600 shadow-sm focus:border-teal-700 focus:ring-teal-600 sm:text-sm px-4 py-3"
            />
          </div>
          <MultiSelect
            label="Equipment"
            options={equipment?.map(eq => ({ value: String(eq.id), label: eq.name })) || []}
            selected={filters.equipment}
            onChange={(selected) => handleFilterChange('equipment', selected)}
            placeholder="All Equipment"
            searchable={true}
          />
          <MultiSelect
            label="User"
            options={users?.map(user => ({ value: String(user.id), label: user.name })) || []}
            selected={filters.user}
            onChange={(selected) => handleFilterChange('user', selected)}
            placeholder="All Users"
            searchable={true}
          />
          <MultiSelect
            label="Status"
            options={[
              { value: 'ACTIVE', label: 'Active' },
              { value: 'COMPLETED', label: 'Completed' }
            ]}
            selected={filters.status}
            onChange={(selected) => handleFilterChange('status', selected)}
            placeholder="All Status"
            searchable={false}
          />
        </div>
      </div>

      {/* Sessions Table */}
      <div className="bg-white shadow-lg rounded-lg overflow-hidden border-2 border-teal-600">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <h3 className="text-lg font-medium text-gray-900">
            All Sessions ({allSessions?.length || 0})
          </h3>
          <div className="flex gap-3">
            <button
              onClick={handlePrint}
              className="inline-flex items-center justify-center rounded-md border border-transparent bg-teal-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-teal-700 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 transition-all duration-200"
            >
              <PrinterIcon className="h-5 w-5 mr-2" />
              Print Report
            </button>
            <button
              onClick={downloadCSV}
              className="inline-flex items-center justify-center rounded-md border border-transparent bg-blue-500 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-all duration-200"
            >
              <ArrowDownTrayIcon className="h-5 w-5 mr-2" />
              Export CSV
            </button>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Equipment</th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">User</th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Start Time</th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">End Time</th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Duration</th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Description</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {paginatedSessions.map((session) => {
                const duration = session.end_time 
                  ? ((new Date(session.end_time) - new Date(session.start_time)) / (1000 * 60 * 60)).toFixed(2)
                  : '-';
                
                return (
                  <tr key={session.id} className="hover:bg-gray-50">
                    <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">
                      <div>
                        <div className="font-medium">{session.equipment?.name}</div>
                        <div className="text-gray-500">{session.equipment?.equipment_id}</div>
                      </div>
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">{session.user?.name}</td>
                    <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">
                      {format(new Date(session.start_time), 'MMM d, h:mm a')}
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">
                      {session.end_time ? format(new Date(session.end_time), 'MMM d, h:mm a') : '-'}
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">{duration}h</td>
                    <td className="px-4 py-4 whitespace-nowrap">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        session.status === 'ACTIVE' 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-gray-100 text-gray-800'
                      }`}>
                        {session.status}
                      </span>
                    </td>
                    <td className="px-4 py-4 text-sm text-gray-900">
                      {session.description 
                        ? (session.description.length > 30 
                          ? session.description.substring(0, 30) + '...' 
                          : session.description)
                        : '-'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {allSessions && allSessions.length > ITEMS_PER_PAGE && (
          <div className="px-6 py-4 border-t border-gray-200">
            <Pagination
              totalItems={allSessions.length}
              itemsPerPage={ITEMS_PER_PAGE}
              currentPage={currentPage}
              onPageChange={setCurrentPage}
            />
          </div>
        )}
      </div>

      {/* Analytics Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Equipment Utilization Chart */}
        <div className="bg-white shadow-lg rounded-lg p-6 border-2 border-teal-600">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Equipment Utilization</h3>
          {(() => {
            const equipmentUsage = {};
            allSessions?.forEach(session => {
              const eqId = session.equipment?.id;
              const eqName = session.equipment?.name;
              if (eqId && eqName) {
                if (!equipmentUsage[eqId]) {
                  equipmentUsage[eqId] = { name: eqName, sessions: 0, hours: 0 };
                }
                equipmentUsage[eqId].sessions++;
                if (session.end_time) {
                  const hours = (new Date(session.end_time) - new Date(session.start_time)) / (1000 * 60 * 60);
                  equipmentUsage[eqId].hours += hours;
                }
              }
            });

            const chartData = Object.values(equipmentUsage)
              .sort((a, b) => b.sessions - a.sessions)
              .slice(0, 8)
              .map(eq => ({
                name: eq.name.length > 15 ? eq.name.substring(0, 15) + '...' : eq.name,
                sessions: eq.sessions,
                hours: parseFloat(eq.hours.toFixed(1))
              }));

            return chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" angle={-45} textAnchor="end" height={100} style={{ fontSize: '12px' }} />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="sessions" fill="#0d9488" name="Sessions" />
                  <Bar dataKey="hours" fill="#3b82f6" name="Hours" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-sm text-gray-500 text-center py-4">No data available</p>
            );
          })()}
        </div>

        {/* Top Users Chart */}
        <div className="bg-white shadow-lg rounded-lg p-6 border-2 border-teal-600">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Top Users by Activity</h3>
          {(() => {
            const userActivity = {};
            allSessions?.forEach(session => {
              const userId = session.user?.id;
              const userName = session.user?.name;
              if (userId && userName) {
                if (!userActivity[userId]) {
                  userActivity[userId] = { name: userName, sessions: 0, hours: 0 };
                }
                userActivity[userId].sessions++;
                if (session.end_time) {
                  const hours = (new Date(session.end_time) - new Date(session.start_time)) / (1000 * 60 * 60);
                  userActivity[userId].hours += hours;
                }
              }
            });

            const chartData = Object.values(userActivity)
              .sort((a, b) => b.sessions - a.sessions)
              .slice(0, 8)
              .map(user => ({
                name: user.name.length > 15 ? user.name.substring(0, 15) + '...' : user.name,
                sessions: user.sessions,
                hours: parseFloat(user.hours.toFixed(1))
              }));

            return chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" angle={-45} textAnchor="end" height={100} style={{ fontSize: '12px' }} />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="sessions" fill="#0d9488" name="Sessions" />
                  <Bar dataKey="hours" fill="#3b82f6" name="Hours" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-sm text-gray-500 text-center py-4">No data available</p>
            );
          })()}
        </div>
      </div>
    </div>
  );
}

export default AdminDashboard;