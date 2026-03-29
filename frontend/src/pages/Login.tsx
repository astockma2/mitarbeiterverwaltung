import { useState } from 'react';
import { login } from '../services/api';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await login(username, password);
      localStorage.setItem('access_token', res.data.access_token);
      localStorage.setItem('refresh_token', res.data.refresh_token);
      window.location.href = '/';
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Anmeldung fehlgeschlagen');
    } finally {
      setLoading(false);
    }
  };

  const inputStyle = {
    width: '100%', padding: '10px 12px', borderRadius: 6,
    border: '1px solid #d1d5db', fontSize: 14, boxSizing: 'border-box' as const,
    outline: 'none',
  };

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'linear-gradient(135deg, #1e293b 0%, #334155 100%)',
    }}>
      <div style={{
        background: '#fff', borderRadius: 12, padding: 40, width: 380,
        boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
      }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <img src="/logo-ikk.png" alt="Ilm-Kreis-Kliniken" style={{
            width: 80, height: 80, objectFit: 'contain', marginBottom: 12,
          }} />
          <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1e293b', margin: 0 }}>
            Mitarbeiterverwaltung
          </h1>
          <p style={{ color: '#64748b', fontSize: 14, margin: '8px 0 0' }}>
            Ilm-Kreis-Kliniken
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 4, color: '#374151' }}>
              Benutzername
            </label>
            <input
              style={inputStyle}
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="z.B. admin"
              autoFocus
            />
          </div>

          <div style={{ marginBottom: 20 }}>
            <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 4, color: '#374151' }}>
              Passwort
            </label>
            <input
              type="password"
              style={inputStyle}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Passwort eingeben"
            />
          </div>

          {error && (
            <div style={{
              padding: '10px 12px', borderRadius: 6, background: '#fef2f2',
              color: '#dc2626', fontSize: 13, marginBottom: 16,
            }}>
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            style={{
              width: '100%', padding: '10px 0', borderRadius: 6,
              background: loading ? '#94a3b8' : '#3b82f6', color: '#fff',
              fontSize: 14, fontWeight: 600, border: 'none', cursor: loading ? 'default' : 'pointer',
            }}
          >
            {loading ? 'Anmeldung...' : 'Anmelden'}
          </button>
        </form>

        <div style={{
          marginTop: 24, padding: '12px', background: '#f8fafc', borderRadius: 6,
          fontSize: 12, color: '#64748b',
        }}>
          <strong>Dev-Modus:</strong> Passwort ist "dev"<br />
          Benutzer: admin, hr.leitung, m.mueller, s.schmidt, t.weber
        </div>

        <div style={{ textAlign: 'center', marginTop: 20, fontSize: 11, color: '#94a3b8', letterSpacing: 0.5 }}>
          Powered by <strong>IKK IT</strong>
        </div>
      </div>
    </div>
  );
}
