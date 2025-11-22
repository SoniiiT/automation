# Install Chocolatey (if not already installed)
if (!(Get-Command choco -ErrorAction SilentlyContinue)) {
    Set-ExecutionPolicy Bypass -Scope Process -Force
    Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))
}

# Install Chocolatey packages
choco install googlechrome -y
choco install 7zip -y
choco install vlc -y
choco install powershell-core -y
choco install discord -y
choco install steam -y
choco install ubisoft-connect -y
choco install ea-app -y
choco install itch -y
choco install voicemeeter-potato.install -y
choco install prismlauncher -y
choco install 1password -y
choco install nvidia-app -y
choco install nvidia-geforce-now -y
choco install lghub -y
choco install icloud -y


#Set Default Browser
$browserPath = "C:\Program Files\Google\Chrome\Application\chrome.exe" # Replace with the path to your desired browser executable
Set-ItemProperty -Path "HKLM:\SOFTWARE\Classes\http\shell\open\command" -Name "(Default)" -Value """$browserPath"" %1"
Set-ItemProperty -Path "HKLM:\SOFTWARE\Classes\https\shell\open\command" -Name "(Default)" -Value """$browserPath"" %1"