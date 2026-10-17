package com.gamified.chat.model;

import java.util.ArrayList;
import java.util.List;

public class UserRank {

    private long rank;
    private String username;
    private long score;
    private int level;
    private long xp;
    private long messagesCount;
    private long storiesCount;
    private String avatarUrl;
    private List<String> badges = new ArrayList<>();

    public UserRank() {}

    public UserRank(long rank, String username, long score, int level, long xp, long messagesCount, long storiesCount, String avatarUrl) {
        this.rank = rank;
        this.username = username;
        this.score = score;
        this.level = level;
        this.xp = xp;
        this.messagesCount = messagesCount;
        this.storiesCount = storiesCount;
        this.avatarUrl = avatarUrl;
    }

    public long getRank() {
        return rank;
    }

    public void setRank(long rank) {
        this.rank = rank;
    }

    public String getUsername() {
        return username;
    }

    public void setUsername(String username) {
        this.username = username;
    }

    public long getScore() {
        return score;
    }

    public void setScore(long score) {
        this.score = score;
    }

    public int getLevel() {
        return level;
    }

    public void setLevel(int level) {
        this.level = level;
    }

    public long getXp() {
        return xp;
    }

    public void setXp(long xp) {
        this.xp = xp;
    }

    public long getMessagesCount() {
        return messagesCount;
    }

    public void setMessagesCount(long messagesCount) {
        this.messagesCount = messagesCount;
    }

    public long getStoriesCount() {
        return storiesCount;
    }

    public void setStoriesCount(long storiesCount) {
        this.storiesCount = storiesCount;
    }

    public String getAvatarUrl() {
        return avatarUrl;
    }

    public void setAvatarUrl(String avatarUrl) {
        this.avatarUrl = avatarUrl;
    }

    public List<String> getBadges() {
        return badges;
    }

    public void setBadges(List<String> badges) {
        this.badges = badges;
    }
}
