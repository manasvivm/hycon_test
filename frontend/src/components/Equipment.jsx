import { format } from 'date-fns';

// Status Badge Component
function StatusBadge({ status }) {
  const colors = {
    AVAILABLE: 'bg-green-100 text-green-800',
    IN_USE: 'bg-blue-100 text-blue-800',
    MAINTENANCE: 'bg-red-100 text-red-800'
  };

  const labels = {
    AVAILABLE: 'Available',
    IN_USE: 'In Use',
    MAINTENANCE: 'Maintenance'
  };

  const normalizedStatus = (status || 'MAINTENANCE').toUpperCase();

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colors[normalizedStatus]}`}>
      {labels[normalizedStatus]}
    </span>
  );
}

// Equipment Card Component
function EquipmentCard({ equipment, onSelect, activeSessions = [] }) {
  // Check if this equipment is in use by the current user
  const userSession = activeSessions?.find(session => session.equipment.id === equipment.id);
  const handleStartSession = (e) => {
    e.stopPropagation();
    onSelect(equipment);
  };

  return (
    <div className="bg-white overflow-hidden shadow-lg rounded-lg divide-y divide-gray-200 hover:shadow-2xl hover:border-2 hover:border-teal-500 transition-all duration-300 border-2 border-transparent">
      <div className="px-4 py-5 sm:p-6">
        <div className="flex justify-between items-start">
          <div>
            <h3 className="text-lg font-medium text-gray-900">{equipment.name}</h3>
            <p className="mt-1 text-sm text-gray-500">{equipment.equipment_id}</p>
          </div>
          <StatusBadge status={equipment.current_status} />
        </div>
        
        <div className="mt-4">
          <p className="text-sm text-gray-500">
            {equipment.description 
              ? (equipment.description.length > 50 
                ? equipment.description.substring(0, 50) + '...' 
                : equipment.description)
              : 'No description available.'}
          </p>
          {equipment.location && (
            <p className="mt-2 text-sm text-gray-500">
              <span className="font-medium">Location:</span> {equipment.location}
            </p>
          )}
        </div>

        {equipment.current_status === 'IN_USE' && (
          <div className={`mt-4 ${userSession ? 'bg-orange-50' : 'bg-yellow-50'} p-3 rounded-md`}>
            <p className={`text-sm ${userSession ? 'text-orange-800' : 'text-yellow-800'}`}>
              {userSession ? (
                'You are currently using this equipment'
              ) : (
                <>
                  In use by: {equipment.current_user?.name || 'Unknown'}
                  {equipment.current_session_start && (
                    <>
                      <br />
                      Since: {format(new Date(equipment.current_session_start), 'h:mm a')}
                    </>
                  )}
                </>
              )}
            </p>
          </div>
        )}

        <div className="mt-5 space-y-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onSelect({ type: 'START_SESSION', equipment });
            }}
            disabled={equipment.current_status !== 'AVAILABLE' || userSession}
            className={`w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white transition-all duration-200
              ${equipment.current_status === 'AVAILABLE' && !userSession
                ? 'bg-teal-600 hover:bg-teal-700 hover:shadow-lg' 
                : 'bg-gray-300 cursor-not-allowed'}`}
          >
            Start Session
          </button>
          
          <button
            onClick={(e) => {
              e.stopPropagation();
              onSelect({ type: 'LOG_PAST_USAGE', equipment });
            }}
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-500 hover:bg-blue-600 hover:shadow-lg transition-all duration-200"
          >
            Log Past Usage
          </button>

          <button
            onClick={(e) => {
              e.stopPropagation();
              onSelect({ type: 'CLOSE', equipment });
            }}
            className="w-full flex justify-center py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 hover:shadow transition-all duration-200"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

// Active Session Card Component
function ActiveSessionCard({ session }) {
  if (!session) return null;

  return (
    <div className="bg-white overflow-hidden shadow rounded-lg">
      <div className="p-5">
        <div className="flex items-center">
          <div className="flex-shrink-0">
            <div className="h-10 w-10 rounded-full bg-teal-100 flex items-center justify-center">
              <svg className="h-6 w-6 text-teal-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
          <div className="ml-4">
            <h4 className="text-lg font-medium text-gray-900">{session.equipment?.name}</h4>
            <p className="text-sm text-gray-500">{session.equipment?.equipment_id}</p>
          </div>
        </div>
        <div className="mt-4 border-t border-gray-200 pt-4">
          <dl className="grid grid-cols-1 gap-x-4 gap-y-4 sm:grid-cols-2">
            <div>
              <dt className="text-sm font-medium text-gray-500">Start Time</dt>
              <dd className="mt-1 text-sm text-gray-900">
                {format(new Date(session.start_time), 'MMM d, yyyy h:mm a')}
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500">Description</dt>
              <dd className="mt-1 text-sm text-gray-900">{session.description || 'N/A'}</dd>
            </div>
          </dl>
        </div>
      </div>
    </div>
  );
}

// Export all components
export {
  StatusBadge,
  EquipmentCard,
  ActiveSessionCard
};