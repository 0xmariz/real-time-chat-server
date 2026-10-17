package com.gamified.chat.controller;

import com.gamified.chat.model.CacheResult;
import com.gamified.chat.model.StoryItem;
import com.gamified.chat.service.StoryService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/stories")
@CrossOrigin(origins = "*")
public class StoryController {

    private final StoryService storyService;

    public StoryController(StoryService storyService) {
        this.storyService = storyService;
    }

    @GetMapping("/active")
    public ResponseEntity<List<StoryItem>> getActiveStories() {
        CacheResult<List<StoryItem>> result = storyService.getActiveStories();
        return ResponseEntity.ok()
                .header("X-Cache", result.getHeaderValue())
                .body(result.getData());
    }

    @PostMapping
    public ResponseEntity<?> createStory(@RequestBody Map<String, String> payload) {
        String username = payload.get("username");
        String content = payload.get("content");
        String mediaUrl = payload.get("mediaUrl");

        if (username == null || username.trim().isEmpty()) {
            return ResponseEntity.badRequest().body(Map.of("error", "Username is required"));
        }

        StoryItem created = storyService.createStory(username.trim(), content, mediaUrl);
        return ResponseEntity.ok(created);
    }

    @PostMapping("/{id}/view")
    public ResponseEntity<?> recordView(
            @PathVariable Long id,
            @RequestBody Map<String, String> payload) {
        String viewerUsername = payload.get("viewer");
        if (viewerUsername == null || viewerUsername.trim().isEmpty()) {
            viewerUsername = "Anonymous";
        }

        boolean recorded = storyService.recordView(id, viewerUsername.trim());
        return ResponseEntity.ok(Map.of("success", recorded, "storyId", id));
    }
}
