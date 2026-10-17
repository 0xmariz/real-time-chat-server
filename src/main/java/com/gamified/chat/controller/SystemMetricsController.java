package com.gamified.chat.controller;

import com.gamified.chat.model.SystemMetrics;
import com.gamified.chat.repository.ChatMessageRepository;
import com.gamified.chat.repository.StoryRepository;
import com.gamified.chat.repository.UserRepository;
import com.gamified.chat.tcp.TcpBroadcaster;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import javax.sql.DataSource;
import java.lang.management.ManagementFactory;
import java.lang.management.OperatingSystemMXBean;
import java.lang.management.RuntimeMXBean;
import java.lang.management.ThreadMXBean;
import java.sql.Connection;
import java.util.Map;

@RestController
@RequestMapping("/api/system")
@CrossOrigin(origins = "*")
public class SystemMetricsController {

    private final TcpBroadcaster tcpBroadcaster;
    private final UserRepository userRepository;
    private final ChatMessageRepository chatMessageRepository;
    private final StoryRepository storyRepository;
    private final DataSource dataSource;

    @Value("${spring.profiles.active:default}")
    private String activeProfile;

    public SystemMetricsController(
            TcpBroadcaster tcpBroadcaster,
            UserRepository userRepository,
            ChatMessageRepository chatMessageRepository,
            StoryRepository storyRepository,
            DataSource dataSource) {
        this.tcpBroadcaster = tcpBroadcaster;
        this.userRepository = userRepository;
        this.chatMessageRepository = chatMessageRepository;
        this.storyRepository = storyRepository;
        this.dataSource = dataSource;
    }

    @GetMapping("/metrics")
    public ResponseEntity<SystemMetrics> getMetrics() {
        SystemMetrics metrics = new SystemMetrics();

        // 1. Memory metrics
        Runtime runtime = Runtime.getRuntime();
        long totalMemory = runtime.totalMemory();
        long freeMemory = runtime.freeMemory();
        long usedMemory = totalMemory - freeMemory;
        long maxMemory = runtime.maxMemory();

        metrics.setUsedMemoryMb(usedMemory / (1024 * 1024));
        metrics.setMaxMemoryMb(maxMemory / (1024 * 1024));
        metrics.setMemoryUsagePercent(maxMemory > 0 ? ((double) usedMemory / maxMemory) * 100.0 : 0.0);

        // 2. CPU and Threads
        OperatingSystemMXBean osBean = ManagementFactory.getOperatingSystemMXBean();
        double load = osBean.getSystemLoadAverage();
        metrics.setCpuLoadPercent(load >= 0 ? load * 10.0 : Math.min(100.0, (usedMemory * 100.0) / maxMemory));

        ThreadMXBean threadBean = ManagementFactory.getThreadMXBean();
        metrics.setActiveThreads(threadBean.getThreadCount());

        // 3. TCP Connections
        metrics.setTcpConnections(tcpBroadcaster.getConnectedCount());

        // 4. Uptime
        RuntimeMXBean runtimeBean = ManagementFactory.getRuntimeMXBean();
        long uptimeMs = runtimeBean.getUptime();
        long seconds = (uptimeMs / 1000) % 60;
        long minutes = (uptimeMs / (1000 * 60)) % 60;
        long hours = (uptimeMs / (1000 * 60 * 60));
        metrics.setUptime(String.format("%02dh %02dm %02ds", hours, minutes, seconds));

        // 5. Database Status and Record Counts
        String dbType = "Connected (" + activeProfile + ")";
        try (Connection conn = dataSource.getConnection()) {
            dbType = "Healthy (" + conn.getMetaData().getDatabaseProductName() + ")";
        } catch (Exception ignored) {}
        metrics.setDbStatus(dbType);

        metrics.setRecordCounts(Map.of(
                "users", userRepository.count(),
                "messages", chatMessageRepository.count(),
                "stories", storyRepository.count()
        ));

        return ResponseEntity.ok(metrics);
    }
}
