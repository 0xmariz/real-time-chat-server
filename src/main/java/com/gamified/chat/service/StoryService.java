package com.gamified.chat.service;

import com.gamified.chat.cache.InMemoryCacheService;
import com.gamified.chat.entity.StoryEntity;
import com.gamified.chat.model.CacheResult;
import com.gamified.chat.model.ChatMessage;
import com.gamified.chat.model.StoryItem;
import com.gamified.chat.repository.StoryRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.annotation.Lazy;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Optional;

@Service
public class StoryService {

    private static final Logger log = LoggerFactory.getLogger(StoryService.class);
    private static final String CACHE_KEY_ACTIVE_STORIES = "stories:active";

    private final StoryRepository storyRepository;
    private final LeaderboardService leaderboardService;
    private final InMemoryCacheService cacheService;
    private final SimpMessagingTemplate messagingTemplate;

    public StoryService(
            StoryRepository storyRepository,
            LeaderboardService leaderboardService,
            InMemoryCacheService cacheService,
            @Lazy SimpMessagingTemplate messagingTemplate) {
        this.storyRepository = storyRepository;
        this.leaderboardService = leaderboardService;
        this.cacheService = cacheService;
        this.messagingTemplate = messagingTemplate;
    }

    public CacheResult<List<StoryItem>> getActiveStories() {
        CacheResult<List<StoryItem>> cached = cacheService.get(CACHE_KEY_ACTIVE_STORIES);
        if (cached.isHit()) {
            return cached;
        }

        List<StoryEntity> entities = storyRepository.findActiveStories(Instant.now());
        List<StoryItem> items = new ArrayList<>();
        for (StoryEntity entity : entities) {
            items.add(mapToStoryItem(entity));
        }

        cacheService.put(CACHE_KEY_ACTIVE_STORIES, items, 30);
        return new CacheResult<>(items, false);
    }

    @Transactional
    public StoryItem createStory(String username, String content, String mediaUrl) {
        StoryEntity story = new StoryEntity(username, content, mediaUrl);
        StoryEntity saved = storyRepository.save(story);

        // Award gamification XP for posting a story
        boolean leveledUp = leaderboardService.recordStoryActivity(username);

        // Evict cached stories
        cacheService.evict(CACHE_KEY_ACTIVE_STORIES);

        StoryItem item = mapToStoryItem(saved);

        // Broadcast story to WebSocket subscribers
        try {
            messagingTemplate.convertAndSend("/topic/stories", item);

            // Also post a system alert in public chat
            ChatMessage alert = new ChatMessage(
                    ChatMessage.MessageType.STORY_ALERT,
                    username,
                    "📸 " + username + " just posted a new Story! Check the top story bar."
            );
            alert.setAvatarUrl(item.getAvatarUrl());
            messagingTemplate.convertAndSend("/topic/public", alert);

            if (leveledUp) {
                ChatMessage lvlAlert = new ChatMessage(
                        ChatMessage.MessageType.LEVEL_UP,
                        "System",
                        "🎉 " + username + " leveled up to Level " + leaderboardService.getOrCreateUser(username).getLevel() + "!"
                );
                messagingTemplate.convertAndSend("/topic/public", lvlAlert);
            }
        } catch (Exception e) {
            log.warn("Failed to broadcast new story via WebSocket: {}", e.getMessage());
        }

        return item;
    }

    @Transactional
    public boolean recordView(Long storyId, String viewerUsername) {
        Optional<StoryEntity> opt = storyRepository.findById(storyId);
        if (opt.isEmpty() || opt.get().isExpired()) {
            return false;
        }

        StoryEntity story = opt.get();
        String currentViewers = story.getViewersCsv() != null ? story.getViewersCsv() : "";
        List<String> viewersList = new ArrayList<>();
        if (!currentViewers.isEmpty()) {
            viewersList.addAll(Arrays.asList(currentViewers.split(",")));
        }

        if (!viewersList.contains(viewerUsername)) {
            viewersList.add(viewerUsername);
            story.setViewersCsv(String.join(",", viewersList));
            story.setViewCount(viewersList.size());
            storyRepository.save(story);
            cacheService.evict(CACHE_KEY_ACTIVE_STORIES);
            return true;
        }
        return false;
    }

    @Scheduled(fixedRate = 300000) // Every 5 minutes
    @Transactional
    public void cleanupExpiredStories() {
        long deleted = storyRepository.deleteByExpiresAtBefore(Instant.now());
        if (deleted > 0) {
            log.info("Cleaned up {} expired stories", deleted);
            cacheService.evict(CACHE_KEY_ACTIVE_STORIES);
        }
    }

    private StoryItem mapToStoryItem(StoryEntity entity) {
        StoryItem item = new StoryItem();
        item.setId(entity.getId());
        item.setUsername(entity.getUsername());
        item.setContent(entity.getContent());
        item.setMediaUrl(entity.getMediaUrl());
        item.setCreatedAt(entity.getCreatedAt().toString());
        item.setExpiresAt(entity.getExpiresAt().toString());
        item.setSecondsRemaining(Math.max(0, Duration.between(Instant.now(), entity.getExpiresAt()).getSeconds()));
        item.setViewCount(entity.getViewCount());
        item.setAvatarUrl("https://api.dicebear.com/7.x/bottts/svg?seed=" + entity.getUsername());

        if (entity.getViewersCsv() != null && !entity.getViewersCsv().isEmpty()) {
            item.setViewers(Arrays.asList(entity.getViewersCsv().split(",")));
        }
        return item;
    }
}
