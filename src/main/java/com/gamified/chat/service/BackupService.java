package com.gamified.chat.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.gamified.chat.entity.ChatMessageEntity;
import com.gamified.chat.entity.StoryEntity;
import com.gamified.chat.entity.UserAccount;
import com.gamified.chat.model.BackupInfo;
import com.gamified.chat.repository.ChatMessageRepository;
import com.gamified.chat.repository.StoryRepository;
import com.gamified.chat.repository.UserRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import javax.annotation.PostConstruct;
import java.io.*;
import java.nio.file.*;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.zip.GZIPInputStream;
import java.util.zip.GZIPOutputStream;

@Service
public class BackupService {

    private static final Logger log = LoggerFactory.getLogger(BackupService.class);
    private static final DateTimeFormatter FILE_DATE_FMT = DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss");

    private final UserRepository userRepository;
    private final ChatMessageRepository chatMessageRepository;
    private final StoryRepository storyRepository;
    private final Path backupDir;
    private final ObjectMapper objectMapper;
    private final boolean backupEnabled;

    public BackupService(
            UserRepository userRepository,
            ChatMessageRepository chatMessageRepository,
            StoryRepository storyRepository,
            @Value("${backup.directory:./backups}") String backupDirStr,
            @Value("${backup.enabled:true}") boolean backupEnabled) {
        this.userRepository = userRepository;
        this.chatMessageRepository = chatMessageRepository;
        this.storyRepository = storyRepository;
        this.backupDir = Paths.get(backupDirStr);
        this.backupEnabled = backupEnabled;
        this.objectMapper = new ObjectMapper();
        this.objectMapper.registerModule(new JavaTimeModule());
    }

    @PostConstruct
    public void init() {
        try {
            if (!Files.exists(backupDir)) {
                Files.createDirectories(backupDir);
            }
        } catch (IOException e) {
            log.error("Failed to create backup directory: {}", e.getMessage());
        }
    }

    public static class DatabaseSnapshot {
        public Instant timestamp = Instant.now();
        public List<UserAccount> users = new ArrayList<>();
        public List<ChatMessageEntity> messages = new ArrayList<>();
        public List<StoryEntity> stories = new ArrayList<>();
    }

    @Transactional(readOnly = true)
    public BackupInfo createBackup() throws IOException {
        String filename = "backup_" + LocalDateTime.now().format(FILE_DATE_FMT) + ".json.gz";
        Path targetFile = backupDir.resolve(filename);

        DatabaseSnapshot snapshot = new DatabaseSnapshot();
        snapshot.users = userRepository.findAll();
        snapshot.messages = chatMessageRepository.findAll();
        snapshot.stories = storyRepository.findAll();

        byte[] jsonBytes = objectMapper.writeValueAsBytes(snapshot);

        try (OutputStream fos = Files.newOutputStream(targetFile);
             BufferedOutputStream bos = new BufferedOutputStream(fos);
             GZIPOutputStream gzos = new GZIPOutputStream(bos)) {
            gzos.write(jsonBytes);
            gzos.finish();
        }

        long sizeBytes = Files.size(targetFile);
        BackupInfo info = new BackupInfo(filename, sizeBytes, Instant.now().toString(), "COMPLETED");
        info.setUserCount(snapshot.users.size());
        info.setMessageCount(snapshot.messages.size());
        info.setStoryCount(snapshot.stories.size());

        log.info("Database backup created successfully: {} ({} bytes, {} users, {} messages, {} stories)",
                filename, sizeBytes, snapshot.users.size(), snapshot.messages.size(), snapshot.stories.size());

        rotateOldBackups(10);
        return info;
    }

    @Transactional
    public BackupInfo restoreBackup(String filename) throws IOException {
        Path targetFile = backupDir.resolve(filename).normalize();
        if (!targetFile.startsWith(backupDir) || !Files.exists(targetFile)) {
            throw new FileNotFoundException("Backup file not found: " + filename);
        }

        DatabaseSnapshot snapshot;
        try (InputStream fis = Files.newInputStream(targetFile);
             BufferedInputStream bis = new BufferedInputStream(fis);
             GZIPInputStream gzis = new GZIPInputStream(bis)) {
            snapshot = objectMapper.readValue(gzis, DatabaseSnapshot.class);
        }

        if (snapshot == null) {
            throw new IOException("Failed to deserialize backup snapshot");
        }

        // Restore tables
        if (snapshot.users != null && !snapshot.users.isEmpty()) {
            userRepository.saveAll(snapshot.users);
        }
        if (snapshot.messages != null && !snapshot.messages.isEmpty()) {
            chatMessageRepository.saveAll(snapshot.messages);
        }
        if (snapshot.stories != null && !snapshot.stories.isEmpty()) {
            storyRepository.saveAll(snapshot.stories);
        }

        BackupInfo info = new BackupInfo(filename, Files.size(targetFile), Instant.now().toString(), "RESTORED");
        info.setUserCount(snapshot.users != null ? snapshot.users.size() : 0);
        info.setMessageCount(snapshot.messages != null ? snapshot.messages.size() : 0);
        info.setStoryCount(snapshot.stories != null ? snapshot.stories.size() : 0);

        log.info("Database successfully restored from backup: {}", filename);
        return info;
    }

    public List<BackupInfo> listBackups() {
        List<BackupInfo> list = new ArrayList<>();
        if (!Files.exists(backupDir)) return list;

        try (DirectoryStream<Path> stream = Files.newDirectoryStream(backupDir, "*.json.gz")) {
            for (Path entry : stream) {
                long size = Files.size(entry);
                Instant lastModified = Files.getLastModifiedTime(entry).toInstant();
                list.add(new BackupInfo(entry.getFileName().toString(), size, lastModified.toString(), "AVAILABLE"));
            }
        } catch (IOException e) {
            log.error("Failed to list backups: {}", e.getMessage());
        }

        list.sort((a, b) -> b.getFilename().compareTo(a.getFilename()));
        return list;
    }

    public void rotateOldBackups(int maxToKeep) {
        List<BackupInfo> all = listBackups();
        if (all.size() > maxToKeep) {
            for (int i = maxToKeep; i < all.size(); i++) {
                try {
                    Path old = backupDir.resolve(all.get(i).getFilename());
                    Files.deleteIfExists(old);
                    log.info("Purged rotated old backup: {}", all.get(i).getFilename());
                } catch (IOException e) {
                    log.warn("Failed to delete rotated backup: {}", e.getMessage());
                }
            }
        }
    }

    @Scheduled(fixedRateString = "${backup.auto-interval-ms:3600000}")
    public void scheduledAutoBackup() {
        if (!backupEnabled) return;
        try {
            log.info("Triggering scheduled automated database backup...");
            createBackup();
        } catch (Exception e) {
            log.error("Scheduled backup failed: {}", e.getMessage());
        }
    }
}
