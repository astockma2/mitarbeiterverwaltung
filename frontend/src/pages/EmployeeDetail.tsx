import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Save, X, Pencil, User, MapPin, Briefcase, Phone, Shield, KeyRound } from 'lucide-react';
import Card from '../components/Card';
import { getEmployee, updateEmployee, getDepartments, resetEmployeePassword } from '../services/api';

const ROLE_LABELS: Record<string, string> = {
  ADMIN: 'Admin', HR: 'HR', DEPARTMENT_MANAGER: 'Abteilungsleitung',
  TEAM_LEADER: 'Teamleitung', EMPLOYEE: 'Mitarbeiter',
};
const EMPLOYMENT_LABELS: Record<string, string> = {
  FULLTIME: 'Vollzeit', PARTTIME: 'Teilzeit', MINI: 'Minijob', TRAINEE: 'Auszubildende/r',
};

interface EmployeeData {
  id: number;
  personnel_number: string;
  ad_username: string | null;
  first_name: string;
  last_name: string;
  email: string | null;
  phone: string | null;
  mobile: string | null;
  date_of_birth: string | null;
  street: string | null;
  zip_code: string | null;
  city: string | null;
  department_id: number | null;
  department: { id: number; name: string; short_name: string } | null;
  role: string;
  job_title: string | null;
  employment_type: string;
  weekly_hours: number;
  hire_date: string;
  exit_date: string | null;
  is_active: boolean;
  vacation_days_per_year: number;
  emergency_contact_name: string | null;
  emergency_contact_phone: string | null;
  qualifications: { id: number; name: string; description: string | null; valid_until: string | null }[];
  created_at: string;
}

export default function EmployeeDetail({ isHR, isAdmin }: { isHR: boolean; isAdmin: boolean }) {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [employee, setEmployee] = useState<EmployeeData | null>(null);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<Record<string, any>>({});
  const [departments, setDepartments] = useState<any[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [password, setPassword] = useState('');
  const [passwordRepeat, setPasswordRepeat] = useState('');
  const [passwordSaving, setPasswordSaving] = useState(false);
  const [passwordMessage, setPasswordMessage] = useState('');

  useEffect(() => {
    if (!id) return;
    getEmployee(Number(id)).then((r) => setEmployee(r.data)).catch(() => navigate('/employees'));
    getDepartments().then((r) => setDepartments(r.data));
  }, [id]);

  const startEdit = () => {
    if (!employee) return;
    setForm({
      first_name: employee.first_name,
      last_name: employee.last_name,
      email: employee.email || '',
      phone: employee.phone || '',
      mobile: employee.mobile || '',
      date_of_birth: employee.date_of_birth || '',
      street: employee.street || '',
      zip_code: employee.zip_code || '',
      city: employee.city || '',
      department_id: employee.department_id || '',
      role: employee.role,
      job_title: employee.job_title || '',
      employment_type: employee.employment_type,
      weekly_hours: employee.weekly_hours,
      vacation_days_per_year: employee.vacation_days_per_year,
      emergency_contact_name: employee.emergency_contact_name || '',
      emergency_contact_phone: employee.emergency_contact_phone || '',
      is_active: employee.is_active,
    });
    setEditing(true);
    setError('');
  };

  const cancelEdit = () => {
    setEditing(false);
    setForm({});
    setError('');
  };

  const saveChanges = async () => {
    if (!employee) return;
    setSaving(true);
    setError('');
    try {
      // Nur geaenderte Felder senden
      const changes: Record<string, any> = {};
      for (const [key, value] of Object.entries(form)) {
        const orig = (employee as any)[key];
        const origStr = orig === null || orig === undefined ? '' : String(orig);
        const newStr = value === '' ? '' : String(value);
        if (origStr !== newStr) {
          if (value === '' && (key !== 'is_active' && key !== 'weekly_hours' && key !== 'vacation_days_per_year')) {
            changes[key] = null;
          } else if (key === 'weekly_hours') {
            changes[key] = parseFloat(value);
          } else if (key === 'vacation_days_per_year' || key === 'department_id') {
            changes[key] = value ? parseInt(value) : null;
          } else if (key === 'is_active') {
            changes[key] = value;
          } else {
            changes[key] = value;
          }
        }
      }
      if (Object.keys(changes).length === 0) {
        setEditing(false);
        return;
      }
      const res = await updateEmployee(employee.id, changes);
      setEmployee(res.data);
      setEditing(false);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Fehler beim Speichern');
    } finally {
      setSaving(false);
    }
  };

  const setField = (key: string, value: any) => setForm((f) => ({ ...f, [key]: value }));

  const savePassword = async () => {
    if (!employee) return;
    setError('');
    setPasswordMessage('');
    if (password.length < 8) {
      setError('Das neue Passwort muss mindestens 8 Zeichen lang sein.');
      return;
    }
    if (password !== passwordRepeat) {
      setError('Die beiden Passwoerter stimmen nicht ueberein.');
      return;
    }
    setPasswordSaving(true);
    try {
      await resetEmployeePassword(employee.id, password);
      setPassword('');
      setPasswordRepeat('');
      setPasswordMessage('Passwort wurde gesetzt.');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Passwort konnte nicht gesetzt werden');
    } finally {
      setPasswordSaving(false);
    }
  };

  if (!employee) {
    return <div style={{ padding: 40, color: '#64748b' }}>Laden...</div>;
  }

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
        <button onClick={() => navigate('/employees')} style={backBtn}>
          <ArrowLeft size={18} />
        </button>
        <div style={{ flex: 1 }}>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1e293b', margin: 0 }}>
            {employee.first_name} {employee.last_name}
          </h1>
          <span style={{ fontSize: 13, color: '#64748b' }}>
            {employee.personnel_number} · {employee.job_title || 'Keine Berufsbezeichnung'}
          </span>
        </div>
        {isHR && !editing && (
          <button onClick={startEdit} style={editBtn}>
            <Pencil size={15} /> Bearbeiten
          </button>
        )}
        {editing && (
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={cancelEdit} style={cancelBtn}><X size={15} /> Abbrechen</button>
            <button onClick={saveChanges} disabled={saving} style={saveBtn}>
              <Save size={15} /> {saving ? 'Speichere...' : 'Speichern'}
            </button>
          </div>
        )}
      </div>

      {error && (
        <div style={{ background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 8, padding: '10px 14px', marginBottom: 16, color: '#dc2626', fontSize: 14 }}>
          {error}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
        {/* Persoenliche Daten */}
        <Card>
          <SectionTitle icon={<User size={16} />} text="Persoenliche Daten" />
          <div style={fieldGrid}>
            <Field label="Vorname" value={employee.first_name} editing={editing}
              editValue={form.first_name} onChange={(v) => setField('first_name', v)} />
            <Field label="Nachname" value={employee.last_name} editing={editing}
              editValue={form.last_name} onChange={(v) => setField('last_name', v)} />
            <Field label="Geburtsdatum" value={formatDate(employee.date_of_birth)} editing={editing}
              editValue={form.date_of_birth} onChange={(v) => setField('date_of_birth', v)} type="date" />
            <Field label="E-Mail" value={employee.email} editing={editing}
              editValue={form.email} onChange={(v) => setField('email', v)} type="email" />
            <Field label="Telefon" value={employee.phone} editing={editing}
              editValue={form.phone} onChange={(v) => setField('phone', v)} />
            <Field label="Mobil" value={employee.mobile} editing={editing}
              editValue={form.mobile} onChange={(v) => setField('mobile', v)} />
            <Field label="AD-Benutzername" value={employee.ad_username} />
          </div>
        </Card>

        {/* Adresse */}
        <Card>
          <SectionTitle icon={<MapPin size={16} />} text="Adresse" />
          <div style={fieldGrid}>
            <Field label="Strasse" value={employee.street} editing={editing} fullWidth
              editValue={form.street} onChange={(v) => setField('street', v)} />
            <Field label="PLZ" value={employee.zip_code} editing={editing}
              editValue={form.zip_code} onChange={(v) => setField('zip_code', v)} />
            <Field label="Ort" value={employee.city} editing={editing}
              editValue={form.city} onChange={(v) => setField('city', v)} />
          </div>

          <div style={{ marginTop: 24 }} />
          <SectionTitle icon={<Shield size={16} />} text="Notfallkontakt" />
          <div style={fieldGrid}>
            <Field label="Name" value={employee.emergency_contact_name} editing={editing}
              editValue={form.emergency_contact_name} onChange={(v) => setField('emergency_contact_name', v)} />
            <Field label="Telefon" value={employee.emergency_contact_phone} editing={editing}
              editValue={form.emergency_contact_phone} onChange={(v) => setField('emergency_contact_phone', v)} />
          </div>
        </Card>

        {/* Beschaeftigung */}
        <Card>
          <SectionTitle icon={<Briefcase size={16} />} text="Beschaeftigung" />
          <div style={fieldGrid}>
            <Field label="Berufsbezeichnung" value={employee.job_title} editing={editing} fullWidth
              editValue={form.job_title} onChange={(v) => setField('job_title', v)} />
            {editing ? (
              <div style={fieldWrap}>
                <label style={fieldLabel}>Abteilung</label>
                <select value={form.department_id} onChange={(e) => setField('department_id', e.target.value)}
                  style={inputStyle}>
                  <option value="">-- Keine --</option>
                  {departments.map((d: any) => <option key={d.id} value={d.id}>{d.name}</option>)}
                </select>
              </div>
            ) : (
              <Field label="Abteilung" value={employee.department?.name || '--'} />
            )}
            {editing ? (
              <div style={fieldWrap}>
                <label style={fieldLabel}>Rolle</label>
                <select value={form.role} onChange={(e) => setField('role', e.target.value)} style={inputStyle}>
                  {Object.entries(ROLE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </div>
            ) : (
              <Field label="Rolle" value={ROLE_LABELS[employee.role] || employee.role} />
            )}
            {editing ? (
              <div style={fieldWrap}>
                <label style={fieldLabel}>Beschaeftigungsart</label>
                <select value={form.employment_type} onChange={(e) => setField('employment_type', e.target.value)}
                  style={inputStyle}>
                  {Object.entries(EMPLOYMENT_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </div>
            ) : (
              <Field label="Beschaeftigungsart" value={EMPLOYMENT_LABELS[employee.employment_type] || employee.employment_type} />
            )}
            <Field label="Wochenstunden" value={`${employee.weekly_hours} h`} editing={editing}
              editValue={form.weekly_hours} onChange={(v) => setField('weekly_hours', v)} type="number" />
            <Field label="Urlaubstage/Jahr" value={`${employee.vacation_days_per_year} Tage`} editing={editing}
              editValue={form.vacation_days_per_year} onChange={(v) => setField('vacation_days_per_year', v)} type="number" />
            <Field label="Eintrittsdatum" value={formatDate(employee.hire_date)} />
            <Field label="Austrittsdatum" value={formatDate(employee.exit_date)} />
            {editing ? (
              <div style={fieldWrap}>
                <label style={fieldLabel}>Status</label>
                <select value={form.is_active ? 'true' : 'false'}
                  onChange={(e) => setField('is_active', e.target.value === 'true')} style={inputStyle}>
                  <option value="true">Aktiv</option>
                  <option value="false">Inaktiv</option>
                </select>
              </div>
            ) : (
              <Field label="Status" value={employee.is_active ? 'Aktiv' : 'Inaktiv'} />
            )}
          </div>
        </Card>

        {/* Kontakt & Qualifikationen */}
        <Card>
          <SectionTitle icon={<Phone size={16} />} text="Qualifikationen" />
          {employee.qualifications.length === 0 ? (
            <p style={{ color: '#94a3b8', fontSize: 14 }}>Keine Qualifikationen hinterlegt.</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {employee.qualifications.map((q) => (
                <div key={q.id} style={{
                  padding: '8px 12px', background: '#f8fafc', borderRadius: 6,
                  border: '1px solid #e2e8f0', fontSize: 14,
                }}>
                  <strong>{q.name}</strong>
                  {q.description && <span style={{ color: '#64748b' }}> — {q.description}</span>}
                  {q.valid_until && (
                    <span style={{ color: '#f59e0b', marginLeft: 8, fontSize: 12 }}>
                      Gueltig bis {formatDate(q.valid_until)}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}

          <div style={{ marginTop: 24 }}>
            <div style={{ fontSize: 12, color: '#94a3b8' }}>
              Erstellt am {new Date(employee.created_at).toLocaleDateString('de-DE')}
            </div>
          </div>
        </Card>

        {isAdmin && (
          <Card>
            <SectionTitle icon={<KeyRound size={16} />} text="Login & Passwort" />
            <div style={{ color: '#64748b', fontSize: 13, marginBottom: 12 }}>
              Benutzername: <span style={{ color: '#1e293b', fontWeight: 600 }}>{employee.ad_username || '--'}</span>
            </div>
            <div style={fieldGrid}>
              <div style={fieldWrap}>
                <label style={fieldLabel}>Neues Passwort</label>
                <input
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  style={inputStyle}
                  minLength={8}
                  autoComplete="new-password"
                />
              </div>
              <div style={fieldWrap}>
                <label style={fieldLabel}>Wiederholen</label>
                <input
                  type="password"
                  value={passwordRepeat}
                  onChange={(event) => setPasswordRepeat(event.target.value)}
                  style={inputStyle}
                  minLength={8}
                  autoComplete="new-password"
                />
              </div>
            </div>
            {passwordMessage && (
              <div style={{ color: '#15803d', fontSize: 13, marginTop: 10 }}>{passwordMessage}</div>
            )}
            <button
              onClick={savePassword}
              disabled={passwordSaving || !employee.ad_username}
              style={{ ...saveBtn, marginTop: 14 }}
            >
              <KeyRound size={15} /> {passwordSaving ? 'Setze...' : 'Passwort setzen'}
            </button>
          </Card>
        )}
      </div>
    </div>
  );
}

function SectionTitle({ icon, text }: { icon: React.ReactNode; text: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16, color: '#334155', fontWeight: 600, fontSize: 15 }}>
      {icon} {text}
    </div>
  );
}

function Field({ label, value, editing, editValue, onChange, type, fullWidth }: {
  label: string; value: any; editing?: boolean; editValue?: any;
  onChange?: (v: string) => void; type?: string; fullWidth?: boolean;
}) {
  if (editing && onChange) {
    return (
      <div style={{ ...fieldWrap, ...(fullWidth ? { gridColumn: '1 / -1' } : {}) }}>
        <label style={fieldLabel}>{label}</label>
        <input type={type || 'text'} value={editValue ?? ''} onChange={(e) => onChange(e.target.value)}
          style={inputStyle} step={type === 'number' ? '0.5' : undefined} />
      </div>
    );
  }
  return (
    <div style={{ ...fieldWrap, ...(fullWidth ? { gridColumn: '1 / -1' } : {}) }}>
      <div style={fieldLabel}>{label}</div>
      <div style={{ fontSize: 14, color: '#1e293b' }}>{value || '--'}</div>
    </div>
  );
}

function formatDate(d: string | null | undefined): string {
  if (!d) return '--';
  return new Date(d).toLocaleDateString('de-DE');
}

const fieldGrid: React.CSSProperties = { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px 20px' };
const fieldWrap: React.CSSProperties = {};
const fieldLabel: React.CSSProperties = { fontSize: 12, color: '#64748b', marginBottom: 2 };
const inputStyle: React.CSSProperties = {
  width: '100%', padding: '6px 10px', borderRadius: 6,
  border: '1px solid #d1d5db', fontSize: 14, boxSizing: 'border-box',
};

const backBtn: React.CSSProperties = {
  background: '#f1f5f9', border: 'none', borderRadius: 8, padding: 8,
  cursor: 'pointer', color: '#475569', display: 'flex', alignItems: 'center',
};
const editBtn: React.CSSProperties = {
  display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px',
  background: '#3b82f6', color: '#fff', border: 'none', borderRadius: 8,
  cursor: 'pointer', fontSize: 14, fontWeight: 500,
};
const saveBtn: React.CSSProperties = {
  display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px',
  background: '#22c55e', color: '#fff', border: 'none', borderRadius: 8,
  cursor: 'pointer', fontSize: 14, fontWeight: 500,
};
const cancelBtn: React.CSSProperties = {
  display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px',
  background: '#f1f5f9', color: '#475569', border: '1px solid #d1d5db', borderRadius: 8,
  cursor: 'pointer', fontSize: 14,
};
