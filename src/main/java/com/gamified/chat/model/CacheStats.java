package com.gamified.chat.model;

public class CacheStats {

    private long hits;
    private long misses;
    private long totalRequests;
    private double hitRatePercentage;
    private int currentSize;
    private int maxCapacity;
    private long evictions;

    public CacheStats() {}

    public CacheStats(long hits, long misses, int currentSize, int maxCapacity, long evictions) {
        this.hits = hits;
        this.misses = misses;
        this.totalRequests = hits + misses;
        this.hitRatePercentage = totalRequests > 0 ? ((double) hits / totalRequests) * 100.0 : 0.0;
        this.currentSize = currentSize;
        this.maxCapacity = maxCapacity;
        this.evictions = evictions;
    }

    public long getHits() {
        return hits;
    }

    public void setHits(long hits) {
        this.hits = hits;
    }

    public long getMisses() {
        return misses;
    }

    public void setMisses(long misses) {
        this.misses = misses;
    }

    public long getTotalRequests() {
        return totalRequests;
    }

    public void setTotalRequests(long totalRequests) {
        this.totalRequests = totalRequests;
    }

    public double getHitRatePercentage() {
        return hitRatePercentage;
    }

    public void setHitRatePercentage(double hitRatePercentage) {
        this.hitRatePercentage = hitRatePercentage;
    }

    public int getCurrentSize() {
        return currentSize;
    }

    public void setCurrentSize(int currentSize) {
        this.currentSize = currentSize;
    }

    public int getMaxCapacity() {
        return maxCapacity;
    }

    public void setMaxCapacity(int maxCapacity) {
        this.maxCapacity = maxCapacity;
    }

    public long getEvictions() {
        return evictions;
    }

    public void setEvictions(long evictions) {
        this.evictions = evictions;
    }
}
