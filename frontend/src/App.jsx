import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from 'react-query';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import Layout from './components/Layout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import EquipmentList from './pages/EquipmentList';
import SessionManager from './pages/SessionManager';
import AdminDashboard from './pages/AdminDashboard';
import EquipmentManagement from './pages/EquipmentManagement';
import SampleSubmission from './pages/SampleSubmission';
import EmailRecipients from './pages/EmailRecipients';

// Create optimized QueryClient with performance-focused settings
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2, // Retry failed requests twice (handles network hiccups)
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 3000), // Exponential backoff
      refetchOnWindowFocus: false, // Don't refetch on window focus
      refetchOnMount: true, // Refetch on component mount
      refetchOnReconnect: true, // Refetch when connection restored
      staleTime: 30000, // Consider data fresh for 30 seconds
      cacheTime: 5 * 60 * 1000, // Keep unused data in cache for 5 minutes
      suspense: false, // Don't use React Suspense
      useErrorBoundary: false, // Don't throw errors to error boundary
    },
    mutations: {
      retry: 1, // Retry mutations once
      retryDelay: 1000, // 1 second delay before retry
    },
  },
});

function PrivateRoute({ children }) {
  const { isAuthenticated, user } = useAuth();
  
  if (!isAuthenticated) {
    return <Navigate to="/login" />;
  }
  
  return children;
}

function AdminRoute({ children }) {
  const { isAuthenticated, user } = useAuth();
  
  if (!isAuthenticated) {
    return <Navigate to="/login" />;
  }
  
  if (user?.role !== 'admin') {
    return <Navigate to="/" />;
  }
  
  return children;
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <Router>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route
              path="/"
              element={
                <PrivateRoute>
                  <Layout />
                </PrivateRoute>
              }
            >
              <Route index element={<Dashboard />} />
              <Route path="equipment" element={<EquipmentList />} />
              <Route path="sessions" element={<SessionManager />} />
              <Route path="samples" element={<SampleSubmission />} />
              <Route
                path="admin"
                element={
                  <AdminRoute>
                    <AdminDashboard />
                  </AdminRoute>
                }
              />
              <Route
                path="admin/equipment"
                element={
                  <AdminRoute>
                    <EquipmentManagement />
                  </AdminRoute>
                }
              />
              <Route
                path="admin/emails"
                element={
                  <AdminRoute>
                    <EmailRecipients />
                  </AdminRoute>
                }
              />
            </Route>
          </Routes>
        </Router>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;