package com.gamified.chat.repository;

import com.gamified.chat.entity.UserAccount;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface UserRepository extends JpaRepository<UserAccount, Long> {

    Optional<UserAccount> findByUsername(String username);

    @Query("SELECT u FROM UserAccount u ORDER BY u.score DESC, u.xp DESC, u.createdAt ASC")
    List<UserAccount> findTopRanked(Pageable pageable);

    @Query("SELECT COUNT(u) + 1 FROM UserAccount u WHERE u.score > (SELECT target.score FROM UserAccount target WHERE target.username = :username)")
    Long findRankByUsername(String username);
}
