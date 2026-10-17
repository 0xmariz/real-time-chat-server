package com.gamified.chat.repository;

import com.gamified.chat.entity.ChatMessageEntity;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface ChatMessageRepository extends JpaRepository<ChatMessageEntity, Long> {

    List<ChatMessageEntity> findByRoomIdOrderByTimestampDesc(String roomId, Pageable pageable);

    @Query("SELECT m FROM ChatMessageEntity m WHERE (m.sender = :user1 AND m.recipient = :user2) OR (m.sender = :user2 AND m.recipient = :user1) ORDER BY m.timestamp DESC")
    List<ChatMessageEntity> findDirectMessages(String user1, String user2, Pageable pageable);

    List<ChatMessageEntity> findTop50ByRoomIdOrderByTimestampAsc(String roomId);
}
