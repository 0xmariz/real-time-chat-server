package com.gamified.chat.service;

import com.gamified.chat.entity.UserAccount;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;

@Service
public class GamificationService {

    private final long xpPerMessage;
    private final long xpPerStory;
    private final long levelMultiplier;

    public GamificationService(
            @Value("${gamification.xp-per-message:10}") long xpPerMessage,
            @Value("${gamification.xp-per-story:50}") long xpPerStory,
            @Value("${gamification.level-threshold-multiplier:100}") long levelMultiplier) {
        this.xpPerMessage = xpPerMessage;
        this.xpPerStory = xpPerStory;
        this.levelMultiplier = levelMultiplier;
    }

    public long getXpPerMessage() {
        return xpPerMessage;
    }

    public long getXpPerStory() {
        return xpPerStory;
    }

    public int calculateLevel(long xp) {
        if (xp <= 0) return 1;
        return (int) (1 + (xp / levelMultiplier));
    }

    public boolean applyMessageActivity(UserAccount user) {
        int oldLevel = user.getLevel();
        user.setMessagesCount(user.getMessagesCount() + 1);
        user.setXp(user.getXp() + xpPerMessage);
        user.setScore(user.getScore() + xpPerMessage);

        int newLevel = calculateLevel(user.getXp());
        user.setLevel(newLevel);
        return newLevel > oldLevel;
    }

    public boolean applyStoryActivity(UserAccount user) {
        int oldLevel = user.getLevel();
        user.setStoriesCount(user.getStoriesCount() + 1);
        user.setXp(user.getXp() + xpPerStory);
        user.setScore(user.getScore() + xpPerStory);

        int newLevel = calculateLevel(user.getXp());
        user.setLevel(newLevel);
        return newLevel > oldLevel;
    }

    public boolean applyBonusPoints(UserAccount user, long bonusPoints) {
        int oldLevel = user.getLevel();
        user.setScore(user.getScore() + bonusPoints);
        user.setXp(user.getXp() + bonusPoints);
        int newLevel = calculateLevel(user.getXp());
        user.setLevel(newLevel);
        return newLevel > oldLevel;
    }

    public List<String> determineBadges(UserAccount user) {
        List<String> badges = new ArrayList<>();
        badges.add("🌟 Pioneer");

        if (user.getMessagesCount() >= 5) {
            badges.add("💬 Chatterbox");
        }
        if (user.getMessagesCount() >= 25) {
            badges.add("⚡ Chat Master");
        }
        if (user.getStoriesCount() >= 1) {
            badges.add("📸 Storyteller");
        }
        if (user.getScore() >= 100) {
            badges.add("💎 Century Club");
        }
        if (user.getScore() >= 500) {
            badges.add("👑 High Roller");
        }
        if (user.getLevel() >= 5) {
            badges.add("🏆 Grandmaster");
        }
        return badges;
    }
}
