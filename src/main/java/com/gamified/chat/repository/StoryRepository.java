package com.gamified.chat.repository;

import com.gamified.chat.entity.StoryEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.List;

@Repository
public interface StoryRepository extends JpaRepository<StoryEntity, Long> {

    @Query("SELECT s FROM StoryEntity s WHERE s.expiresAt > :now ORDER BY s.createdAt DESC")
    List<StoryEntity> findActiveStories(Instant now);

    List<StoryEntity> findByUsernameAndExpiresAtAfterOrderByCreatedAtDesc(String username, Instant now);

    long deleteByExpiresAtBefore(Instant now);
}
