import { useEffect, useState, useRef } from 'react';
import { Plus, Calendar, CheckCircle, Eraser, MousePointer, Settings, Pencil, Trash2 } from 'lucide-react';
import Card, { Badge } from '../components/Card';
import {
  getShiftPlans, getShiftTemplates, viewShiftPlan, getEmployees,
  getDepartments, createShiftTemplate, updateShiftTemplate, deleteShiftTemplate,
} from '../services/api';
import api from '../services/api';

const STATUS_COLORS: Record<string, string> = {
  DRAFT: '#f59e0b', PUBLISHED: '#22c55e', ARCHIVED: '#94a3b8',
};
const STATUS_LABELS: Record<string, string> = {
  DRAFT: 'Entwurf', PUBLISHED: 'Veroeffentlicht', ARCHIVED: 'Archiviert',
};
const MONTH_NAMES = [
  'Januar', 'Februar', 'Maerz', 'April', 'Mai', 'Juni',
  'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember',
];
const WEEKDAY_SHORT = ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa'];

export default function ShiftPlans() {
  const [plans, setPlans] = useState<any[]>([]);
  const [templates, setTemplates] = useState<any[]>([]);
  const [departments, setDepartments] = useState<any[]>([]);
  const [employees, setEmployees] = useState<any[]>([]);
  const [selectedPlan, setSelectedPlan] = useState<any>(null);
  const [planView, setPlanView] = useState<any>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState({ department_id: '', year: new Date().getFullYear(), month: new Date().getMonth() + 1 });
  const [error, setError] = useState('');

  // Pinsel-Modus: ausgewaehlte Schichtvorlage oder "eraser"
  const [activeTool, setActiveTool] = useState<number | 'eraser' | null>(null);

  // Drag-Zustand
  const isDragging = useRef(false);
  const dragEmpId = useRef<number | null>(null);
  const draggedCells = useRef<Set<string>>(new Set());
  const [highlightCells, setHighlightCells] = useState<Set<string>>(new Set());
  const [saving, setSaving] = useState(false);

  // Schichtvorlagen-Verwaltung
  const [showTemplateManager, setShowTemplateManager] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<any>(null);
  const [templateForm, setTemplateForm] = useState({
    name: '', short_code: '', start_time: '06:00', end_time: '14:00',
    break_minutes: 30, crosses_midnight: false, color: '#3B82F6',
  });
  const [templateError, setTemplateError] = useState('');

  const openTemplateEdit = (t?: any) => {
    if (t) {
      setEditingTemplate(t);
      setTemplateForm({
        name: t.name, short_code: t.short_code, start_time: t.start_time,
        end_time: t.end_time, break_minutes: t.break_minutes,
        crosses_midnight: t.crosses_midnight, color: t.color,
      });
    } else {
      setEditingTemplate(null);
      setTemplateForm({
        name: '', short_code: '', start_time: '06:00', end_time: '14:00',
        break_minutes: 30, crosses_midnight: false, color: '#3B82F6',
      });
    }
    setTemplateError('');
  };

  const saveTemplate = async () => {
    setTemplateError('');
    if (!templateForm.name || !templateForm.short_code) {
      setTemplateError('Name und Kuerzel sind Pflichtfelder');
      return;
    }
    try {
      if (editingTemplate) {
        await updateShiftTemplate(editingTemplate.id, templateForm);
      } else {
        await createShiftTemplate(templateForm);
      }
      setEditingTemplate(null);
      load();
    } catch (err: any) {
      setTemplateError(err.response?.data?.detail || 'Fehler beim Speichern');
    }
  };

  const removeTemplate = async (id: number) => {
    if (!confirm('Schichtvorlage wirklich loeschen?')) return;
    try {
      await deleteShiftTemplate(id);
      load();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Fehler beim Loeschen');
    }
  };

  const load = () => {
    getShiftPlans().then((r) => setPlans(r.data));
    getShiftTemplates().then((r) => setTemplates(r.data));
    getDepartments().then((r) => setDepartments(r.data));
    getEmployees({ page_size: 100, is_active: true }).then((r) => setEmployees(r.data.items));
  };

  useEffect(load, []);

  // Global mouseup listener
  useEffect(() => {
    const handleMouseUp = () => {
      if (isDragging.current && draggedCells.current.size > 0) {
        commitDrag();
      }
      isDragging.current = false;
      dragEmpId.current = null;
      draggedCells.current = new Set();
      setHighlightCells(new Set());
    };
    window.addEventListener('mouseup', handleMouseUp);
    return () => window.removeEventListener('mouseup', handleMouseUp);
  }, [selectedPlan, activeTool, planView]);

  const loadPlanView = async (plan: any) => {
    const r = await viewShiftPlan(plan.id);
    setPlanView(r.data);
    setSelectedPlan(plan);
  };

  const createPlan = async () => {
    setError('');
    if (!createForm.department_id) { setError('Bitte Abteilung waehlen'); return; }
    try {
      await api.post('/shifts/plans', {
        department_id: parseInt(createForm.department_id),
        year: createForm.year,
        month: createForm.month,
      });
      setShowCreate(false);
      load();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Fehler beim Erstellen');
    }
  };

  const publishPlan = async (planId: number) => {
    try {
      await api.post(`/shifts/plans/${planId}/publish`);
      load();
      if (selectedPlan?.id === planId) loadPlanView({ ...selectedPlan, status: 'PUBLISHED' });
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Fehler');
    }
  };

  const commitDrag = async () => {
    if (!selectedPlan || !activeTool || draggedCells.current.size === 0) return;
    setSaving(true);

    const cells = Array.from(draggedCells.current);
    // Alle Zellen haben denselben empId (dragEmpId)
    const empId = dragEmpId.current;
    if (!empId) { setSaving(false); return; }

    try {
      if (activeTool === 'eraser') {
        // Loeschen: assignment IDs aus planView holen
        for (const cellKey of cells) {
          const dateStr = cellKey.split(':')[1];
          const assignmentId = findAssignmentId(empId, dateStr);
          if (assignmentId) {
            await api.delete(`/shifts/assignments/${assignmentId}`);
          }
        }
      } else {
        // Bulk-Zuweisung
        const dates = cells.map((c) => c.split(':')[1]);
        await api.post(`/shifts/plans/${selectedPlan.id}/assign-bulk`, {
          employee_id: empId,
          shift_template_id: activeTool,
          dates,
        });
      }
      await loadPlanView(selectedPlan);
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      if (typeof detail === 'object' && detail.errors) {
        alert('Regelverstoesse:\n' + detail.errors.join('\n'));
      } else if (detail) {
        alert(detail);
      }
      await loadPlanView(selectedPlan);
    } finally {
      setSaving(false);
    }
  };

  const findAssignmentId = (empId: number, dateStr: string): number | null => {
    if (!planView) return null;
    const emp = planView.employees?.find((e: any) => e.employee_id === empId);
    if (!emp) return null;
    const shift = emp.shifts?.[dateStr];
    return shift?.assignment_id || null;
  };

  const handleCellMouseDown = (empId: number, dateStr: string, e: React.MouseEvent) => {
    e.preventDefault();
    if (!activeTool || selectedPlan?.status === 'ARCHIVED' || saving) return;

    // Bei Eraser nur auf belegte Zellen, bei Pinsel nur auf leere
    if (activeTool === 'eraser') {
      if (!findAssignmentId(empId, dateStr)) return;
    } else {
      if (findAssignmentId(empId, dateStr)) return; // Schon belegt
    }

    isDragging.current = true;
    dragEmpId.current = empId;
    const key = `${empId}:${dateStr}`;
    draggedCells.current = new Set([key]);
    setHighlightCells(new Set([key]));
  };

  const handleCellMouseEnter = (empId: number, dateStr: string) => {
    if (!isDragging.current || empId !== dragEmpId.current || !activeTool) return;

    if (activeTool === 'eraser') {
      if (!findAssignmentId(empId, dateStr)) return;
    } else {
      if (findAssignmentId(empId, dateStr)) return;
    }

    const key = `${empId}:${dateStr}`;
    draggedCells.current.add(key);
    setHighlightCells(new Set(draggedCells.current));
  };

  const getActiveTemplate = () => {
    if (activeTool === 'eraser' || activeTool === null) return null;
    return templates.find((t) => t.id === activeTool) || null;
  };

  // Alle Mitarbeiter fuer die Kalenderansicht (Plan + Abteilung)
  const allCalendarEmployees = (): { id: number; name: string; inPlan: boolean }[] => {
    if (!planView) return [];
    const result: { id: number; name: string; inPlan: boolean }[] = [];
    const ids = new Set<number>();

    for (const emp of planView.employees || []) {
      result.push({ id: emp.employee_id, name: emp.employee_name, inPlan: true });
      ids.add(emp.employee_id);
    }

    const deptEmps = employees.filter((e) => e.department_id === selectedPlan?.department_id);
    for (const e of deptEmps) {
      if (!ids.has(e.id)) {
        result.push({ id: e.id, name: `${e.first_name} ${e.last_name}`, inPlan: false });
      }
    }
    return result;
  };

  const getShiftForCell = (empId: number, dateStr: string) => {
    const emp = planView?.employees?.find((e: any) => e.employee_id === empId);
    return emp?.shifts?.[dateStr] || null;
  };

  const activeTempl = getActiveTemplate();

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1e293b', margin: 0 }}>
          <Calendar size={22} style={{ verticalAlign: 'middle', marginRight: 8 }} />
          Dienstplanung
        </h1>
        <button onClick={() => setShowCreate(true)} style={primaryBtn}>
          <Plus size={16} /> Neuer Dienstplan
        </button>
      </div>

      {/* Werkzeugleiste: Schichtvorlagen als Pinsel */}
      <Card style={{ marginBottom: 20 }}>
        <div style={{ fontWeight: 600, fontSize: 14, color: '#334155', marginBottom: 10 }}>
          Werkzeug waehlen {activeTool && <span style={{ fontWeight: 400, fontSize: 12, color: '#64748b' }}>— dann im Kalender ueber Zellen ziehen</span>}
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          {/* Auswahl-Modus (kein Werkzeug) */}
          <button
            onClick={() => setActiveTool(null)}
            style={{
              ...toolBtn,
              border: activeTool === null ? '2px solid #3b82f6' : '2px solid #e2e8f0',
              background: activeTool === null ? '#eff6ff' : '#f8fafc',
            }}
          >
            <MousePointer size={14} style={{ color: '#64748b' }} />
            <span>Keine</span>
          </button>

          {/* Radierer */}
          <button
            onClick={() => setActiveTool('eraser')}
            style={{
              ...toolBtn,
              border: activeTool === 'eraser' ? '2px solid #ef4444' : '2px solid #e2e8f0',
              background: activeTool === 'eraser' ? '#fef2f2' : '#f8fafc',
            }}
          >
            <Eraser size={14} style={{ color: '#ef4444' }} />
            <span>Radierer</span>
          </button>

          <div style={{ width: 1, height: 32, background: '#e2e8f0', margin: '0 4px' }} />

          {/* Schichtvorlagen */}
          {templates.map((t) => (
            <button
              key={t.id}
              onClick={() => setActiveTool(t.id)}
              style={{
                ...toolBtn,
                border: activeTool === t.id ? `3px solid ${t.color}` : '2px solid #e2e8f0',
                background: activeTool === t.id ? t.color + '20' : '#f8fafc',
                boxShadow: activeTool === t.id ? `0 0 0 2px ${t.color}40` : 'none',
              }}
            >
              <span style={{
                fontWeight: 700, color: t.color, fontSize: 15,
                width: 24, textAlign: 'center',
              }}>{t.short_code}</span>
              <div style={{ textAlign: 'left' }}>
                <div style={{ fontSize: 12, fontWeight: 500, color: '#1e293b' }}>{t.name}</div>
                <div style={{ fontSize: 10, color: '#94a3b8' }}>{t.start_time}–{t.end_time}</div>
              </div>
            </button>
          ))}
        </div>
        {saving && <div style={{ marginTop: 8, fontSize: 13, color: '#3b82f6' }}>Speichere...</div>}
        <div style={{ marginTop: 10, borderTop: '1px solid #e2e8f0', paddingTop: 10 }}>
          <button onClick={() => { setShowTemplateManager(!showTemplateManager); openTemplateEdit(); }}
            style={{ ...smallBtn, gap: 6 }}>
            <Settings size={14} /> Schichtvorlagen verwalten
          </button>
        </div>

        {showTemplateManager && (
          <div style={{ marginTop: 12, border: '1px solid #e2e8f0', borderRadius: 8, padding: 16, background: '#fafafa' }}>
            <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 12 }}>Schichtvorlagen</div>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, marginBottom: 12 }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #e2e8f0' }}>
                  <th style={th}>Kuerzel</th>
                  <th style={th}>Name</th>
                  <th style={th}>Beginn</th>
                  <th style={th}>Ende</th>
                  <th style={th}>Pause</th>
                  <th style={th}>Farbe</th>
                  <th style={th}>Aktionen</th>
                </tr>
              </thead>
              <tbody>
                {templates.map((t: any) => (
                  <tr key={t.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                    <td style={tdd}><span style={{ fontWeight: 700, color: t.color }}>{t.short_code}</span></td>
                    <td style={tdd}>{t.name}</td>
                    <td style={tdd}>{t.start_time}</td>
                    <td style={tdd}>{t.end_time}</td>
                    <td style={tdd}>{t.break_minutes} min</td>
                    <td style={tdd}>
                      <span style={{ display: 'inline-block', width: 20, height: 20, borderRadius: 4, background: t.color, verticalAlign: 'middle' }} />
                    </td>
                    <td style={tdd}>
                      <div style={{ display: 'flex', gap: 4 }}>
                        <button onClick={() => openTemplateEdit(t)} style={{ ...smallBtn, padding: '3px 8px' }}>
                          <Pencil size={12} />
                        </button>
                        <button onClick={() => removeTemplate(t.id)}
                          style={{ ...smallBtn, padding: '3px 8px', color: '#ef4444', borderColor: '#fecaca' }}>
                          <Trash2 size={12} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Formular fuer Neue/Bearbeiten */}
            <div style={{ border: '1px solid #d1d5db', borderRadius: 8, padding: 12, background: '#fff' }}>
              <div style={{ fontWeight: 500, fontSize: 13, marginBottom: 8 }}>
                {editingTemplate ? `"${editingTemplate.name}" bearbeiten` : 'Neue Schichtvorlage'}
              </div>
              {templateError && <div style={{ color: '#dc2626', fontSize: 12, marginBottom: 8 }}>{templateError}</div>}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
                <div>
                  <label style={labelStyle}>Name *</label>
                  <input value={templateForm.name}
                    onChange={(e) => setTemplateForm((f) => ({ ...f, name: e.target.value }))}
                    style={inputStyle} placeholder="Fruehdienst" />
                </div>
                <div>
                  <label style={labelStyle}>Kuerzel *</label>
                  <input value={templateForm.short_code} maxLength={5}
                    onChange={(e) => setTemplateForm((f) => ({ ...f, short_code: e.target.value }))}
                    style={inputStyle} placeholder="F" />
                </div>
                <div>
                  <label style={labelStyle}>Beginn</label>
                  <input type="time" value={templateForm.start_time}
                    onChange={(e) => setTemplateForm((f) => ({ ...f, start_time: e.target.value }))}
                    style={inputStyle} />
                </div>
                <div>
                  <label style={labelStyle}>Ende</label>
                  <input type="time" value={templateForm.end_time}
                    onChange={(e) => setTemplateForm((f) => ({ ...f, end_time: e.target.value }))}
                    style={inputStyle} />
                </div>
                <div>
                  <label style={labelStyle}>Pause (min)</label>
                  <input type="number" value={templateForm.break_minutes}
                    onChange={(e) => setTemplateForm((f) => ({ ...f, break_minutes: parseInt(e.target.value) || 0 }))}
                    style={inputStyle} />
                </div>
                <div>
                  <label style={labelStyle}>Farbe</label>
                  <input type="color" value={templateForm.color}
                    onChange={(e) => setTemplateForm((f) => ({ ...f, color: e.target.value }))}
                    style={{ ...inputStyle, padding: 2, height: 34 }} />
                </div>
                <div style={{ display: 'flex', alignItems: 'end' }}>
                  <label style={{ fontSize: 13, display: 'flex', alignItems: 'center', gap: 6 }}>
                    <input type="checkbox" checked={templateForm.crosses_midnight}
                      onChange={(e) => setTemplateForm((f) => ({ ...f, crosses_midnight: e.target.checked }))} />
                    Ueber Mitternacht
                  </label>
                </div>
                <div style={{ display: 'flex', alignItems: 'end', gap: 6 }}>
                  <button onClick={saveTemplate} style={primaryBtn}>
                    {editingTemplate ? 'Speichern' : 'Erstellen'}
                  </button>
                  {editingTemplate && (
                    <button onClick={() => openTemplateEdit()} style={smallBtn}>Abbrechen</button>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </Card>

      {/* Dienstplaene */}
      <Card style={{ marginBottom: 20 }}>
        <div style={{ fontWeight: 600, fontSize: 14, color: '#334155', marginBottom: 10 }}>Dienstplaene</div>
        {plans.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 24, color: '#94a3b8', fontSize: 14 }}>
            Keine Dienstplaene vorhanden. Erstelle einen neuen Plan.
          </div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #e2e8f0' }}>
                <th style={th}>Abteilung</th>
                <th style={th}>Monat</th>
                <th style={th}>Status</th>
                <th style={th}>Aktionen</th>
              </tr>
            </thead>
            <tbody>
              {plans.map((p) => (
                <tr key={p.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                  <td style={{ ...tdd, fontWeight: 500 }}>{p.department_name || `Abt. ${p.department_id}`}</td>
                  <td style={tdd}>{MONTH_NAMES[p.month - 1]} {p.year}</td>
                  <td style={tdd}>
                    <Badge text={STATUS_LABELS[p.status] || p.status} color={STATUS_COLORS[p.status] || '#64748b'} />
                  </td>
                  <td style={tdd}>
                    <div style={{ display: 'flex', gap: 6 }}>
                      <button onClick={() => loadPlanView(p)} style={smallBtn}>Anzeigen</button>
                      {p.status === 'DRAFT' && (
                        <button onClick={() => publishPlan(p.id)} style={{ ...smallBtn, background: '#22c55e', color: '#fff', border: 'none' }}>
                          <CheckCircle size={12} /> Veroeffentlichen
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      {/* Kalender-Ansicht */}
      {planView && selectedPlan && (
        <Card>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <div>
              <div style={{ fontWeight: 600, fontSize: 16, color: '#1e293b' }}>
                {planView.department} — {MONTH_NAMES[planView.month - 1]} {planView.year}
              </div>
              <Badge text={STATUS_LABELS[planView.status] || planView.status} color={STATUS_COLORS[planView.status] || '#64748b'} />
            </div>
            <button onClick={() => { setPlanView(null); setSelectedPlan(null); }} style={smallBtn}>Schliessen</button>
          </div>

          <div style={{ overflowX: 'auto', userSelect: 'none' }}>
            <table style={{ borderCollapse: 'collapse', fontSize: 12, minWidth: '100%' }}>
              <thead>
                <tr>
                  <th style={{ ...thCal, minWidth: 140, textAlign: 'left', position: 'sticky', left: 0, background: '#fff', zIndex: 1 }}>
                    Mitarbeiter
                  </th>
                  {planView.days?.map((d: string) => {
                    const dt = new Date(d);
                    const wd = WEEKDAY_SHORT[dt.getDay()];
                    const isWeekend = dt.getDay() === 0 || dt.getDay() === 6;
                    return (
                      <th key={d} style={{
                        ...thCal, textAlign: 'center', minWidth: 36,
                        background: isWeekend ? '#fef3c7' : '#fff',
                      }}>
                        <div style={{ fontSize: 10, color: isWeekend ? '#d97706' : '#94a3b8' }}>{wd}</div>
                        <div>{dt.getDate()}</div>
                      </th>
                    );
                  })}
                </tr>
              </thead>
              <tbody>
                {allCalendarEmployees().map((emp) => (
                  <tr key={emp.id} style={{ opacity: emp.inPlan ? 1 : 0.55 }}>
                    <td style={{
                      ...tdCal, fontWeight: 500, whiteSpace: 'nowrap',
                      fontStyle: emp.inPlan ? 'normal' : 'italic',
                      position: 'sticky', left: 0, background: '#fff', zIndex: 1,
                    }}>
                      {emp.name}
                    </td>
                    {planView.days?.map((d: string) => {
                      const shift = getShiftForCell(emp.id, d);
                      const dt = new Date(d);
                      const isWeekend = dt.getDay() === 0 || dt.getDay() === 6;
                      const cellKey = `${emp.id}:${d}`;
                      const isHighlighted = highlightCells.has(cellKey);

                      // Hintergrundfarbe bestimmen
                      let bg = isWeekend ? '#fffbeb' : undefined;
                      if (shift) {
                        bg = shift.color + '30';
                      }
                      if (isHighlighted) {
                        bg = activeTool === 'eraser' ? '#fecaca' : (activeTempl ? activeTempl.color + '50' : '#bfdbfe');
                      }

                      return (
                        <td key={d}
                          onMouseDown={(e) => handleCellMouseDown(emp.id, d, e)}
                          onMouseEnter={() => handleCellMouseEnter(emp.id, d)}
                          style={{
                            ...tdCal, textAlign: 'center',
                            cursor: activeTool ? 'crosshair' : 'default',
                            background: bg,
                            transition: 'background 0.1s',
                            border: isHighlighted ? '2px solid ' + (activeTool === 'eraser' ? '#ef4444' : (activeTempl?.color || '#3b82f6')) : '1px solid #f1f5f9',
                          }}
                          title={shift ? shift.shift_name : ''}
                        >
                          {shift ? (
                            <span style={{ fontWeight: 700, color: shift.color || '#1e293b', fontSize: 11 }}>
                              {shift.shift_code}
                            </span>
                          ) : (
                            <span style={{ color: '#e2e8f0', fontSize: 10 }}>·</span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Legende */}
          <div style={{ marginTop: 12, display: 'flex', gap: 12, flexWrap: 'wrap', fontSize: 11, color: '#64748b' }}>
            <span>Legende:</span>
            {templates.map((t) => (
              <span key={t.id} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ width: 14, height: 14, borderRadius: 3, background: t.color, display: 'inline-block' }} />
                {t.short_code} = {t.name} ({t.start_time}–{t.end_time})
              </span>
            ))}
          </div>
        </Card>
      )}

      {/* Dialog: Neuen Plan erstellen */}
      {showCreate && (
        <div style={overlay}>
          <div style={dialogStyle}>
            <h3 style={{ margin: '0 0 16px', fontSize: 16, color: '#1e293b' }}>Neuen Dienstplan erstellen</h3>
            {error && <div style={{ color: '#dc2626', fontSize: 13, marginBottom: 10 }}>{error}</div>}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div>
                <label style={labelStyle}>Abteilung</label>
                <select value={createForm.department_id}
                  onChange={(e) => setCreateForm((f) => ({ ...f, department_id: e.target.value }))}
                  style={inputStyle}>
                  <option value="">-- Waehlen --</option>
                  {departments.map((d: any) => <option key={d.id} value={d.id}>{d.name}</option>)}
                </select>
              </div>
              <div style={{ display: 'flex', gap: 12 }}>
                <div style={{ flex: 1 }}>
                  <label style={labelStyle}>Jahr</label>
                  <input type="number" value={createForm.year}
                    onChange={(e) => setCreateForm((f) => ({ ...f, year: parseInt(e.target.value) }))}
                    style={inputStyle} />
                </div>
                <div style={{ flex: 1 }}>
                  <label style={labelStyle}>Monat</label>
                  <select value={createForm.month}
                    onChange={(e) => setCreateForm((f) => ({ ...f, month: parseInt(e.target.value) }))}
                    style={inputStyle}>
                    {MONTH_NAMES.map((m, i) => <option key={i} value={i + 1}>{m}</option>)}
                  </select>
                </div>
              </div>
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 20 }}>
              <button onClick={() => { setShowCreate(false); setError(''); }} style={smallBtn}>Abbrechen</button>
              <button onClick={createPlan} style={primaryBtn}>Erstellen</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const th: React.CSSProperties = { textAlign: 'left', padding: '8px 12px', color: '#64748b', fontWeight: 500 };
const tdd: React.CSSProperties = { padding: '8px 12px' };
const thCal: React.CSSProperties = { padding: '4px 3px', color: '#475569', fontWeight: 600, borderBottom: '2px solid #e2e8f0' };
const tdCal: React.CSSProperties = { padding: '4px 3px', borderBottom: '1px solid #f1f5f9' };

const toolBtn: React.CSSProperties = {
  display: 'flex', alignItems: 'center', gap: 6, padding: '6px 12px',
  borderRadius: 8, cursor: 'pointer', fontSize: 13, background: '#f8fafc',
  transition: 'all 0.15s',
};

const primaryBtn: React.CSSProperties = {
  display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px',
  background: '#3b82f6', color: '#fff', border: 'none', borderRadius: 8,
  cursor: 'pointer', fontSize: 14, fontWeight: 500,
};
const smallBtn: React.CSSProperties = {
  padding: '5px 12px', borderRadius: 6, border: '1px solid #d1d5db',
  background: '#fff', fontSize: 13, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4,
};
const overlay: React.CSSProperties = {
  position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
  background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
};
const dialogStyle: React.CSSProperties = {
  background: '#fff', borderRadius: 12, padding: 24, minWidth: 380, maxWidth: 480, boxShadow: '0 20px 60px rgba(0,0,0,0.2)',
};
const labelStyle: React.CSSProperties = { display: 'block', fontSize: 12, color: '#64748b', marginBottom: 4 };
const inputStyle: React.CSSProperties = {
  width: '100%', padding: '8px 10px', borderRadius: 6, border: '1px solid #d1d5db',
  fontSize: 14, boxSizing: 'border-box',
};
