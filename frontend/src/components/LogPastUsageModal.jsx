import { Fragment, useState, useEffect } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { XMarkIcon } from '@heroicons/react/24/outline';
import { format } from 'date-fns';

export default function LogPastUsageModal({ isOpen, onClose, equipment, onSubmit, isLoading }) {
  const [startTime, setStartTime] = useState(format(new Date(), "yyyy-MM-dd'T'HH:mm"));
  const [endTime, setEndTime] = useState('');
  const [description, setDescription] = useState('');
  const [remarks, setRemarks] = useState('');

  // Update title based on equipment
  const title = equipment ? `Log Past Usage - ${equipment.name}` : 'Log Past Usage';

  useEffect(() => {
    // Only reset form when modal opens
    if (isOpen && equipment) {
      resetForm();
    }
  }, [isOpen, equipment]); // Add equipment to dependencies to ensure form reset when equipment changes

  // Early return if modal is not open or no equipment is selected
  if (!isOpen || !equipment) return null;

  // Reset form when modal opens
  const resetForm = () => {
    setStartTime(format(new Date(), "yyyy-MM-dd'T'HH:mm"));
    setEndTime('');
    setDescription('');
    setRemarks('');
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!equipment?.id) {
      console.error('No equipment ID available');
      alert('Equipment information is missing. Please try again.');
      return;
    }

    if (!startTime || !endTime) {
      alert('Please provide both start and end times for past usage');
      return;
    }

    if (!description.trim()) {
      alert('Please provide a description of your equipment usage');
      return;
    }

    // Create timezone-aware dates
    let start = new Date(startTime);
    let end = new Date(endTime);
    const now = new Date();

    // Basic validations
    if (end <= start) {
      alert('End time must be after start time');
      return;
    }

    if (end > now) {
      alert('End time cannot be in the future for past usage logging');
      return;
    }

    // Calculate duration
    const duration = end - start;
    const maxDuration = 24 * 60 * 60 * 1000; // 24 hours in milliseconds

    if (duration > maxDuration) {
      if (!window.confirm('This session is longer than 24 hours. Are you sure this is correct?')) {
        return;
      }
    }

    // Adjust dates to UTC while preserving local time
    const startOffset = start.getTimezoneOffset();
    const endOffset = end.getTimezoneOffset();
    start = new Date(start.getTime() - (startOffset * 60 * 1000));
    end = new Date(end.getTime() - (endOffset * 60 * 1000));

    const submitData = {
      equipment_id: equipment.id,
      start_time: start.toISOString(),
      end_time: end.toISOString(),  // Changed from planned_end_time to end_time
      description: description.trim(),
      remarks: remarks.trim()
    };
    
    console.log('LogPastUsageModal handleSubmit - Submitting data:', submitData);
    onSubmit(submitData);
  };

  return (
    <Transition.Root show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-10" onClose={handleClose}>
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
                    onClick={handleClose}
                  >
                    <span className="sr-only">Close</span>
                    <XMarkIcon className="h-6 w-6" aria-hidden="true" />
                  </button>
                </div>

                <div>
                  <div className="mt-3 text-center sm:mt-5">
                    <Dialog.Title as="h3" className="text-base font-semibold leading-6 text-gray-900">
                      {title}
                    </Dialog.Title>
                    <div className="mt-2">
                      <p className="text-sm text-gray-900">{equipment.equipment_id}</p>
                      <p className="mt-1 text-sm text-gray-500">
                        Use this form to record your past usage of this equipment
                      </p>
                    </div>
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
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-teal-500 focus:ring-teal-500 sm:text-sm"
                        required
                      />
                    </div>
                    <div>
                      <label htmlFor="end-time" className="block text-sm font-medium text-gray-700">
                        End Time
                      </label>
                      <input
                        type="datetime-local"
                        id="end-time"
                        value={endTime}
                        min={startTime}
                        onChange={(e) => setEndTime(e.target.value)}
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-teal-500 focus:ring-teal-500 sm:text-sm"
                        required
                      />
                    </div>
                  </div>

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
                      placeholder="What did you use the equipment for?"
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
                      placeholder="Any additional notes about the usage"
                    />
                  </div>

                  <div className="mt-5 sm:mt-6 sm:grid sm:grid-flow-row-dense sm:grid-cols-2 sm:gap-3">
                    <button
                      type="submit"
                      disabled={isLoading}
                      className="inline-flex w-full justify-center rounded-md bg-teal-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-teal-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-600 sm:col-start-2"
                    >
                      {isLoading ? 'Logging...' : 'Log Usage'}
                    </button>
                    <button
                      type="button"
                      onClick={handleClose}
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