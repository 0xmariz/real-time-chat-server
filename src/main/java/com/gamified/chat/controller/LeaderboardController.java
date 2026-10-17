package com.gamified.chat.controller;

import com.gamified.chat.cache.InMemoryCacheService;
import com.gamified.chat.model.CacheResult;
import com.gamified.chat.model.CacheStats;
import com.gamified.chat.model.UserRank;
import com.gamified.chat.service.LeaderboardService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api")
@CrossOrigin(origins = "*")
public class LeaderboardController {

    private final LeaderboardService leaderboardService;
    private final InMemoryCacheService cacheService;

    public LeaderboardController(LeaderboardService leaderboardService, InMemoryCacheService cacheService) {
        this.leaderboardService = leaderboardService;
        this.cacheService = cacheService;
    }

    @GetMapping("/leaderboard/top")
    public ResponseEntity<List<UserRank>> getTopLeaderboard(
            @RequestParam(defaultValue = "10") int limit) {
        CacheResult<List<UserRank>> result = leaderboardService.getTopLeaderboard(limit);
        return ResponseEntity.ok()
                .header("X-Cache", result.getHeaderValue())
                .body(result.getData());
    }

    @GetMapping("/leaderboard/user/{username}")
    public ResponseEntity<?> getUserRank(@PathVariable String username) {
        CacheResult<UserRank> result = leaderboardService.getUserRank(username);
        if (result.getData() == null) {
            return ResponseEntity.notFound()
                    .header("X-Cache", result.getHeaderValue())
                    .build();
        }
        return ResponseEntity.ok()
                .header("X-Cache", result.getHeaderValue())
                .body(result.getData());
    }

    @PostMapping("/leaderboard/bonus")
    public ResponseEntity<?> addBonusScore(@RequestBody Map<String, Object> payload) {
        String username = (String) payload.get("username");
        Number pointsNum = (Number) payload.get("points");

        if (username == null || pointsNum == null) {
            return ResponseEntity.badRequest().body(Map.of("error", "username and points required"));
        }

        boolean leveledUp = leaderboardService.addBonusPoints(username, pointsNum.longValue());
        return ResponseEntity.ok(Map.of(
                "success", true,
                "username", username,
                "pointsAdded", pointsNum.longValue(),
                "leveledUp", leveledUp
        ));
    }

    @GetMapping("/cache/stats")
    public ResponseEntity<CacheStats> getCacheStats() {
        return ResponseEntity.ok(cacheService.getStats());
    }

    @PostMapping("/cache/clear")
    public ResponseEntity<?> clearCache() {
        cacheService.clear();
        return ResponseEntity.ok(Map.of("message", "Cache cleared successfully", "status", "SUCCESS"));
    }
}
