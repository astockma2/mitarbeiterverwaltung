import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;
import '../services/api_service.dart';
import '../services/auth_provider.dart';
import '../models/chat.dart';
import 'package:intl/intl.dart';

class ChatListScreen extends StatefulWidget {
  const ChatListScreen({super.key});

  @override
  State<ChatListScreen> createState() => _ChatListScreenState();
}

class _ChatListScreenState extends State<ChatListScreen> {
  List<ChatConversation> _conversations = [];
  bool _loading = true;
  int? _botEmployeeId;

  @override
  void initState() {
    super.initState();
    _initBotAndLoad();
  }

  Future<void> _initBotAndLoad() async {
    _botEmployeeId = await ApiService.getSupportBotId();
    await _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      List<ChatConversation> convs = await ApiService.getConversations();

      // Bot-Konversation automatisch anlegen falls nicht vorhanden
      if (_botEmployeeId != null) {
        final hasBot = convs.any((c) =>
          c.type == 'DIRECT' &&
          c.members.any((m) => m.id == _botEmployeeId)
        );
        if (!hasBot) {
          try {
            await ApiService.createConversation(
              type: 'DIRECT',
              memberIds: [_botEmployeeId!],
            );
            convs = await ApiService.getConversations();
          } catch (_) {}
        }
      }

      // Bot-Konversation immer an erste Stelle sortieren
      convs.sort((a, b) {
        final aIsBot = _botEmployeeId != null &&
            a.type == 'DIRECT' &&
            a.members.any((m) => m.id == _botEmployeeId);
        final bIsBot = _botEmployeeId != null &&
            b.type == 'DIRECT' &&
            b.members.any((m) => m.id == _botEmployeeId);
        if (aIsBot && !bIsBot) return -1;
        if (!aIsBot && bIsBot) return 1;
        final aTime = a.lastMessage?.createdAt ?? '';
        final bTime = b.lastMessage?.createdAt ?? '';
        return bTime.compareTo(aTime);
      });

      _conversations = convs;
    } catch (_) {}
    setState(() => _loading = false);
  }

  void _openNewChat() async {
    final employees = await ApiService.getChatEmployees();
    if (!mounted) return;
    showModalBottomSheet(
      context: context,
      builder: (ctx) => _NewChatSheet(
        employees: employees,
        onSelect: (empId) async {
          Navigator.pop(ctx);
          final result = await ApiService.createConversation(
            type: 'DIRECT',
            memberIds: [empId],
          );
          await _load();
          final conv = _conversations.firstWhere(
            (c) => c.id == result['id'],
            orElse: () => _conversations.first,
          );
          _openConversation(conv);
        },
      ),
    );
  }

  void _openConversation(ChatConversation conv) async {
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => ChatDetailScreen(conversation: conv),
      ),
    );
    _load(); // Reload nach Rueckkehr
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Nachrichten')),
      floatingActionButton: FloatingActionButton(
        onPressed: _openNewChat,
        child: const Icon(Icons.edit),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: _conversations.isEmpty
                  ? ListView(
                      children: [
                        SizedBox(height: 120),
                        Center(
                          child: Column(
                            children: [
                              Icon(Icons.chat_bubble_outline,
                                  size: 48, color: Colors.grey.shade300),
                              const SizedBox(height: 12),
                              Text(
                                'Keine Konversationen',
                                style: TextStyle(color: Colors.grey.shade400),
                              ),
                            ],
                          ),
                        ),
                      ],
                    )
                  : ListView.separated(
                      itemCount: _conversations.length,
                      separatorBuilder: (_, __) =>
                          Divider(height: 1, indent: 72),
                      itemBuilder: (_, i) {
                        final conv = _conversations[i];
                        final isBot = _botEmployeeId != null &&
                            conv.type == 'DIRECT' &&
                            conv.members.any((m) => m.id == _botEmployeeId);
                        return _ConversationTile(
                          conversation: conv,
                          isBot: isBot,
                          onTap: () => _openConversation(conv),
                        );
                      },
                    ),
            ),
    );
  }
}

class _ConversationTile extends StatelessWidget {
  final ChatConversation conversation;
  final bool isBot;
  final VoidCallback onTap;

  const _ConversationTile({
    required this.conversation,
    required this.isBot,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final initials = conversation.name
        .split(' ')
        .take(2)
        .map((w) => w.isNotEmpty ? w[0] : '')
        .join()
        .toUpperCase();

    return ListTile(
      onTap: onTap,
      tileColor: isBot ? Colors.green.shade50 : null,
      leading: CircleAvatar(
        backgroundColor: isBot ? Colors.green.shade100 : Colors.blue.shade100,
        child: isBot
            ? Icon(Icons.smart_toy, size: 20, color: Colors.green.shade700)
            : Text(
                initials,
                style: TextStyle(
                  color: Colors.blue.shade700,
                  fontWeight: FontWeight.w600,
                  fontSize: 14,
                ),
              ),
      ),
      title: Row(
        children: [
          if (isBot) ...[
            Icon(Icons.circle, size: 8, color: Colors.green.shade500),
            const SizedBox(width: 6),
          ],
          Text(
            conversation.name,
            style: TextStyle(
              fontWeight:
                  conversation.unreadCount > 0 ? FontWeight.w700 : FontWeight.w500,
            ),
          ),
        ],
      ),
      subtitle: conversation.lastMessage?.content != null
          ? Text(
              conversation.lastMessage!.content!,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                color: Colors.grey.shade600,
                fontSize: 13,
              ),
            )
          : null,
      trailing: conversation.unreadCount > 0
          ? Container(
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: Colors.blue,
                shape: BoxShape.circle,
              ),
              child: Text(
                '${conversation.unreadCount}',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                ),
              ),
            )
          : (conversation.lastMessage?.createdAt != null
              ? Text(
                  _formatTime(conversation.lastMessage!.createdAt!),
                  style: TextStyle(color: Colors.grey.shade400, fontSize: 11),
                )
              : null),
    );
  }

  String _formatTime(String iso) {
    try {
      final dt = DateTime.parse(iso);
      final now = DateTime.now();
      if (dt.day == now.day && dt.month == now.month && dt.year == now.year) {
        return DateFormat('HH:mm').format(dt);
      }
      return DateFormat('dd.MM').format(dt);
    } catch (_) {
      return '';
    }
  }
}

class _NewChatSheet extends StatefulWidget {
  final List<ChatEmployee> employees;
  final Function(int) onSelect;

  const _NewChatSheet({required this.employees, required this.onSelect});

  @override
  State<_NewChatSheet> createState() => _NewChatSheetState();
}

class _NewChatSheetState extends State<_NewChatSheet> {
  String _search = '';
  final Set<String> _collapsedDepts = {};

  List<ChatEmployee> get _filtered {
    if (_search.isEmpty) return widget.employees;
    final q = _search.toLowerCase();
    return widget.employees.where((e) => e.name.toLowerCase().contains(q)).toList();
  }

  Map<String, List<ChatEmployee>> get _grouped {
    final map = <String, List<ChatEmployee>>{};
    for (final e in _filtered) {
      final dept = e.departmentName ?? 'Ohne Abteilung';
      map.putIfAbsent(dept, () => []);
      map[dept]!.add(e);
    }
    return Map.fromEntries(
      map.entries.toList()..sort((a, b) => a.key.compareTo(b.key)),
    );
  }

  @override
  Widget build(BuildContext context) {
    final groups = _grouped;
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Padding(
          padding: const EdgeInsets.all(16),
          child: Text(
            'Neuen Chat starten',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
          ),
        ),
        // Suchfeld
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: TextField(
            autofocus: true,
            decoration: InputDecoration(
              hintText: 'Mitarbeiter suchen...',
              prefixIcon: const Icon(Icons.search, size: 20),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
              contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              isDense: true,
            ),
            onChanged: (v) => setState(() => _search = v),
          ),
        ),
        const SizedBox(height: 8),
        Flexible(
          child: groups.isEmpty
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Text('Kein Mitarbeiter gefunden.',
                        style: TextStyle(color: Colors.grey.shade400)),
                  ),
                )
              : ListView(
                  shrinkWrap: true,
                  children: groups.entries.expand((entry) {
                    final dept = entry.key;
                    final emps = entry.value;
                    final collapsed = _collapsedDepts.contains(dept);
                    return [
                      // Abteilungs-Header
                      InkWell(
                        onTap: () => setState(() {
                          collapsed ? _collapsedDepts.remove(dept) : _collapsedDepts.add(dept);
                        }),
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                          color: Colors.grey.shade100,
                          child: Row(
                            children: [
                              Icon(
                                collapsed ? Icons.chevron_right : Icons.expand_more,
                                size: 18, color: Colors.grey.shade600,
                              ),
                              const SizedBox(width: 4),
                              Text(
                                '$dept (${emps.length})',
                                style: TextStyle(
                                  fontSize: 12, fontWeight: FontWeight.w600,
                                  color: Colors.grey.shade700,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                      // Mitarbeiter
                      if (!collapsed)
                        ...emps.map((emp) => ListTile(
                              leading: CircleAvatar(
                                backgroundColor: Colors.blue.shade50,
                                radius: 18,
                                child: Text(
                                  emp.name.split(' ').take(2).map((w) => w[0]).join().toUpperCase(),
                                  style: TextStyle(color: Colors.blue.shade700, fontSize: 12),
                                ),
                              ),
                              title: Text(emp.name, style: const TextStyle(fontSize: 14)),
                              trailing: emp.online
                                  ? const Icon(Icons.circle, size: 10, color: Colors.green)
                                  : null,
                              dense: true,
                              onTap: () => widget.onSelect(emp.id),
                            )),
                    ];
                  }).toList(),
                ),
        ),
      ],
    );
  }
}

// ── Chat-Detail-Screen ───────────────────────────────────────────

class ChatDetailScreen extends StatefulWidget {
  final ChatConversation conversation;

  const ChatDetailScreen({super.key, required this.conversation});

  @override
  State<ChatDetailScreen> createState() => _ChatDetailScreenState();
}

class _ChatDetailScreenState extends State<ChatDetailScreen> {
  List<ChatMessage> _messages = [];
  final _controller = TextEditingController();
  final _scrollController = ScrollController();
  bool _loading = true;

  // Spracherkennung
  final stt.SpeechToText _speech = stt.SpeechToText();
  bool _speechAvailable = false;
  bool _isListening = false;

  // Polling
  Timer? _pollTimer;

  @override
  void initState() {
    super.initState();
    _loadMessages();
    _initSpeech();
    // Nachrichten alle 5 Sekunden aktualisieren
    _pollTimer = Timer.periodic(const Duration(seconds: 5), (_) {
      _refreshMessages();
    });
  }

  Future<void> _refreshMessages() async {
    try {
      final fresh = await ApiService.getMessages(widget.conversation.id);
      if (!mounted) return;
      // ID-Vergleich statt Längenvergleich: erkennt auch Updates bei gleicher Anzahl
      final lastFreshId = fresh.isNotEmpty ? fresh.last.id : null;
      final lastCurrentId = _messages.isNotEmpty ? _messages.last.id : null;
      if (lastFreshId != lastCurrentId) {
        setState(() => _messages = fresh);
        _scrollToBottom();
      }
    } catch (_) {}
  }

  Future<void> _initSpeech() async {
    _speechAvailable = await _speech.initialize(
      onError: (error) {
        setState(() => _isListening = false);
      },
    );
    setState(() {});
  }

  Future<void> _toggleListening() async {
    if (!_speechAvailable) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Spracherkennung nicht verfuegbar'),
          backgroundColor: Colors.orange,
        ),
      );
      return;
    }

    if (_isListening) {
      await _speech.stop();
      setState(() => _isListening = false);
    } else {
      setState(() => _isListening = true);
      await _speech.listen(
        onResult: (result) {
          setState(() {
            _controller.text = result.recognizedWords;
            _controller.selection = TextSelection.fromPosition(
              TextPosition(offset: _controller.text.length),
            );
          });
        },
        localeId: 'de_DE',
        listenMode: stt.ListenMode.dictation,
        cancelOnError: true,
        partialResults: true,
      );
    }
  }

  Future<void> _loadMessages() async {
    setState(() => _loading = true);
    try {
      _messages = await ApiService.getMessages(widget.conversation.id);
    } catch (_) {}
    setState(() => _loading = false);
    _scrollToBottom();
  }

  void _scrollToBottom() {
    Future.delayed(const Duration(milliseconds: 100), () {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 200),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<void> _send() async {
    final text = _controller.text.trim();
    if (text.isEmpty) return;
    _controller.clear();

    try {
      final msg = await ApiService.sendChatMessage(widget.conversation.id, text);
      setState(() => _messages.add(msg));
      _scrollToBottom();
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Fehler beim Senden'), backgroundColor: Colors.red),
      );
    }
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    _speech.stop();
    _controller.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final userId = context.read<AuthProvider>().user?.id ?? 0;

    return Scaffold(
      appBar: AppBar(
        title: Text(widget.conversation.name),
      ),
      body: Column(
        children: [
          // Nachrichten
          Expanded(
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : _messages.isEmpty
                    ? Center(
                        child: Text(
                          'Noch keine Nachrichten',
                          style: TextStyle(color: Colors.grey.shade400),
                        ),
                      )
                    : ListView.builder(
                        controller: _scrollController,
                        padding: const EdgeInsets.all(16),
                        itemCount: _messages.length,
                        itemBuilder: (_, i) {
                          final msg = _messages[i];
                          final isMine = msg.senderId == userId;
                          final isSystem = msg.messageType == 'SYSTEM';

                          if (isSystem) {
                            return Center(
                              child: Padding(
                                padding: const EdgeInsets.symmetric(vertical: 8),
                                child: Text(
                                  msg.content,
                                  style: TextStyle(
                                    color: Colors.grey.shade400,
                                    fontSize: 12,
                                  ),
                                ),
                              ),
                            );
                          }

                          return Align(
                            alignment: isMine
                                ? Alignment.centerRight
                                : Alignment.centerLeft,
                            child: Container(
                              margin: const EdgeInsets.only(bottom: 8),
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 14, vertical: 10),
                              constraints: BoxConstraints(
                                maxWidth:
                                    MediaQuery.of(context).size.width * 0.7,
                              ),
                              decoration: BoxDecoration(
                                color: isMine
                                    ? Theme.of(context).colorScheme.primary
                                    : Colors.white,
                                borderRadius: BorderRadius.only(
                                  topLeft: const Radius.circular(16),
                                  topRight: const Radius.circular(16),
                                  bottomLeft: Radius.circular(isMine ? 16 : 4),
                                  bottomRight: Radius.circular(isMine ? 4 : 16),
                                ),
                                boxShadow: [
                                  BoxShadow(
                                    color: Colors.black.withValues(alpha: 0.05),
                                    blurRadius: 4,
                                  ),
                                ],
                              ),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  if (!isMine)
                                    Text(
                                      msg.senderName,
                                      style: TextStyle(
                                        fontSize: 11,
                                        fontWeight: FontWeight.w600,
                                        color: Colors.blue.shade700,
                                      ),
                                    ),
                                  Text(
                                    msg.content,
                                    style: TextStyle(
                                      color: isMine ? Colors.white : Colors.black87,
                                      fontSize: 14,
                                    ),
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    _formatTime(msg.createdAt),
                                    style: TextStyle(
                                      fontSize: 10,
                                      color: isMine
                                          ? Colors.white70
                                          : Colors.grey.shade400,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          );
                        },
                      ),
          ),

          // Spracherkennung aktiv - Anzeige
          if (_isListening)
            Container(
              padding: const EdgeInsets.symmetric(vertical: 6),
              color: Colors.red.shade50,
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.graphic_eq, color: Colors.red.shade400, size: 18),
                  const SizedBox(width: 8),
                  Text(
                    'Spracherkennung aktiv...',
                    style: TextStyle(color: Colors.red.shade600, fontSize: 12, fontWeight: FontWeight.w500),
                  ),
                ],
              ),
            ),

          // Eingabe
          Container(
            padding: EdgeInsets.only(
              left: 12,
              right: 8,
              top: 8,
              bottom: MediaQuery.of(context).padding.bottom + 8,
            ),
            decoration: BoxDecoration(
              color: Colors.white,
              border: Border(top: BorderSide(color: Colors.grey.shade200)),
            ),
            child: Row(
              children: [
                // Mikrofon-Button
                GestureDetector(
                  onTap: _toggleListening,
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 200),
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: _isListening ? Colors.red : Colors.grey.shade100,
                    ),
                    child: Icon(
                      _isListening ? Icons.mic : Icons.mic_none,
                      size: 22,
                      color: _isListening ? Colors.white : Colors.grey.shade600,
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: TextField(
                    controller: _controller,
                    decoration: InputDecoration(
                      hintText: _isListening ? 'Sprechen Sie...' : 'Nachricht schreiben...',
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(24),
                        borderSide: BorderSide(color: Colors.grey.shade300),
                      ),
                      contentPadding: const EdgeInsets.symmetric(
                          horizontal: 16, vertical: 10),
                      isDense: true,
                    ),
                    textInputAction: TextInputAction.send,
                    onSubmitted: (_) => _send(),
                  ),
                ),
                const SizedBox(width: 8),
                IconButton.filled(
                  onPressed: _send,
                  icon: const Icon(Icons.send, size: 20),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  String _formatTime(String iso) {
    try {
      return DateFormat('HH:mm').format(DateTime.parse(iso));
    } catch (_) {
      return '';
    }
  }
}
