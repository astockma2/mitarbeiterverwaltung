import { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, ChevronDown, ChevronRight } from 'lucide-react';
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
const EMPLOYMENT_LABELS: Record<string, string> = {
  FULLTIME: 'Vollzeit', PARTTIME: 'Teilzeit', MINI: 'Minijob', TRAINEE: 'Azubi',
};

export default function Employees() {
  const navigate = useNavigate();
  const [employees, setEmployees] = useState<any[]>([]);
  const [search, setSearch] = useState('');
  const [departments, setDepartments] = useState<any[]>([]);
  const [deptFilter, setDeptFilter] = useState('');
  const [collapsedDepts, setCollapsedDepts] = useState<Set<string>>(new Set());

  useEffect(() => {
    getDepartments().then((r) => setDepartments(r.data));
  }, []);

  useEffect(() => {
    const params: any = { page_size: 100 };
    if (deptFilter) params.department_id = deptFilter;
    getEmployees(params).then((r) => {
      setEmployees(r.data.items);
    });
  }, [deptFilter]);

  // Client-seitige Suche + Gruppierung nach Abteilung
  const filtered = useMemo(() => {
    if (!search) return employees;
    const q = search.toLowerCase();
    return employees.filter((e) =>
      `${e.first_name} ${e.last_name}`.toLowerCase().includes(q) ||
      e.personnel_number?.toLowerCase().includes(q) ||
      e.email?.toLowerCase().includes(q)
    );
  }, [employees, search]);

  const grouped = useMemo(() => {
    const deptMap = new Map<string, { dept: any; emps: any[] }>();
    for (const e of filtered) {
      const deptName = e.department_name || 'Ohne Abteilung';
      if (!deptMap.has(deptName)) {
        const dept = departments.find((d) => d.id === e.department_id);
        deptMap.set(deptName, { dept, emps: [] });
      }
      deptMap.get(deptName)!.emps.push(e);
    }
    return Array.from(deptMap.entries()).sort((a, b) => a[0].localeCompare(b[0]));
  }, [filtered, departments]);

  const toggleDept = (name: string) => {
    setCollapsedDepts((prev) => {
      const next = new Set(prev);
      next.has(name) ? next.delete(name) : next.add(name);
      return next;
    });
  };

  return (
    <div>
      <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1e293b', marginBottom: 24 }}>
        Mitarbeiter ({filtered.length})
      </h1>

      {/* Filter */}
      <Card style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
          <div style={{ position: 'relative', flex: 1, minWidth: 200 }}>
            <Search size={16} style={{ position: 'absolute', left: 10, top: 10, color: '#94a3b8' }} />
            <input
              placeholder="Name, Personalnummer, E-Mail..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{
                width: '100%', padding: '8px 8px 8px 34px', borderRadius: 6,
                border: '1px solid #d1d5db', fontSize: 14, boxSizing: 'border-box',
              }}
            />
          </div>
          <select
            value={deptFilter}
            onChange={(e) => setDeptFilter(e.target.value)}
            style={{ padding: '8px 12px', borderRadius: 6, border: '1px solid #d1d5db', fontSize: 14 }}
          >
            <option value="">Alle Abteilungen</option>
            {departments.map((d: any) => (
              <option key={d.id} value={d.id}>{d.name}</option>
            ))}
          </select>
        </div>
      </Card>

      {/* Gruppierte Tabelle */}
      {grouped.map(([deptName, { emps }]) => {
        const collapsed = collapsedDepts.has(deptName);
        return (
          <Card key={deptName} style={{ marginBottom: 12 }}>
            <div
              onClick={() => toggleDept(deptName)}
              style={{
                display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer',
                padding: '4px 0', marginBottom: collapsed ? 0 : 8,
              }}
            >
              {collapsed ? <ChevronRight size={18} color="#64748b" /> : <ChevronDown size={18} color="#64748b" />}
              <span style={{ fontWeight: 600, fontSize: 15, color: '#1e293b' }}>{deptName}</span>
              <span style={{ fontSize: 12, color: '#94a3b8', marginLeft: 4 }}>({emps.length})</span>
            </div>

            {!collapsed && (
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
                <thead>
                  <tr style={{ borderBottom: '2px solid #e2e8f0' }}>
                    <th style={th}>PNr</th>
                    <th style={th}>Name</th>
                    <th style={th}>E-Mail</th>
                    <th style={th}>Beschaeftigung</th>
                    <th style={th}>Rolle</th>
                    <th style={th}>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {emps.map((e: any) => (
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
                        <span style={{ color: '#475569', fontSize: 13 }}>
                          {EMPLOYMENT_LABELS[e.employment_type] || e.employment_type}
                        </span>
                      </td>
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
            )}
          </Card>
        );
      })}

      {filtered.length === 0 && (
        <Card>
          <div style={{ textAlign: 'center', padding: 32, color: '#94a3b8', fontSize: 14 }}>
            Keine Mitarbeiter gefunden.
          </div>
        </Card>
      )}
    </div>
  );
}

const th = { textAlign: 'left' as const, padding: '8px 12px', color: '#64748b', fontWeight: 500 as const };
const td = { padding: '10px 12px' };
