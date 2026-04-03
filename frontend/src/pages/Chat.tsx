import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import { Send, Plus, MessageCircle, Circle, Search, ChevronDown, ChevronRight, Bot, Users, UserPlus, UserMinus, Pencil, X, Check, Paperclip, Download, Image } from 'lucide-react';
import { getConversations, getMessages, sendMessage, getChatEmployees, createConversation, getSupportBotId, updateConversation, updateMembers, uploadChatFile, getChatFileUrl } from '../services/api';

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
  const [newChatMode, setNewChatMode] = useState<'direct' | 'group'>('direct');
  const [groupName, setGroupName] = useState('');
  const [selectedMembers, setSelectedMembers] = useState<number[]>([]);
  const [empSearch, setEmpSearch] = useState('');
  const [collapsedDepts, setCollapsedDepts] = useState<Set<string>>(new Set());
  const [botEmployeeId, setBotEmployeeId] = useState<number | null>(null);
  const [showMemberPanel, setShowMemberPanel] = useState(false);
  const [editingName, setEditingName] = useState(false);
  const [newName, setNewName] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);
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

  // Browser-Notification-Berechtigung anfragen
  useEffect(() => {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }
  }, []);

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
          // Browser-Notification wenn Tab nicht aktiv und Nachricht nicht von mir
          if (document.hidden && data.sender_id !== userId && 'Notification' in window && Notification.permission === 'granted') {
            new Notification(`${data.sender_name}`, {
              body: data.message_type === 'IMAGE' ? '📷 Bild' : data.message_type === 'FILE' ? '📎 Datei' : data.content,
              icon: '/favicon.ico',
              tag: `chat-${data.conversation_id}`,
            });
          }
          loadConversationsRef.current?.().catch(() => {});
        } else if (data.type === 'conversation_updated') {
          const currentConv = activeConvRef.current;
          if (currentConv && currentConv.id === data.conversation_id) {
            setActiveConv((prev: any) => prev ? { ...prev, name: data.name } : prev);
          }
          loadConversationsRef.current?.().catch(() => {});
        } else if (data.type === 'members_updated') {
          const currentConv = activeConvRef.current;
          if (currentConv && currentConv.id === data.conversation_id) {
            setActiveConv((prev: any) => prev ? { ...prev, members: data.members } : prev);
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

  // Gruppe erstellen
  const createGroup = async () => {
    if (!groupName.trim() || selectedMembers.length === 0) return;
    try {
      const r = await createConversation({
        type: 'GROUP',
        name: groupName.trim(),
        member_ids: selectedMembers,
      });
      setShowNewChat(false);
      setGroupName('');
      setSelectedMembers([]);
      setNewChatMode('direct');
      await loadConversations();
      setConversations((prev) => {
        const conv = prev.find((c: any) => c.id === r.data.id);
        if (conv) openConversation(conv);
        return prev;
      });
    } catch {}
  };

  // Mitglied-Toggle fuer Gruppenerstellung
  const toggleMember = (id: number) => {
    setSelectedMembers((prev) =>
      prev.includes(id) ? prev.filter((m) => m !== id) : [...prev, id]
    );
  };

  // Gruppe umbenennen
  const renameGroup = async () => {
    if (!activeConv || !newName.trim()) return;
    try {
      await updateConversation(activeConv.id, { name: newName.trim() });
      setActiveConv({ ...activeConv, name: newName.trim() });
      setEditingName(false);
      loadConversations().catch(() => {});
    } catch {}
  };

  // Mitglied zur aktiven Gruppe hinzufuegen
  const addMemberToGroup = async (empId: number) => {
    if (!activeConv) return;
    try {
      const r = await updateMembers(activeConv.id, { add: [empId] });
      setActiveConv({ ...activeConv, members: r.data.members });
      loadConversations().catch(() => {});
    } catch {}
  };

  // Mitglied aus aktiver Gruppe entfernen
  const removeMemberFromGroup = async (empId: number) => {
    if (!activeConv) return;
    try {
      const r = await updateMembers(activeConv.id, { remove: [empId] });
      setActiveConv({ ...activeConv, members: r.data.members });
      loadConversations().catch(() => {});
    } catch {}
  };

  // Datei hochladen
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !activeConv) return;
    e.target.value = '';

    if (file.size > 20 * 1024 * 1024) {
      alert('Datei zu gross (max 20 MB)');
      return;
    }

    setUploading(true);
    setUploadProgress(0);
    try {
      await uploadChatFile(activeConv.id, file, (pct) => setUploadProgress(pct));
      loadConversations().catch(() => {});
    } catch {
      alert('Fehler beim Hochladen');
    }
    setUploading(false);
  };

  // Mitarbeiter laden wenn "Neuer Chat" geoeffnet
  useEffect(() => {
    if (showNewChat || showMemberPanel) {
      getChatEmployees().then((r) => setEmployees(r.data));
      setEmpSearch('');
      setCollapsedDepts(new Set());
    }
    if (!showNewChat) {
      setNewChatMode('direct');
      setGroupName('');
      setSelectedMembers([]);
    }
  }, [showNewChat, showMemberPanel]);

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
              {/* Tabs: Direkt / Gruppe */}
              <div style={{ display: 'flex', borderBottom: '1px solid #e2e8f0' }}>
                <button onClick={() => setNewChatMode('direct')} style={{
                  flex: 1, padding: '8px', fontSize: 13, fontWeight: 500, border: 'none',
                  cursor: 'pointer', background: newChatMode === 'direct' ? '#fff' : '#f8fafc',
                  borderBottom: newChatMode === 'direct' ? '2px solid #3b82f6' : '2px solid transparent',
                  color: newChatMode === 'direct' ? '#3b82f6' : '#64748b',
                }}>Direktnachricht</button>
                <button onClick={() => setNewChatMode('group')} style={{
                  flex: 1, padding: '8px', fontSize: 13, fontWeight: 500, border: 'none',
                  cursor: 'pointer', background: newChatMode === 'group' ? '#fff' : '#f8fafc',
                  borderBottom: newChatMode === 'group' ? '2px solid #3b82f6' : '2px solid transparent',
                  color: newChatMode === 'group' ? '#3b82f6' : '#64748b',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4,
                }}>
                  <Users size={13} /> Gruppe
                </button>
              </div>

              {/* Gruppenname + Erstellen-Button */}
              {newChatMode === 'group' && (
                <div style={{ padding: '8px 12px', borderBottom: '1px solid #e2e8f0' }}>
                  <input
                    placeholder="Gruppenname..."
                    value={groupName}
                    onChange={(e) => setGroupName(e.target.value)}
                    style={{
                      width: '100%', padding: '6px 10px', borderRadius: 6,
                      border: '1px solid #d1d5db', fontSize: 13, boxSizing: 'border-box',
                      marginBottom: 6,
                    }}
                  />
                  {selectedMembers.length > 0 && (
                    <div style={{ fontSize: 12, color: '#64748b', marginBottom: 6 }}>
                      {selectedMembers.length} Mitglied{selectedMembers.length !== 1 ? 'er' : ''} ausgewaehlt
                    </div>
                  )}
                  <button onClick={createGroup} disabled={!groupName.trim() || selectedMembers.length === 0}
                    style={{
                      width: '100%', padding: '6px', borderRadius: 6, border: 'none',
                      background: groupName.trim() && selectedMembers.length > 0 ? '#3b82f6' : '#e2e8f0',
                      color: '#fff', fontSize: 13, fontWeight: 500, cursor: 'pointer',
                    }}>
                    Gruppe erstellen
                  </button>
                </div>
              )}

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
                      <div key={e.id}
                        onClick={() => newChatMode === 'direct' ? startNewChat(e.id) : toggleMember(e.id)}
                        style={{
                          padding: '8px 16px', cursor: 'pointer', display: 'flex',
                          alignItems: 'center', gap: 10, borderBottom: '1px solid #f1f5f9',
                          transition: 'background 0.15s',
                          background: selectedMembers.includes(e.id) ? '#eff6ff' : '',
                        }}
                        onMouseEnter={(ev) => { if (!selectedMembers.includes(e.id)) ev.currentTarget.style.background = '#f8fafc'; }}
                        onMouseLeave={(ev) => { if (!selectedMembers.includes(e.id)) ev.currentTarget.style.background = ''; }}>
                        {newChatMode === 'group' && (
                          <input type="checkbox" checked={selectedMembers.includes(e.id)}
                            onChange={() => toggleMember(e.id)}
                            style={{ accentColor: '#3b82f6' }} />
                        )}
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
                const isGroup = c.type === 'GROUP';
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
                      {isGroup && !isBot && <Users size={13} color="#6366f1" />}
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
              background: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                {editingName ? (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <input value={newName} onChange={(e) => setNewName(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && renameGroup()}
                      autoFocus
                      style={{ fontSize: 15, fontWeight: 600, border: '1px solid #d1d5db', borderRadius: 4, padding: '2px 6px' }} />
                    <button onClick={renameGroup} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 2 }}>
                      <Check size={16} color="#22c55e" />
                    </button>
                    <button onClick={() => setEditingName(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 2 }}>
                      <X size={16} color="#ef4444" />
                    </button>
                  </div>
                ) : (
                  <>
                    <span style={{ fontWeight: 600, fontSize: 15 }}>{activeConv.name}</span>
                    {activeConv.type !== 'DIRECT' && (
                      <button onClick={() => { setNewName(activeConv.name); setEditingName(true); }}
                        style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 2 }}>
                        <Pencil size={13} color="#94a3b8" />
                      </button>
                    )}
                  </>
                )}
                <span style={{ fontSize: 12, color: '#94a3b8', fontWeight: 400 }}>
                  {activeConv.members?.length} Teilnehmer
                </span>
              </div>
              {activeConv.type !== 'DIRECT' && (
                <button onClick={() => setShowMemberPanel(!showMemberPanel)}
                  style={{
                    background: showMemberPanel ? '#eff6ff' : 'none', border: '1px solid #e2e8f0',
                    borderRadius: 6, padding: '4px 8px', cursor: 'pointer',
                    display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, color: '#64748b',
                  }}>
                  <Users size={14} /> Mitglieder
                </button>
              )}
            </div>

            {/* Mitglieder-Panel (nur fuer Gruppen) */}
            {showMemberPanel && activeConv.type !== 'DIRECT' && (
              <div style={{
                borderBottom: '1px solid #e2e8f0', background: '#fafbfc',
                padding: '10px 16px', maxHeight: 250, overflowY: 'auto',
              }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#475569', marginBottom: 6 }}>
                  Mitglieder ({activeConv.members?.length})
                </div>
                {activeConv.members?.map((m: any) => (
                  <div key={m.id} style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '4px 0', fontSize: 13,
                  }}>
                    <span>{m.name}</span>
                    {m.id !== userId && m.id !== activeConv.created_by && (
                      <button onClick={() => removeMemberFromGroup(m.id)}
                        style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 2 }}
                        title="Entfernen">
                        <UserMinus size={14} color="#ef4444" />
                      </button>
                    )}
                  </div>
                ))}
                <div style={{ marginTop: 8, borderTop: '1px solid #e2e8f0', paddingTop: 8 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: '#475569', marginBottom: 4 }}>
                    Hinzufuegen
                  </div>
                  <div style={{ position: 'relative', marginBottom: 6 }}>
                    <Search size={12} style={{ position: 'absolute', left: 6, top: 7, color: '#94a3b8' }} />
                    <input placeholder="Suchen..." value={empSearch} onChange={(e) => setEmpSearch(e.target.value)}
                      style={{
                        width: '100%', padding: '4px 4px 4px 24px', borderRadius: 4,
                        border: '1px solid #d1d5db', fontSize: 12, boxSizing: 'border-box',
                      }} />
                  </div>
                  {employees
                    .filter((e) => !activeConv.members?.some((m: any) => m.id === e.id))
                    .filter((e) => !empSearch || e.name.toLowerCase().includes(empSearch.toLowerCase()))
                    .slice(0, 5)
                    .map((e: any) => (
                      <div key={e.id} onClick={() => addMemberToGroup(e.id)}
                        style={{
                          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                          padding: '4px 0', fontSize: 13, cursor: 'pointer',
                        }}
                        onMouseEnter={(ev) => ev.currentTarget.style.background = '#f1f5f9'}
                        onMouseLeave={(ev) => ev.currentTarget.style.background = ''}>
                        <span>{e.name}</span>
                        <UserPlus size={14} color="#3b82f6" />
                      </div>
                    ))}
                </div>
              </div>
            )}

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
                      {m.message_type === 'IMAGE' && m.file_path ? (
                        <div>
                          <img
                            src={getChatFileUrl(m.file_path)}
                            alt={m.content}
                            style={{ maxWidth: '100%', borderRadius: 8, cursor: 'pointer', marginBottom: 4 }}
                            onClick={() => window.open(getChatFileUrl(m.file_path), '_blank')}
                          />
                          <div style={{ fontSize: 12, opacity: 0.8 }}>{m.content}</div>
                        </div>
                      ) : m.message_type === 'FILE' && m.file_path ? (
                        <a href={getChatFileUrl(m.file_path)} target="_blank" rel="noopener noreferrer"
                          style={{
                            display: 'flex', alignItems: 'center', gap: 6, textDecoration: 'none',
                            color: isMine ? '#fff' : '#3b82f6',
                          }}>
                          <Download size={16} />
                          <span style={{ textDecoration: 'underline' }}>{m.content}</span>
                        </a>
                      ) : (
                        <div>{m.content}</div>
                      )}
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

            {/* Upload-Fortschritt */}
            {uploading && (
              <div style={{ padding: '4px 20px', background: '#f0f9ff', borderTop: '1px solid #e2e8f0' }}>
                <div style={{ fontSize: 12, color: '#3b82f6', marginBottom: 2 }}>Hochladen... {uploadProgress}%</div>
                <div style={{ height: 3, background: '#e2e8f0', borderRadius: 2 }}>
                  <div style={{ height: '100%', width: `${uploadProgress}%`, background: '#3b82f6', borderRadius: 2, transition: 'width 0.2s' }} />
                </div>
              </div>
            )}

            {/* Eingabe */}
            <div style={{
              padding: '12px 20px', borderTop: '1px solid #e2e8f0', background: '#fff',
              display: 'flex', gap: 8, alignItems: 'center',
            }}>
              <input type="file" ref={fileInputRef} onChange={handleFileUpload}
                style={{ display: 'none' }} />
              <button onClick={() => fileInputRef.current?.click()} disabled={uploading}
                style={{
                  width: 36, height: 36, borderRadius: '50%', border: 'none',
                  background: '#f1f5f9', cursor: 'pointer',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}
                title="Datei senden">
                <Paperclip size={16} color="#64748b" />
              </button>
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
