import { Link, Outlet, useLocation } from 'react-router-dom';
import {
  Users, Clock, Calendar, BarChart3, Building2, LogOut,
  ClipboardList, CalendarDays, Home, MessageCircle, Lock, FileSpreadsheet, TicketCheck
} from 'lucide-react';

interface LayoutProps {
  user: { name: string; role: string } | null;
  isManager: boolean;
  isHR: boolean;
  onLogout: () => void;
}

const NAV_ITEMS = [
  { path: '/', label: 'Dashboard', icon: Home, roles: ['all'] },
  { path: '/time', label: 'Zeiterfassung', icon: Clock, roles: ['all'] },
  { path: '/schedule', label: 'Mein Dienstplan', icon: CalendarDays, roles: ['all'] },
  { path: '/absences', label: 'Abwesenheiten', icon: ClipboardList, roles: ['all'] },
  { path: '/chat', label: 'Nachrichten', icon: MessageCircle, roles: ['all'] },
  { path: '/tickets', label: 'Tickets', icon: TicketCheck, roles: ['all'] },
  { path: '/employees', label: 'Mitarbeiter', icon: Users, roles: ['HR', 'ADMIN'] },
  { path: '/departments', label: 'Abteilungen', icon: Building2, roles: ['HR', 'ADMIN'] },
  { path: '/shift-plans', label: 'Dienstplanung', icon: Calendar, roles: ['manager'] },
  { path: '/monthly-closing', label: 'Monatsabschluss', icon: Lock, roles: ['HR', 'ADMIN'] },
  { path: '/reports', label: 'Auswertungen', icon: BarChart3, roles: ['HR', 'ADMIN'] },
];

const ROLE_LABELS: Record<string, string> = {
  ADMIN: 'Administrator',
  HR: 'Personalabteilung',
  DEPARTMENT_MANAGER: 'Abteilungsleitung',
  TEAM_LEADER: 'Teamleitung',
  EMPLOYEE: 'Mitarbeiter',
};

export default function Layout({ user, isManager, isHR, onLogout }: LayoutProps) {
  const location = useLocation();

  const visibleItems = NAV_ITEMS.filter((item) => {
    if (item.roles.includes('all')) return true;
    if (item.roles.includes('manager') && isManager) return true;
    if (item.roles.some((r) => r === user?.role)) return true;
    if (item.roles.includes('HR') && isHR) return true;
    return false;
  });

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: '#f1f5f9' }}>
      {/* Sidebar */}
      <aside style={{
        width: 250, background: '#1e293b', color: '#e2e8f0',
        display: 'flex', flexDirection: 'column', flexShrink: 0,
      }}>
        <div style={{ padding: '16px 16px', borderBottom: '1px solid #334155', display: 'flex', alignItems: 'center', gap: 12 }}>
          <img src="/logo-ikk.png" alt="IKK Logo" style={{ width: 40, height: 40, objectFit: 'contain', borderRadius: 6, background: '#fff', padding: 3 }} />
          <div>
            <h1 style={{ fontSize: 14, fontWeight: 700, color: '#fff', margin: 0, lineHeight: 1.3 }}>
              Mitarbeiter&shy;verwaltung
            </h1>
            <div style={{ fontSize: 11, color: '#94a3b8' }}>
              Ilm-Kreis-Kliniken
            </div>
          </div>
        </div>

        <nav style={{ flex: 1, padding: '8px 0' }}>
          {visibleItems.map((item) => {
            const active = location.pathname === item.path ||
              (item.path !== '/' && location.pathname.startsWith(item.path));
            const Icon = item.icon;
            return (
              <Link
                key={item.path}
                to={item.path}
                style={{
                  display: 'flex', alignItems: 'center', gap: 10,
                  padding: '10px 16px', color: active ? '#fff' : '#94a3b8',
                  background: active ? '#334155' : 'transparent',
                  textDecoration: 'none', fontSize: 14,
                  borderLeft: active ? '3px solid #3b82f6' : '3px solid transparent',
                }}
              >
                <Icon size={18} />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div style={{ padding: 16, borderTop: '1px solid #334155' }}>
          <div style={{ fontSize: 13, color: '#fff', fontWeight: 500 }}>{user?.name}</div>
          <div style={{ fontSize: 11, color: '#94a3b8' }}>
            {ROLE_LABELS[user?.role || ''] || user?.role}
          </div>
          <button
            onClick={onLogout}
            style={{
              marginTop: 10, display: 'flex', alignItems: 'center', gap: 6,
              background: 'none', border: 'none', color: '#ef4444',
              cursor: 'pointer', fontSize: 13, padding: 0,
            }}
          >
            <LogOut size={14} /> Abmelden
          </button>
        </div>

        {/* Powered by */}
        <div style={{
          padding: '10px 16px', borderTop: '1px solid #334155',
          textAlign: 'center', fontSize: 10, color: '#475569', letterSpacing: 0.5,
        }}>
          Powered by <span style={{ color: '#94a3b8', fontWeight: 600 }}>IKK IT</span>
        </div>
      </aside>

      {/* Main Content */}
      <main style={{ flex: 1, padding: 24, overflow: 'auto' }}>
        <Outlet />
      </main>
    </div>
  );
}
