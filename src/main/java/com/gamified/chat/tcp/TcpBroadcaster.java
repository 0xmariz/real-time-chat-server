package com.gamified.chat.tcp;

import com.gamified.chat.model.ChatMessage;
import org.springframework.context.annotation.Lazy;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Component;

import java.util.concurrent.CopyOnWriteArraySet;

@Component
public class TcpBroadcaster {

    private final CopyOnWriteArraySet<TcpClientHandler> activeClients = new CopyOnWriteArraySet<>();
    private final SimpMessagingTemplate messagingTemplate;

    public TcpBroadcaster(@Lazy SimpMessagingTemplate messagingTemplate) {
        this.messagingTemplate = messagingTemplate;
    }

    public void register(TcpClientHandler client) {
        activeClients.add(client);
    }

    public void unregister(TcpClientHandler client) {
        activeClients.remove(client);
    }

    public int getConnectedCount() {
        return activeClients.size();
    }

    public void broadcastToTcpClients(String message, TcpClientHandler sender) {
        for (TcpClientHandler client : activeClients) {
            if (client != sender && client.isAuthenticated()) {
                client.sendMessage(message);
            }
        }
    }

    public void broadcastToTcpRoom(String roomId, String message, TcpClientHandler sender) {
        for (TcpClientHandler client : activeClients) {
            if (client != sender && client.isAuthenticated() && roomId.equalsIgnoreCase(client.getCurrentRoom())) {
                client.sendMessage(message);
            }
        }
    }

    public boolean sendDirectTcp(String recipient, String message) {
        for (TcpClientHandler client : activeClients) {
            if (client.isAuthenticated() && recipient.equalsIgnoreCase(client.getUsername())) {
                client.sendMessage(message);
                return true;
            }
        }
        return false;
    }

    public void pushToWebSockets(ChatMessage chatMessage) {
        try {
            if (chatMessage.getRecipient() != null && !chatMessage.getRecipient().isEmpty()) {
                messagingTemplate.convertAndSend("/user/" + chatMessage.getRecipient() + "/queue/private", chatMessage);
            } else if (chatMessage.getRoomId() != null && !chatMessage.getRoomId().isEmpty() && !chatMessage.getRoomId().equalsIgnoreCase("public")) {
                messagingTemplate.convertAndSend("/topic/room/" + chatMessage.getRoomId(), chatMessage);
            } else {
                messagingTemplate.convertAndSend("/topic/public", chatMessage);
            }
        } catch (Exception e) {
            org.slf4j.LoggerFactory.getLogger(TcpBroadcaster.class).warn("Failed to push to WebSockets: {}", e.getMessage());
        }
    }
}
