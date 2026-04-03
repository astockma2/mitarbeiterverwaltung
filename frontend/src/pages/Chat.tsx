import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import { Send, Plus, MessageCircle, Circle, Search, ChevronDown, ChevronRight, Bot } from 'lucide-react';
import { getConversations, getMessages, sendMessage, getChatEmployees, createConversation, getSupportBotId } from '../services/api';

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
  const [empSearch, setEmpSearch] = useState('');
  const [collapsedDepts, setCollapsedDepts] = useState<Set<string>>(new Set());
  const [botEmployeeId, setBotEmployeeId] = useState<number | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const activeConvRef = useRef<any>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // activeConvRef synchron halten
  useEffect(() => {
    activeConvRef.current = activeConv;
  }, [activeConv]);

  // Bot-ID einmalig laden und Bot-Konversation sicherstellen
  useEffect(() => {
    getSupportBotId()
      .then((r) => setBotEmployeeId(r.data.id))
      .catch(() => {});
  }, []);

  // Konversationen laden, Bot-Konversation immer an Position 1
  const loadConversations = useCallback(async () => {
    const r = await getConversations();
    const convs: any[] = r.data;

    if (botEmployeeId) {
      const hasBot = convs.some((c) =>
        c.type === 'DIRECT' &&
        c.members?.some((m: any) => m.id === botEmployeeId)
      );
      if (!hasBot) {
        try {
          await createConversation({ type: 'DIRECT', member_ids: [botEmployeeId] });
          const r2 = await getConversations();
          convs.splice(0, convs.length, ...r2.data);
        } catch {}
      }
    }

    // Bot-Konversation an Position 1 sortieren
    convs.sort((a, b) => {
      const aIsBot = botEmployeeId != null && a.members?.some((m: any) => m.id === botEmployeeId);
      const bIsBot = botEmployeeId != null && b.members?.some((m: any) => m.id === botEmployeeId);
      if (aIsBot && !bIsBot) return -1;
      if (!aIsBot && bIsBot) return 1;
      const aTime = a.last_message?.created_at ?? '';
      const bTime = b.last_message?.created_at ?? '';
      return bTime.localeCompare(aTime);
    });

    setConversations(convs);
  }, [botEmployeeId]);

  // Ref auf loadConversations, damit WS/Polling immer die aktuelle Version nutzen,
  // ohne dass sich die Effekte bei jeder botEmployeeId-Änderung neu registrieren.
  const loadConversationsRef = useRef(loadConversations);
  useEffect(() => { loadConversationsRef.current = loadConversations; }, [loadConversations]);

  // Konversationen beim Mount und bei botEmployeeId-Änderung laden
  useEffect(() => {
    loadConversations().catch(() => {});
  }, [loadConversations]);

  // WebSocket einmalig beim Mount aufbauen (keine Abhängigkeit von loadConversations,
  // da sonst bei botEmployeeId-Laden eine Race Condition entsteht: WS schließen + neu öffnen)
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    const connect = () => {
      const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsHost = isLocal ? '127.0.0.1:8000' : window.location.host;
      const wsUrl = `${wsProtocol}//${wsHost}/api/v1/chat/ws`;
      const socket = new WebSocket(wsUrl);

      // Token als erste Nachricht nach dem Handshake senden (nicht in der URL)
      socket.onopen = () => {
        socket.send(JSON.stringify({ action: 'auth', token }));
        console.log('WS verbunden');
      };

      socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'new_message') {
          const currentConv = activeConvRef.current;
          if (currentConv && currentConv.id === data.conversation_id) {
            setMessages((prev) => {
              if (prev.some((m) => m.id === data.id)) return prev;
              return [...prev, data];
            });
          }
          loadConversationsRef.current?.().catch(() => {});
        }
      };

      socket.onclose = (e) => {
        console.log('WS getrennt', e.code);
        // Reconnect nach 3 Sekunden
        if (e.code !== 4001) {
          setTimeout(connect, 3000);
        }
      };
      socket.onerror = () => socket.close();

      wsRef.current = socket;
    };

    connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.onclose = null; // Kein Reconnect beim Unmount
        wsRef.current.close();
      }
    };
  }, []); // Leeres Array: WS wird nur einmal beim Mount aufgebaut

  // Polling als Fallback fuer Nachrichten-Aktualisierung
  useEffect(() => {
    // Konversationsliste alle 10s aktualisieren
    pollRef.current = setInterval(() => {
      loadConversationsRef.current?.().catch(() => {});
      // Aktive Konversation Nachrichten neu laden
      const conv = activeConvRef.current;
      if (conv) {
        getMessages(conv.id).then((r) => setMessages(r.data)).catch(() => {});
      }
    }, 10000);

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []); // Leeres Array: Polling-Interval einmalig starten

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
      const ws = wsRef.current;
      if (ws?.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ action: 'read', conversation_id: conv.id }));
      }
      loadConversations().catch(() => {});
    } catch {
      setMessages([]);
    }
  };

  // Nachricht senden
  const handleSend = async () => {
    if (!input.trim() || !activeConv) return;
    const text = input.trim();
    setInput('');

    const ws = wsRef.current;
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
        loadConversations().catch(() => {});
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
      await loadConversations();
      setConversations((prev) => {
        const conv = prev.find((c: any) => c.id === r.data.id);
        if (conv) openConversation(conv);
        return prev;
      });
    } catch {}
  };

  // Mitarbeiter laden wenn "Neuer Chat" geoeffnet
  useEffect(() => {
    if (showNewChat) {
      getChatEmployees().then((r) => setEmployees(r.data));
      setEmpSearch('');
      setCollapsedDepts(new Set());
    }
  }, [showNewChat]);

  // Mitarbeiter filtern und nach Abteilung gruppieren
  const groupedEmployees = useMemo(() => {
    let filtered = employees;
    if (empSearch) {
      const q = empSearch.toLowerCase();
      filtered = employees.filter((e) => e.name.toLowerCase().includes(q));
    }
    const groups = new Map<string, any[]>();
    for (const e of filtered) {
      const dept = e.department_name || 'Ohne Abteilung';
      if (!groups.has(dept)) groups.set(dept, []);
      groups.get(dept)!.push(e);
    }
    return Array.from(groups.entries()).sort((a, b) => a[0].localeCompare(b[0]));
  }, [employees, empSearch]);

  const toggleDept = (name: string) => {
    setCollapsedDepts((prev) => {
      const next = new Set(prev);
      next.has(name) ? next.delete(name) : next.add(name);
      return next;
    });
  };

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
            <div>
              {/* Suchfeld */}
              <div style={{ padding: '8px 12px' }}>
                <div style={{ position: 'relative' }}>
                  <Search size={14} style={{ position: 'absolute', left: 8, top: 8, color: '#94a3b8' }} />
                  <input
                    placeholder="Mitarbeiter suchen..."
                    value={empSearch}
                    onChange={(e) => setEmpSearch(e.target.value)}
                    autoFocus
                    style={{
                      width: '100%', padding: '6px 6px 6px 28px', borderRadius: 6,
                      border: '1px solid #d1d5db', fontSize: 13, boxSizing: 'border-box',
                    }}
                  />
                </div>
              </div>

              {/* Mitarbeiter nach Abteilungen */}
              {groupedEmployees.map(([deptName, emps]) => {
                const collapsed = collapsedDepts.has(deptName);
                return (
                  <div key={deptName}>
                    <div
                      onClick={() => toggleDept(deptName)}
                      style={{
                        padding: '6px 12px', fontSize: 12, color: '#475569', fontWeight: 600,
                        cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4,
                        background: '#f8fafc', borderBottom: '1px solid #e2e8f0',
                      }}
                    >
                      {collapsed ? <ChevronRight size={12} /> : <ChevronDown size={12} />}
                      {deptName} ({emps.length})
                    </div>
                    {!collapsed && emps.map((e: any) => (
                      <div key={e.id} onClick={() => startNewChat(e.id)} style={{
                        padding: '8px 16px', cursor: 'pointer', display: 'flex',
                        alignItems: 'center', gap: 10, borderBottom: '1px solid #f1f5f9',
                        transition: 'background 0.15s',
                      }}
                      onMouseEnter={(ev) => ev.currentTarget.style.background = '#f8fafc'}
                      onMouseLeave={(ev) => ev.currentTarget.style.background = ''}>
                        <div style={{
                          width: 32, height: 32, borderRadius: '50%',
                          background: '#e0e7ff', display: 'flex', alignItems: 'center',
                          justifyContent: 'center', fontSize: 12, fontWeight: 600, color: '#3730a3',
                          flexShrink: 0,
                        }}>
                          {e.name.split(' ').map((n: string) => n[0]).join('')}
                        </div>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontSize: 13, fontWeight: 500 }}>{e.name}</div>
                        </div>
                        {e.online && (
                          <Circle size={8} fill="#22c55e" color="#22c55e" />
                        )}
                      </div>
                    ))}
                  </div>
                );
              })}
              {groupedEmployees.length === 0 && empSearch && (
                <div style={{ padding: 16, textAlign: 'center', color: '#94a3b8', fontSize: 13 }}>
                  Kein Mitarbeiter gefunden.
                </div>
              )}
            </div>
          ) : (
            // Konversationsliste
            <>
              {conversations.map((c) => {
                const isBot = botEmployeeId != null && c.members?.some((m: any) => m.id === botEmployeeId);
                return (
                <div key={c.id}
                  onClick={() => openConversation(c)}
                  style={{
                    padding: '12px 16px', cursor: 'pointer',
                    borderBottom: '1px solid #f1f5f9',
                    background: activeConv?.id === c.id ? '#eff6ff' : isBot ? '#f0fdf4' : 'transparent',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: 14, fontWeight: c.unread_count > 0 ? 700 : 500, display: 'flex', alignItems: 'center', gap: 5 }}>
                      {isBot && <Bot size={13} color="#16a34a" />}
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
                );
              })}
              {conversations.length === 0 && (
                <div style={{ padding: 32, textAlign: 'center', color: '#94a3b8', fontSize: 13 }}>
                  Keine Konversationen.{'\n'}Starte einen neuen Chat!
                </div>
              )}
            </>
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
