import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Configure axios defaults
axios.defaults.baseURL = BASE_URL;
axios.defaults.withCredentials = true;

// Add request interceptor to add token to all requests
axios.interceptors.request.use(function (config) {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, function (error) {
  return Promise.reject(error);
});

// Equipment API
export const equipmentApi = {
  getAll: () => axios.get('/equipment'),
  getById: (id) => axios.get(`/equipment/${id}`),
  create: (data) => axios.post('/equipment', data),
  update: (id, data) => axios.put(`/equipment/${id}`, data),
  delete: (id) => axios.delete(`/equipment/${id}`),
  getDescriptionSuggestions: (query) => 
    axios.get(`/equipment/descriptions/suggestions?query=${query}`),
};

// Session API
export const sessionApi = {
  startSession: (data) => axios.post('/sessions/start', data),
  logPastUsage: (data) => axios.post('/sessions/log-past-usage', data),
  endSession: (sessionId, data) => axios.put(`/sessions/${sessionId}/end`, data),
  getMySessions: () => axios.get('/sessions/my-sessions'),
  getMyActiveSessions: () => axios.get('/sessions/my-active'),  // Changed to expect multiple sessions
  getMyActiveSession: () => axios.get('/sessions/my-active'),  // Keep for backward compatibility
  checkConflict: (data) => axios.post('/sessions/check-conflict', data),
};

// Analytics API
export const analyticsApi = {
  getEquipmentUtilization: (startDate, endDate) => 
    axios.get(`/analytics/equipment-utilization?start_date=${startDate}&end_date=${endDate}`),
  getUserActivity: (startDate, endDate) =>
    axios.get(`/analytics/user-activity?start_date=${startDate}&end_date=${endDate}`),
  generateReport: (startDate, endDate) =>
    axios.get(`/analytics/generate-report?start_date=${startDate}&end_date=${endDate}`, 
      { responseType: 'blob' }),
};