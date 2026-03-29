import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, UserPlus } from 'lucide-react';
import Card, { Badge } from '../components/Card';
import { getEmployees, getDepartments } from '../services/api';

const ROLE_COLORS: Record<string, string> = {
  ADMIN: '#ef4444', HR: '#8b5cf6', DEPARTMENT_MANAGER: '#3b82f6',
  TEAM_LEADER: '#f59e0b', EMPLOYEE: '#64748b',
};
const ROLE_LABELS: Record<string, string> = {
  ADMIN: 'Admin', HR: 'HR', DEPARTMENT_MANAGER: 'Abt.Leitung',
  TEAM_LEADER: 'Teamleitung', EMPLOYEE: 'Mitarbeiter',
};

export default function Employees() {
  const navigate = useNavigate();
  const [employees, setEmployees] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [departments, setDepartments] = useState<any[]>([]);
  const [deptFilter, setDeptFilter] = useState('');

  useEffect(() => {
    getDepartments().then((r) => setDepartments(r.data));
  }, []);

  useEffect(() => {
    const params: any = { page, page_size: 20 };
    if (search) params.search = search;
    if (deptFilter) params.department_id = deptFilter;
    getEmployees(params).then((r) => {
      setEmployees(r.data.items);
      setTotal(r.data.total);
    });
  }, [page, search, deptFilter]);

  return (
    <div>
      <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1e293b', marginBottom: 24 }}>
        Mitarbeiter ({total})
      </h1>

      {/* Filter */}
      <Card style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
          <div style={{ position: 'relative', flex: 1, minWidth: 200 }}>
            <Search size={16} style={{ position: 'absolute', left: 10, top: 10, color: '#94a3b8' }} />
            <input
              placeholder="Name, Personalnummer..."
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              style={{
                width: '100%', padding: '8px 8px 8px 34px', borderRadius: 6,
                border: '1px solid #d1d5db', fontSize: 14, boxSizing: 'border-box',
              }}
            />
          </div>
          <select
            value={deptFilter}
            onChange={(e) => { setDeptFilter(e.target.value); setPage(1); }}
            style={{ padding: '8px 12px', borderRadius: 6, border: '1px solid #d1d5db', fontSize: 14 }}
          >
            <option value="">Alle Abteilungen</option>
            {departments.map((d: any) => (
              <option key={d.id} value={d.id}>{d.name}</option>
            ))}
          </select>
        </div>
      </Card>

      {/* Tabelle */}
      <Card>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #e2e8f0' }}>
              <th style={th}>PNr</th>
              <th style={th}>Name</th>
              <th style={th}>E-Mail</th>
              <th style={th}>Rolle</th>
              <th style={th}>Status</th>
            </tr>
          </thead>
          <tbody>
            {employees.map((e) => (
              <tr key={e.id} onClick={() => navigate(`/employees/${e.id}`)}
                style={{ borderBottom: '1px solid #f1f5f9', cursor: 'pointer', transition: 'background 0.15s' }}
                onMouseEnter={(ev) => ev.currentTarget.style.background = '#f8fafc'}
                onMouseLeave={(ev) => ev.currentTarget.style.background = ''}>
                <td style={td}>
                  <span style={{ fontFamily: 'monospace', color: '#64748b' }}>{e.personnel_number}</span>
                </td>
                <td style={{ ...td, fontWeight: 500 }}>{e.first_name} {e.last_name}</td>
                <td style={{ ...td, color: '#64748b' }}>{e.email || '--'}</td>
                <td style={td}>
                  <Badge text={ROLE_LABELS[e.role] || e.role} color={ROLE_COLORS[e.role] || '#64748b'} />
                </td>
                <td style={td}>
                  <Badge text={e.is_active ? 'Aktiv' : 'Inaktiv'} color={e.is_active ? '#22c55e' : '#ef4444'} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {/* Paginierung */}
        {total > 20 && (
          <div style={{ display: 'flex', justifyContent: 'center', gap: 8, marginTop: 16 }}>
            <button disabled={page <= 1} onClick={() => setPage(page - 1)}
              style={pgBtn}>Zurueck</button>
            <span style={{ padding: '6px 12px', fontSize: 13 }}>Seite {page}</span>
            <button disabled={employees.length < 20} onClick={() => setPage(page + 1)}
              style={pgBtn}>Weiter</button>
          </div>
        )}
      </Card>
    </div>
  );
}

const th = { textAlign: 'left' as const, padding: '8px 12px', color: '#64748b', fontWeight: 500 as const };
const td = { padding: '10px 12px' };
const pgBtn = {
  padding: '6px 14px', borderRadius: 6, border: '1px solid #d1d5db',
  background: '#fff', fontSize: 13, cursor: 'pointer',
};
