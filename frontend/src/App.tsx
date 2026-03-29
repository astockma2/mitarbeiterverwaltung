import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './hooks/useAuth';
import Layout from './components/Layout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import TimeTracking from './pages/TimeTracking';
import MySchedule from './pages/MySchedule';
import Absences from './pages/Absences';
import Employees from './pages/Employees';
import Departments from './pages/Departments';
import ShiftPlans from './pages/ShiftPlans';
import Reports from './pages/Reports';
import EmployeeDetail from './pages/EmployeeDetail';
import MonthlyClosingPage from './pages/MonthlyClosing';
import Chat from './pages/Chat';

export default function App() {
  const { user, loading, logout, isAdmin, isHR, isManager } = useAuth();

  if (loading) {
    return (
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        height: '100vh', fontSize: 16, color: '#64748b',
      }}>
        Laden...
      </div>
    );
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={user ? <Navigate to="/" /> : <Login />} />

        {!user ? (
          <Route path="*" element={<Navigate to="/login" />} />
        ) : (
          <Route element={<Layout user={user} isManager={isManager} isHR={isHR} onLogout={logout} />}>
            <Route path="/" element={<Dashboard user={user} isHR={isHR} />} />
            <Route path="/time" element={<TimeTracking />} />
            <Route path="/schedule" element={<MySchedule />} />
            <Route path="/absences" element={<Absences isManager={isManager} />} />
            <Route path="/chat" element={<Chat userId={user.id} />} />
            {isHR && <Route path="/employees" element={<Employees />} />}
            <Route path="/employees/:id" element={<EmployeeDetail isHR={isHR} />} />
            {isHR && <Route path="/departments" element={<Departments />} />}
            {isManager && <Route path="/shift-plans" element={<ShiftPlans />} />}
            {isHR && <Route path="/monthly-closing" element={<MonthlyClosingPage />} />}
            {isHR && <Route path="/reports" element={<Reports />} />}
            <Route path="*" element={<Navigate to="/" />} />
          </Route>
        )}
      </Routes>
    </BrowserRouter>
  );
}
