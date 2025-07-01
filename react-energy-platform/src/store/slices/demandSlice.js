import { createSlice /*, createAsyncThunk*/ } from '@reduxjs/toolkit';
// import demandService from '../../services/demandService';

// Example:
// export const fetchDemandProjection = createAsyncThunk(
//   'demand/fetchProjection',
//   async (config, { rejectWithValue }) => {
//     try {
//       const response = await demandService.getDemandProjection(config);
//       return response.data;
//     } catch (error) {
//       return rejectWithValue(error.response?.data || error.message);
//     }
//   }
// );

const demandSlice = createSlice({
  name: 'demand',
  initialState: {
    projection: null,
    visualizationData: null,
    loading: 'idle',
    error: null,
  },
  reducers: {
    // setProjectionData: (state, action) => {
    //   state.projection = action.payload;
    // },
  },
  // extraReducers: (builder) => {
  //   builder
  //     .addCase(fetchDemandProjection.pending, (state) => {
  //       state.loading = 'pending';
  //     })
  //     .addCase(fetchDemandProjection.fulfilled, (state, action) => {
  //       state.loading = 'succeeded';
  //       state.projection = action.payload;
  //     })
  //     .addCase(fetchDemandProjection.rejected, (state, action) => {
  //       state.loading = 'failed';
  //       state.error = action.payload;
  //     });
  // },
});

// export const { setProjectionData } = demandSlice.actions;
export default demandSlice.reducer;
console.log("Demand slice created (placeholder)");
