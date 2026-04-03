class ChatConversation {
  final int id;
  final String type;
  final String name;
  final List<ChatMember> members;
  final ChatLastMessage? lastMessage;
  final int unreadCount;

  ChatConversation({
    required this.id,
    required this.type,
    required this.name,
    required this.members,
    this.lastMessage,
    required this.unreadCount,
  });

  factory ChatConversation.fromJson(Map<String, dynamic> json) {
    return ChatConversation(
      id: json['id'],
      type: json['type'] ?? 'DIRECT',
      name: json['name'] ?? '',
      members: (json['members'] as List? ?? [])
          .map((m) => ChatMember.fromJson(m))
          .toList(),
      lastMessage: json['last_message'] != null
          ? ChatLastMessage.fromJson(json['last_message'])
          : null,
      unreadCount: json['unread_count'] ?? 0,
    );
  }
}

class ChatMember {
  final int id;
  final String name;

  ChatMember({required this.id, required this.name});

  factory ChatMember.fromJson(Map<String, dynamic> json) {
    return ChatMember(
      id: json['id'],
      name: json['name'] ?? '',
    );
  }
}

class ChatLastMessage {
  final String? content;
  final int? senderId;
  final String? senderName;
  final String? createdAt;

  ChatLastMessage({this.content, this.senderId, this.senderName, this.createdAt});

  factory ChatLastMessage.fromJson(Map<String, dynamic> json) {
    return ChatLastMessage(
      content: json['content'],
      senderId: json['sender_id'],
      senderName: json['sender_name'],
      createdAt: json['created_at'],
    );
  }
}

class ChatMessage {
  final int id;
  final int conversationId;
  final int senderId;
  final String senderName;
  final String content;
  final String messageType;
  final String? filePath;
  final String createdAt;

  ChatMessage({
    required this.id,
    required this.conversationId,
    required this.senderId,
    required this.senderName,
    required this.content,
    required this.messageType,
    this.filePath,
    required this.createdAt,
  });

  factory ChatMessage.fromJson(Map<String, dynamic> json) {
    return ChatMessage(
      id: json['id'] ?? 0,
      conversationId: json['conversation_id'] ?? 0,
      senderId: json['sender_id'] ?? 0,
      senderName: json['sender_name'] ?? '',
      content: json['content'] ?? '',
      messageType: json['message_type'] ?? 'TEXT',
      filePath: json['file_path'],
      createdAt: json['created_at'] ?? '',
    );
  }
}

class ChatEmployee {
  final int id;
  final String name;
  final String role;
  final int? departmentId;
  final String? departmentName;
  final bool online;

  ChatEmployee({
    required this.id,
    required this.name,
    required this.role,
    this.departmentId,
    this.departmentName,
    required this.online,
  });

  factory ChatEmployee.fromJson(Map<String, dynamic> json) {
    return ChatEmployee(
      id: json['id'],
      name: json['name'] ?? '',
      role: json['role'] ?? '',
      departmentId: json['department_id'],
      departmentName: json['department_name'],
      online: json['online'] ?? false,
    );
  }
}
