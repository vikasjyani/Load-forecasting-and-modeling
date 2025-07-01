import { configureStore } from '@reduxjs/toolkit';
// Import slices and middleware
// import projectReducer from './slices/projectSlice';
// import demandReducer from './slices/demandSlice';
// import authReducer from './slices/authSlice';
// import uiReducer from './slices/uiSlice';
// import apiMiddleware from './middleware/apiMiddleware';

// Placeholder reducers
const placeholderReducer = (state = {}, action) => state;

export const store = configureStore({
  reducer: {
    // projects: projectReducer,
    // demand: demandReducer,
    // auth: authReducer,
    // ui: uiReducer,
    placeholder: placeholderReducer, // Replace with actual reducers
  },
  // middleware: (getDefaultMiddleware) =>
  //   getDefaultMiddleware().concat(apiMiddleware), // Example middleware
});

// export default store; // Default export is not conventional for 'store'
console.log("Redux store configured (placeholder)");
