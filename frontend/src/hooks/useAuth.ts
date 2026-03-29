import { useState, useEffect } from 'react';
import { getMe } from '../services/api';

interface User {
  id: number;
  personnel_number: string;
  name: string;
  role: string;
  department_id: number | null;
}

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      setLoading(false);
      return;
    }
    getMe()
      .then((res) => setUser(res.data))
      .catch(() => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
      })
      .finally(() => setLoading(false));
  }, []);

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setUser(null);
    window.location.href = '/login';
  };

  const isAdmin = user?.role === 'ADMIN';
  const isHR = user?.role === 'HR' || isAdmin;
  const isManager = isHR || user?.role === 'DEPARTMENT_MANAGER' || user?.role === 'TEAM_LEADER';

  return { user, loading, logout, isAdmin, isHR, isManager };
}
