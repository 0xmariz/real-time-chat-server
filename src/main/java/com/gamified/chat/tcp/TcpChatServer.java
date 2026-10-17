package com.gamified.chat.tcp;

import com.gamified.chat.repository.ChatMessageRepository;
import com.gamified.chat.service.LeaderboardService;
import com.gamified.chat.service.StoryService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

import javax.annotation.PreDestroy;
import java.io.IOException;
import java.net.ServerSocket;
import java.net.Socket;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

@Component
public class TcpChatServer implements CommandLineRunner {

    private static final Logger log = LoggerFactory.getLogger(TcpChatServer.class);

    private final int port;
    private final boolean enabled;
    private final TcpBroadcaster broadcaster;
    private final LeaderboardService leaderboardService;
    private final StoryService storyService;
    private final ChatMessageRepository chatMessageRepository;

    private ServerSocket serverSocket;
    private final ExecutorService executorService = Executors.newCachedThreadPool();
    private volatile boolean running = false;

    public TcpChatServer(
            @Value("${tcp.server.port:8888}") int port,
            @Value("${tcp.server.enabled:true}") boolean enabled,
            TcpBroadcaster broadcaster,
            LeaderboardService leaderboardService,
            StoryService storyService,
            ChatMessageRepository chatMessageRepository) {
        this.port = port;
        this.enabled = enabled;
        this.broadcaster = broadcaster;
        this.leaderboardService = leaderboardService;
        this.storyService = storyService;
        this.chatMessageRepository = chatMessageRepository;
    }

    @Override
    public void run(String... args) {
        if (!enabled) {
            log.info("TCP Chat Server is disabled via configuration.");
            return;
        }

        running = true;
        executorService.submit(this::listen);
    }

    private void listen() {
        try {
            serverSocket = new ServerSocket(port);
            log.info("==========================================================");
            log.info("🚀 Raw TCP Chat Server listening on port: {}", port);
            log.info("👉 Connect via: telnet localhost {} OR nc localhost {}", port, port);
            log.info("==========================================================");

            while (running && !serverSocket.isClosed()) {
                Socket clientSocket = serverSocket.accept();
                log.info("New TCP Client connected from: {}", clientSocket.getRemoteSocketAddress());
                TcpClientHandler handler = new TcpClientHandler(
                        clientSocket,
                        broadcaster,
                        leaderboardService,
                        storyService,
                        chatMessageRepository
                );
                executorService.submit(handler);
            }
        } catch (IOException e) {
            if (running) {
                log.error("TCP Server encountered error: {}", e.getMessage());
            }
        }
    }

    @PreDestroy
    public void stop() {
        running = false;
        if (serverSocket != null && !serverSocket.isClosed()) {
            try {
                serverSocket.close();
                log.info("TCP Server socket closed.");
            } catch (IOException e) {
                log.warn("Error closing TCP server socket: {}", e.getMessage());
            }
        }
        executorService.shutdownNow();
    }
}
