import axios from 'axios';

// Immer relativen Pfad verwenden — Vite-Proxy leitet /api an das Backend weiter
const API_BASE = '/api/v1';

const api = axios.create({ baseURL: API_BASE });

// Token automatisch mitsenden
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Bei 401: Token loeschen, zum Login
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

// Auth
export const login = (username: string, password: string) =>
  api.post('/auth/login', { username, password });

export const getMe = () => api.get('/auth/me');

// Employees
export const getEmployees = (params?: Record<string, any>) =>
  api.get('/employees', { params });

export const getEmployee = (id: number) => api.get(`/employees/${id}`);

export const createEmployee = (data: any) => api.post('/employees', data);

export const updateEmployee = (id: number, data: any) =>
  api.patch(`/employees/${id}`, data);

// Departments
export const getDepartments = () => api.get('/departments');

// Time Tracking
export const clockIn = () => api.post('/time/clock-in', {});
export const clockOut = (breakMinutes?: number) =>
  api.post('/time/clock-out', { break_minutes: breakMinutes });
export const getClockStatus = () => api.get('/time/status');
export const getTimeEntries = (params?: Record<string, any>) =>
  api.get('/time/entries', { params });
export const getDailySummary = (day: string, employeeId?: number) =>
  api.get('/time/daily', { params: { day, employee_id: employeeId } });
export const getMonthlySummary = (year: number, month: number, employeeId?: number) =>
  api.get('/time/monthly', { params: { year, month, employee_id: employeeId } });

// Absences
export const getAbsences = (params?: Record<string, any>) =>
  api.get('/absences', { params });
export const createAbsence = (data: any) => api.post('/absences', data);
export const getPendingAbsences = () => api.get('/absences/pending');
export const reviewAbsence = (id: number, approved: boolean) =>
  api.post(`/absences/${id}/review`, { approved });
export const getVacationBalance = (year?: number) =>
  api.get('/absences/vacation-balance', { params: { year } });

// Shifts
export const getShiftTemplates = () => api.get('/shifts/templates');
export const createShiftTemplate = (data: any) => api.post('/shifts/templates', data);
export const updateShiftTemplate = (id: number, data: any) => api.put(`/shifts/templates/${id}`, data);
export const deleteShiftTemplate = (id: number) => api.delete(`/shifts/templates/${id}`);
export const getShiftPlans = (params?: Record<string, any>) =>
  api.get('/shifts/plans', { params });
export const viewShiftPlan = (planId: number) =>
  api.get(`/shifts/plans/${planId}/view`);
export const getMySchedule = (startDate: string, endDate: string) =>
  api.get('/shifts/my-schedule', { params: { start_date: startDate, end_date: endDate } });

// Admin
export const getDashboard = () => api.get('/admin/dashboard');

// Monthly Closing
export const closeMonth = (year: number, month: number, employeeId?: number) =>
  api.post('/monthly/close', null, { params: { year, month, employee_id: employeeId } });
export const getMonthlyOverview = (year: number, month: number) =>
  api.get('/monthly/overview', { params: { year, month } });
export const exportLoga = (year: number, month: number) =>
  api.post('/monthly/export', null, {
    params: { year, month },
    responseType: 'blob',
  });

// Reports
export const getYearlyOverview = (year: number) =>
  api.get('/reports/yearly-overview', { params: { year } });
export const getDepartmentSummary = (year: number, month: number) =>
  api.get('/reports/department-summary', { params: { year, month } });
export const getSurchargeSummary = (year: number, month: number) =>
  api.get('/reports/surcharge-summary', { params: { year, month } });
export const getAbsenceStatistics = (year: number) =>
  api.get('/reports/absence-statistics', { params: { year } });
export const exportExtendedCsv = (year: number, month: number) =>
  api.get('/reports/export-extended', {
    params: { year, month },
    responseType: 'blob',
  });

// Chat
export const getSupportBotId = () => api.get('/chat/support-bot-id');
export const getConversations = () => api.get('/chat/conversations');
export const createConversation = (data: { type: string; name?: string; member_ids: number[] }) =>
  api.post('/chat/conversations', data);
export const getMessages = (conversationId: number, before?: string) =>
  api.get(`/chat/conversations/${conversationId}/messages`, { params: { before } });
export const sendMessage = (conversationId: number, content: string) =>
  api.post(`/chat/conversations/${conversationId}/messages`, { content });
export const getChatEmployees = () => api.get('/chat/employees');
export const updateConversation = (conversationId: number, data: { name: string }) =>
  api.put(`/chat/conversations/${conversationId}`, data);
export const updateMembers = (conversationId: number, data: { add?: number[]; remove?: number[] }) =>
  api.put(`/chat/conversations/${conversationId}/members`, data);
export const uploadChatFile = (conversationId: number, file: File, onProgress?: (pct: number) => void) =>
  api.post(`/chat/conversations/${conversationId}/upload`, (() => {
    const fd = new FormData();
    fd.append('file', file);
    return fd;
  })(), {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: onProgress ? (e: any) => onProgress(Math.round((e.loaded * 100) / e.total)) : undefined,
  });
export const getChatFileUrl = (filePath: string) =>
  `${api.defaults.baseURL}/chat/files/${filePath}`;

// Tickets
export const getTickets = (params?: Record<string, any>) =>
  api.get('/tickets', { params });
export const createTicket = (data: { title: string; description: string; priority: string }) =>
  api.post('/tickets', data);
export const getTicket = (id: number) => api.get(`/tickets/${id}`);
export const updateTicket = (id: number, data: Record<string, any>) =>
  api.patch(`/tickets/${id}`, data);
export const closeTicket = (id: number) => api.delete(`/tickets/${id}`);

export default api;
