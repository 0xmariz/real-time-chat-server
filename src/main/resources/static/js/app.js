// ============================================================================
// Real-Time Gamified Chat & Leaderboard Arena Engine
// ============================================================================

let stompClient = null;
let currentUsername = null;
let currentRoom = "public";
let userLevel = 1;
let userScore = 0;
let userXp = 0;

// Stories state
let activeStories = [];
let currentStoryIndex = 0;
let storyTimer = null;

// Initialize on page load
document.addEventListener("DOMContentLoaded", () => {
    initUserSession();
    connectWebSocket();
    loadLeaderboard();
    loadActiveStories();
    loadCacheTelemetry();
    setupEventListeners();
});

// ============================================================================
// 1. User Session & Authentication
// ============================================================================
function initUserSession() {
    const stored = localStorage.getItem('nexus_username');
    if (!stored) {
        // No session — redirect to login page
        window.location.href = '/login';
        return;
    }
    currentUsername = stored;
    const level = parseInt(localStorage.getItem('nexus_level') || '1', 10);
    const score = parseInt(localStorage.getItem('nexus_score') || '0', 10);
    const xp    = parseInt(localStorage.getItem('nexus_xp')    || '0', 10);
    updateUserCard(currentUsername, level, score, xp);
}

function updateUserCard(username, level, score, xp) {
    userLevel = level;
    userScore = score;
    userXp = xp;

    document.getElementById("headerUsername").textContent = username;
    document.getElementById("headerLevelBadge").textContent = "Lv." + level;
    document.getElementById("headerUserAvatar").src = "https://api.dicebear.com/7.x/bottts/svg?seed=" + encodeURIComponent(username);

    const xpNext = level * 100;
    const xpCurrentInLevel = xp % 100;
    const pct = Math.min(100, Math.max(5, (xpCurrentInLevel / 100) * 100));

    const fill = document.getElementById("headerXpFill");
    if (fill) fill.style.width = pct + "%";
    const txt = document.getElementById("headerXpText");
    if (txt) txt.textContent = score + " pts";
}

// ============================================================================
// 2. WebSocket & STOMP Protocol
// ============================================================================
function connectWebSocket() {
    const socket = new SockJS('/ws');
    stompClient = Stomp.over(socket);
    stompClient.debug = null; // Quiet console in production

    stompClient.connect({}, (frame) => {
        document.getElementById("wsStatusBadge").className = "status-badge ws";
        document.getElementById("wsStatusBadge").innerHTML = '<span class="status-pulse"></span> WS: Connected';

        // 1. Subscribe to public chat
        stompClient.subscribe('/topic/public', (msg) => {
            const data = JSON.parse(msg.body);
            handleIncomingMessage(data);
        });

        // 2. Subscribe to live leaderboard
        stompClient.subscribe('/topic/leaderboard', (msg) => {
            const ranks = JSON.parse(msg.body);
            renderLeaderboard(ranks, "WebSocket Broadcast");
        });

        // 3. Subscribe to stories stream
        stompClient.subscribe('/topic/stories', (msg) => {
            const newStory = JSON.parse(msg.body);
            onNewStoryReceived(newStory);
        });

        // 4. Subscribe to private messages queue
        stompClient.subscribe('/user/' + currentUsername + '/queue/private', (msg) => {
            const data = JSON.parse(msg.body);
            handleIncomingMessage(data);
        });

        // Register user with server
        stompClient.send("/app/chat.addUser", {}, JSON.stringify({
            sender: currentUsername,
            type: 'JOIN'
        }));

        // Refresh stats from server (authoritative)
        fetchUserStats(currentUsername);

        // Load message history for the current room
        loadRoomHistory(currentRoom);
    }, (error) => {
        console.error("WebSocket connection error:", error);
        document.getElementById("wsStatusBadge").className = "status-badge";
        document.getElementById("wsStatusBadge").innerHTML = '<span class="status-pulse" style="background:red"></span> WS: Disconnected';
        setTimeout(connectWebSocket, 4000); // Reconnect
    });
}

// ============================================================================
// 3. Chat Messaging & UI
// ============================================================================
function handleIncomingMessage(msg) {
    const chatContainer = document.getElementById("chatMessages");
    if (!chatContainer) return;

    if (msg.type === "LEVEL_UP") {
        renderEventBanner(msg.content, "levelup");
        fetchUserStats(currentUsername);
        return;
    }

    if (msg.type === "STORY_ALERT") {
        renderEventBanner(msg.content, "story");
        return;
    }

    if (msg.type === "JOIN" || msg.type === "LEAVE") {
        renderEventBanner(msg.content || (msg.sender + " " + (msg.type === "JOIN" ? "joined" : "left")), "system");
        return;
    }

    // Standard Chat or Private Message
    const isSelf = msg.sender === currentUsername;
    const card = document.createElement("div");
    card.className = "message-card" + (isSelf ? " outgoing" : "");

    const avatarUrl = msg.avatarUrl || ("https://api.dicebear.com/7.x/bottts/svg?seed=" + encodeURIComponent(msg.sender));
    const timeFormatted = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    card.innerHTML = `
        <img src="${avatarUrl}" class="msg-avatar" alt="${msg.sender}">
        <div class="msg-body">
            <div class="msg-header">
                <span class="msg-author">${msg.sender}</span>
                <span class="msg-lvl">Lv.${msg.userLevel || 1}</span>
                <span class="msg-time">${timeFormatted}</span>
            </div>
            <div class="msg-bubble">
                ${escapeHtml(msg.content)}
                ${isSelf ? '<span class="xp-badge-floater">+10 XP</span>' : ''}
            </div>
        </div>
    `;

    chatContainer.appendChild(card);
    chatContainer.scrollTop = chatContainer.scrollHeight;

    if (isSelf) {
        userScore += 10;
        userXp += 10;
        updateUserCard(currentUsername, userLevel, userScore, userXp);
    }
}

function renderEventBanner(text, type) {
    const chatContainer = document.getElementById("chatMessages");
    const banner = document.createElement("div");
    banner.className = "event-banner " + type;
    banner.textContent = text;
    chatContainer.appendChild(banner);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// Load up to 50 persisted messages for a room from the database
function loadRoomHistory(roomId) {
    const chatContainer = document.getElementById("chatMessages");
    // Clear existing messages (keep welcome banner)
    chatContainer.innerHTML = '';
    renderEventBanner('📜 Loading message history for #' + roomId + '...', 'system');

    fetch('/api/chat/history/' + encodeURIComponent(roomId))
        .then(res => res.json())
        .then(messages => {
            // Remove loading banner
            chatContainer.innerHTML = '';
            if (messages.length === 0) {
                renderEventBanner('🚀 No messages yet in #' + roomId + '. Be the first to chat! (+10 XP)', 'system');
                return;
            }
            renderEventBanner('📜 Last ' + messages.length + ' messages in #' + roomId + ':', 'system');
            messages.forEach(m => {
                renderHistoryMessage(m);
            });
            chatContainer.scrollTop = chatContainer.scrollHeight;
        })
        .catch(() => {
            chatContainer.innerHTML = '';
            renderEventBanner('🚀 Server ready! Chatting awards +10 XP.', 'system');
        });
}

function renderHistoryMessage(m) {
    const chatContainer = document.getElementById('chatMessages');
    const isSelf = m.sender === currentUsername;
    const card = document.createElement('div');
    card.className = 'message-card' + (isSelf ? ' outgoing' : '') + ' history-msg';

    const avatarUrl = m.avatarUrl || ('https://api.dicebear.com/7.x/bottts/svg?seed=' + encodeURIComponent(m.sender));
    const ts = m.timestamp ? new Date(m.timestamp) : new Date();
    const timeFormatted = ts.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    card.innerHTML = `
        <img src="${avatarUrl}" class="msg-avatar" alt="${m.sender}">
        <div class="msg-body">
            <div class="msg-header">
                <span class="msg-author">${escapeHtml(m.sender)}</span>
                <span class="msg-time" style="opacity:0.5">${timeFormatted}</span>
            </div>
            <div class="msg-bubble" style="opacity:0.8">${escapeHtml(m.content)}</div>
        </div>
    `;
    chatContainer.appendChild(card);
}

function sendMessage() {
    const input = document.getElementById("chatInput");
    const text = input.value.trim();
    if (!text || !stompClient) return;

    input.value = "";

    // Check whisper command
    if (text.startsWith("/whisper ") || text.startsWith("/w ")) {
        const parts = text.split(" ");
        if (parts.length >= 3) {
            const target = parts[1];
            const content = parts.slice(2).join(" ");
            stompClient.send("/app/chat.sendPrivateMessage", {}, JSON.stringify({
                sender: currentUsername,
                recipient: target,
                content: content,
                type: 'PRIVATE'
            }));
            return;
        }
    }

    // Send public or room message
    if (currentRoom === "public") {
        stompClient.send("/app/chat.sendMessage", {}, JSON.stringify({
            sender: currentUsername,
            content: text,
            type: 'CHAT'
        }));
    } else {
        stompClient.send("/app/chat.sendRoomMessage", {}, JSON.stringify({
            sender: currentUsername,
            roomId: currentRoom,
            content: text,
            type: 'CHAT'
        }));
    }
}

// ============================================================================
// 4. Real-Time Leaderboard System
// ============================================================================
function loadLeaderboard() {
    fetch('/api/leaderboard/top?limit=10')
        .then(res => {
            const cacheHeader = res.headers.get("X-Cache") || "MISS";
            return res.json().then(data => ({ data, cacheHeader }));
        })
        .then(({ data, cacheHeader }) => {
            renderLeaderboard(data, cacheHeader);
        })
        .catch(err => console.error("Failed to load leaderboard:", err));
}

function renderLeaderboard(ranks, cacheStatus) {
    if (!ranks || !Array.isArray(ranks)) return;

    // 1. Render Top 3 Podium
    const p1 = ranks[0] || { username: "---", score: 0, level: 1 };
    const p2 = ranks[1] || { username: "---", score: 0, level: 1 };
    const p3 = ranks[2] || { username: "---", score: 0, level: 1 };

    document.getElementById("podium1Name").textContent = p1.username;
    document.getElementById("podium1Score").textContent = p1.score + " pts";
    document.getElementById("podium1Avatar").src = "https://api.dicebear.com/7.x/bottts/svg?seed=" + encodeURIComponent(p1.username);

    document.getElementById("podium2Name").textContent = p2.username;
    document.getElementById("podium2Score").textContent = p2.score + " pts";
    document.getElementById("podium2Avatar").src = "https://api.dicebear.com/7.x/bottts/svg?seed=" + encodeURIComponent(p2.username);

    document.getElementById("podium3Name").textContent = p3.username;
    document.getElementById("podium3Score").textContent = p3.score + " pts";
    document.getElementById("podium3Avatar").src = "https://api.dicebear.com/7.x/bottts/svg?seed=" + encodeURIComponent(p3.username);

    // 2. Render Ranks #4 to #10
    const listContainer = document.getElementById("leaderboardList");
    listContainer.innerHTML = "";

    ranks.slice(3).forEach(r => {
        const row = document.createElement("div");
        row.className = "leaderboard-row";
        const badgesHtml = (r.badges || []).slice(0, 2).map(b => `<span>${b}</span>`).join(" ");

        row.innerHTML = `
            <span class="leaderboard-rank">#${r.rank}</span>
            <img src="${r.avatarUrl || 'https://api.dicebear.com/7.x/bottts/svg?seed=' + encodeURIComponent(r.username)}" class="leaderboard-avatar" alt="">
            <div class="leaderboard-details">
                <span class="leaderboard-user">${r.username} <small style="color:var(--accent-gold)">Lv.${r.level}</small></span>
                <span class="leaderboard-badges">${badgesHtml}</span>
            </div>
            <div class="leaderboard-score-wrap">
                <span class="leaderboard-score">${r.score}</span>
                <span class="leaderboard-pts">pts</span>
            </div>
        `;
        listContainer.appendChild(row);
    });

    // Update Cache badge
    const badge = document.getElementById("leaderboardCacheBadge");
    if (badge) {
        badge.textContent = cacheStatus.includes("HIT") ? "⚡ Cache HIT" : "🔄 Live Sync";
        badge.style.color = cacheStatus.includes("HIT") ? "var(--accent-emerald)" : "var(--accent-cyan)";
    }
}

// ============================================================================
// 5. 24-Hour Stories Feature (Instagram Clone)
// ============================================================================
function loadActiveStories() {
    fetch('/api/stories/active')
        .then(res => res.json())
        .then(stories => {
            activeStories = stories || [];
            renderStoriesBar();
        })
        .catch(err => console.error("Failed to fetch stories:", err));
}

function renderStoriesBar() {
    const bar = document.getElementById("storiesBar");
    if (!bar) return;

    // Keep add story button
    bar.innerHTML = `
        <div class="story-circle-item" onclick="openCreateStoryModal()">
            <div class="story-ring add-story">
                <div class="add-story-btn">+</div>
            </div>
            <span class="story-name">Add Story</span>
        </div>
    `;

    activeStories.forEach((story, idx) => {
        const item = document.createElement("div");
        item.className = "story-circle-item";
        item.onclick = () => openStoryViewer(idx);

        const hoursLeft = Math.floor(story.secondsRemaining / 3600);
        item.innerHTML = `
            <div class="story-ring">
                <img src="${story.avatarUrl}" class="story-avatar" alt="${story.username}">
            </div>
            <span class="story-name">${story.username}</span>
        `;
        bar.appendChild(item);
    });
}

function onNewStoryReceived(story) {
    activeStories.unshift(story);
    renderStoriesBar();
}

function openCreateStoryModal() {
    document.getElementById("storyCaptionInput").value = "";
    document.getElementById("storyMediaInput").value = "";
    document.getElementById("createStoryModal").classList.add("active");
}

function closeCreateStoryModal() {
    document.getElementById("createStoryModal").classList.remove("active");
}

function submitNewStory() {
    const caption = document.getElementById("storyCaptionInput").value.trim();
    let mediaUrl = document.getElementById("storyMediaInput").value.trim();

    if (!mediaUrl) {
        // Pre-curate a beautiful vibrant wallpaper if left empty
        const presets = [
            "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=800",
            "https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=800",
            "https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?w=800"
        ];
        mediaUrl = presets[Math.floor(Math.random() * presets.length)];
    }

    fetch('/api/stories', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            username: currentUsername,
            content: caption,
            mediaUrl: mediaUrl
        })
    })
    .then(res => res.json())
    .then(newStory => {
        closeCreateStoryModal();
        userScore += 50;
        userXp += 50;
        updateUserCard(currentUsername, userLevel, userScore, userXp);
    })
    .catch(err => alert("Error posting story: " + err));
}

// Story Viewer
function openStoryViewer(index) {
    if (!activeStories[index]) return;
    currentStoryIndex = index;
    const modal = document.getElementById("storyViewerModal");
    modal.classList.add("active");
    showStorySlide(currentStoryIndex);
}

function closeStoryViewer() {
    clearInterval(storyTimer);
    document.getElementById("storyViewerModal").classList.remove("active");
}

function showStorySlide(index) {
    clearInterval(storyTimer);
    const story = activeStories[index];
    if (!story) {
        closeStoryViewer();
        return;
    }

    document.getElementById("viewerAvatar").src = story.avatarUrl;
    document.getElementById("viewerAuthor").textContent = story.username;
    document.getElementById("viewerImage").src = story.mediaUrl;
    document.getElementById("viewerCaption").textContent = story.content || "";
    document.getElementById("viewerViewCount").textContent = "👁️ " + story.viewCount + " views";

    // Record view
    fetch(`/api/stories/${story.id}/view`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ viewer: currentUsername })
    });

    // Auto-advance progress timer (5 seconds)
    const progressBar = document.getElementById("viewerProgressBar");
    progressBar.style.transition = 'none';
    progressBar.style.width = '0%';
    setTimeout(() => {
        progressBar.style.transition = 'width 5s linear';
        progressBar.style.width = '100%';
    }, 50);

    storyTimer = setTimeout(() => {
        if (currentStoryIndex < activeStories.length - 1) {
            currentStoryIndex++;
            showStorySlide(currentStoryIndex);
        } else {
            closeStoryViewer();
        }
    }, 5000);
}

function nextStory() {
    if (currentStoryIndex < activeStories.length - 1) {
        currentStoryIndex++;
        showStorySlide(currentStoryIndex);
    } else {
        closeStoryViewer();
    }
}

function prevStory() {
    if (currentStoryIndex > 0) {
        currentStoryIndex--;
        showStorySlide(currentStoryIndex);
    }
}

// ============================================================================
// 6. Caching Telemetry
// ============================================================================
function loadCacheTelemetry() {
    fetch('/api/cache/stats')
        .then(res => res.json())
        .then(stats => {
            document.getElementById("cacheHitsVal").textContent = stats.hits;
            document.getElementById("cacheMissesVal").textContent = stats.misses;
            document.getElementById("cacheRatioVal").textContent = (stats.hitRatePercentage || 0).toFixed(1) + "%";
            document.getElementById("cacheEntriesVal").textContent = stats.currentSize + " / " + stats.maxCapacity;
        })
        .catch(err => console.error("Cache stats fetch error:", err));
}

function clearCache() {
    fetch('/api/cache/clear', { method: 'POST' })
        .then(res => res.json())
        .then(res => {
            alert("Cache cleared successfully!");
            loadCacheTelemetry();
            loadLeaderboard();
        });
}

// ============================================================================
// 7. Database Backup Utility
// ============================================================================
function openBackupModal() {
    loadBackupsList();
    document.getElementById("backupModal").classList.add("active");
}

function closeBackupModal() {
    document.getElementById("backupModal").classList.remove("active");
}

function loadBackupsList() {
    const list = document.getElementById("backupsList");
    list.innerHTML = '<div style="color:var(--text-muted)">Loading backups...</div>';

    fetch('/api/backup/list')
        .then(res => res.json())
        .then(backups => {
            list.innerHTML = "";
            if (!backups || backups.length === 0) {
                list.innerHTML = '<div style="color:var(--text-muted)">No backups generated yet. Click "Create Instant Backup" below.</div>';
                return;
            }

            backups.forEach(b => {
                const item = document.createElement("div");
                item.className = "leaderboard-row";
                item.style.justifyContent = "space-between";
                item.innerHTML = `
                    <div>
                        <div style="font-weight:700;font-size:0.85rem">${b.filename}</div>
                        <div style="font-size:0.7rem;color:var(--text-muted)">Size: ${b.formattedSize} | Created: ${new Date(b.createdAt).toLocaleString()}</div>
                    </div>
                    <button class="nav-btn" style="padding:4px 10px;font-size:0.72rem" onclick="restoreBackup('${b.filename}')">Restore</button>
                `;
                list.appendChild(item);
            });
        });
}

function triggerInstantBackup() {
    fetch('/api/backup/create', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            alert("Database backup created successfully: " + data.filename);
            loadBackupsList();
        })
        .catch(err => alert("Backup error: " + err));
}

function restoreBackup(filename) {
    if (!confirm("Are you sure you want to restore the database from: " + filename + "? Current data will be merged/restored.")) return;

    fetch(`/api/backup/restore/${encodeURIComponent(filename)}`, { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            alert("Database restored successfully!");
            loadLeaderboard();
            loadActiveStories();
        })
        .catch(err => alert("Restore error: " + err));
}

// ============================================================================
// 8. TCP Terminal Guide Modal & Bonus XP
// ============================================================================
function openTcpGuideModal() {
    document.getElementById("tcpGuideModal").classList.add("active");
}

function closeTcpGuideModal() {
    document.getElementById("tcpGuideModal").classList.remove("active");
}

function addBonusXp() {
    fetch('/api/leaderboard/bonus', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: currentUsername, points: 50 })
    })
    .then(res => res.json())
    .then(res => {
        userScore += 50;
        userXp += 50;
        updateUserCard(currentUsername, userLevel, userScore, userXp);
    });
}

function fetchUserStats(username) {
    fetch(`/api/leaderboard/user/${encodeURIComponent(username)}`)
        .then(res => res.json())
        .then(user => {
            if (user) {
                updateUserCard(user.username, user.level, user.score, user.xp);
                // Persist authoritative values from server
                localStorage.setItem('nexus_level', user.level);
                localStorage.setItem('nexus_score', user.score);
                localStorage.setItem('nexus_xp', user.xp);
            }
        })
        .catch(err => {});
}

let currentRoomSubscription = null;

function switchRoom(roomId) {
    currentRoom = roomId;
    document.querySelectorAll(".channel-item").forEach(el => el.classList.remove("active"));
    const activeEl = document.getElementById("room-" + roomId);
    if (activeEl) activeEl.classList.add("active");

    if (currentRoomSubscription) {
        currentRoomSubscription.unsubscribe();
        currentRoomSubscription = null;
    }

    if (stompClient && roomId !== "public") {
        currentRoomSubscription = stompClient.subscribe('/topic/room/' + roomId, (msg) => {
            const data = JSON.parse(msg.body);
            handleIncomingMessage(data);
        });
        stompClient.send("/app/chat.joinRoom", {}, JSON.stringify({
            sender: currentUsername,
            roomId: roomId,
            type: 'JOIN'
        }));
    }

    // Load history for the new room from the database
    loadRoomHistory(roomId);
}

function promptCreateRoom() {
    const roomName = prompt("Enter new room name (alphanumeric):");
    if (roomName && roomName.trim()) {
        const cleanName = roomName.trim().toLowerCase().replace(/[^a-z0-9_-]/g, "");
        const channelList = document.getElementById("roomsChannelList");
        const li = document.createElement("li");
        li.className = "channel-item";
        li.id = "room-" + cleanName;
        li.onclick = () => switchRoom(cleanName);
        li.innerHTML = `<span class="channel-left">💬 #${cleanName}</span><span class="panel-badge">Custom</span>`;
        channelList.appendChild(li);
        switchRoom(cleanName);
    }
}

function changeUsername() {
    const newName = prompt("Enter your new player username:", currentUsername);
    if (newName && newName.trim() && newName.trim() !== currentUsername) {
        currentUsername = newName.trim();
        localStorage.setItem("nexus_username", currentUsername);
        updateUserCard(currentUsername, 1, 0, 0);
        if (stompClient) {
            stompClient.send("/app/chat.addUser", {}, JSON.stringify({
                sender: currentUsername,
                type: 'JOIN'
            }));
        }
        fetchUserStats(currentUsername);
    }
}

function logout() {
    if (!confirm('Are you sure you want to logout?')) return;
    // Clear all session keys
    ['nexus_username','nexus_avatarUrl','nexus_level','nexus_score','nexus_xp','nexus_guest']
        .forEach(k => localStorage.removeItem(k));
    window.location.href = '/login';
}

function loadSystemMetrics() {
    fetch('/api/system/metrics')
        .then(res => res.json())
        .then(metrics => {
            const cpuEl = document.getElementById("sysCpuVal");
            if (cpuEl) cpuEl.textContent = (metrics.cpuLoadPercent || 0).toFixed(1) + "%";

            const ramEl = document.getElementById("sysRamVal");
            if (ramEl) ramEl.textContent = metrics.usedMemoryMb + " / " + metrics.maxMemoryMb + " MB";

            const thrEl = document.getElementById("sysThreadsVal");
            if (thrEl) thrEl.textContent = metrics.activeThreads;

            const tcpEl = document.getElementById("sysTcpConnsVal");
            if (tcpEl) tcpEl.textContent = metrics.tcpConnections;

            const uptimeEl = document.getElementById("serverUptimeBadge");
            if (uptimeEl) uptimeEl.textContent = metrics.uptime;

            const dbStatusEl = document.getElementById("sysDbStatus");
            if (dbStatusEl) dbStatusEl.textContent = metrics.dbStatus;

            const dbCountsEl = document.getElementById("sysDbCounts");
            if (dbCountsEl && metrics.recordCounts) {
                dbCountsEl.textContent = `Users: ${metrics.recordCounts.users || 0} | Msgs: ${metrics.recordCounts.messages || 0} | Stories: ${metrics.recordCounts.stories || 0}`;
            }
        })
        .catch(err => {});
}

function setupEventListeners() {
    const chatInput = document.getElementById("chatInput");
    if (chatInput) {
        chatInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                sendMessage();
            }
        });
    }

    // Refresh telemetry and server load
    loadSystemMetrics();
    setInterval(loadSystemMetrics, 3000);
    setInterval(loadCacheTelemetry, 10000);
}

function escapeHtml(text) {
    if (!text) return "";
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
