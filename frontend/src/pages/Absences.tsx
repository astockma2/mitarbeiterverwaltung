import { useCallback, useEffect, useMemo, useState } from 'react';
import type { CSSProperties, FormEvent } from 'react';
import { Check, Plane, X } from 'lucide-react';
import Card, { Badge } from '../components/Card';
import {
  createAbsence,
  createTravelRequest,
  getAbsences,
  getEmployees,
  getPendingAbsences,
  getPendingTravelRequests,
  getTravelRequests,
  getVacationBalance,
  reviewAbsence,
  reviewTravelRequest,
} from '../services/api';

const TYPE_LABELS: Record<string, string> = {
  VACATION: 'Urlaub',
  SICK: 'Krankheit',
  TRAINING: 'Fortbildung',
  SPECIAL: 'Sonderurlaub',
  COMP_TIME: 'Freizeitausgleich',
};

const STATUS_COLORS: Record<string, string> = {
  REQUESTED: '#f59e0b',
  MANAGER_APPROVED: '#0ea5e9',
  APPROVED: '#22c55e',
  APPROVED_LEGACY: '#22c55e',
  REJECTED: '#ef4444',
  CANCELLED: '#94a3b8',
};

const STATUS_LABELS: Record<string, string> = {
  REQUESTED: 'Beantragt',
  MANAGER_APPROVED: 'Fachlich frei',
  APPROVED: 'Genehmigt',
  APPROVED_LEGACY: 'Importiert',
  REJECTED: 'Abgelehnt',
  CANCELLED: 'Storniert',
};

type Absence = {
  id: number;
  employee_name?: string | null;
  type: string;
  start_date: string;
  end_date: string;
  days: number;
  status: string;
  notes?: string | null;
};

type TravelRequest = {
  id: number;
  employee_id: number;
  employee_name?: string | null;
  start_date: string;
  end_date: string;
  destination: string;
  purpose: string;
  status: string;
};

type EmployeeOption = {
  id: number;
  first_name: string;
  last_name: string;
};

type Props = {
  isManager: boolean;
  isHR: boolean;
};

function pad(value: number) {
  return String(value).padStart(2, '0');
}

function todayKey() {
  const today = new Date();
  return `${today.getFullYear()}-${pad(today.getMonth() + 1)}-${pad(today.getDate())}`;
}

function travelDays(travel: TravelRequest) {
  const start = new Date(`${travel.start_date}T00:00:00`);
  const end = new Date(`${travel.end_date}T00:00:00`);
  return Math.max(1, Math.round((end.getTime() - start.getTime()) / 86_400_000) + 1);
}

function employeeLabel(employee: EmployeeOption) {
  return `${employee.first_name} ${employee.last_name}`;
}

export default function Absences({ isManager, isHR }: Props) {
  const year = new Date().getFullYear();
  const [absences, setAbsences] = useState<Absence[]>([]);
  const [pending, setPending] = useState<Absence[]>([]);
  const [travels, setTravels] = useState<TravelRequest[]>([]);
  const [pendingTravel, setPendingTravel] = useState<TravelRequest[]>([]);
  const [employees, setEmployees] = useState<EmployeeOption[]>([]);
  const [vacation, setVacation] = useState<any>(null);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState('');
  const [form, setForm] = useState({ type: 'VACATION', start_date: '', end_date: '', notes: '' });
  const [travelForm, setTravelForm] = useState({
    employee_id: '',
    start_date: todayKey(),
    end_date: todayKey(),
    destination: '',
    purpose: '',
    cost_center: '',
    transport_type: '',
    estimated_costs: '',
  });
  const [tab, setTab] = useState<'my' | 'pending'>('my');

  const load = useCallback(async () => {
    setError('');
    try {
      const [absenceResponse, vacationResponse, travelResponse] = await Promise.all([
        getAbsences({ year }),
        getVacationBalance(year),
        getTravelRequests({ year }),
      ]);
      setAbsences(absenceResponse.data as Absence[]);
      setVacation(vacationResponse.data);
      setTravels(travelResponse.data as TravelRequest[]);

      if (isManager) {
        const [pendingResponse, pendingTravelResponse, employeeResponse] = await Promise.all([
          getPendingAbsences(),
          getPendingTravelRequests(),
          getEmployees({ page_size: 500, is_active: true }),
        ]);
        setPending(pendingResponse.data as Absence[]);
        setPendingTravel(pendingTravelResponse.data as TravelRequest[]);
        setEmployees((employeeResponse.data.items || []) as EmployeeOption[]);
      } else {
        setPending([]);
        setPendingTravel([]);
        setEmployees([]);
      }
    } catch (loadError: any) {
      setError(loadError.response?.data?.detail || 'Abwesenheiten konnten nicht geladen werden');
    }
  }, [isManager, year]);

  useEffect(() => {
    void load();
  }, [load]);

  const summary = useMemo(() => {
    const activeTravels = travels.filter((travel) => !['REJECTED', 'CANCELLED'].includes(travel.status));
    return {
      vacationApproved: absences
        .filter((absence) => absence.type === 'VACATION' && absence.status === 'APPROVED')
        .reduce((sum, absence) => sum + Number(absence.days || 0), 0),
      vacationPlanned: absences
        .filter((absence) => absence.type === 'VACATION' && absence.status === 'REQUESTED')
        .reduce((sum, absence) => sum + Number(absence.days || 0), 0),
      compTime: absences
        .filter((absence) => absence.type === 'COMP_TIME' && !['REJECTED', 'CANCELLED'].includes(absence.status))
        .reduce((sum, absence) => sum + Number(absence.days || 0), 0),
      travel: activeTravels.reduce((sum, travel) => sum + travelDays(travel), 0),
    };
  }, [absences, travels]);

  const handleCreate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    try {
      await createAbsence(form);
      setShowForm(false);
      setForm({ type: 'VACATION', start_date: '', end_date: '', notes: '' });
      await load();
    } catch (createError: any) {
      setError(createError.response?.data?.detail || 'Abwesenheit konnte nicht gespeichert werden');
    }
  };

  const handleCreateTravel = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    try {
      await createTravelRequest({
        employee_id: travelForm.employee_id ? Number(travelForm.employee_id) : undefined,
        start_date: travelForm.start_date,
        end_date: travelForm.end_date,
        destination: travelForm.destination,
        purpose: travelForm.purpose,
        cost_center: travelForm.cost_center || undefined,
        transport_type: travelForm.transport_type || undefined,
        estimated_costs: travelForm.estimated_costs ? Number(travelForm.estimated_costs) : null,
      });
      setTravelForm((current) => ({
        ...current,
        destination: '',
        purpose: '',
        cost_center: '',
        transport_type: '',
        estimated_costs: '',
      }));
      await load();
    } catch (createError: any) {
      setError(createError.response?.data?.detail || 'Dienstreise konnte nicht gespeichert werden');
    }
  };

  const handleReview = async (id: number, approved: boolean) => {
    await reviewAbsence(id, approved);
    await load();
  };

  const handleReviewTravel = async (id: number, approved: boolean) => {
    await reviewTravelRequest(id, { approved, final_approval: isHR });
    await load();
  };

  const shownAbsences = tab === 'pending' ? pending : absences;

  return (
    <div>
      <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1e293b', marginBottom: 24 }}>
        Abwesenheiten
      </h1>

      {error && <div style={errorStyle}>{error}</div>}

      <div style={topGridStyle}>
        {vacation && (
          <Card>
            <div style={{ display: 'flex', gap: 32, flexWrap: 'wrap', alignItems: 'center' }}>
              <Metric label={`Anspruch ${vacation.year}`} value={`${vacation.entitlement} Tage`} />
              <Metric label="Genommen" value={vacation.taken} color="#3b82f6" />
              <Metric label="Beantragt" value={vacation.pending} color="#f59e0b" />
              <Metric label="Verbleibend" value={vacation.remaining} color="#22c55e" />
              <div style={{ marginLeft: 'auto' }}>
                <button onClick={() => setShowForm(!showForm)} style={primaryButtonStyle}>
                  Neuer Antrag
                </button>
              </div>
            </div>
          </Card>
        )}

        <Card title="Kartei Abwesenheiten">
          <div style={summaryGridStyle}>
            <SummaryPill label="Urlaub" value={summary.vacationApproved} color="#D97706" />
            <SummaryPill label="Geplant" value={summary.vacationPlanned} color="#0EA5E9" />
            <SummaryPill label="AZA" value={summary.compTime} color="#E11D48" />
            <SummaryPill label="Reisen" value={summary.travel} color="#65A30D" />
          </div>
          <div style={cardSubheadingStyle}>Dienstreise</div>
          <form onSubmit={handleCreateTravel} style={travelFormStyle}>
            {isManager && (
              <select
                value={travelForm.employee_id}
                onChange={(event) => setTravelForm((current) => ({ ...current, employee_id: event.target.value }))}
                style={inputStyle}
              >
                <option value="">Eigene Dienstreise</option>
                {employees.map((employee) => (
                  <option key={employee.id} value={employee.id}>{employeeLabel(employee)}</option>
                ))}
              </select>
            )}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              <input
                type="date"
                value={travelForm.start_date}
                onChange={(event) => setTravelForm((current) => ({ ...current, start_date: event.target.value }))}
                style={inputStyle}
                required
              />
              <input
                type="date"
                value={travelForm.end_date}
                onChange={(event) => setTravelForm((current) => ({ ...current, end_date: event.target.value }))}
                style={inputStyle}
                required
              />
            </div>
            <input
              value={travelForm.destination}
              onChange={(event) => setTravelForm((current) => ({ ...current, destination: event.target.value }))}
              placeholder="Ziel"
              style={inputStyle}
              required
            />
            <input
              value={travelForm.purpose}
              onChange={(event) => setTravelForm((current) => ({ ...current, purpose: event.target.value }))}
              placeholder="Anlass"
              style={inputStyle}
              required
            />
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              <input
                value={travelForm.cost_center}
                onChange={(event) => setTravelForm((current) => ({ ...current, cost_center: event.target.value }))}
                placeholder="Kostenstelle"
                style={inputStyle}
              />
              <input
                type="number"
                value={travelForm.estimated_costs}
                onChange={(event) => setTravelForm((current) => ({ ...current, estimated_costs: event.target.value }))}
                placeholder="Kosten"
                style={inputStyle}
              />
            </div>
            <input
              value={travelForm.transport_type}
              onChange={(event) => setTravelForm((current) => ({ ...current, transport_type: event.target.value }))}
              placeholder="Verkehrsmittel"
              style={inputStyle}
            />
            <button type="submit" style={travelButtonStyle}>
              <Plane size={16} />
              Beantragen
            </button>
          </form>
        </Card>
      </div>

      {isManager && (
        <Card title={`Offene Dienstreisen (${pendingTravel.length})`} style={{ marginBottom: 20 }}>
          {pendingTravel.length === 0 ? (
            <div style={{ color: '#94a3b8', fontSize: 13, padding: '8px 0' }}>
              Keine offenen Antraege
            </div>
          ) : (
            <div style={pendingTravelListStyle}>
              {pendingTravel.map((travel) => (
                <div key={travel.id} style={pendingTravelStyle}>
                  <div style={{ fontWeight: 700, color: '#0f172a', fontSize: 13 }}>
                    {travel.employee_name || `Mitarbeiter ${travel.employee_id}`}
                  </div>
                  <div style={{ color: '#64748b', fontSize: 12 }}>
                    {travel.start_date} bis {travel.end_date}
                  </div>
                  <div style={{ color: '#334155', fontSize: 12, marginTop: 2 }}>
                    {travel.destination}
                  </div>
                  <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
                    <button onClick={() => void handleReviewTravel(travel.id, true)} style={{ ...actionBtn, color: '#22c55e' }}>
                      <Check size={16} />
                    </button>
                    <button onClick={() => void handleReviewTravel(travel.id, false)} style={{ ...actionBtn, color: '#ef4444' }}>
                      <X size={16} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {showForm && (
        <Card title="Neuer Abwesenheitsantrag" style={{ marginBottom: 20 }}>
          <form onSubmit={handleCreate} style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'end' }}>
            <div>
              <label style={labelStyle}>Typ</label>
              <select value={form.type} onChange={(event) => setForm({ ...form, type: event.target.value })} style={inputStyle}>
                {Object.entries(TYPE_LABELS).map(([key, value]) => <option key={key} value={key}>{value}</option>)}
              </select>
            </div>
            <div>
              <label style={labelStyle}>Von</label>
              <input type="date" value={form.start_date} onChange={(event) => setForm({ ...form, start_date: event.target.value })} style={inputStyle} required />
            </div>
            <div>
              <label style={labelStyle}>Bis</label>
              <input type="date" value={form.end_date} onChange={(event) => setForm({ ...form, end_date: event.target.value })} style={inputStyle} required />
            </div>
            <div style={{ flex: 1, minWidth: 150 }}>
              <label style={labelStyle}>Anmerkung</label>
              <input value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} style={{ ...inputStyle, width: '100%' }} />
            </div>
            <button type="submit" style={successButtonStyle}>Absenden</button>
          </form>
        </Card>
      )}

      {isManager && (
        <div style={{ display: 'flex', gap: 4, marginBottom: 16 }}>
          {(['my', 'pending'] as const).map((currentTab) => (
            <button key={currentTab} onClick={() => setTab(currentTab)} style={tabButtonStyle(tab === currentTab)}>
              {currentTab === 'my' ? 'Meine Abwesenheiten' : `Offene Antraege (${pending.length})`}
            </button>
          ))}
        </div>
      )}

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
            {shownAbsences.map((absence) => (
              <tr key={absence.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                {tab === 'pending' && <td style={td}>{absence.employee_name}</td>}
                <td style={td}><Badge text={TYPE_LABELS[absence.type] || absence.type} color="#3b82f6" /></td>
                <td style={td}>{absence.start_date}</td>
                <td style={td}>{absence.end_date}</td>
                <td style={td}>{absence.days}</td>
                <td style={td}>
                  <Badge text={STATUS_LABELS[absence.status] || absence.status} color={STATUS_COLORS[absence.status] || '#64748b'} />
                </td>
                <td style={{ ...td, color: '#64748b', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {absence.notes || '--'}
                </td>
                {tab === 'pending' && (
                  <td style={td}>
                    <div style={{ display: 'flex', gap: 4 }}>
                      <button onClick={() => void handleReview(absence.id, true)} style={{ ...actionBtn, color: '#22c55e' }}>
                        <Check size={16} />
                      </button>
                      <button onClick={() => void handleReview(absence.id, false)} style={{ ...actionBtn, color: '#ef4444' }}>
                        <X size={16} />
                      </button>
                    </div>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
        {shownAbsences.length === 0 && (
          <div style={{ textAlign: 'center', padding: 24, color: '#94a3b8', fontSize: 14 }}>
            Keine Eintraege
          </div>
        )}
      </Card>
    </div>
  );
}

function Metric({ label, value, color = '#0f172a' }: { label: string; value: string | number; color?: string }) {
  return (
    <div>
      <div style={{ fontSize: 12, color: '#64748b' }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 700, color }}>{value}</div>
    </div>
  );
}

function SummaryPill({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div style={{ ...summaryPillStyle, borderColor: `${color}55`, background: `${color}12` }}>
      <span style={{ color }}>{label}</span>
      <strong style={{ color: '#0f172a' }}>{value}</strong>
    </div>
  );
}

function tabButtonStyle(active: boolean): CSSProperties {
  return {
    padding: '8px 16px',
    borderRadius: 6,
    border: 'none',
    fontSize: 13,
    fontWeight: 500,
    background: active ? '#3b82f6' : '#e2e8f0',
    color: active ? '#fff' : '#64748b',
    cursor: 'pointer',
  };
}

const topGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'minmax(0, 1fr) 360px',
  gap: 16,
  alignItems: 'start',
  marginBottom: 20,
};

const summaryGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
  gap: 8,
};

const summaryPillStyle: CSSProperties = {
  minHeight: 42,
  border: '1px solid #e2e8f0',
  borderRadius: 8,
  padding: '7px 9px',
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  fontSize: 12,
  fontWeight: 800,
};

const cardSubheadingStyle: CSSProperties = {
  margin: '14px 0 8px',
  fontSize: 13,
  fontWeight: 800,
  color: '#0f172a',
};

const travelFormStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 10,
};

const pendingTravelListStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
  gap: 10,
};

const pendingTravelStyle: CSSProperties = {
  border: '1px solid #e2e8f0',
  borderRadius: 8,
  padding: 10,
  background: '#f8fafc',
};

const labelStyle: CSSProperties = {
  display: 'block',
  fontSize: 12,
  color: '#64748b',
  marginBottom: 4,
};

const inputStyle: CSSProperties = {
  minHeight: 36,
  border: '1px solid #d1d5db',
  borderRadius: 8,
  padding: '0 10px',
  fontSize: 14,
  boxSizing: 'border-box',
  width: '100%',
};

const primaryButtonStyle: CSSProperties = {
  padding: '8px 16px',
  borderRadius: 8,
  background: '#3b82f6',
  color: '#fff',
  border: 'none',
  cursor: 'pointer',
  fontSize: 13,
  fontWeight: 700,
};

const successButtonStyle: CSSProperties = {
  ...primaryButtonStyle,
  padding: '8px 20px',
  background: '#22c55e',
};

const travelButtonStyle: CSSProperties = {
  ...primaryButtonStyle,
  minHeight: 36,
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: 8,
};

const errorStyle: CSSProperties = {
  marginBottom: 12,
  padding: '10px 12px',
  borderRadius: 8,
  background: '#fee2e2',
  color: '#991b1b',
  fontSize: 13,
};

const th: CSSProperties = {
  textAlign: 'left',
  padding: '8px 12px',
  color: '#64748b',
  fontWeight: 500,
};

const td: CSSProperties = {
  padding: '10px 12px',
};

const actionBtn: CSSProperties = {
  background: 'none',
  border: '1px solid #e2e8f0',
  borderRadius: 4,
  padding: 4,
  cursor: 'pointer',
  display: 'flex',
};
