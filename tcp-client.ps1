# Real-Time TCP Chat Client for Windows PowerShell
$hostName = "127.0.0.1"
$port = 8888

Write-Host "Connecting to TCP Chat Server at ${hostName}:${port}..." -ForegroundColor Cyan

try {
    $client = New-Object System.Net.Sockets.TcpClient($hostName, $port)
    $stream = $client.GetStream()
    $reader = New-Object System.IO.StreamReader($stream)
    $writer = New-Object System.IO.StreamWriter($stream)
    $writer.AutoFlush = $true
} catch {
    Write-Host "Failed to connect to TCP server: $_" -ForegroundColor Red
    exit
}

# Start background reader job
$runspace = [runspacefactory]::CreateRunspace()
$runspace.Open()
$powershell = [powershell]::Create()
$powershell.Runspace = $runspace
$powershell.AddScript({
    param($stream)
    $reader = New-Object System.IO.StreamReader($stream)
    while ($true) {
        $line = $reader.ReadLine()
        if ($line -eq $null) { break }
        Write-Host $line
    }
}).AddArgument($stream) | Out-Null
$powershell.BeginInvoke() | Out-Null

Write-Host "Connected! Enter commands (e.g. /nick MyName, /leaderboard, /help):" -ForegroundColor Green

try {
    while ($client.Connected) {
        $inputMsg = Read-Host
        if ($inputMsg -eq "/quit" -or $inputMsg -eq "/exit") {
            $writer.WriteLine($inputMsg)
            break
        }
        $writer.WriteLine($inputMsg)
    }
} finally {
    $client.Close()
    Write-Host "Disconnected from TCP server." -ForegroundColor Yellow
}
