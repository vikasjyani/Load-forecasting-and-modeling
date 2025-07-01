import api from './api';

const uploadService = {
  uploadFile: (file, endpoint = '/upload') => {
    const formData = new FormData();
    formData.append('file', file);

    return api.post(endpoint, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
  // Add other specific upload-related functions if needed
};

export default uploadService;
