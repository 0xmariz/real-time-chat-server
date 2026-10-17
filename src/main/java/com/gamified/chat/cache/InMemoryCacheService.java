package com.gamified.chat.cache;

import com.gamified.chat.model.CacheResult;
import com.gamified.chat.model.CacheStats;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.locks.ReentrantReadWriteLock;

@Service
public class InMemoryCacheService {

    private static final Logger log = LoggerFactory.getLogger(InMemoryCacheService.class);

    private final int maxEntries;
    private final long defaultTtlSeconds;

    private final AtomicLong hits = new AtomicLong(0);
    private final AtomicLong misses = new AtomicLong(0);
    private final AtomicLong evictions = new AtomicLong(0);

    private final ReentrantReadWriteLock lock = new ReentrantReadWriteLock();

    private static class CacheEntry {
        final Object value;
        final Instant expiresAt;

        CacheEntry(Object value, long ttlSeconds) {
            this.value = value;
            this.expiresAt = Instant.now().plusSeconds(ttlSeconds);
        }

        boolean isExpired() {
            return Instant.now().isAfter(expiresAt);
        }
    }

    private final LinkedHashMap<String, CacheEntry> cache;

    public InMemoryCacheService(
            @Value("${cache.max-entries:1000}") int maxEntries,
            @Value("${cache.ttl-seconds:60}") long defaultTtlSeconds) {
        this.maxEntries = maxEntries;
        this.defaultTtlSeconds = defaultTtlSeconds;

        // true = access-order for LRU
        this.cache = new LinkedHashMap<String, CacheEntry>(maxEntries, 0.75f, true) {
            @Override
            protected boolean removeEldestEntry(Map.Entry<String, CacheEntry> eldest) {
                if (size() > InMemoryCacheService.this.maxEntries) {
                    evictions.incrementAndGet();
                    return true;
                }
                return false;
            }
        };
    }

    @SuppressWarnings("unchecked")
    public <T> CacheResult<T> get(String key) {
        lock.readLock().lock();
        try {
            CacheEntry entry = cache.get(key);
            if (entry != null && !entry.isExpired()) {
                hits.incrementAndGet();
                return new CacheResult<>((T) entry.value, true);
            }
        } finally {
            lock.readLock().unlock();
        }

        // If expired or missing:
        lock.writeLock().lock();
        try {
            CacheEntry entry = cache.get(key);
            if (entry != null && entry.isExpired()) {
                cache.remove(key);
                evictions.incrementAndGet();
            }
            misses.incrementAndGet();
            return new CacheResult<>(null, false);
        } finally {
            lock.writeLock().unlock();
        }
    }

    public void put(String key, Object value) {
        put(key, value, this.defaultTtlSeconds);
    }

    public void put(String key, Object value, long ttlSeconds) {
        if (key == null || value == null) return;
        lock.writeLock().lock();
        try {
            cache.put(key, new CacheEntry(value, ttlSeconds));
        } finally {
            lock.writeLock().unlock();
        }
    }

    public void evict(String key) {
        lock.writeLock().lock();
        try {
            cache.remove(key);
        } finally {
            lock.writeLock().unlock();
        }
    }

    public void clear() {
        lock.writeLock().lock();
        try {
            cache.clear();
            log.info("In-memory cache cleared successfully");
        } finally {
            lock.writeLock().unlock();
        }
    }

    public CacheStats getStats() {
        lock.readLock().lock();
        try {
            return new CacheStats(
                    hits.get(),
                    misses.get(),
                    cache.size(),
                    maxEntries,
                    evictions.get()
            );
        } finally {
            lock.readLock().unlock();
        }
    }
}
