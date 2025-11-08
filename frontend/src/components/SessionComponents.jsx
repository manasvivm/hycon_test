import { format } from 'date-fns';
import { StatusBadge } from './Equipment';
import Pagination from './Pagination';

export function SessionTable({ sessions, onViewDetails, currentPage, totalSessions, itemsPerPage, onPageChange, onExport }) {
  return (
    <div className="flex flex-col">
      <div className="-my-2 overflow-x-auto sm:-mx-6 lg:-mx-8">
        <div className="py-2 align-middle inline-block min-w-full sm:px-6 lg:px-8">

          <div className="shadow overflow-hidden border-b border-gray-200 sm:rounded-lg">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Equipment
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Start Time
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    End Time
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Description
                  </th>
                  <th scope="col" className="relative px-6 py-3">
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {sessions.map((session) => (
                  <tr key={session.id}>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">{session.equipment.name}</div>
                      <div className="text-sm text-gray-500">ID: {session.equipment.equipment_id}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {format(new Date(session.start_time), 'MMM d, yyyy h:mm a')}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {session.end_time 
                        ? format(new Date(session.end_time), 'MMM d, yyyy h:mm a')
                        : '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <SessionStatusBadge status={session.status} />
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {session.description 
                        ? (session.description.length > 15 
                          ? session.description.substring(0, 15) + '...' 
                          : session.description)
                        : '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <button
                        onClick={() => onViewDetails(session)}
                        className="text-teal-600 hover:text-teal-900"
                      >
                        View Details
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {totalSessions > itemsPerPage && (
            <div className="mt-4">
              <Pagination
                totalItems={totalSessions}
                itemsPerPage={itemsPerPage}
                currentPage={currentPage}
                onPageChange={onPageChange}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export function SessionStatusBadge({ status }) {
  const colors = {
    active: 'bg-green-100 text-green-800',
    completed: 'bg-gray-100 text-gray-800'
  };

  const labels = {
    active: 'Active',
    completed: 'Completed'
  };

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colors[status]}`}>
      {labels[status]}
    </span>
  );
}

export function SessionDetailsModal({ session, isOpen, onClose, onEndSession, isLoading }) {
  if (!session) return null;

  return (
    <div className={`fixed inset-0 overflow-y-auto ${isOpen ? '' : 'hidden'}`}>
      <div className="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" onClick={onClose}></div>

        <div className="inline-block align-bottom bg-white rounded-lg px-4 pt-5 pb-4 text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full sm:p-6">
          <div>
            <div className="mt-3 sm:mt-5">
              <h3 className="text-lg leading-6 font-medium text-gray-900">
                Session Details
              </h3>
              <div className="mt-5">
                <dl className="grid grid-cols-1 gap-x-4 gap-y-6 sm:grid-cols-2">
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Equipment</dt>
                    <dd className="mt-1 text-sm text-gray-900">{session.equipment.name}</dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Equipment ID</dt>
                    <dd className="mt-1 text-sm text-gray-900">{session.equipment.equipment_id}</dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Start Time</dt>
                    <dd className="mt-1 text-sm text-gray-900">
                      {format(new Date(session.start_time), 'MMM d, yyyy h:mm a')}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-gray-500">End Time</dt>
                    <dd className="mt-1 text-sm text-gray-900">
                      {session.end_time 
                        ? format(new Date(session.end_time), 'MMM d, yyyy h:mm a')
                        : '-'}
                    </dd>
                  </div>
                  <div className="sm:col-span-2">
                    <dt className="text-sm font-medium text-gray-500">Description</dt>
                    <dd className="mt-1 text-sm text-gray-900">{session.description || '-'}</dd>
                  </div>
                  <div className="sm:col-span-2">
                    <dt className="text-sm font-medium text-gray-500">Remarks</dt>
                    <dd className="mt-1 text-sm text-gray-900">{session.remarks || '-'}</dd>
                  </div>
                </dl>
              </div>
            </div>
          </div>
          <div className="mt-5 sm:mt-6 sm:grid sm:grid-cols-2 sm:gap-3">
            {session.status === 'active' && (
              <button
                type="button"
                onClick={onEndSession}
                disabled={isLoading}
                className="inline-flex justify-center w-full rounded-md border border-transparent shadow-sm px-4 py-2 bg-red-600 text-base font-medium text-white hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 sm:text-sm"
              >
                {isLoading ? 'Ending...' : 'End Session'}
              </button>
            )}
            <button
              type="button"
              onClick={onClose}
              className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-teal-500 sm:mt-0 sm:text-sm"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}