import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
// import projectService from '../../services/projectService';

// Example async thunk for fetching projects
// export const fetchProjects = createAsyncThunk(
//   'projects/fetchProjects',
//   async (_, { rejectWithValue }) => {
//     try {
//       const response = await projectService.getProjects();
//       return response.data;
//     } catch (error) {
//       return rejectWithValue(error.response?.data || error.message);
//     }
//   }
// );

const projectSlice = createSlice({
  name: 'projects',
  initialState: {
    items: [],
    loading: 'idle', // 'idle' | 'pending' | 'succeeded' | 'failed'
    error: null,
    currentProject: null,
  },
  reducers: {
    // setCurrentProject: (state, action) => {
    //   state.currentProject = action.payload;
    // },
    // addProjectOptimistic: (state, action) => { // Example of optimistic update
    //   state.items.push(action.payload);
    // },
  },
  // extraReducers: (builder) => {
  //   builder
  //     .addCase(fetchProjects.pending, (state) => {
  //       state.loading = 'pending';
  //     })
  //     .addCase(fetchProjects.fulfilled, (state, action) => {
  //       state.loading = 'succeeded';
  //       state.items = action.payload;
  //     })
  //     .addCase(fetchProjects.rejected, (state, action) => {
  //       state.loading = 'failed';
  //       state.error = action.payload;
  //     });
  // },
});

// export const { setCurrentProject, addProjectOptimistic } = projectSlice.actions;
export default projectSlice.reducer;
console.log("Project slice created (placeholder)");
