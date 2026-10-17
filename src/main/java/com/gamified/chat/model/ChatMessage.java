package com.gamified.chat.model;

import java.time.Instant;
import java.util.List;

public class ChatMessage {

    public enum MessageType {
        CHAT,
        JOIN,
        LEAVE,
        PRIVATE,
        SYSTEM,
        STORY_ALERT,
        LEVEL_UP,
        SCORE_UPDATE
    }

    private MessageType type;
    private String sender;
    private String recipient;
    private String roomId;
    private String content;
    private String timestamp;
    private String avatarUrl;
    private String status = "online";
    private long xpEarned = 0;
    private int userLevel = 1;
    private long userScore = 0;
    private List<String> roomUsers;

    public ChatMessage() {
        this.timestamp = Instant.now().toString();
    }

    public ChatMessage(MessageType type, String sender, String content) {
        this.type = type;
        this.sender = sender;
        this.content = content;
        this.timestamp = Instant.now().toString();
        this.status = "online";
    }

    public MessageType getType() {
        return type;
    }

    public void setType(MessageType type) {
        this.type = type;
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

    public String getTimestamp() {
        return timestamp;
    }

    public void setTimestamp(String timestamp) {
        this.timestamp = timestamp;
    }

    public String getAvatarUrl() {
        return avatarUrl;
    }

    public void setAvatarUrl(String avatarUrl) {
        this.avatarUrl = avatarUrl;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public long getXpEarned() {
        return xpEarned;
    }

    public void setXpEarned(long xpEarned) {
        this.xpEarned = xpEarned;
    }

    public int getUserLevel() {
        return userLevel;
    }

    public void setUserLevel(int userLevel) {
        this.userLevel = userLevel;
    }

    public long getUserScore() {
        return userScore;
    }

    public void setUserScore(long userScore) {
        this.userScore = userScore;
    }

    public List<String> getRoomUsers() {
        return roomUsers;
    }

    public void setRoomUsers(List<String> roomUsers) {
        this.roomUsers = roomUsers;
    }
}
