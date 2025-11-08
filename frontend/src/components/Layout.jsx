import { useAuth } from '../contexts/AuthContext';
import { Link, useLocation, useNavigate, Outlet } from 'react-router-dom';

function Layout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const isActive = (path) => location.pathname === path;

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Navigation Header */}
      <nav className="bg-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex justify-between h-16">
            <div className="flex">
              <div className="flex-shrink-0 flex items-center gap-3">
                <img src="/image.png" alt="HyCON Logo" className="h-14 w-auto" />
              </div>
              <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                <Link
                  to="/"
                  className={`${
                    isActive('/')
                      ? 'border-teal-500 text-gray-900 bg-teal-50'
                      : 'border-transparent text-gray-500 hover:border-teal-500 hover:text-teal-700 hover:bg-teal-50'
                  } inline-flex items-center px-4 pt-1 border-b-2 text-sm font-medium transition-all duration-200`}
                >
                  Dashboard
                </Link>
                <Link
                  to="/equipment"
                  className={`${
                    isActive('/equipment')
                      ? 'border-teal-500 text-gray-900 bg-teal-50'
                      : 'border-transparent text-gray-500 hover:border-teal-500 hover:text-teal-700 hover:bg-teal-50'
                  } inline-flex items-center px-4 pt-1 border-b-2 text-sm font-medium transition-all duration-200`}
                >
                  Equipment
                </Link>
                <Link
                  to="/sessions"
                  className={`${
                    isActive('/sessions')
                      ? 'border-teal-500 text-gray-900 bg-teal-50'
                      : 'border-transparent text-gray-500 hover:border-teal-500 hover:text-teal-700 hover:bg-teal-50'
                  } inline-flex items-center px-4 pt-1 border-b-2 text-sm font-medium transition-all duration-200`}
                >
                  Sessions
                </Link>
                {user?.role === 'admin' && (
                  <>
                    <Link
                      to="/admin"
                      className={`${
                        isActive('/admin')
                          ? 'border-teal-500 text-gray-900 bg-teal-50'
                          : 'border-transparent text-gray-500 hover:border-teal-500 hover:text-teal-700 hover:bg-teal-50'
                      } inline-flex items-center px-4 pt-1 border-b-2 text-sm font-medium transition-all duration-200`}
                    >
                      Admin Dashboard
                    </Link>
                    <Link
                      to="/admin/equipment"
                      className={`${
                        isActive('/admin/equipment')
                          ? 'border-teal-500 text-gray-900 bg-teal-50'
                          : 'border-transparent text-gray-500 hover:border-teal-500 hover:text-teal-700 hover:bg-teal-50'
                      } inline-flex items-center px-4 pt-1 border-b-2 text-sm font-medium transition-all duration-200`}
                    >
                      Manage Equipment
                    </Link>
                  </>
                )}
              </div>
            </div>
            <div className="flex items-center">
              <span className="text-gray-700 mr-4">{user?.name}</span>
              <button
                onClick={handleLogout}
                className="bg-teal-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-teal-700 hover:shadow-lg transition-all duration-200"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <Outlet />
      </main>
    </div>
  );
}

export default Layout;