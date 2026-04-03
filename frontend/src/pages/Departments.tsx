import { useEffect, useState } from 'react';
import { Building2 } from 'lucide-react';
import Card from '../components/Card';
import { getDepartments } from '../services/api';

export default function Departments() {
  const [departments, setDepartments] = useState<any[]>([]);

  useEffect(() => {
    getDepartments().then((r) => setDepartments(r.data));
  }, []);

  return (
    <div>
      <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1e293b', marginBottom: 24 }}>
        Abteilungen ({departments.length})
      </h1>

      <Card>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #e2e8f0' }}>
              <th style={th}>Name</th>
              <th style={th}>Kostenstelle</th>
              <th style={th}>Uebergeordnet</th>
            </tr>
          </thead>
          <tbody>
            {departments.map((d) => {
              const parent = departments.find((p) => p.id === d.parent_id);
              return (
                <tr key={d.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                  <td style={{ ...td, fontWeight: 500 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <Building2 size={16} style={{ color: '#94a3b8' }} />
                      {d.name}
                    </div>
                  </td>
                  <td style={td}>
                    <span style={{ fontFamily: 'monospace', color: '#64748b' }}>
                      {d.cost_center || '--'}
                    </span>
                  </td>
                  <td style={td}>{parent ? parent.name : '--'}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {departments.length === 0 && (
          <div style={{ textAlign: 'center', padding: 24, color: '#94a3b8', fontSize: 14 }}>
            Keine Abteilungen vorhanden
          </div>
        )}
      </Card>
    </div>
  );
}

const th = { textAlign: 'left' as const, padding: '8px 12px', color: '#64748b', fontWeight: 500 as const };
const td = { padding: '10px 12px' };
