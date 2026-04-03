import { useEffect, useState } from 'react';
import { Check, X } from 'lucide-react';
import Card, { Badge } from '../components/Card';
import { getAbsences, createAbsence, getPendingAbsences, reviewAbsence, getVacationBalance } from '../services/api';

const TYPE_LABELS: Record<string, string> = {
  VACATION: 'Urlaub', SICK: 'Krankheit', TRAINING: 'Fortbildung',
  SPECIAL: 'Sonderurlaub', COMP_TIME: 'Freizeitausgleich',
};
const STATUS_COLORS: Record<string, string> = {
  REQUESTED: '#f59e0b', APPROVED: '#22c55e', REJECTED: '#ef4444', CANCELLED: '#94a3b8',
};
const STATUS_LABELS: Record<string, string> = {
  REQUESTED: 'Beantragt', APPROVED: 'Genehmigt', REJECTED: 'Abgelehnt', CANCELLED: 'Storniert',
};

interface Props { isManager: boolean; }

export default function Absences({ isManager }: Props) {
  const [absences, setAbsences] = useState<any[]>([]);
  const [pending, setPending] = useState<any[]>([]);
  const [vacation, setVacation] = useState<any>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ type: 'VACATION', start_date: '', end_date: '', notes: '' });
  const [tab, setTab] = useState<'my' | 'pending'>('my');

  const load = () => {
    getAbsences().then((r) => setAbsences(r.data));
    getVacationBalance().then((r) => setVacation(r.data));
    if (isManager) getPendingAbsences().then((r) => setPending(r.data));
  };
  useEffect(load, [isManager]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createAbsence(form);
      setShowForm(false);
      setForm({ type: 'VACATION', start_date: '', end_date: '', notes: '' });
      load();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Fehler');
    }
  };

  const handleReview = async (id: number, approved: boolean) => {
    await reviewAbsence(id, approved);
    load();
  };

  const inputStyle = {
    padding: '8px 10px', borderRadius: 6, border: '1px solid #d1d5db', fontSize: 14,
  };

  return (
    <div>
      <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1e293b', marginBottom: 24 }}>
        Abwesenheiten
      </h1>

      {/* Urlaubskonto */}
      {vacation && (
        <Card style={{ marginBottom: 20 }}>
          <div style={{ display: 'flex', gap: 32, flexWrap: 'wrap', alignItems: 'center' }}>
            <div>
              <div style={{ fontSize: 12, color: '#64748b' }}>Anspruch {vacation.year}</div>
              <div style={{ fontSize: 20, fontWeight: 700 }}>{vacation.entitlement} Tage</div>
            </div>
            <div>
              <div style={{ fontSize: 12, color: '#64748b' }}>Genommen</div>
              <div style={{ fontSize: 20, fontWeight: 700, color: '#3b82f6' }}>{vacation.taken}</div>
            </div>
            <div>
              <div style={{ fontSize: 12, color: '#64748b' }}>Beantragt</div>
              <div style={{ fontSize: 20, fontWeight: 700, color: '#f59e0b' }}>{vacation.pending}</div>
            </div>
            <div>
              <div style={{ fontSize: 12, color: '#64748b' }}>Verbleibend</div>
              <div style={{ fontSize: 20, fontWeight: 700, color: '#22c55e' }}>{vacation.remaining}</div>
            </div>
            <div style={{ marginLeft: 'auto' }}>
              <button onClick={() => setShowForm(!showForm)} style={{
                padding: '8px 16px', borderRadius: 6, background: '#3b82f6',
                color: '#fff', border: 'none', cursor: 'pointer', fontSize: 13, fontWeight: 600,
              }}>
                Neuer Antrag
              </button>
            </div>
          </div>
        </Card>
      )}

      {/* Formular */}
      {showForm && (
        <Card title="Neuer Abwesenheitsantrag" style={{ marginBottom: 20 }}>
          <form onSubmit={handleCreate} style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'end' }}>
            <div>
              <label style={{ display: 'block', fontSize: 12, color: '#64748b', marginBottom: 4 }}>Typ</label>
              <select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })} style={inputStyle}>
                {Object.entries(TYPE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 12, color: '#64748b', marginBottom: 4 }}>Von</label>
              <input type="date" value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} style={inputStyle} required />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 12, color: '#64748b', marginBottom: 4 }}>Bis</label>
              <input type="date" value={form.end_date} onChange={(e) => setForm({ ...form, end_date: e.target.value })} style={inputStyle} required />
            </div>
            <div style={{ flex: 1, minWidth: 150 }}>
              <label style={{ display: 'block', fontSize: 12, color: '#64748b', marginBottom: 4 }}>Anmerkung</label>
              <input value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} style={{ ...inputStyle, width: '100%', boxSizing: 'border-box' as const }} />
            </div>
            <button type="submit" style={{
              padding: '8px 20px', borderRadius: 6, background: '#22c55e',
              color: '#fff', border: 'none', cursor: 'pointer', fontSize: 13, fontWeight: 600,
            }}>Absenden</button>
          </form>
        </Card>
      )}

      {/* Tabs */}
      {isManager && (
        <div style={{ display: 'flex', gap: 4, marginBottom: 16 }}>
          {(['my', 'pending'] as const).map((t) => (
            <button key={t} onClick={() => setTab(t)} style={{
              padding: '8px 16px', borderRadius: 6, border: 'none', fontSize: 13, fontWeight: 500,
              background: tab === t ? '#3b82f6' : '#e2e8f0', color: tab === t ? '#fff' : '#64748b',
              cursor: 'pointer',
            }}>
              {t === 'my' ? 'Meine Abwesenheiten' : `Offene Antraege (${pending.length})`}
            </button>
          ))}
        </div>
      )}

      {/* Liste */}
      <Card>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #e2e8f0' }}>
              {tab === 'pending' && <th style={th}>Mitarbeiter</th>}
              <th style={th}>Typ</th>
              <th style={th}>Von</th>
              <th style={th}>Bis</th>
              <th style={th}>Tage</th>
              <th style={th}>Status</th>
              <th style={th}>Anmerkung</th>
              {tab === 'pending' && <th style={th}>Aktion</th>}
            </tr>
          </thead>
          <tbody>
            {(tab === 'pending' ? pending : absences).map((a) => (
              <tr key={a.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                {tab === 'pending' && <td style={td}>{a.employee_name}</td>}
                <td style={td}><Badge text={TYPE_LABELS[a.type] || a.type} color="#3b82f6" /></td>
                <td style={td}>{a.start_date}</td>
                <td style={td}>{a.end_date}</td>
                <td style={td}>{a.days}</td>
                <td style={td}>
                  <Badge text={STATUS_LABELS[a.status] || a.status} color={STATUS_COLORS[a.status] || '#64748b'} />
                </td>
                <td style={{ ...td, color: '#64748b', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {a.notes || '--'}
                </td>
                {tab === 'pending' && (
                  <td style={td}>
                    <div style={{ display: 'flex', gap: 4 }}>
                      <button onClick={() => handleReview(a.id, true)} style={{ ...actionBtn, color: '#22c55e' }}>
                        <Check size={16} />
                      </button>
                      <button onClick={() => handleReview(a.id, false)} style={{ ...actionBtn, color: '#ef4444' }}>
                        <X size={16} />
                      </button>
                    </div>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
        {(tab === 'pending' ? pending : absences).length === 0 && (
          <div style={{ textAlign: 'center', padding: 24, color: '#94a3b8', fontSize: 14 }}>
            Keine Eintraege
          </div>
        )}
      </Card>
    </div>
  );
}

const th = { textAlign: 'left' as const, padding: '8px 12px', color: '#64748b', fontWeight: 500 as const };
const td = { padding: '10px 12px' };
const actionBtn = {
  background: 'none', border: '1px solid #e2e8f0', borderRadius: 4,
  padding: 4, cursor: 'pointer', display: 'flex',
};
