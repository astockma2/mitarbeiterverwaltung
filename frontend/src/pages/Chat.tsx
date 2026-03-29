import { useEffect, useRef, useState } from 'react';
import { Send, Plus, MessageCircle, Circle } from 'lucide-react';
import { getConversations, getMessages, sendMessage, getChatEmployees, createConversation } from '../services/api';

interface Props {
  userId: number;
}

export default function Chat({ userId }: Props) {
  const [conversations, setConversations] = useState<any[]>([]);
  const [activeConv, setActiveConv] = useState<any>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [input, setInput] = useState('');
  const [employees, setEmployees] = useState<any[]>([]);
  const [showNewChat, setShowNewChat] = useState(false);
  const [ws, setWs] = useState<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [onlineUsers, setOnlineUsers] = useState<number[]>([]);

  // Konversationen laden
  const loadConversations = () => {
    getConversations().then((r) => setConversations(r.data));
  };

  useEffect(() => {
    loadConversations();

    // WebSocket verbinden
    const token = localStorage.getItem('access_token');
    if (token) {
      const wsUrl = `ws://127.0.0.1:8000/api/v1/chat/ws/${token}`;
      const socket = new WebSocket(wsUrl);

      socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'new_message') {
          setMessages((prev) => {
            if (prev.length > 0 && prev[0]?.conversation_id === data.conversation_id) {
              // Duplikat vermeiden
              if (prev.some((m) => m.id === data.id)) return prev;
              return [...prev, data];
            }
            return prev;
          });
          loadConversations();
        } else if (data.type === 'online_status') {
          setOnlineUsers(data.online_users || []);
        }
      };

      socket.onopen = () => console.log('WS verbunden');
      socket.onclose = () => console.log('WS getrennt');

      setWs(socket);
      return () => socket.close();
    }
  }, []);

  // Nachrichten scrollen
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Konversation oeffnen
  const openConversation = async (conv: any) => {
    setActiveConv(conv);
    setShowNewChat(false);
    try {
      const r = await getMessages(conv.id);
      setMessages(r.data);
      // Als gelesen markieren
      if (ws?.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ action: 'read', conversation_id: conv.id }));
      }
      loadConversations();
    } catch {
      setMessages([]);
    }
  };

  // Nachricht senden
  const handleSend = async () => {
    if (!input.trim() || !activeConv) return;
    const text = input.trim();
    setInput('');

    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        action: 'message',
        conversation_id: activeConv.id,
        content: text,
      }));
    } else {
      try {
        const r = await sendMessage(activeConv.id, text);
        setMessages((prev) => [...prev, r.data]);
        loadConversations();
      } catch {}
    }
  };

  // Neuen Chat starten
  const startNewChat = async (employeeId: number) => {
    try {
      const r = await createConversation({
        type: 'DIRECT',
        member_ids: [employeeId],
      });
      setShowNewChat(false);
      loadConversations();
      // Konversation oeffnen
      const convR = await getConversations();
      setConversations(convR.data);
      const conv = convR.data.find((c: any) => c.id === r.data.id);
      if (conv) openConversation(conv);
    } catch {}
  };

  // Mitarbeiter laden wenn "Neuer Chat" geoeffnet
  useEffect(() => {
    if (showNewChat) {
      getChatEmployees().then((r) => setEmployees(r.data));
    }
  }, [showNewChat]);

  return (
    <div style={{ display: 'flex', height: 'calc(100vh - 80px)' }}>
      {/* Sidebar: Konversationen */}
      <div style={{
        width: 300, borderRight: '1px solid #e2e8f0', display: 'flex',
        flexDirection: 'column', background: '#fff',
      }}>
        <div style={{
          padding: '16px', borderBottom: '1px solid #e2e8f0',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <h2 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>Nachrichten</h2>
          <button onClick={() => setShowNewChat(!showNewChat)} style={{
            background: '#3b82f6', color: '#fff', border: 'none',
            borderRadius: 6, width: 32, height: 32, cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <Plus size={16} />
          </button>
        </div>

        <div style={{ flex: 1, overflow: 'auto' }}>
          {showNewChat ? (
            // Mitarbeiterliste
            <div>
              <div style={{ padding: '8px 16px', fontSize: 12, color: '#64748b', fontWeight: 600 }}>
                Neuen Chat starten
              </div>
              {employees.map((e) => (
                <div key={e.id} onClick={() => startNewChat(e.id)} style={{
                  padding: '10px 16px', cursor: 'pointer', display: 'flex',
                  alignItems: 'center', gap: 10, borderBottom: '1px solid #f1f5f9',
                }}>
                  <div style={{
                    width: 36, height: 36, borderRadius: '50%',
                    background: '#e0e7ff', display: 'flex', alignItems: 'center',
                    justifyContent: 'center', fontSize: 13, fontWeight: 600, color: '#3730a3',
                  }}>
                    {e.name.split(' ').map((n: string) => n[0]).join('')}
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 14, fontWeight: 500 }}>{e.name}</div>
                    <div style={{ fontSize: 11, color: '#94a3b8' }}>{e.role}</div>
                  </div>
                  {e.online && (
                    <Circle size={8} fill="#22c55e" color="#22c55e" />
                  )}
                </div>
              ))}
            </div>
          ) : (
            // Konversationsliste
            conversations.map((c) => (
              <div key={c.id}
                onClick={() => openConversation(c)}
                style={{
                  padding: '12px 16px', cursor: 'pointer',
                  borderBottom: '1px solid #f1f5f9',
                  background: activeConv?.id === c.id ? '#eff6ff' : 'transparent',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 14, fontWeight: c.unread_count > 0 ? 700 : 500 }}>
                    {c.name}
                  </span>
                  {c.unread_count > 0 && (
                    <span style={{
                      background: '#3b82f6', color: '#fff', borderRadius: 10,
                      padding: '1px 7px', fontSize: 11, fontWeight: 600,
                    }}>{c.unread_count}</span>
                  )}
                </div>
                {c.last_message && (
                  <div style={{
                    fontSize: 12, color: '#94a3b8', marginTop: 2,
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                  }}>
                    {c.last_message.sender_id === userId ? 'Du: ' : ''}
                    {c.last_message.content}
                  </div>
                )}
              </div>
            ))
          )}
          {!showNewChat && conversations.length === 0 && (
            <div style={{ padding: 32, textAlign: 'center', color: '#94a3b8', fontSize: 13 }}>
              Keine Konversationen.{'\n'}Starte einen neuen Chat!
            </div>
          )}
        </div>
      </div>

      {/* Chat-Bereich */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', background: '#f8fafc' }}>
        {activeConv ? (
          <>
            {/* Header */}
            <div style={{
              padding: '12px 20px', borderBottom: '1px solid #e2e8f0',
              background: '#fff', fontWeight: 600, fontSize: 15,
            }}>
              {activeConv.name}
              <span style={{ fontSize: 12, color: '#94a3b8', marginLeft: 8, fontWeight: 400 }}>
                {activeConv.members?.length} Teilnehmer
              </span>
            </div>

            {/* Nachrichten */}
            <div style={{ flex: 1, overflow: 'auto', padding: 20 }}>
              {messages.map((m) => {
                const isMine = m.sender_id === userId;
                return (
                  <div key={m.id} style={{
                    display: 'flex', justifyContent: isMine ? 'flex-end' : 'flex-start',
                    marginBottom: 8,
                  }}>
                    <div style={{
                      maxWidth: '65%', padding: '10px 14px', borderRadius: 12,
                      background: m.message_type === 'SYSTEM' ? '#f1f5f9'
                        : isMine ? '#3b82f6' : '#fff',
                      color: m.message_type === 'SYSTEM' ? '#94a3b8'
                        : isMine ? '#fff' : '#1e293b',
                      fontSize: m.message_type === 'SYSTEM' ? 12 : 14,
                      textAlign: m.message_type === 'SYSTEM' ? 'center' : 'left',
                      boxShadow: m.message_type !== 'SYSTEM' ? '0 1px 2px rgba(0,0,0,0.05)' : 'none',
                    }}>
                      {!isMine && m.message_type !== 'SYSTEM' && (
                        <div style={{
                          fontSize: 11, fontWeight: 600, marginBottom: 2,
                          color: isMine ? '#dbeafe' : '#3b82f6',
                        }}>{m.sender_name}</div>
                      )}
                      <div>{m.content}</div>
                      <div style={{
                        fontSize: 10, marginTop: 4, textAlign: 'right',
                        color: isMine ? '#bfdbfe' : '#94a3b8',
                      }}>
                        {new Date(m.created_at).toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })}
                      </div>
                    </div>
                  </div>
                );
              })}
              <div ref={messagesEndRef} />
            </div>

            {/* Eingabe */}
            <div style={{
              padding: '12px 20px', borderTop: '1px solid #e2e8f0', background: '#fff',
              display: 'flex', gap: 8,
            }}>
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                placeholder="Nachricht schreiben..."
                style={{
                  flex: 1, padding: '10px 14px', borderRadius: 20,
                  border: '1px solid #d1d5db', fontSize: 14, outline: 'none',
                }}
              />
              <button onClick={handleSend} disabled={!input.trim()} style={{
                width: 40, height: 40, borderRadius: '50%', border: 'none',
                background: input.trim() ? '#3b82f6' : '#e2e8f0',
                color: '#fff', cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <Send size={16} />
              </button>
            </div>
          </>
        ) : (
          <div style={{
            flex: 1, display: 'flex', flexDirection: 'column',
            alignItems: 'center', justifyContent: 'center', color: '#94a3b8',
          }}>
            <MessageCircle size={48} />
            <div style={{ marginTop: 12, fontSize: 15 }}>
              Waehle eine Konversation oder starte einen neuen Chat
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
