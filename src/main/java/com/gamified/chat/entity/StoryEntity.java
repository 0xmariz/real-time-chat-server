package com.gamified.chat.entity;

import javax.persistence.*;
import java.time.Instant;
import java.time.temporal.ChronoUnit;

@Entity
@Table(name = "stories", indexes = {
    @Index(name = "idx_story_user", columnList = "username"),
    @Index(name = "idx_story_expires", columnList = "expires_at")
})
public class StoryEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 64)
    private String username;

    @Column(columnDefinition = "TEXT")
    private String content;

    @Column(columnDefinition = "TEXT", name = "media_url")
    private String mediaUrl;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    @Column(name = "expires_at", nullable = false)
    private Instant expiresAt = Instant.now().plus(24, ChronoUnit.HOURS);

    @Column(name = "view_count", nullable = false)
    private int viewCount = 0;

    @Column(columnDefinition = "TEXT", name = "viewers_csv")
    private String viewersCsv = "";

    public StoryEntity() {}

    public StoryEntity(String username, String content, String mediaUrl) {
        this.username = username;
        this.content = content;
        this.mediaUrl = mediaUrl;
        this.createdAt = Instant.now();
        this.expiresAt = this.createdAt.plus(24, ChronoUnit.HOURS);
        this.viewCount = 0;
        this.viewersCsv = "";
    }

    public boolean isExpired() {
        return Instant.now().isAfter(this.expiresAt);
    }

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getUsername() {
        return username;
    }

    public void setUsername(String username) {
        this.username = username;
    }

    public String getContent() {
        return content;
    }

    public void setContent(String content) {
        this.content = content;
    }

    public String getMediaUrl() {
        return mediaUrl;
    }

    public void setMediaUrl(String mediaUrl) {
        this.mediaUrl = mediaUrl;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(Instant createdAt) {
        this.createdAt = createdAt;
    }

    public Instant getExpiresAt() {
        return expiresAt;
    }

    public void setExpiresAt(Instant expiresAt) {
        this.expiresAt = expiresAt;
    }

    public int getViewCount() {
        return viewCount;
    }

    public void setViewCount(int viewCount) {
        this.viewCount = viewCount;
    }

    public String getViewersCsv() {
        return viewersCsv;
    }

    public void setViewersCsv(String viewersCsv) {
        this.viewersCsv = viewersCsv;
    }
}
