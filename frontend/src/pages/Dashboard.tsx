import { useEffect, useState } from 'react';
import type { CSSProperties } from 'react';
import { Users, Clock, CalendarDays, TrendingUp, Download, Smartphone } from 'lucide-react';
import Card, { StatCard } from '../components/Card';
import { getDashboard, getClockStatus, getMonthlySummary, getVacationBalance } from '../services/api';

interface Props {
  user: { name: string; role: string } | null;
  isHR: boolean;
}

export default function Dashboard({ user, isHR }: Props) {
  const [stats, setStats] = useState<any>(null);
  const [clockStatus, setClockStatus] = useState<any>(null);
  const [monthly, setMonthly] = useState<any>(null);
  const [vacation, setVacation] = useState<any>(null);
  const appDownloadUrl = 'https://downloads.c3po42.de/mva/app-release.apk';

  useEffect(() => {
    getClockStatus().then((r) => setClockStatus(r.data)).catch(() => {});
    const now = new Date();
    getMonthlySummary(now.getFullYear(), now.getMonth() + 1)
      .then((r) => setMonthly(r.data)).catch(() => {});
    getVacationBalance().then((r) => setVacation(r.data)).catch(() => {});
    if (isHR) {
      getDashboard().then((r) => setStats(r.data)).catch(() => {});
    }
  }, [isHR]);

  return (
    <div>
      <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1e293b', marginBottom: 24 }}>
        Willkommen, {user?.name?.split(' ')[0]}
      </h1>

      {/* Stempel-Status */}
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
        gap: 16, marginBottom: 24,
      }}>
        <StatCard
          label={clockStatus?.clocked_in ? `Eingestempelt seit ${new Date(clockStatus.since).toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })}` : 'Nicht eingestempelt'}
          value={clockStatus?.clocked_in ? `${clockStatus.elapsed_hours}h` : '--'}
          color={clockStatus?.clocked_in ? '#22c55e' : '#94a3b8'}
          icon={<Clock size={24} />}
        />
        <StatCard
          label="Stunden diesen Monat"
          value={monthly ? `${monthly.total_hours}h` : '--'}
          color="#3b82f6"
          icon={<TrendingUp size={24} />}
        />
        <StatCard
          label="Ueberstunden"
          value={monthly ? `${monthly.overtime_hours > 0 ? '+' : ''}${monthly.overtime_hours}h` : '--'}
          color={monthly?.overtime_hours > 0 ? '#f59e0b' : '#64748b'}
          icon={<Clock size={24} />}
        />
        <StatCard
          label="Resturlaub"
          value={vacation ? `${vacation.remaining} Tage` : '--'}
          color="#8b5cf6"
          icon={<CalendarDays size={24} />}
        />
      </div>

      <Card style={{ marginBottom: 24 }}>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(0, 1fr) 112px',
          gap: 18,
          alignItems: 'center',
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#1e293b', fontWeight: 700, marginBottom: 6 }}>
              <Smartphone size={18} />
              Handy-App
            </div>
            <div style={{ color: '#64748b', fontSize: 13, marginBottom: 12 }}>
              Android APK fuer MVA
            </div>
            <a href={appDownloadUrl} style={downloadButtonStyle}>
              <Download size={16} />
              APK herunterladen
            </a>
          </div>
          <a href={appDownloadUrl} title="Handy-App herunterladen" style={qrLinkStyle}>
            <img src="/app-download-qr.svg" alt="QR-Code fuer den Handy-App Download" style={{ width: 104, height: 104, display: 'block' }} />
          </a>
        </div>
      </Card>

      {/* Monatsdetails */}
      {monthly && (
        <Card title={`Monatsübersicht ${monthly.month}/${monthly.year}`} style={{ marginBottom: 24 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16 }}>
            <div>
              <div style={{ fontSize: 13, color: '#64748b' }}>Soll-Stunden</div>
              <div style={{ fontSize: 20, fontWeight: 600 }}>{monthly.target_hours}h</div>
            </div>
            <div>
              <div style={{ fontSize: 13, color: '#64748b' }}>Ist-Stunden</div>
              <div style={{ fontSize: 20, fontWeight: 600 }}>{monthly.total_hours}h</div>
            </div>
            <div>
              <div style={{ fontSize: 13, color: '#64748b' }}>Arbeitstage</div>
              <div style={{ fontSize: 20, fontWeight: 600 }}>{monthly.work_days}</div>
            </div>
          </div>
          {Object.keys(monthly.surcharges || {}).length > 0 && (
            <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid #e2e8f0' }}>
              <div style={{ fontSize: 13, color: '#64748b', marginBottom: 8 }}>Zuschlaege</div>
              <div style={{ display: 'flex', gap: 16 }}>
                {Object.entries(monthly.surcharges).map(([type, hours]) => (
                  <span key={type} style={{
                    padding: '4px 10px', background: '#f1f5f9', borderRadius: 6, fontSize: 13,
                  }}>
                    {type}: {hours as number}h
                  </span>
                ))}
              </div>
            </div>
          )}
        </Card>
      )}

      {/* HR Dashboard */}
      {isHR && stats && (
        <Card title="Personaluebersicht">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16 }}>
            <StatCard label="Mitarbeiter gesamt" value={stats.employees_total} color="#3b82f6" icon={<Users size={24} />} />
            <StatCard label="Aktiv" value={stats.employees_active} color="#22c55e" icon={<Users size={24} />} />
            <StatCard label="Inaktiv" value={stats.employees_inactive} color="#ef4444" icon={<Users size={24} />} />
          </div>
        </Card>
      )}
    </div>
  );
}

const downloadButtonStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: 8,
  minHeight: 36,
  padding: '0 12px',
  borderRadius: 8,
  background: '#2563eb',
  color: '#ffffff',
  fontSize: 13,
  fontWeight: 700,
  textDecoration: 'none',
};

const qrLinkStyle: CSSProperties = {
  width: 112,
  height: 112,
  borderRadius: 8,
  border: '1px solid #e2e8f0',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  background: '#ffffff',
};
