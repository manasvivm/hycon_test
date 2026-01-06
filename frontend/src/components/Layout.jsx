import { useAuth } from '../contexts/AuthContext';
import { Link, useLocation, useNavigate, Outlet } from 'react-router-dom';
import { useState } from 'react';

function Layout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const isActive = (path) => location.pathname === path;

  const navItems = [
    { path: '/', label: 'Dashboard', icon: '📊' },
    { path: '/equipment', label: 'Equipment', icon: '🔬' },
    { path: '/sessions', label: 'Sessions', icon: '📅' },
    { path: '/samples', label: 'Sample Submission', icon: '📋' },
  ];

  const adminItems = user?.role === 'admin' ? [
    { path: '/admin', label: 'Admin Dashboard', icon: '⚙️' },
    { path: '/admin/equipment', label: 'Manage Equipment', icon: '🛠️' },
    { path: '/admin/emails', label: 'Email Recipients', icon: '✉️' },
  ] : [];

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Sidebar */}
      <div className={`${sidebarOpen ? 'w-64' : 'w-20'} bg-gradient-to-b from-gray-900 to-gray-800 text-white transition-all duration-300 flex flex-col shadow-2xl`}>
        {/* Logo & Toggle - Fixed height to match header */}
        <div className="h-[73px] px-4 flex items-center justify-between border-b border-gray-700 bg-white">
          <div className="flex items-center justify-center flex-1">
            <img 
              src="/image.png" 
              alt="HyCON" 
              className="h-12 w-auto object-contain"
            />
          </div>
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 rounded-lg hover:bg-gray-100 transition-colors text-gray-700 flex-shrink-0 ml-2"
          >
            {sidebarOpen ? '◀' : '▶'}
          </button>
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 py-6 px-2 space-y-2 overflow-y-auto">
          {/* Main Section */}
          {sidebarOpen && <div className="px-4 py-2 text-xs font-semibold text-gray-400 uppercase tracking-wider">Main</div>}
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 ${
                isActive(item.path)
                  ? 'bg-teal-600 text-white font-semibold shadow-lg'
                  : 'text-gray-300 hover:bg-gray-700 hover:text-white'
              }`}
              title={!sidebarOpen ? item.label : ''}
            >
              <span className="text-xl">{item.icon}</span>
              {sidebarOpen && <span>{item.label}</span>}
            </Link>
          ))}

          {/* Admin Section */}
          {adminItems.length > 0 && (
            <>
              {sidebarOpen && <div className="px-4 py-2 mt-6 text-xs font-semibold text-gray-400 uppercase tracking-wider">Administration</div>}
              {adminItems.map((item) => (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 ${
                    isActive(item.path)
                      ? 'bg-teal-600 text-white font-semibold shadow-lg'
                      : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                  }`}
                  title={!sidebarOpen ? item.label : ''}
                >
                  <span className="text-xl">{item.icon}</span>
                  {sidebarOpen && <span>{item.label}</span>}
                </Link>
              ))}
            </>
          )}
        </nav>

        {/* User Section */}
        <div className="p-4 border-t border-gray-700">
          {sidebarOpen ? (
            <div className="mb-3">
              <div className="text-sm font-semibold">{user?.name}</div>
              <div className="text-xs text-gray-400">{user?.role}</div>
            </div>
          ) : (
            <div className="flex justify-center mb-3 text-2xl" title={user?.name}>
              👤
            </div>
          )}
          <button
            onClick={handleLogout}
            className="w-full bg-red-600 hover:bg-red-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2"
          >
            <span>🚪</span>
            {sidebarOpen && <span>Logout</span>}
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Bar - Fixed height to match sidebar logo section */}
        <div className="h-[73px] bg-white shadow-sm px-6 border-b border-gray-200 flex items-center">
          <h1 className="text-2xl font-bold text-gray-800">
            {navItems.find(item => isActive(item.path))?.label || 
             adminItems.find(item => isActive(item.path))?.label || 
             'HyCON Lab Management'}
          </h1>
        </div>

        {/* Main Content */}
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default Layout;