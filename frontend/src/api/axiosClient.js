import axios from 'axios';

/**
 * Axios Client dùng chung cho cả 3 phân hệ.
 * Bật `withCredentials: true` để tự động đính kèm httpOnly Cookie (`access_token`, `refresh_token`).
 */
const axiosClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  timeout: 15000,
  withCredentials: true,
});

export default axiosClient;
