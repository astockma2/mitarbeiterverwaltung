import { useEffect, useState } from 'react';
import { TicketCheck, Plus, X, ChevronDown, ChevronUp } from 'lucide-react';
import Card, { Badge } from '../components/Card';
import { getTickets, createTicket, updateTicket, closeTicket } from '../services/api';

const STATUS_LABELS: Record<string, string> = {
  open: 'Offen',
  in_progress: 'In Bearbeitung',
  resolved: 'Gelöst',
  closed: 'Geschlossen',
};

const STATUS_COLORS: Record<string, string> = {
  open: '#3b82f6',
  in_progress: '#f59e0b',
  resolved: '#22c55e',
  closed: '#94a3b8',
};

const PRIORITY_LABELS: Record<string, string> = {
  low: 'Niedrig',
  medium: 'Mittel',
  high: 'Hoch',
  critical: 'Kritisch',
};

const PRIORITY_COLORS: Record<string, string> = {
  low: '#22c55e',
  medium: '#3b82f6',
  high: '#f59e0b',
  critical: '#ef4444',
};

interface Ticket {
  id: number;
  title: string;
  description: string;
  status: string;
  priority: string;
  created_by: number;
  creator_name: string | null;
  assigned_to: number | null;
  assignee_name: string | null;
  created_at: string;
  updated_at: string;
}

interface Props {
  isHR: boolean;
}

export default function Tickets({ isHR }: Props) {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [selectedTicket, setSelectedTicket] = useState<Ticket | null>(null);
  const [filterStatus, setFilterStatus] = useState('');
  const [filterPriority, setFilterPriority] = useState('');
  const [form, setForm] = useState({ title: '', description: '', priority: 'medium' });
  const [statusUpdate, setStatusUpdate] = useState('');

  const load = () => {
    const params: Record<string, string> = {};
    if (filterStatus) params.status = filterStatus;
    if (filterPriority) params.priority = filterPriority;
    getTickets(params).then((r) => setTickets(r.data));
  };

  useEffect(load, [filterStatus, filterPriority]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createTicket(form);
      setShowForm(false);
      setForm({ title: '', description: '', priority: 'medium' });
      load();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Fehler beim Erstellen');
    }
  };

  const handleStatusUpdate = async (ticket: Ticket) => {
    if (!statusUpdate) return;
    try {
      const updated = await updateTicket(ticket.id, { status: statusUpdate });
      setSelectedTicket(updated.data);
      setStatusUpdate('');
      load();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Fehler beim Aktualisieren');
    }
  };

  const handleClose = async (ticket: Ticket) => {
    if (!confirm(`Ticket #${ticket.id} wirklich schließen?`)) return;
    try {
      await closeTicket(ticket.id);
      setSelectedTicket(null);
      load();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Fehler');
    }
  };

  const inputStyle = {
    padding: '8px 10px', borderRadius: 6, border: '1px solid #d1d5db',
    fontSize: 14, width: '100%', boxSizing: 'border-box' as const,
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1e293b', margin: 0 }}>
          Tickets
        </h1>
        <button
          onClick={() => setShowForm(true)}
          style={{
            display: 'flex', alignItems: 'center', gap: 6,
            background: '#3b82f6', color: '#fff', border: 'none',
            borderRadius: 6, padding: '8px 14px', cursor: 'pointer', fontSize: 14,
          }}
        >
          <Plus size={16} /> Neues Ticket
        </button>
      </div>

      {/* Filter (nur für HR/Admin) */}
      {isHR && (
        <Card style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
            <div style={{ fontSize: 13, color: '#64748b', fontWeight: 500 }}>Filter:</div>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              style={{ ...inputStyle, width: 160 }}
            >
              <option value="">Alle Status</option>
              {Object.entries(STATUS_LABELS).map(([v, l]) => (
                <option key={v} value={v}>{l}</option>
              ))}
            </select>
            <select
              value={filterPriority}
              onChange={(e) => setFilterPriority(e.target.value)}
              style={{ ...inputStyle, width: 160 }}
            >
              <option value="">Alle Prioritäten</option>
              {Object.entries(PRIORITY_LABELS).map(([v, l]) => (
                <option key={v} value={v}>{l}</option>
              ))}
            </select>
            {(filterStatus || filterPriority) && (
              <button
                onClick={() => { setFilterStatus(''); setFilterPriority(''); }}
                style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', fontSize: 13 }}
              >
                Filter zurücksetzen
              </button>
            )}
          </div>
        </Card>
      )}

      {/* Formular: Neues Ticket */}
      {showForm && (
        <Card style={{ marginBottom: 20, border: '1px solid #bfdbfe' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h2 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>Neues Ticket erstellen</h2>
            <button onClick={() => setShowForm(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#94a3b8' }}>
              <X size={18} />
            </button>
          </div>
          <form onSubmit={handleCreate} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div>
              <label style={{ fontSize: 13, color: '#374151', display: 'block', marginBottom: 4 }}>Titel *</label>
              <input
                required
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                placeholder="Kurze Beschreibung des Problems"
                style={inputStyle}
              />
            </div>
            <div>
              <label style={{ fontSize: 13, color: '#374151', display: 'block', marginBottom: 4 }}>Beschreibung *</label>
              <textarea
                required
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                rows={4}
                placeholder="Detaillierte Beschreibung..."
                style={{ ...inputStyle, resize: 'vertical' }}
              />
            </div>
            <div>
              <label style={{ fontSize: 13, color: '#374151', display: 'block', marginBottom: 4 }}>Priorität</label>
              <select
                value={form.priority}
                onChange={(e) => setForm({ ...form, priority: e.target.value })}
                style={{ ...inputStyle, width: 200 }}
              >
                {Object.entries(PRIORITY_LABELS).map(([v, l]) => (
                  <option key={v} value={v}>{l}</option>
                ))}
              </select>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                type="submit"
                style={{ background: '#3b82f6', color: '#fff', border: 'none', borderRadius: 6, padding: '8px 16px', cursor: 'pointer', fontSize: 14 }}
              >
                Ticket erstellen
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                style={{ background: '#f1f5f9', color: '#374151', border: 'none', borderRadius: 6, padding: '8px 16px', cursor: 'pointer', fontSize: 14 }}
              >
                Abbrechen
              </button>
            </div>
          </form>
        </Card>
      )}

      {/* Ticket-Detailansicht */}
      {selectedTicket && (
        <Card style={{ marginBottom: 20, border: '1px solid #e2e8f0' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
            <div>
              <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 4 }}>Ticket #{selectedTicket.id}</div>
              <h2 style={{ fontSize: 17, fontWeight: 600, margin: 0, color: '#1e293b' }}>{selectedTicket.title}</h2>
            </div>
            <button onClick={() => setSelectedTicket(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#94a3b8' }}>
              <X size={18} />
            </button>
          </div>

          <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
            <Badge text={STATUS_LABELS[selectedTicket.status] || selectedTicket.status} color={STATUS_COLORS[selectedTicket.status]} />
            <Badge text={PRIORITY_LABELS[selectedTicket.priority] || selectedTicket.priority} color={PRIORITY_COLORS[selectedTicket.priority]} />
          </div>

          <div style={{ fontSize: 14, color: '#374151', marginBottom: 16, lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
            {selectedTicket.description}
          </div>

          <div style={{ display: 'flex', gap: 24, fontSize: 12, color: '#94a3b8', marginBottom: 16, flexWrap: 'wrap' }}>
            {selectedTicket.creator_name && (
              <span>Erstellt von: <strong style={{ color: '#64748b' }}>{selectedTicket.creator_name}</strong></span>
            )}
            {selectedTicket.assignee_name && (
              <span>Zugewiesen an: <strong style={{ color: '#64748b' }}>{selectedTicket.assignee_name}</strong></span>
            )}
            <span>Erstellt: {new Date(selectedTicket.created_at).toLocaleString('de-DE')}</span>
            <span>Aktualisiert: {new Date(selectedTicket.updated_at).toLocaleString('de-DE')}</span>
          </div>

          {selectedTicket.status !== 'closed' && (
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap', borderTop: '1px solid #f1f5f9', paddingTop: 12 }}>
              {isHR && (
                <>
                  <select
                    value={statusUpdate}
                    onChange={(e) => setStatusUpdate(e.target.value)}
                    style={{ ...inputStyle, width: 180 }}
                  >
                    <option value="">Status ändern...</option>
                    {Object.entries(STATUS_LABELS).map(([v, l]) => (
                      <option key={v} value={v}>{l}</option>
                    ))}
                  </select>
                  <button
                    onClick={() => handleStatusUpdate(selectedTicket)}
                    disabled={!statusUpdate}
                    style={{
                      background: statusUpdate ? '#3b82f6' : '#e2e8f0',
                      color: statusUpdate ? '#fff' : '#94a3b8',
                      border: 'none', borderRadius: 6, padding: '8px 14px',
                      cursor: statusUpdate ? 'pointer' : 'default', fontSize: 14,
                    }}
                  >
                    Speichern
                  </button>
                </>
              )}
              <button
                onClick={() => handleClose(selectedTicket)}
                style={{ background: '#fef2f2', color: '#ef4444', border: '1px solid #fecaca', borderRadius: 6, padding: '8px 14px', cursor: 'pointer', fontSize: 14 }}
              >
                Ticket schließen
              </button>
            </div>
          )}
        </Card>
      )}

      {/* Ticket-Liste */}
      {tickets.length === 0 ? (
        <Card>
          <div style={{ textAlign: 'center', padding: '32px 0', color: '#94a3b8' }}>
            <TicketCheck size={40} style={{ marginBottom: 12, opacity: 0.4 }} />
            <div style={{ fontSize: 15 }}>Keine Tickets vorhanden</div>
            <div style={{ fontSize: 13, marginTop: 4 }}>Erstellen Sie ein neues Ticket über den Button oben rechts.</div>
          </div>
        </Card>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {tickets.map((ticket) => (
            <div
              key={ticket.id}
              onClick={() => setSelectedTicket(selectedTicket?.id === ticket.id ? null : ticket)}
              style={{
                background: '#fff',
                borderRadius: 8,
                boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
                padding: '14px 16px',
                cursor: 'pointer',
                border: selectedTicket?.id === ticket.id ? '1px solid #3b82f6' : '1px solid transparent',
                transition: 'border-color 0.15s',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4, flexWrap: 'wrap' }}>
                    <span style={{ fontSize: 11, color: '#94a3b8' }}>#{ticket.id}</span>
                    <span style={{ fontSize: 14, fontWeight: 600, color: '#1e293b' }}>{ticket.title}</span>
                  </div>
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
                    <Badge text={STATUS_LABELS[ticket.status] || ticket.status} color={STATUS_COLORS[ticket.status]} />
                    <Badge text={PRIORITY_LABELS[ticket.priority] || ticket.priority} color={PRIORITY_COLORS[ticket.priority]} />
                    {isHR && ticket.creator_name && (
                      <span style={{ fontSize: 11, color: '#94a3b8' }}>von {ticket.creator_name}</span>
                    )}
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
                  <span style={{ fontSize: 11, color: '#94a3b8' }}>
                    {new Date(ticket.created_at).toLocaleDateString('de-DE')}
                  </span>
                  {selectedTicket?.id === ticket.id ? <ChevronUp size={16} color="#94a3b8" /> : <ChevronDown size={16} color="#94a3b8" />}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
