import { createSlice } from '@reduxjs/toolkit';

const uiSlice = createSlice({
  name: 'ui',
  initialState: {
    isLoadingGlobally: false, // For a global loading indicator
    notifications: [], // For snackbars/toasts
    modal: {
      isOpen: false,
      content: null, // Could be a component or string
      props: {},
    },
    // Add other UI state like theme, sidebar open/closed, etc.
  },
  reducers: {
    setGlobalLoading: (state, action) => {
      state.isLoadingGlobally = action.payload;
    },
    addNotification: (state, action) => {
      // action.payload should be like { id, message, type: 'success' | 'error' | 'info' }
      state.notifications.push({ id: Date.now(), ...action.payload });
    },
    removeNotification: (state, action) => {
      state.notifications = state.notifications.filter(
        (notification) => notification.id !== action.payload // payload is id
      );
    },
    openModal: (state, action) => {
      state.modal.isOpen = true;
      state.modal.content = action.payload.content;
      state.modal.props = action.payload.props || {};
    },
    closeModal: (state) => {
      state.modal.isOpen = false;
      state.modal.content = null;
      state.modal.props = {};
    },
  },
});

export const {
  setGlobalLoading,
  addNotification,
  removeNotification,
  openModal,
  closeModal,
} = uiSlice.actions;

export default uiSlice.reducer;
console.log("UI slice created");
