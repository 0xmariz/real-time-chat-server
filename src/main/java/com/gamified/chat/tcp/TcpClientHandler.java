package com.gamified.chat.tcp;

import com.gamified.chat.entity.ChatMessageEntity;
import com.gamified.chat.entity.UserAccount;
import com.gamified.chat.model.CacheResult;
import com.gamified.chat.model.ChatMessage;
import com.gamified.chat.model.StoryItem;
import com.gamified.chat.model.UserRank;
import com.gamified.chat.repository.ChatMessageRepository;
import com.gamified.chat.service.LeaderboardService;
import com.gamified.chat.service.StoryService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.*;
import java.net.Socket;
import java.util.List;

public class TcpClientHandler implements Runnable {

    private static final Logger log = LoggerFactory.getLogger(TcpClientHandler.class);

    private final Socket socket;
    private final TcpBroadcaster broadcaster;
    private final LeaderboardService leaderboardService;
    private final StoryService storyService;
    private final ChatMessageRepository chatMessageRepository;

    private BufferedReader reader;
    private PrintWriter writer;
    private String username;
    private String currentRoom = "public";
    private boolean authenticated = false;

    public TcpClientHandler(
            Socket socket,
            TcpBroadcaster broadcaster,
            LeaderboardService leaderboardService,
            StoryService storyService,
            ChatMessageRepository chatMessageRepository) {
        this.socket = socket;
        this.broadcaster = broadcaster;
        this.leaderboardService = leaderboardService;
        this.storyService = storyService;
        this.chatMessageRepository = chatMessageRepository;
    }

    @Override
    public void run() {
        try {
            reader = new BufferedReader(new InputStreamReader(socket.getInputStream()));
            writer = new PrintWriter(new OutputStreamWriter(socket.getOutputStream()), true);

            sendWelcomeBanner();

            String line;
            while ((line = reader.readLine()) != null) {
                line = line.trim();
                if (line.isEmpty()) continue;

                if (line.equalsIgnoreCase("/quit") || line.equalsIgnoreCase("/exit")) {
                    sendMessage("[Server] Goodbye! Disconnecting...");
                    break;
                }

                handleInput(line);
            }
        } catch (IOException e) {
            log.info("TCP Client disconnected ({}): {}", username != null ? username : socket.getRemoteSocketAddress(), e.getMessage());
        } finally {
            close();
        }
    }

    private void sendWelcomeBanner() {
        writer.println("==========================================================");
        writer.println("   🚀 WELCOME TO THE REALTIME TCP CHAT & LEADERBOARD SERVER");
        writer.println("==========================================================");
        writer.println("Commands:");
        writer.println("  /nick <username>      - Set your username");
        writer.println("  /msg <text>           - Send public or room message");
        writer.println("  /join <room>          - Join or switch room");
        writer.println("  /whisper <user> <msg> - Send direct private message");
        writer.println("  /leaderboard          - View live real-time leaderboard");
        writer.println("  /stories              - View active 24-hr stories");
        writer.println("  /stats                - View personal XP and Level");
        writer.println("  /help                 - List commands");
        writer.println("  /quit                 - Disconnect");
        writer.println("----------------------------------------------------------");
        writer.println("Please enter your username using: /nick <your_name>");
    }

    private void handleInput(String input) {
        if (input.startsWith("/")) {
            handleCommand(input);
        } else {
            if (!authenticated) {
                sendMessage("[Server] Please set your username first using /nick <username>");
                return;
            }
            sendPublicMessage(input);
        }
    }

    private void handleCommand(String commandLine) {
        String[] parts = commandLine.split("\\s+", 3);
        String cmd = parts[0].toLowerCase();

        switch (cmd) {
            case "/nick":
                if (parts.length < 2 || parts[1].trim().isEmpty()) {
                    sendMessage("[Server] Usage: /nick <username>");
                } else {
                    setUsername(parts[1].trim());
                }
                break;

            case "/msg":
                if (!authenticated) {
                    sendMessage("[Server] Please set your nickname first with /nick <name>");
                    return;
                }
                if (parts.length < 2 || parts[1].trim().isEmpty()) {
                    sendMessage("[Server] Usage: /msg <message content>");
                } else {
                    String msgContent = commandLine.substring(5).trim();
                    sendPublicMessage(msgContent);
                }
                break;

            case "/join":
                if (!authenticated) {
                    sendMessage("[Server] Please set your nickname first with /nick <name>");
                    return;
                }
                if (parts.length < 2 || parts[1].trim().isEmpty()) {
                    sendMessage("[Server] Usage: /join <room_name>");
                } else {
                    this.currentRoom = parts[1].trim();
                    sendMessage("[Server] Joined room: #" + this.currentRoom);
                }
                break;

            case "/whisper":
                if (!authenticated) {
                    sendMessage("[Server] Please set your nickname first with /nick <name>");
                    return;
                }
                if (parts.length < 3) {
                    sendMessage("[Server] Usage: /whisper <username> <message>");
                } else {
                    String targetUser = parts[1];
                    String privateMsg = parts[2];
                    sendWhisper(targetUser, privateMsg);
                }
                break;

            case "/leaderboard":
                showLeaderboard();
                break;

            case "/stories":
                showStories();
                break;

            case "/stats":
                showStats();
                break;

            case "/help":
                sendWelcomeBanner();
                break;

            default:
                sendMessage("[Server] Unknown command: " + cmd + ". Type /help for assistance.");
                break;
        }
    }

    private void setUsername(String newName) {
        String oldName = this.username;
        this.username = newName;
        this.authenticated = true;
        leaderboardService.getOrCreateUser(this.username);
        broadcaster.register(this);

        sendMessage("[Server] Welcome, " + this.username + "! You are connected to room #" + this.currentRoom);

        // Broadcast to TCP and WebSockets
        String notice = oldName == null
                ? "🚀 [" + this.username + "] joined the chat server via TCP!"
                : "🔄 [" + oldName + "] is now known as [" + this.username + "]";
        broadcaster.broadcastToTcpClients("[Server] " + notice, this);

        ChatMessage cm = new ChatMessage(ChatMessage.MessageType.JOIN, this.username, notice);
        broadcaster.pushToWebSockets(cm);
    }

    private void sendPublicMessage(String text) {
        // Award XP and increment score
        boolean leveledUp = leaderboardService.recordMessageActivity(this.username);
        UserAccount acc = leaderboardService.getOrCreateUser(this.username);

        // Save to DB
        chatMessageRepository.save(new ChatMessageEntity(this.username, null, this.currentRoom, text, "CHAT"));

        // Format for TCP
        String formatted = String.format("[#%s] %s (Lv.%d): %s", this.currentRoom, this.username, acc.getLevel(), text);
        sendMessage("[You] " + text + " (+10 XP)");
        broadcaster.broadcastToTcpRoom(this.currentRoom, formatted, this);

        // Push to WebSockets
        ChatMessage cm = new ChatMessage(ChatMessage.MessageType.CHAT, this.username, text);
        cm.setRoomId(this.currentRoom);
        cm.setUserLevel(acc.getLevel());
        cm.setUserScore(acc.getScore());
        cm.setXpEarned(10);
        cm.setAvatarUrl(acc.getAvatarUrl());
        broadcaster.pushToWebSockets(cm);

        if (leveledUp) {
            String lvlNotice = "🎉 " + this.username + " reached Level " + acc.getLevel() + "!";
            broadcaster.broadcastToTcpClients("[Level Up] " + lvlNotice, null);
            ChatMessage lvlMsg = new ChatMessage(ChatMessage.MessageType.LEVEL_UP, "System", lvlNotice);
            broadcaster.pushToWebSockets(lvlMsg);
        }
    }

    private void sendWhisper(String targetUser, String text) {
        boolean sent = broadcaster.sendDirectTcp(targetUser, String.format("[Whisper from %s]: %s", this.username, text));
        sendMessage(String.format("[Whisper to %s]: %s", targetUser, text));

        // Push to WebSockets
        ChatMessage cm = new ChatMessage(ChatMessage.MessageType.PRIVATE, this.username, text);
        cm.setRecipient(targetUser);
        broadcaster.pushToWebSockets(cm);

        if (!sent) {
            sendMessage("[Server] Note: " + targetUser + " is not currently active on a TCP terminal session (sent to Web queues).");
        }
    }

    private void showLeaderboard() {
        CacheResult<List<UserRank>> result = leaderboardService.getTopLeaderboard(10);
        List<UserRank> list = result.getData();
        writer.println("----------------------------------------------------------");
        writer.println(" 🏆 REAL-TIME LEADERBOARD (Top 10)  [" + (result.isHit() ? "Cache HIT" : "Live DB") + "]");
        writer.println("----------------------------------------------------------");
        writer.printf("%-6s %-16s %-8s %-6s %-10s%n", "Rank", "User", "Level", "Score", "Badges");
        writer.println("----------------------------------------------------------");
        if (list == null || list.isEmpty()) {
            writer.println("No rankings recorded yet. Send a message to start scoring!");
        } else {
            for (UserRank r : list) {
                String badges = String.join(" ", r.getBadges());
                writer.printf("#%-5d %-16s Lv.%-5d %-6d %-10s%n",
                        r.getRank(), r.getUsername(), r.getLevel(), r.getScore(), badges);
            }
        }
        writer.println("----------------------------------------------------------");
    }

    private void showStories() {
        CacheResult<List<StoryItem>> result = storyService.getActiveStories();
        List<StoryItem> stories = result.getData();
        writer.println("----------------------------------------------------------");
        writer.println(" 📸 ACTIVE STORIES (24h Ephemeral Feed) [" + (result.isHit() ? "Cache HIT" : "Live DB") + "]");
        writer.println("----------------------------------------------------------");
        if (stories == null || stories.isEmpty()) {
            writer.println("No active stories right now.");
        } else {
            for (StoryItem s : stories) {
                long hoursLeft = s.getSecondsRemaining() / 3600;
                long minsLeft = (s.getSecondsRemaining() % 3600) / 60;
                writer.printf("• @%-14s: %-30s (Expires in %dh %dm, %d views)%n",
                        s.getUsername(),
                        s.getContent() != null ? s.getContent() : "[Media]",
                        hoursLeft, minsLeft, s.getViewCount());
            }
        }
        writer.println("----------------------------------------------------------");
    }

    private void showStats() {
        if (!authenticated) {
            sendMessage("[Server] Please set username first with /nick <name>");
            return;
        }
        CacheResult<UserRank> res = leaderboardService.getUserRank(this.username);
        UserRank r = res.getData();
        if (r == null) {
            sendMessage("[Server] No statistics recorded yet.");
            return;
        }
        writer.println("----------------------------------------------------------");
        writer.printf(" 📊 STATS FOR: %s%n", this.username);
        writer.printf(" Rank: #%d | Level: %d | XP: %d | Score: %d%n", r.getRank(), r.getLevel(), r.getXp(), r.getScore());
        writer.printf(" Messages Sent: %d | Stories Posted: %d%n", r.getMessagesCount(), r.getStoriesCount());
        writer.printf(" Badges: %s%n", String.join(", ", r.getBadges()));
        writer.println("----------------------------------------------------------");
    }

    public void sendMessage(String msg) {
        if (writer != null) {
            writer.println(msg);
        }
    }

    public boolean isAuthenticated() {
        return authenticated;
    }

    public String getUsername() {
        return username;
    }

    public String getCurrentRoom() {
        return currentRoom;
    }

    public void close() {
        broadcaster.unregister(this);
        if (authenticated && username != null) {
            String leaveMsg = "👋 [" + username + "] left the chat server.";
            broadcaster.broadcastToTcpClients("[Server] " + leaveMsg, this);
            ChatMessage cm = new ChatMessage(ChatMessage.MessageType.LEAVE, username, leaveMsg);
            broadcaster.pushToWebSockets(cm);
        }
        try {
            if (socket != null && !socket.isClosed()) {
                socket.close();
            }
        } catch (IOException ignored) {}
    }
}
