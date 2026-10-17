package com.gamified.chat.model;

public class CacheResult<T> {

    private final T data;
    private final boolean hit;

    public CacheResult(T data, boolean hit) {
        this.data = data;
        this.hit = hit;
    }

    public T getData() {
        return data;
    }

    public boolean isHit() {
        return hit;
    }

    public String getHeaderValue() {
        return hit ? "HIT" : "MISS";
    }
}
