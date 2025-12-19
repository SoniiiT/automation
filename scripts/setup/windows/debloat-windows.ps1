<#
.SYNOPSIS
    Windows 11 Debloat Script
.DESCRIPTION
    This script removes bloatware, disables Edge (best effort), hides the Weather Widget,
    enables Dark Mode, and sets the Taskbar to Auto-Hide.
    Run as Administrator.
#>

# Check for Administrator privileges
if (!([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "Please run this script as Administrator!" -ForegroundColor Red
    Start-Sleep -Seconds 2
    Exit
}

Write-Host "Starting Windows 11 Debloat..." -ForegroundColor Cyan

# ---------------------------------------------------------
# 1. Remove Bloatware (Advanced)
# ---------------------------------------------------------
Write-Host "Removing Bloatware (User & System Provisioned)..." -ForegroundColor Yellow

# Define patterns to match unwanted apps
$bloatPatterns = @(
    "*BingNews*"
    "*BingWeather*"
    "*GamingApp*"
    "*GetHelp*"
    "*Getstarted*"
    "*Microsoft3DViewer*"
    "*MicrosoftOfficeHub*"
    "*SolitaireCollection*"
    "*NetworkSpeedTest*"
    "*News*"
    "*OneNote*"
    "*People*"
    "*PowerAutomateDesktop*"
    "*SkypeApp*"
    "*Todos*"
    "*WindowsAlarms*"
    "*WindowsCamera*"
    "*windowscommunicationsapps*"
    "*WindowsFeedbackHub*"
    "*WindowsMaps*"
    "*SoundRecorder*"
    "*Xbox*"
    "*YourPhone*"
    "*ZuneMusic*"
    "*ZuneVideo*"
    "*Cortana*"
    "*Clipchamp*"
    "*OutlookForWindows*"
    "*MicrosoftTeams*"
    "*MSTeams*"
    "*BingSearch*"
    "*DevHome*"
    "*CrossDevice*"       # Mobile Geräte
    "*Start.Experience*"  # Start Experience
    "*OneConnect*"        # Mobile Plans
    "*MixedReality*"
    "*PenSettings*"
    "*Microsoft.AsyncTextService*"
    "*GamingServices*"       # Gaming Services
    "*Start.Experience*"     # Start Experience
    "*StartExperience*"
    "*Microsoft.XboxGamingOverlay*" # Explicit Game Bar
    "*Microsoft.XboxGameOverlay*"
    "*Microsoft.Xbox.TCUI*"
    "*Microsoft.XboxSpeechToTextOverlay*"
    "*Microsoft.GamingApp*"
    "*Microsoft.XboxIdentityProvider*"
)

# Function to remove packages
function Remove-PackageByPattern {
    param ($pattern)
    
    # 1. Remove from Current/All Users (Installed)
    # Filter out known System Apps that cause errors to keep log clean
    $systemApps = @("Microsoft.Windows.PeopleExperienceHost", "Microsoft.AsyncTextService")
    
    $packages = Get-AppxPackage -Name $pattern -AllUsers -ErrorAction SilentlyContinue | Where-Object { $systemApps -notcontains $_.Name }
    
    foreach ($pkg in $packages) {
        Write-Host "Removing Appx: $($pkg.Name)..." -NoNewline
        try {
            $pkg | Remove-AppxPackage -AllUsers -ErrorAction Stop
            Write-Host " Done." -ForegroundColor Gray
        } catch {
            Write-Host " Failed (System Protected)." -ForegroundColor DarkGray
            # Try removing for current user only as fallback
            try {
                Get-AppxPackage -Name $pkg.Name | Remove-AppxPackage -ErrorAction Stop
                Write-Host " (Removed for Current User)" -ForegroundColor Gray
            } catch {
                # Ignore
            }
        }
    }
}

foreach ($pattern in $bloatPatterns) {
    Remove-PackageByPattern -pattern $pattern
}

# ---------------------------------------------------------
# 1.1 DISM Removal (Hardcore Mode for Provisioned Apps)
# ---------------------------------------------------------
Write-Host "Attempting removal via DISM (System Image)..." -ForegroundColor Yellow
foreach ($pattern in $bloatPatterns) {
    $provisioned = Get-AppxProvisionedPackage -Online | Where-Object { $_.DisplayName -like $pattern }
    foreach ($pkg in $provisioned) {
        Write-Host "DISM Removing: $($pkg.DisplayName)..." -NoNewline
        try {
            # Use cmd /c to ensure DISM runs correctly in PS environment
            $proc = Start-Process -FilePath "dism.exe" -ArgumentList "/Online /Remove-ProvisionedAppxPackage /PackageName:$($pkg.PackageName) /NoRestart" -Wait -PassThru -NoNewWindow
            if ($proc.ExitCode -eq 0) {
                Write-Host " Done." -ForegroundColor Gray
            } else {
                Write-Host " Failed (Exit Code: $($proc.ExitCode))." -ForegroundColor DarkGray
            }
        } catch {
            Write-Host " Failed." -ForegroundColor Red
        }
    }
}

# ---------------------------------------------------------
# 1.2 Clean Start Menu Shortcuts (Dead Pins & Edge)
# ---------------------------------------------------------
Write-Host "Cleaning Start Menu Shortcuts & Desktop (Deep Search)..." -ForegroundColor Yellow
$shortcutPaths = @(
    "$env:APPDATA\Microsoft\Windows\Start Menu\Programs",
    "$env:ProgramData\Microsoft\Windows\Start Menu\Programs",
    "$env:SystemDrive\Users\Default\AppData\Roaming\Microsoft\Windows\Start Menu\Programs",
    "$env:USERPROFILE\Desktop",
    "$env:PUBLIC\Desktop",
    "C:\ProgramData\Microsoft\Windows\Start Menu" # Broader scope
)
# Added "Edge" and "LinkedIn" explicitly to the kill list
$unwantedShortcuts = @("TikTok", "Instagram", "Facebook", "Twitter", "Solitaire", "Xbox", "Clipchamp", "Prime Video", "Disney+", "Spotify", "ESPN", "Spielassistent")

foreach ($path in $shortcutPaths) {
    if (Test-Path $path) {
        # Search recursively for .lnk files matching unwanted names
        Get-ChildItem -Path $path -Recurse -Include "*.lnk" -ErrorAction SilentlyContinue | ForEach-Object {
            $lnk = $_
            foreach ($bad in $unwantedShortcuts) {
                if ($lnk.Name -like "*$bad*") {
                    Write-Host "Removing Shortcut: $($lnk.FullName)..." -NoNewline
                    Remove-Item $lnk.FullName -Force -ErrorAction SilentlyContinue
                    Write-Host " Done." -ForegroundColor Gray
                }
            }
        }
    }
}

# Special handling for Edge Desktop Shortcut (Keep Start Menu, Remove Desktop)
$desktopPaths = @(
    "$env:USERPROFILE\Desktop",
    "$env:PUBLIC\Desktop"
)
foreach ($path in $desktopPaths) {
    if (Test-Path $path) {
        Get-ChildItem -Path $path -Filter "*Edge*.lnk" -ErrorAction SilentlyContinue | ForEach-Object {
            Write-Host "Removing Edge Desktop Shortcut: $($_.FullName)..." -NoNewline
            Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue
            Write-Host " Done." -ForegroundColor Gray
        }
    }
}

# ---------------------------------------------------------
# 1.3 Reset Start Menu Pins
# ---------------------------------------------------------
Write-Host "Resetting Start Menu Pins to remove ghost entries..." -ForegroundColor Yellow

# Stop StartMenuExperienceHost to unlock files
Stop-Process -Name "StartMenuExperienceHost" -Force -ErrorAction SilentlyContinue
Stop-Process -Name "explorer" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3

# Define a clean layout
$cleanLayoutJson = @'
{
  "pinnedList": [
    { "desktopAppId": "Microsoft.Windows.Explorer" },
    { "packagedAppId": "Microsoft.MicrosoftEdge.Stable_8wekyb3d8bbwe!App" },
    { "packagedAppId": "windows.immersivecontrolpanel_cw5n1h2txyewy!microsoft.windows.immersivecontrolpanel" },
    { "packagedAppId": "Microsoft.WindowsStore_8wekyb3d8bbwe!App" }
  ]
}
'@

# Path 1: StartMenuExperienceHost LocalState (Primary for Win11)
$startMenuPath = "$env:LOCALAPPDATA\Packages\Microsoft.Windows.StartMenuExperienceHost_cw5n1h2txyewy\LocalState"

# SCORCHED EARTH: Delete EVERYTHING in LocalState to force a full rebuild
if (Test-Path $startMenuPath) {
    Write-Host "Wiping Start Menu LocalState Database..." -ForegroundColor Red
    Get-ChildItem -Path $startMenuPath -Recurse -Force | Remove-Item -Force -Recurse -ErrorAction SilentlyContinue
} else {
    New-Item -Path $startMenuPath -ItemType Directory -Force | Out-Null
}

# Write the clean JSON to the now empty folder
$jsonPath1 = Join-Path $startMenuPath "LayoutModification.json"

# Remove existing file and ReadOnly attribute if present
if (Test-Path $jsonPath1) {
    $item = Get-Item $jsonPath1
    if ($item.IsReadOnly) { $item.IsReadOnly = $false }
    Remove-Item $jsonPath1 -Force
}

Write-Host "Writing Clean Layout to LocalState..." -ForegroundColor Green
$cleanLayoutJson | Out-File -FilePath $jsonPath1 -Encoding utf8 -Force

# LOCK THE FILE: Set ReadOnly to prevent Windows from overwriting it immediately
try {
    $fileItem = Get-Item $jsonPath1
    $fileItem.IsReadOnly = $true
    Write-Host "Locked LayoutModification.json (ReadOnly)" -ForegroundColor Green
} catch {
    Write-Host "Failed to lock LayoutModification.json" -ForegroundColor Red
}

# Path 2: Windows Shell (Fallback/Legacy)
$shellPath = "$env:LOCALAPPDATA\Microsoft\Windows\Shell"
if (!(Test-Path $shellPath)) { New-Item -Path $shellPath -ItemType Directory -Force | Out-Null }
$jsonPath2 = Join-Path $shellPath "LayoutModification.json"
Write-Host "Writing Clean Layout to Shell..." -ForegroundColor Green
$cleanLayoutJson | Out-File -FilePath $jsonPath2 -Encoding utf8 -Force
try {
    $fileItem2 = Get-Item $jsonPath2
    $fileItem2.IsReadOnly = $true
} catch {}

# Clear Suggested Apps from Registry (Iris Service)
$irisPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
New-ItemProperty -Path $irisPath -Name "Start_IrisRecommendations" -Value 0 -PropertyType DWord -Force | Out-Null

# Clear Suggested Apps from Registry (ContentDeliveryManager)
$suggestedAppsPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager\SuggestedApps"
if (Test-Path $suggestedAppsPath) {
    Remove-Item $suggestedAppsPath -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "Cleared SuggestedApps Registry Key" -ForegroundColor Gray
}

# Force overwrite Start Layout to blank to kill pinned ads
$layoutPath = "$env:LOCALAPPDATA\Microsoft\Windows\Shell\LayoutModification.xml"
if (Test-Path $layoutPath) {
    Remove-Item $layoutPath -Force -ErrorAction SilentlyContinue
}

# Disable Cloud Content (prevents re-downloading of ad pins)
$cloudContentPath = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\CloudContent"
if (!(Test-Path $cloudContentPath)) { New-Item -Path $cloudContentPath -Force | Out-Null }
New-ItemProperty -Path $cloudContentPath -Name "DisableWindowsConsumerFeatures" -Value 1 -PropertyType DWord -Force | Out-Null

# ---------------------------------------------------------
# 2. Remove/Disable Edge (Best Effort)
# ---------------------------------------------------------
Write-Host "Skipping Edge Removal as requested..." -ForegroundColor Yellow

# [DISABLED] Kill Edge Processes first
# Stop-Process -Name msedge -Force -ErrorAction SilentlyContinue
# Stop-Process -Name msedgewebview2 -Force -ErrorAction SilentlyContinue

# [DISABLED] 1. Try to force uninstall Edge via setup.exe if available
# ...

# [DISABLED] 2. Nuclear Option: Delete Edge Files (If uninstall failed/ignored)
# ...

# [DISABLED] 3. Block Edge via Registry (IEToEdge BHO)
# $edgeBlockPath = "HKLM:\SOFTWARE\Microsoft\EdgeUpdate"
# if (!(Test-Path $edgeBlockPath)) { New-Item -Path $edgeBlockPath -Force | Out-Null }
# New-ItemProperty -Path $edgeBlockPath -Name "DoNotUpdateToEdgeWithChromium" -Value 1 -PropertyType DWord -Force | Out-Null

# Disable Game Bar / Game DVR (Spielassistent)
Write-Host "Disabling Game Bar & Game DVR..." -ForegroundColor Yellow
$gameConfigPath = "HKCU:\System\GameConfigStore"
if (!(Test-Path $gameConfigPath)) { New-Item -Path $gameConfigPath -Force | Out-Null }
New-ItemProperty -Path $gameConfigPath -Name "GameDVR_Enabled" -Value 0 -PropertyType DWord -Force | Out-Null

$gamePolicyPath = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\GameDVR"
if (!(Test-Path $gamePolicyPath)) { New-Item -Path $gamePolicyPath -Force | Out-Null }
New-ItemProperty -Path $gamePolicyPath -Name "AllowGameDVR" -Value 0 -PropertyType DWord -Force | Out-Null

# Disable AppCapture (Additional Game Bar setting)
$gameDVRPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\GameDVR"
if (!(Test-Path $gameDVRPath)) { New-Item -Path $gameDVRPath -Force | Out-Null }
New-ItemProperty -Path $gameDVRPath -Name "AppCaptureEnabled" -Value 0 -PropertyType DWord -Force | Out-Null

# Additional Game Bar Registry Keys
$gameBarPath = "HKCU:\Software\Microsoft\GameBar"
if (!(Test-Path $gameBarPath)) { New-Item -Path $gameBarPath -Force | Out-Null }
New-ItemProperty -Path $gameBarPath -Name "AllowAutoGameMode" -Value 0 -PropertyType DWord -Force | Out-Null
New-ItemProperty -Path $gameBarPath -Name "AutoGameModeEnabled" -Value 0 -PropertyType DWord -Force | Out-Null
New-ItemProperty -Path $gameBarPath -Name "ShowStartupPanel" -Value 0 -PropertyType DWord -Force | Out-Null
New-ItemProperty -Path $gameBarPath -Name "UseNexusForGameBarEnabled" -Value 0 -PropertyType DWord -Force | Out-Null

# ---------------------------------------------------------
# 2.1 Clean Shortcuts for ALL Users (Aggressive)
# ---------------------------------------------------------
Write-Host "Scanning ALL User Profiles for stubborn shortcuts..." -ForegroundColor Yellow
$usersPath = "C:\Users"
if (Test-Path $usersPath) {
    $userFolders = Get-ChildItem -Path $usersPath -Directory
    foreach ($userFolder in $userFolders) {
        $desktopPath = Join-Path $userFolder.FullName "Desktop"
        $startMenuPath = Join-Path $userFolder.FullName "AppData\Roaming\Microsoft\Windows\Start Menu\Programs"
        
        $pathsToCheck = @($desktopPath, $startMenuPath)
        
        foreach ($path in $pathsToCheck) {
            if (Test-Path $path) {
                Get-ChildItem -Path $path -Recurse -Include "*.lnk" -ErrorAction SilentlyContinue | ForEach-Object {
                    $lnk = $_
                    foreach ($bad in $unwantedShortcuts) {
                        if ($lnk.Name -like "*$bad*") {
                            Write-Host "Removing Shortcut ($($userFolder.Name)): $($lnk.FullName)..." -NoNewline
                            Remove-Item $lnk.FullName -Force -ErrorAction SilentlyContinue
                            Write-Host " Done." -ForegroundColor Gray
                        }
                    }
                }
            }
        }
    }
}

# Specific Edge patterns to target (excluding System components)
# Write-Host "Attempting to remove Edge components..." -ForegroundColor Yellow

# [DISABLED] Specific Edge patterns to target (excluding System components)
# $edgePatterns = @(
#     "*MicrosoftEdge.Stable*"
#     "*MicrosoftEdge*" # Will be filtered
# )

# $edgePackages = Get-AppxPackage *MicrosoftEdge* -AllUsers | Where-Object { 
#     $_.Name -notlike "*DevToolsClient*" -and 
#     $_.Name -notlike "*WebView2*" -and 
#     $_.Name -notlike "*System*" -and
#     $_.NonRemovable -eq $false
# }

# if ($edgePackages) {
#     foreach ($pkg in $edgePackages) {
#         Write-Host "Removing Edge Component: $($pkg.Name)..." -NoNewline
#         try {
#             $pkg | Remove-AppxPackage -AllUsers -ErrorAction Stop
#             Write-Host " Done." -ForegroundColor Gray
#         } catch {
#             Write-Host " Failed (System Protected)." -ForegroundColor DarkGray
#         }
#     }
# } else {
#     Write-Host "No removable Edge Appx packages found." -ForegroundColor Gray
# }

# [DISABLED] Disable Edge Pre-launch via Registry
# $edgePolicyPath = "HKLM:\SOFTWARE\Policies\Microsoft\MicrosoftEdge\Main"
# if (!(Test-Path $edgePolicyPath)) { New-Item -Path $edgePolicyPath -Force | Out-Null }
# New-ItemProperty -Path $edgePolicyPath -Name "AllowPrelaunch" -Value 0 -PropertyType DWord -Force | Out-Null

# $edgeTabPath = "HKLM:\SOFTWARE\Policies\Microsoft\MicrosoftEdge\TabPreloader"
# if (!(Test-Path $edgeTabPath)) { New-Item -Path $edgeTabPath -Force | Out-Null }
# New-ItemProperty -Path $edgeTabPath -Name "AllowTabPreloading" -Value 0 -PropertyType DWord -Force | Out-Null

# ---------------------------------------------------------
# 3. Disable Widgets (Weather)
# ---------------------------------------------------------
Write-Host "Disabling Widgets/Weather..." -ForegroundColor Yellow
# Hide from Taskbar (Current User)
New-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" -Name "TaskbarDa" -Value 0 -PropertyType DWord -Force | Out-Null

# Disable via Policy (Machine)
$dshPath = "HKLM:\SOFTWARE\Policies\Microsoft\Dsh"
if (!(Test-Path $dshPath)) { New-Item -Path $dshPath -Force | Out-Null }
New-ItemProperty -Path $dshPath -Name "AllowNewsAndInterests" -Value 0 -PropertyType DWord -Force | Out-Null

# ---------------------------------------------------------
# 4. Enable Dark Mode
# ---------------------------------------------------------
Write-Host "Enabling Dark Mode..." -ForegroundColor Yellow
$themePath = "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize"
if (!(Test-Path $themePath)) { New-Item -Path $themePath -Force | Out-Null }
New-ItemProperty -Path $themePath -Name "AppsUseLightTheme" -Value 0 -PropertyType DWord -Force | Out-Null
New-ItemProperty -Path $themePath -Name "SystemUsesLightTheme" -Value 0 -PropertyType DWord -Force | Out-Null

# ---------------------------------------------------------
# 5. Auto-Hide Taskbar
# ---------------------------------------------------------
Write-Host "Setting Taskbar to Auto-Hide..." -ForegroundColor Yellow
try {
    $p = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\StuckRects3"
    $v = (Get-ItemProperty -Path $p).Settings
    if ($v) {
        $v[8] = 3 # Set 9th byte to 3 for auto-hide (default is 2)
        Set-ItemProperty -Path $p -Name Settings -Value $v
    }
} catch {
    Write-Host "Could not modify Taskbar settings. Explorer might need to be restarted first." -ForegroundColor Red
}

# ---------------------------------------------------------
# 6. Disable Telemetry & Privacy
# ---------------------------------------------------------
Write-Host "Disabling Telemetry & Advertising ID..." -ForegroundColor Yellow
$telemetryPath = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\DataCollection"
if (!(Test-Path $telemetryPath)) { New-Item -Path $telemetryPath -Force | Out-Null }
New-ItemProperty -Path $telemetryPath -Name "AllowTelemetry" -Value 0 -PropertyType DWord -Force | Out-Null

$advPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo"
if (!(Test-Path $advPath)) { New-Item -Path $advPath -Force | Out-Null }
New-ItemProperty -Path $advPath -Name "Enabled" -Value 0 -PropertyType DWord -Force | Out-Null

# ---------------------------------------------------------
# 7. Clean Start Menu & Search (No Bing)
# ---------------------------------------------------------
Write-Host "Disabling Bing Search & Start Menu Ads..." -ForegroundColor Yellow
$searchPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Search"
if (!(Test-Path $searchPath)) { New-Item -Path $searchPath -Force | Out-Null }
New-ItemProperty -Path $searchPath -Name "BingSearchEnabled" -Value 0 -PropertyType DWord -Force | Out-Null
New-ItemProperty -Path $searchPath -Name "CortanaConsent" -Value 0 -PropertyType DWord -Force | Out-Null

$contentPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"
if (!(Test-Path $contentPath)) { New-Item -Path $contentPath -Force | Out-Null }
New-ItemProperty -Path $contentPath -Name "SystemPaneSuggestionsEnabled" -Value 0 -PropertyType DWord -Force | Out-Null

# Extended Content Delivery disabling (Stops auto-installing apps like LinkedIn)
$cdmKeys = @(
    "ContentDeliveryAllowed",
    "OemPreInstalledAppsEnabled",
    "PreInstalledAppsEnabled",
    "SilentInstalledAppsEnabled",
    "SubscribedContent-338388Enabled",
    "SubscribedContent-338389Enabled",
    "SubscribedContent-353698Enabled",
    "SubscribedContent-310093Enabled"
)
foreach ($key in $cdmKeys) {
    New-ItemProperty -Path $contentPath -Name $key -Value 0 -PropertyType DWord -Force | Out-Null
}

# ---------------------------------------------------------
# 8. Clean Lock Screen & Explorer
# ---------------------------------------------------------
Write-Host "Cleaning Lock Screen & Taskbar..." -ForegroundColor Yellow
# Disable Lock Screen Tips
New-ItemProperty -Path $contentPath -Name "RotatingLockScreenEnabled" -Value 0 -PropertyType DWord -Force | Out-Null
New-ItemProperty -Path $contentPath -Name "SubscribedContent-338387Enabled" -Value 0 -PropertyType DWord -Force | Out-Null

# Hide Chat Icon
New-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" -Name "TaskbarMn" -Value 0 -PropertyType DWord -Force | Out-Null

# ---------------------------------------------------------
# 9. Remove OneDrive
# ---------------------------------------------------------
Write-Host "Removing OneDrive..." -ForegroundColor Yellow
$onedrive = "$env:SYSTEMROOT\SysWOW64\OneDriveSetup.exe"
if (!(Test-Path $onedrive)) {
    $onedrive = "$env:SYSTEMROOT\System32\OneDriveSetup.exe"
}
if (Test-Path $onedrive) {
    Start-Process $onedrive -ArgumentList "/uninstall" -NoNewWindow -Wait
} else {
    Write-Host "OneDrive installer not found, skipping." -ForegroundColor Gray
}

# ---------------------------------------------------------
# 10. Disable Mouse Acceleration
# ---------------------------------------------------------
Write-Host "Disabling Mouse Acceleration..." -ForegroundColor Yellow
$mousePath = "HKCU:\Control Panel\Mouse"
New-ItemProperty -Path $mousePath -Name "MouseSpeed" -Value "0" -PropertyType String -Force | Out-Null
New-ItemProperty -Path $mousePath -Name "MouseThreshold1" -Value "0" -PropertyType String -Force | Out-Null
New-ItemProperty -Path $mousePath -Name "MouseThreshold2" -Value "0" -PropertyType String -Force | Out-Null

# ---------------------------------------------------------
# 11. Disable Windows Copilot
# ---------------------------------------------------------
Write-Host "Disabling Windows Copilot..." -ForegroundColor Yellow
$copilotPathUser = "HKCU:\Software\Policies\Microsoft\Windows\WindowsCopilot"
$copilotPathMachine = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsCopilot"

if (!(Test-Path $copilotPathUser)) { New-Item -Path $copilotPathUser -Force | Out-Null }
New-ItemProperty -Path $copilotPathUser -Name "TurnOffWindowsCopilot" -Value 1 -PropertyType DWord -Force | Out-Null

if (!(Test-Path $copilotPathMachine)) { New-Item -Path $copilotPathMachine -Force | Out-Null }
New-ItemProperty -Path $copilotPathMachine -Name "TurnOffWindowsCopilot" -Value 1 -PropertyType DWord -Force | Out-Null

# ---------------------------------------------------------
# Finish
# ---------------------------------------------------------
Write-Host "Restarting Explorer to apply changes..." -ForegroundColor Cyan
Stop-Process -Name explorer -Force

Write-Host "Debloat Complete!" -ForegroundColor Green
