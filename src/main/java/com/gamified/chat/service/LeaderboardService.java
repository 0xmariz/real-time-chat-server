package com.gamified.chat.service;

import com.gamified.chat.cache.InMemoryCacheService;
import com.gamified.chat.entity.UserAccount;
import com.gamified.chat.model.CacheResult;
import com.gamified.chat.model.UserRank;
import com.gamified.chat.repository.UserRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.annotation.Lazy;
import org.springframework.data.domain.PageRequest;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

@Service
public class LeaderboardService {

    private static final Logger log = LoggerFactory.getLogger(LeaderboardService.class);
    private static final String CACHE_KEY_LEADERBOARD_TOP = "leaderboard:top:";
    private static final String CACHE_KEY_USER_PREFIX = "leaderboard:user:";

    private final UserRepository userRepository;
    private final GamificationService gamificationService;
    private final InMemoryCacheService cacheService;
    private final SimpMessagingTemplate messagingTemplate;

    public LeaderboardService(
            UserRepository userRepository,
            GamificationService gamificationService,
            InMemoryCacheService cacheService,
            @Lazy SimpMessagingTemplate messagingTemplate) {
        this.userRepository = userRepository;
        this.gamificationService = gamificationService;
        this.cacheService = cacheService;
        this.messagingTemplate = messagingTemplate;
    }

    @Transactional
    public UserAccount getOrCreateUser(String username) {
        if (username == null || username.trim().isEmpty()) {
            username = "Anonymous";
        }
        final String finalUsername = username.trim();
        return userRepository.findByUsername(finalUsername).orElseGet(() -> {
            UserAccount newUser = new UserAccount(finalUsername);
            return userRepository.save(newUser);
        });
    }

    public CacheResult<List<UserRank>> getTopLeaderboard(int limit) {
        String cacheKey = CACHE_KEY_LEADERBOARD_TOP + limit;
        CacheResult<List<UserRank>> cached = cacheService.get(cacheKey);
        if (cached.isHit()) {
            return cached;
        }

        List<UserAccount> topUsers = userRepository.findTopRanked(PageRequest.of(0, limit));
        List<UserRank> ranks = new ArrayList<>();
        long currentRank = 1;
        for (UserAccount user : topUsers) {
            UserRank rank = mapToUserRank(user, currentRank++);
            ranks.add(rank);
        }

        cacheService.put(cacheKey, ranks, 15); // 15 seconds TTL
        return new CacheResult<>(ranks, false);
    }

    public CacheResult<UserRank> getUserRank(String username) {
        String cacheKey = CACHE_KEY_USER_PREFIX + username;
        CacheResult<UserRank> cached = cacheService.get(cacheKey);
        if (cached.isHit()) {
            return cached;
        }

        Optional<UserAccount> opt = userRepository.findByUsername(username);
        if (opt.isEmpty()) {
            return new CacheResult<>(null, false);
        }

        UserAccount user = opt.get();
        Long rankPosition = userRepository.findRankByUsername(username);
        if (rankPosition == null) rankPosition = 1L;

        UserRank userRank = mapToUserRank(user, rankPosition);
        cacheService.put(cacheKey, userRank, 30);
        return new CacheResult<>(userRank, false);
    }

    @Transactional
    public boolean recordMessageActivity(String username) {
        UserAccount user = getOrCreateUser(username);
        boolean leveledUp = gamificationService.applyMessageActivity(user);
        user.setUpdatedAt(Instant.now());
        userRepository.save(user);

        invalidateLeaderboardCache(username);
        broadcastLeaderboardUpdate();
        return leveledUp;
    }

    @Transactional
    public boolean recordStoryActivity(String username) {
        UserAccount user = getOrCreateUser(username);
        boolean leveledUp = gamificationService.applyStoryActivity(user);
        user.setUpdatedAt(Instant.now());
        userRepository.save(user);

        invalidateLeaderboardCache(username);
        broadcastLeaderboardUpdate();
        return leveledUp;
    }

    @Transactional
    public boolean addBonusPoints(String username, long bonusPoints) {
        UserAccount user = getOrCreateUser(username);
        boolean leveledUp = gamificationService.applyBonusPoints(user, bonusPoints);
        user.setUpdatedAt(Instant.now());
        userRepository.save(user);

        invalidateLeaderboardCache(username);
        broadcastLeaderboardUpdate();
        return leveledUp;
    }

    public void broadcastLeaderboardUpdate() {
        try {
            List<UserAccount> topUsers = userRepository.findTopRanked(PageRequest.of(0, 10));
            List<UserRank> ranks = new ArrayList<>();
            long currentRank = 1;
            for (UserAccount user : topUsers) {
                ranks.add(mapToUserRank(user, currentRank++));
            }
            messagingTemplate.convertAndSend("/topic/leaderboard", ranks);
        } catch (Exception e) {
            log.warn("Failed to broadcast leaderboard update via WebSocket: {}", e.getMessage());
        }
    }

    private void invalidateLeaderboardCache(String username) {
        cacheService.evict(CACHE_KEY_LEADERBOARD_TOP + "10");
        cacheService.evict(CACHE_KEY_LEADERBOARD_TOP + "25");
        cacheService.evict(CACHE_KEY_USER_PREFIX + username);
    }

    private UserRank mapToUserRank(UserAccount user, long rank) {
        UserRank r = new UserRank(
                rank,
                user.getUsername(),
                user.getScore(),
                user.getLevel(),
                user.getXp(),
                user.getMessagesCount(),
                user.getStoriesCount(),
                user.getAvatarUrl()
        );
        r.setBadges(gamificationService.determineBadges(user));
        return r;
    }
}
