package com.gamified.chat.controller;

import com.gamified.chat.model.BackupInfo;
import com.gamified.chat.service.BackupService;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/backup")
@CrossOrigin(origins = "*")
public class BackupController {

    private final BackupService backupService;

    public BackupController(BackupService backupService) {
        this.backupService = backupService;
    }

    @PostMapping("/create")
    public ResponseEntity<?> createBackup() {
        try {
            BackupInfo info = backupService.createBackup();
            return ResponseEntity.ok(info);
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(Map.of("error", "Failed to create database backup: " + e.getMessage()));
        }
    }

    @GetMapping("/list")
    public ResponseEntity<List<BackupInfo>> listBackups() {
        return ResponseEntity.ok(backupService.listBackups());
    }

    @PostMapping("/restore/{filename}")
    public ResponseEntity<?> restoreBackup(@PathVariable String filename) {
        try {
            BackupInfo info = backupService.restoreBackup(filename);
            return ResponseEntity.ok(info);
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(Map.of("error", "Failed to restore database from backup: " + e.getMessage()));
        }
    }
}
