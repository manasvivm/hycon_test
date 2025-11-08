import { Fragment, useState, useEffect } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { XMarkIcon } from '@heroicons/react/24/outline';
import { format } from 'date-fns';

export default function StartSessionModal({ isOpen, onClose, equipment, onSubmit, isLoading, allEquipment, activeSessions = [] }) {
  const [startTime, setStartTime] = useState(format(new Date(), "yyyy-MM-dd'T'HH:mm"));
  const [endTime, setEndTime] = useState('');
  const [description, setDescription] = useState('');
  const [remarks, setRemarks] = useState('');
  const [selectedEquipmentId, setSelectedEquipmentId] = useState(equipment?.id || '');

  // Reset form when modal opens
  useEffect(() => {
    if (isOpen) {
      setStartTime(format(new Date(), "yyyy-MM-dd'T'HH:mm"));
      setDescription('');
      setRemarks('');
      setSelectedEquipmentId(equipment?.id || '');
    }
  }, [isOpen, equipment]);

  // Get equipment details for validation
  const selectedEquipment = allEquipment?.find(eq => eq.id === Number(selectedEquipmentId));
  const canSubmit = (equipment?.current_status?.toUpperCase() === 'AVAILABLE') || 
                   (selectedEquipment?.current_status?.toUpperCase() === 'AVAILABLE');

  const handleSubmit = (e) => {
    e.preventDefault();
    const equipmentId = Number(selectedEquipmentId || equipment?.id);
    if (!equipmentId) {
      alert('Please select equipment');
      return;
    }

    if (!startTime) {
      alert('Please select a start time');
      return;
    }

    // Create a timezone-aware date from the input
    let date = new Date(startTime);
    // Adjust the date to UTC while preserving the local time
    const offset = date.getTimezoneOffset();
    date = new Date(date.getTime() - (offset * 60 * 1000));
    
    // Validate end time if provided
    let plannedEndTime = null;
    if (endTime) {
      let endDate = new Date(endTime);
      const endOffset = endDate.getTimezoneOffset();
      endDate = new Date(endDate.getTime() - (endOffset * 60 * 1000));
      
      // Check if end time is after start time
      if (endDate <= date) {
        alert('End time must be after start time');
        return;
      }
      
      plannedEndTime = endDate.toISOString();
    }

    onSubmit({
      equipment_id: equipmentId,
      start_time: date.toISOString(),
      planned_end_time: plannedEndTime,
      description,
      remarks
    });
  };

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
              <Dialog.Panel className="relative transform overflow-hidden rounded-lg bg-white px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg sm:p-6">
                <div className="absolute right-0 top-0 hidden pr-4 pt-4 sm:block">
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
                  <div className="mt-3 text-center sm:mt-5">
                    <Dialog.Title as="h3" className="text-base font-semibold leading-6 text-gray-900">
                      {equipment ? `Start Session - ${equipment.name}` : 'Start New Session'}
                    </Dialog.Title>
                  </div>
                </div>

                <form onSubmit={handleSubmit} className="mt-5 space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label htmlFor="start-time" className="block text-sm font-medium text-gray-700">
                        Start Time
                      </label>
                      <input
                        type="datetime-local"
                        id="start-time"
                        value={startTime}
                        onChange={(e) => setStartTime(e.target.value)}
                        className="mt-2 block w-full rounded-md border-gray-300 shadow-sm focus:border-teal-500 focus:ring-teal-500 sm:text-sm bg-white"
                        required
                      />
                    </div>
                    <div>
                      <label htmlFor="end-time" className="block text-sm font-medium text-gray-700">
                        Planned End Time
                      </label>
                      <input
                        type="datetime-local"
                        id="end-time"
                        value={endTime}
                        min={startTime}
                        onChange={(e) => setEndTime(e.target.value)}
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-teal-500 focus:ring-teal-500 sm:text-sm"
                      />
                    </div>
                  </div>
                  {!equipment && allEquipment && (
                    <div>
                      <label htmlFor="equipment" className="block text-sm font-medium text-gray-700">
                        Select Equipment
                      </label>
                      <div className="mt-2">
                        <select
                          id="equipment"
                          value={selectedEquipmentId}
                          onChange={(e) => setSelectedEquipmentId(e.target.value)}
                          className="mt-1 block w-full rounded-md border-gray-300 py-2 pl-3 pr-10 text-base focus:border-teal-500 focus:outline-none focus:ring-teal-500 sm:text-sm bg-white"
                          style={{
                            backgroundColor: 'white',
                            WebkitAppearance: 'menulist'
                          }}
                          required
                        >
                          <option value="">Choose equipment...</option>
                          {allEquipment?.map((eq) => {
                            const isAvailable = eq.current_status?.toUpperCase() === 'AVAILABLE';
                            const isInUseByUser = activeSessions?.some(session => session.equipment.id === eq.id);
                            const status = isInUseByUser ? 'In use by you' : 
                                         isAvailable ? 'Available' : 
                                         eq.current_status;
                            const style = {
                              backgroundColor: isInUseByUser ? '#fff7ed' :
                                             isAvailable ? '#f0fdf4' : 
                                             '#fef2f2',
                              color: isInUseByUser ? '#9a3412' :
                                     isAvailable ? '#166534' : 
                                     '#991b1b'
                            };
                            
                            return (
                              <option
                                key={eq.id}
                                value={eq.id}
                                disabled={!isAvailable || isInUseByUser}
                                style={style}
                              >
                                {eq.name} - {eq.equipment_id} [{status}]
                              </option>
                            );
                          })}
                        </select>
                      </div>
                    </div>
                  )}

                  <div>
                    <label htmlFor="description" className="block text-sm font-medium text-gray-700">
                      Description
                    </label>
                    <input
                      type="text"
                      id="description"
                      name="description"
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-teal-500 focus:ring-teal-500 sm:text-sm"
                      placeholder="Project Description"
                      required
                    />
                  </div>

                  <div>
                    <label htmlFor="remarks" className="block text-sm font-medium text-gray-700">
                      Remarks
                    </label>
                    <textarea
                      id="remarks"
                      name="remarks"
                      rows={3}
                      value={remarks}
                      onChange={(e) => setRemarks(e.target.value)}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-teal-500 focus:ring-teal-500 sm:text-sm"
                      placeholder="Optional remarks"
                    />
                  </div>

                  <div className="mt-5 sm:mt-6 sm:grid sm:grid-flow-row-dense sm:grid-cols-2 sm:gap-3">
                    <button
                      type="submit"
                      disabled={isLoading || !canSubmit}
                      className={`inline-flex w-full justify-center rounded-md px-3 py-2 text-sm font-semibold text-white shadow-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-600 sm:col-start-2 ${
                        canSubmit 
                          ? 'bg-teal-600 hover:bg-teal-500' 
                          : 'bg-gray-400 cursor-not-allowed'
                      }`}
                    >
                      {isLoading ? 'Starting...' : !canSubmit ? 'Select Available Equipment' : 'Start Session'}
                    </button>
                    <button
                      type="button"
                      onClick={onClose}
                      disabled={isLoading}
                      className="mt-3 inline-flex w-full justify-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 sm:col-start-1 sm:mt-0"
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition.Root>
  );
}