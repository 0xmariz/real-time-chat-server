package com.gamified.chat.controller;

import com.gamified.chat.entity.UserAccount;
import com.gamified.chat.repository.UserRepository;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.time.Instant;
import java.util.Base64;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;

/**
 * Authentication Controller — handles user registration and login.
 * Uses SHA-256 + per-user salt (stored as salt$hash) for passwords.
 * No Spring Security dependency required (avoids version conflicts with Java 11 / SB 2.7).
 */
@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final UserRepository userRepository;

    public AuthController(UserRepository userRepository) {
        this.userRepository = userRepository;
    }

    // -----------------------------------------------------------------------
    // POST /api/auth/register
    // Body: { "username": "...", "password": "..." }
    // -----------------------------------------------------------------------
    @PostMapping("/register")
    public ResponseEntity<Map<String, Object>> register(@RequestBody Map<String, String> body) {
        String username = body.getOrDefault("username", "").trim();
        String password = body.getOrDefault("password", "").trim();

        Map<String, Object> resp = new HashMap<>();

        if (username.isEmpty() || password.isEmpty()) {
            resp.put("success", false);
            resp.put("message", "Username and password are required.");
            return ResponseEntity.badRequest().body(resp);
        }
        if (username.length() < 3 || username.length() > 32) {
            resp.put("success", false);
            resp.put("message", "Username must be 3-32 characters.");
            return ResponseEntity.badRequest().body(resp);
        }
        if (password.length() < 4) {
            resp.put("success", false);
            resp.put("message", "Password must be at least 4 characters.");
            return ResponseEntity.badRequest().body(resp);
        }

        if (userRepository.findByUsername(username).isPresent()) {
            resp.put("success", false);
            resp.put("message", "Username already taken. Try another.");
            return ResponseEntity.badRequest().body(resp);
        }

        UserAccount newUser = new UserAccount(username);
        newUser.setPasswordHash(hashPassword(password));
        newUser.setGuest(false);
        userRepository.save(newUser);

        resp.put("success", true);
        resp.put("username", username);
        resp.put("message", "Account created! Welcome, " + username + "!");
        resp.put("avatarUrl", newUser.getAvatarUrl());
        resp.put("level", newUser.getLevel());
        resp.put("score", newUser.getScore());
        resp.put("xp", newUser.getXp());
        return ResponseEntity.ok(resp);
    }

    // -----------------------------------------------------------------------
    // POST /api/auth/login
    // Body: { "username": "...", "password": "..." }
    // -----------------------------------------------------------------------
    @PostMapping("/login")
    public ResponseEntity<Map<String, Object>> login(@RequestBody Map<String, String> body) {
        String username = body.getOrDefault("username", "").trim();
        String password = body.getOrDefault("password", "").trim();

        Map<String, Object> resp = new HashMap<>();

        if (username.isEmpty() || password.isEmpty()) {
            resp.put("success", false);
            resp.put("message", "Username and password are required.");
            return ResponseEntity.badRequest().body(resp);
        }

        Optional<UserAccount> opt = userRepository.findByUsername(username);
        if (opt.isEmpty()) {
            resp.put("success", false);
            resp.put("message", "No account found for that username.");
            return ResponseEntity.status(401).body(resp);
        }

        UserAccount user = opt.get();

        // If account is a guest (no password set), deny password login
        if (user.getPasswordHash() == null || user.getPasswordHash().isEmpty()) {
            resp.put("success", false);
            resp.put("message", "This username has no password. Use Guest mode or register first.");
            return ResponseEntity.status(401).body(resp);
        }

        if (!verifyPassword(password, user.getPasswordHash())) {
            resp.put("success", false);
            resp.put("message", "Incorrect password. Please try again.");
            return ResponseEntity.status(401).body(resp);
        }

        user.setUpdatedAt(Instant.now());
        userRepository.save(user);

        resp.put("success", true);
        resp.put("username", username);
        resp.put("message", "Welcome back, " + username + "!");
        resp.put("avatarUrl", user.getAvatarUrl());
        resp.put("level", user.getLevel());
        resp.put("score", user.getScore());
        resp.put("xp", user.getXp());
        resp.put("guest", false);
        return ResponseEntity.ok(resp);
    }

    // -----------------------------------------------------------------------
    // POST /api/auth/guest
    // Body: { "username": "..." }  -- join without password (guest mode)
    // -----------------------------------------------------------------------
    @PostMapping("/guest")
    public ResponseEntity<Map<String, Object>> guestLogin(@RequestBody Map<String, String> body) {
        String username = body.getOrDefault("username", "").trim();
        Map<String, Object> resp = new HashMap<>();

        if (username.isEmpty()) {
            resp.put("success", false);
            resp.put("message", "Username is required.");
            return ResponseEntity.badRequest().body(resp);
        }
        if (username.length() < 2 || username.length() > 32) {
            resp.put("success", false);
            resp.put("message", "Username must be 2-32 characters.");
            return ResponseEntity.badRequest().body(resp);
        }

        UserAccount user = userRepository.findByUsername(username).orElseGet(() -> {
            UserAccount g = new UserAccount(username);
            g.setGuest(true);
            return userRepository.save(g);
        });

        resp.put("success", true);
        resp.put("username", user.getUsername());
        resp.put("message", "Joined as guest: " + username);
        resp.put("avatarUrl", user.getAvatarUrl());
        resp.put("level", user.getLevel());
        resp.put("score", user.getScore());
        resp.put("xp", user.getXp());
        resp.put("guest", user.isGuest());
        return ResponseEntity.ok(resp);
    }

    // -----------------------------------------------------------------------
    // Helpers: SHA-256 + random salt
    // -----------------------------------------------------------------------
    private String hashPassword(String password) {
        try {
            byte[] saltBytes = new byte[16];
            new SecureRandom().nextBytes(saltBytes);
            String salt = Base64.getEncoder().encodeToString(saltBytes);
            String hash = sha256(salt + password);
            return salt + "$" + hash;
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException("SHA-256 not available", e);
        }
    }

    private boolean verifyPassword(String rawPassword, String stored) {
        try {
            String[] parts = stored.split("\\$", 2);
            if (parts.length != 2) return false;
            String salt = parts[0];
            String expectedHash = parts[1];
            String actualHash = sha256(salt + rawPassword);
            return MessageDigest.isEqual(expectedHash.getBytes(StandardCharsets.UTF_8),
                    actualHash.getBytes(StandardCharsets.UTF_8));
        } catch (NoSuchAlgorithmException e) {
            return false;
        }
    }

    private String sha256(String input) throws NoSuchAlgorithmException {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        byte[] hash = digest.digest(input.getBytes(StandardCharsets.UTF_8));
        StringBuilder hex = new StringBuilder();
        for (byte b : hash) {
            hex.append(String.format("%02x", b));
        }
        return hex.toString();
    }
}
