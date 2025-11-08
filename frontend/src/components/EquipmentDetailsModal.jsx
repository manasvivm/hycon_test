import { Fragment, useState, useEffect } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { XMarkIcon, ClockIcon } from '@heroicons/react/24/outline';
import { format } from 'date-fns';
import LogPastUsageModal from './LogPastUsageModal';

function formatDuration(ms) {
  const hours = Math.floor(ms / (1000 * 60 * 60));
  const minutes = Math.floor((ms % (1000 * 60 * 60)) / (1000 * 60));
  return `${hours}h ${minutes}m`;
}

export default function EquipmentDetailsModal({ isOpen, onClose, equipment, onStartSession, onLogPastUsage }) {
  const [showLogPastModal, setShowLogPastModal] = useState(false);
  const [historyPage, setHistoryPage] = useState(1);
  const [localEquipment, setLocalEquipment] = useState(equipment);
  const HISTORY_PER_PAGE = 10;
  
  // Update local equipment when prop changes
  useEffect(() => {
    if (equipment) {
      console.log('EquipmentDetailsModal - equipment prop:', equipment);
      console.log('EquipmentDetailsModal - equipment.current_status:', equipment.current_status);
      setLocalEquipment(equipment);
    }
  }, [equipment]);
  
  // Reset history page when modal opens
  useEffect(() => {
    if (isOpen) {
      setHistoryPage(1);
    }
  }, [isOpen]);
  
  if (!localEquipment) return null;

  const isAvailable = localEquipment.current_status?.toUpperCase() === 'AVAILABLE';
  console.log('EquipmentDetailsModal - isAvailable:', isAvailable, 'status:', localEquipment.current_status);
  
  // Pagination for usage history
  const totalSessions = localEquipment.usage_sessions?.length || 0;
  const totalPages = Math.ceil(totalSessions / HISTORY_PER_PAGE);
  const startIndex = (historyPage - 1) * HISTORY_PER_PAGE;
  const endIndex = startIndex + HISTORY_PER_PAGE;
  const paginatedSessions = localEquipment.usage_sessions?.slice(startIndex, endIndex) || [];

  return (
    <Transition.Root show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-10" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" />
        </Transition.Child>

        <div className="fixed inset-0 z-10 overflow-y-auto">
          <div className="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
              enterTo="opacity-100 translate-y-0 sm:scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 translate-y-0 sm:scale-100"
              leaveTo="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
            >
              <Dialog.Panel className="relative transform overflow-hidden rounded-lg bg-white px-4 pt-5 pb-4 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-4xl sm:p-6">
                <div className="absolute top-0 right-0 hidden pt-4 pr-4 sm:block">
                  <button
                    type="button"
                    className="rounded-md bg-white text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2"
                    onClick={onClose}
                  >
                    <span className="sr-only">Close</span>
                    <XMarkIcon className="h-6 w-6" aria-hidden="true" />
                  </button>
                </div>
                <div>
                  <div className="mt-3 sm:mt-5">
                    <Dialog.Title as="h3" className="text-lg font-medium leading-6 text-gray-900">
                      Equipment Details
                    </Dialog.Title>
                    <div className="mt-5">
                      <dl className="grid grid-cols-1 gap-x-4 gap-y-6 sm:grid-cols-2">
                        <div>
                          <dt className="text-sm font-medium text-gray-500">Name</dt>
                          <dd className="mt-1 text-sm text-gray-900">{localEquipment.name}</dd>
                        </div>
                        <div>
                          <dt className="text-sm font-medium text-gray-500">Equipment ID</dt>
                          <dd className="mt-1 text-sm text-gray-900">{localEquipment.equipment_id}</dd>
                        </div>
                        <div>
                          <dt className="text-sm font-medium text-gray-500">Status</dt>
                          <dd className="mt-1">
                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                              isAvailable ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                            }`}>
                              {localEquipment.current_status}
                            </span>
                          </dd>
                        </div>
                        {localEquipment.current_user && (
                          <div>
                            <dt className="text-sm font-medium text-gray-500">Current User</dt>
                            <dd className="mt-1 text-sm text-gray-900">{localEquipment.current_user.name}</dd>
                          </div>
                        )}
                        {localEquipment.current_session_start && (
                          <div>
                            <dt className="text-sm font-medium text-gray-500">Session Started</dt>
                            <dd className="mt-1 text-sm text-gray-900">
                              {format(new Date(localEquipment.current_session_start), 'MMM d, yyyy h:mm a')}
                            </dd>
                          </div>
                        )}
                        <div className="sm:col-span-2">
                          <dt className="text-sm font-medium text-gray-500">Location</dt>
                          <dd className="mt-1 text-sm text-gray-900">{localEquipment.location || '-'}</dd>
                        </div>
                        <div className="sm:col-span-2">
                          <dt className="text-sm font-medium text-gray-500">Description</dt>
                          <dd className="mt-1 text-sm text-gray-900">{localEquipment.description || '-'}</dd>
                        </div>
                      </dl>
                    </div>
                  </div>
                </div>

                {/* Action Buttons Section */}
                <div className="mt-6 pt-6 border-t">
                  <div className="grid grid-cols-2 gap-3">
                    <button
                      type="button"
                      onClick={() => {
                        console.log('Start Session clicked, isAvailable:', isAvailable);
                        console.log('onStartSession:', onStartSession);
                        if (isAvailable && onStartSession) {
                          onStartSession(localEquipment);
                        }
                      }}
                      disabled={!isAvailable}
                      className={`w-full inline-flex items-center justify-center rounded-md border border-transparent px-4 py-2 text-sm font-medium text-white shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 ${
                        isAvailable
                          ? 'bg-blue-500 hover:bg-blue-600 focus:ring-blue-500'
                          : 'bg-gray-300 cursor-not-allowed'
                      }`}
                    >
                      Start New Session
                    </button>
                    <button
                      type="button"
                      onClick={() => setShowLogPastModal(true)}
                      className="w-full inline-flex items-center justify-center rounded-md border border-teal-600 bg-teal-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-teal-700 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2"
                    >
                      <ClockIcon className="mr-2 h-4 w-4" />
                      Log Past Usage
                    </button>
                  </div>
                </div>

                {/* Session History */}
                <div className="mt-6 border-t pt-6">
                  <div className="flex justify-between items-center mb-4">
                    <h4 className="text-base font-medium text-gray-900">
                      Recent Usage History
                      {totalSessions > 0 && (
                        <span className="ml-2 text-sm text-gray-500">
                          ({totalSessions} total sessions)
                        </span>
                      )}
                    </h4>
                  </div>
                  {localEquipment.usage_sessions && localEquipment.usage_sessions.length > 0 ? (
                    <>
                      <div className="mt-4 overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                          <thead>
                            <tr>
                              <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">User</th>
                              <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Start Time</th>
                              <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">End Time</th>
                              <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Duration</th>
                              <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Description</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-gray-200">
                            {paginatedSessions.map((session) => (
                          <tr key={session.id}>
                            <td className="px-4 py-3 text-sm text-gray-900">{session.user?.name}</td>
                            <td className="px-4 py-3 text-sm text-gray-900">
                              {format(new Date(session.start_time), 'MMM d, yyyy h:mm a')}
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-900">
                              {session.end_time ? format(new Date(session.end_time), 'MMM d, yyyy h:mm a') : '-'}
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-900">
                              {session.end_time ? 
                                formatDuration(new Date(session.end_time) - new Date(session.start_time)) : 
                                'Active'}
                            </td>
                              <td className="px-4 py-3 text-sm text-gray-900">{session.description || '-'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    
                    {/* Pagination Controls */}
                    {totalPages > 1 && (
                      <div className="mt-4 flex items-center justify-between border-t border-gray-200 bg-white px-4 py-3 sm:px-6">
                        <div className="flex flex-1 justify-between sm:hidden">
                          <button
                            onClick={() => setHistoryPage(Math.max(1, historyPage - 1))}
                            disabled={historyPage === 1}
                            className="relative inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            Previous
                          </button>
                          <button
                            onClick={() => setHistoryPage(Math.min(totalPages, historyPage + 1))}
                            disabled={historyPage === totalPages}
                            className="relative ml-3 inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            Next
                          </button>
                        </div>
                        <div className="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
                          <div>
                            <p className="text-sm text-gray-700">
                              Showing <span className="font-medium">{startIndex + 1}</span> to{' '}
                              <span className="font-medium">{Math.min(endIndex, totalSessions)}</span> of{' '}
                              <span className="font-medium">{totalSessions}</span> sessions
                            </p>
                          </div>
                          <div>
                            <nav className="isolate inline-flex -space-x-px rounded-md shadow-sm" aria-label="Pagination">
                              <button
                                onClick={() => setHistoryPage(Math.max(1, historyPage - 1))}
                                disabled={historyPage === 1}
                                className="relative inline-flex items-center rounded-l-md px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0 disabled:opacity-50 disabled:cursor-not-allowed"
                              >
                                <span className="sr-only">Previous</span>
                                ‹
                              </button>
                              {[...Array(totalPages)].map((_, i) => (
                                <button
                                  key={i + 1}
                                  onClick={() => setHistoryPage(i + 1)}
                                  className={`relative inline-flex items-center px-4 py-2 text-sm font-semibold ${
                                    historyPage === i + 1
                                      ? 'z-10 bg-teal-600 text-white focus:z-20 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-600'
                                      : 'text-gray-900 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0'
                                  }`}
                                >
                                  {i + 1}
                                </button>
                              ))}
                              <button
                                onClick={() => setHistoryPage(Math.min(totalPages, historyPage + 1))}
                                disabled={historyPage === totalPages}
                                className="relative inline-flex items-center rounded-r-md px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0 disabled:opacity-50 disabled:cursor-not-allowed"
                              >
                                <span className="sr-only">Next</span>
                                ›
                              </button>
                            </nav>
                          </div>
                        </div>
                      </div>
                    )}
                  </>
                  ) : (
                    <p className="mt-4 text-sm text-gray-500 text-center py-4">No usage history available</p>
                  )}
                </div>

                <div className="mt-5 sm:mt-6 flex justify-end">
                  <button
                    type="button"
                    className="inline-flex justify-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2"
                    onClick={onClose}
                  >
                    Close
                  </button>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>

      {/* Log Past Usage Modal */}
      {onLogPastUsage && (
        <LogPastUsageModal 
          isOpen={showLogPastModal}
          onClose={() => setShowLogPastModal(false)}
          equipment={localEquipment}
          isLoading={false}
          onSubmit={async (data) => {
            await onLogPastUsage(data);
            setShowLogPastModal(false);
          }}
        />
      )}
    </Transition.Root>
  );
}