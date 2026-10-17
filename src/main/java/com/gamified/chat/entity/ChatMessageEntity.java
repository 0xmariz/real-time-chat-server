package com.gamified.chat.entity;

import javax.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "chat_messages", indexes = {
    @Index(name = "idx_msg_room", columnList = "room_id"),
    @Index(name = "idx_msg_sender", columnList = "sender"),
    @Index(name = "idx_msg_timestamp", columnList = "timestamp")
})
public class ChatMessageEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 64)
    private String sender;

    @Column(length = 64)
    private String recipient;

    @Column(name = "room_id", length = 64)
    private String roomId;

    @Column(columnDefinition = "TEXT")
    private String content;

    @Column(name = "message_type", nullable = false, length = 32)
    private String messageType;

    @Column(nullable = false)
    private Instant timestamp = Instant.now();

    public ChatMessageEntity() {}

    public ChatMessageEntity(String sender, String recipient, String roomId, String content, String messageType) {
        this.sender = sender;
        this.recipient = recipient;
        this.roomId = roomId;
        this.content = content;
        this.messageType = messageType;
        this.timestamp = Instant.now();
    }

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getSender() {
        return sender;
    }

    public void setSender(String sender) {
        this.sender = sender;
    }

    public String getRecipient() {
        return recipient;
    }

    public void setRecipient(String recipient) {
        this.recipient = recipient;
    }

    public String getRoomId() {
        return roomId;
    }

    public void setRoomId(String roomId) {
        this.roomId = roomId;
    }

    public String getContent() {
        return content;
    }

    public void setContent(String content) {
        this.content = content;
    }

    public String getMessageType() {
        return messageType;
    }

    public void setMessageType(String messageType) {
        this.messageType = messageType;
    }

    public Instant getTimestamp() {
        return timestamp;
    }

    public void setTimestamp(Instant timestamp) {
        this.timestamp = timestamp;
    }
}
