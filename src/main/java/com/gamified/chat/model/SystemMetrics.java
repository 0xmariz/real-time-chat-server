package com.gamified.chat.model;

import java.util.Map;

public class SystemMetrics {

    private double cpuLoadPercent;
    private long usedMemoryMb;
    private long maxMemoryMb;
    private double memoryUsagePercent;
    private int activeThreads;
    private int tcpConnections;
    private String dbStatus;
    private String uptime;
    private Map<String, Long> recordCounts;

    public SystemMetrics() {}

    public double getCpuLoadPercent() {
        return cpuLoadPercent;
    }

    public void setCpuLoadPercent(double cpuLoadPercent) {
        this.cpuLoadPercent = cpuLoadPercent;
    }

    public long getUsedMemoryMb() {
        return usedMemoryMb;
    }

    public void setUsedMemoryMb(long usedMemoryMb) {
        this.usedMemoryMb = usedMemoryMb;
    }

    public long getMaxMemoryMb() {
        return maxMemoryMb;
    }

    public void setMaxMemoryMb(long maxMemoryMb) {
        this.maxMemoryMb = maxMemoryMb;
    }

    public double getMemoryUsagePercent() {
        return memoryUsagePercent;
    }

    public void setMemoryUsagePercent(double memoryUsagePercent) {
        this.memoryUsagePercent = memoryUsagePercent;
    }

    public int getActiveThreads() {
        return activeThreads;
    }

    public void setActiveThreads(int activeThreads) {
        this.activeThreads = activeThreads;
    }

    public int getTcpConnections() {
        return tcpConnections;
    }

    public void setTcpConnections(int tcpConnections) {
        this.tcpConnections = tcpConnections;
    }

    public String getDbStatus() {
        return dbStatus;
    }

    public void setDbStatus(String dbStatus) {
        this.dbStatus = dbStatus;
    }

    public String getUptime() {
        return uptime;
    }

    public void setUptime(String uptime) {
        this.uptime = uptime;
    }

    public Map<String, Long> getRecordCounts() {
        return recordCounts;
    }

    public void setRecordCounts(Map<String, Long> recordCounts) {
        this.recordCounts = recordCounts;
    }
}
