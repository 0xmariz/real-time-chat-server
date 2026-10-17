package com.gamified.chat.controller;

import com.gamified.chat.entity.ChatMessageEntity;
import com.gamified.chat.entity.UserAccount;
import com.gamified.chat.model.ChatMessage;
import com.gamified.chat.repository.ChatMessageRepository;
import com.gamified.chat.service.LeaderboardService;
import com.gamified.chat.tcp.TcpBroadcaster;
import org.springframework.messaging.handler.annotation.MessageMapping;
import org.springframework.messaging.handler.annotation.Payload;
import org.springframework.messaging.handler.annotation.SendTo;
import org.springframework.messaging.simp.SimpMessageHeaderAccessor;
import org.springframework.messaging.simp.SimpMessageSendingOperations;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseBody;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

@Controller
public class WebSocketController {

    private final SimpMessageSendingOperations messagingTemplate;
    private final LeaderboardService leaderboardService;
    private final ChatMessageRepository chatMessageRepository;
    private final TcpBroadcaster tcpBroadcaster;

    private final Map<String, Set<String>> roomUsers = new ConcurrentHashMap<>();

    public WebSocketController(
            SimpMessageSendingOperations messagingTemplate,
            LeaderboardService leaderboardService,
            ChatMessageRepository chatMessageRepository,
            TcpBroadcaster tcpBroadcaster) {
        this.messagingTemplate = messagingTemplate;
        this.leaderboardService = leaderboardService;
        this.chatMessageRepository = chatMessageRepository;
        this.tcpBroadcaster = tcpBroadcaster;
    }

    @MessageMapping("/chat.sendMessage")
    @SendTo("/topic/public")
    public ChatMessage sendMessage(@Payload ChatMessage chatMessage) {
        String sender = chatMessage.getSender();
        boolean leveledUp = leaderboardService.recordMessageActivity(sender);
        UserAccount acc = leaderboardService.getOrCreateUser(sender);

        chatMessage.setStatus("online");
        chatMessage.setUserLevel(acc.getLevel());
        chatMessage.setUserScore(acc.getScore());
        chatMessage.setXpEarned(10);
        chatMessage.setAvatarUrl(acc.getAvatarUrl());

        // Save to Database
        chatMessageRepository.save(new ChatMessageEntity(
                sender,
                null,
                "public",
                chatMessage.getContent(),
                chatMessage.getType().name()
        ));

        // Forward to TCP clients
        tcpBroadcaster.broadcastToTcpClients(
                String.format("[#public] %s (Lv.%d): %s", sender, acc.getLevel(), chatMessage.getContent()),
                null
        );

        if (leveledUp) {
            ChatMessage lvlMsg = new ChatMessage(
                    ChatMessage.MessageType.LEVEL_UP,
                    "System",
                    "🎉 " + sender + " leveled up to Level " + acc.getLevel() + "!"
            );
            messagingTemplate.convertAndSend("/topic/public", lvlMsg);
        }

        return chatMessage;
    }

    @MessageMapping("/chat.addUser")
    @SendTo("/topic/public")
    public ChatMessage addUser(@Payload ChatMessage chatMessage, SimpMessageHeaderAccessor headerAccessor) {
        String sender = chatMessage.getSender();
        if (headerAccessor.getSessionAttributes() != null) {
            headerAccessor.getSessionAttributes().put("username", sender);
        }

        UserAccount acc = leaderboardService.getOrCreateUser(sender);
        chatMessage.setStatus("online");
        chatMessage.setUserLevel(acc.getLevel());
        chatMessage.setUserScore(acc.getScore());
        chatMessage.setAvatarUrl(acc.getAvatarUrl());

        // Notify TCP clients
        tcpBroadcaster.broadcastToTcpClients(
                "🚀 [" + sender + "] joined the chat via Web!",
                null
        );

        return chatMessage;
    }

    @MessageMapping("/chat.sendPrivateMessage")
    public void sendPrivateMessage(@Payload ChatMessage chatMessage) {
        String sender = chatMessage.getSender();
        String recipient = chatMessage.getRecipient();

        leaderboardService.recordMessageActivity(sender);
        UserAccount acc = leaderboardService.getOrCreateUser(sender);

        chatMessage.setType(ChatMessage.MessageType.PRIVATE);
        chatMessage.setStatus("online");
        chatMessage.setUserLevel(acc.getLevel());
        chatMessage.setUserScore(acc.getScore());
        chatMessage.setAvatarUrl(acc.getAvatarUrl());

        // Save to DB
        chatMessageRepository.save(new ChatMessageEntity(
                sender,
                recipient,
                null,
                chatMessage.getContent(),
                "PRIVATE"
        ));

        // Send to both sender and recipient WebSocket queues
        messagingTemplate.convertAndSend("/user/" + recipient + "/queue/private", chatMessage);
        messagingTemplate.convertAndSend("/user/" + sender + "/queue/private", chatMessage);

        // Also push to TCP recipient if active on TCP
        tcpBroadcaster.sendDirectTcp(
                recipient,
                String.format("[Whisper from %s]: %s", sender, chatMessage.getContent())
        );
    }

    @MessageMapping("/chat.sendRoomMessage")
    public void sendRoomMessage(@Payload ChatMessage chatMessage) {
        String roomId = chatMessage.getRoomId();
        String sender = chatMessage.getSender();

        if (roomId != null) {
            boolean leveledUp = leaderboardService.recordMessageActivity(sender);
            UserAccount acc = leaderboardService.getOrCreateUser(sender);

            chatMessage.setType(ChatMessage.MessageType.CHAT);
            chatMessage.setStatus("online");
            chatMessage.setUserLevel(acc.getLevel());
            chatMessage.setUserScore(acc.getScore());
            chatMessage.setAvatarUrl(acc.getAvatarUrl());

            chatMessageRepository.save(new ChatMessageEntity(
                    sender,
                    null,
                    roomId,
                    chatMessage.getContent(),
                    "ROOM"
            ));

            messagingTemplate.convertAndSend("/topic/room/" + roomId, chatMessage);
            tcpBroadcaster.broadcastToTcpRoom(
                    roomId,
                    String.format("[#%s] %s (Lv.%d): %s", roomId, sender, acc.getLevel(), chatMessage.getContent()),
                    null
            );

            if (leveledUp) {
                ChatMessage lvlMsg = new ChatMessage(
                        ChatMessage.MessageType.LEVEL_UP,
                        "System",
                        "🎉 " + sender + " reached Level " + acc.getLevel() + "!"
                );
                messagingTemplate.convertAndSend("/topic/room/" + roomId, lvlMsg);
            }
        }
    }

    @MessageMapping("/chat.joinRoom")
    public void joinRoom(@Payload ChatMessage chatMessage, SimpMessageHeaderAccessor headerAccessor) {
        String roomId = chatMessage.getRoomId();
        String username = chatMessage.getSender();

        if (roomId != null && username != null) {
            if (headerAccessor.getSessionAttributes() != null) {
                headerAccessor.getSessionAttributes().put("roomId", roomId);
            }
            roomUsers.computeIfAbsent(roomId, k -> ConcurrentHashMap.newKeySet()).add(username);

            UserAccount acc = leaderboardService.getOrCreateUser(username);
            chatMessage.setType(ChatMessage.MessageType.JOIN);
            chatMessage.setContent(username + " joined room #" + roomId);
            chatMessage.setStatus("online");
            chatMessage.setUserLevel(acc.getLevel());
            chatMessage.setUserScore(acc.getScore());
            chatMessage.setAvatarUrl(acc.getAvatarUrl());
            chatMessage.setRoomUsers(new ArrayList<>(roomUsers.get(roomId)));

            messagingTemplate.convertAndSend("/topic/room/" + roomId, chatMessage);
        }
    }

    @MessageMapping("/chat.leaveRoom")
    public void leaveRoom(@Payload ChatMessage chatMessage, SimpMessageHeaderAccessor headerAccessor) {
        String roomId = chatMessage.getRoomId();
        String username = chatMessage.getSender();

        if (roomId != null && username != null) {
            Set<String> users = roomUsers.get(roomId);
            if (users != null) {
                users.remove(username);
            }

            chatMessage.setType(ChatMessage.MessageType.LEAVE);
            chatMessage.setContent(username + " left the room.");
            chatMessage.setStatus("offline");
            chatMessage.setRoomUsers(users != null ? new ArrayList<>(users) : Collections.emptyList());

            messagingTemplate.convertAndSend("/topic/room/" + roomId, chatMessage);
        }
    }

    // -----------------------------------------------------------------------
    // REST: GET /api/chat/history/{roomId}?limit=50
    // Returns the last N messages for a given room, oldest first.
    // Used by the web client on page load / room switch to restore message history.
    // -----------------------------------------------------------------------
    @GetMapping("/api/chat/history/{roomId}")
    @ResponseBody
    public List<Map<String, Object>> getRoomHistory(
            @PathVariable String roomId,
            @RequestParam(defaultValue = "50") int limit) {

        List<ChatMessageEntity> msgs = chatMessageRepository.findTop50ByRoomIdOrderByTimestampAsc(roomId);
        List<Map<String, Object>> result = new ArrayList<>();

        for (ChatMessageEntity m : msgs) {
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("sender", m.getSender());
            item.put("content", m.getContent());
            item.put("messageType", m.getMessageType());
            item.put("timestamp", m.getTimestamp() != null ? m.getTimestamp().toEpochMilli() : 0);
            // Attach avatar URL from user lookup
            leaderboardService.getOrCreateUser(m.getSender()); // ensure exists
            item.put("avatarUrl", "https://api.dicebear.com/7.x/bottts/svg?seed=" + m.getSender());
            result.add(item);
        }
        return result;
    }
}
