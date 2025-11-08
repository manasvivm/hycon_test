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

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1, // Only retry once
      refetchOnWindowFocus: false, // Don't refetch on window focus
      staleTime: 30000, // Consider data fresh for 30 seconds
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
            </Route>
          </Routes>
        </Router>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;