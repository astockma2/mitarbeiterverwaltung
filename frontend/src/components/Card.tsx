import type { ReactNode, CSSProperties } from 'react';

interface CardProps {
  title?: string;
  children: ReactNode;
  style?: CSSProperties;
  action?: ReactNode;
}

export default function Card({ title, children, style, action }: CardProps) {
  return (
    <div style={{
      background: '#fff', borderRadius: 8, boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
      padding: 20, ...style,
    }}>
      {(title || action) && (
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          marginBottom: 16,
        }}>
          {title && <h2 style={{ fontSize: 16, fontWeight: 600, margin: 0, color: '#1e293b' }}>{title}</h2>}
          {action}
        </div>
      )}
      {children}
    </div>
  );
}

interface StatCardProps {
  label: string;
  value: string | number;
  color?: string;
  icon?: ReactNode;
}

export function StatCard({ label, value, color = '#3b82f6', icon }: StatCardProps) {
  return (
    <div style={{
      background: '#fff', borderRadius: 8, boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
      padding: 20, display: 'flex', alignItems: 'center', gap: 16,
    }}>
      {icon && (
        <div style={{
          width: 48, height: 48, borderRadius: 10, background: color + '15',
          display: 'flex', alignItems: 'center', justifyContent: 'center', color,
        }}>
          {icon}
        </div>
      )}
      <div>
        <div style={{ fontSize: 24, fontWeight: 700, color: '#1e293b' }}>{value}</div>
        <div style={{ fontSize: 13, color: '#64748b' }}>{label}</div>
      </div>
    </div>
  );
}

export function Badge({ text, color = '#3b82f6' }: { text: string; color?: string }) {
  return (
    <span style={{
      display: 'inline-block', padding: '2px 8px', borderRadius: 9999,
      fontSize: 11, fontWeight: 600, background: color + '20', color,
    }}>
      {text}
    </span>
  );
}
