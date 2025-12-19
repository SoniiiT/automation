import os
import zipfile
import requests
import shutil
import tempfile
import json
import subprocess
import sys
import time

def download_file(url, dest):
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(dest, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

def extract_zip(zip_path, extract_to):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

def detect_loader(modpack_dir):
    manifest = os.path.join(modpack_dir, 'manifest.json')
    if not os.path.exists(manifest):
        raise Exception("manifest.json nicht gefunden!")
    with open(manifest, 'r', encoding='utf-8') as f:
        data = json.load(f)
    mc_version = data['minecraft']['version']
    loader = data['minecraft']['modLoaders'][0]['id']
    if 'forge' in loader:
        return 'forge', mc_version, loader.split('-')[1]
    elif 'fabric' in loader:
        return 'fabric', mc_version, loader.split('-')[1]
    elif 'neoforge' in loader:
        return 'neoforge', mc_version, loader.split('-')[1]
    else:
        raise Exception("Unbekannter Loader: " + loader)

def download_server_jar(loader, mc_version, loader_version, dest_dir):
    # Forge
    if loader == 'forge':
        url = f"https://maven.minecraftforge.net/net/minecraftforge/forge/{mc_version}-{loader_version}/forge-{mc_version}-{loader_version}-installer.jar"
        dest = os.path.join(dest_dir, f"forge-installer.jar")
    # Fabric
    elif loader == 'fabric':
        url = f"https://meta.fabricmc.net/v2/versions/loader/{mc_version}/{loader_version}/server/jar"
        dest = os.path.join(dest_dir, f"fabric-server.jar")
    # NeoForge
    elif loader == 'neoforge':
        url = f"https://maven.neoforged.net/releases/net/neoforged/neoforge/{mc_version}-{loader_version}/neoforge-{mc_version}-{loader_version}-installer.jar"
        dest = os.path.join(dest_dir, f"neoforge-installer.jar")
    else:
        raise Exception("Unbekannter Loader")
    print(f"Lade Server Jar von {url}")
    download_file(url, dest)
    return dest

def run_installer(loader, server_jar, server_dir, mc_version, loader_version):
    """Führt die Forge/NeoForge Installer aus, falls notwendig"""
    if loader == 'forge':
        print("Installiere Forge Server...")
        # Ausführen des Forge-Installers im Server-Verzeichnis
        try:
            subprocess.run(['java', '-jar', server_jar, '--installServer'], 
                          cwd=server_dir, check=True)
            print("Forge Server Installation abgeschlossen.")
            # Lösche den Installer nach erfolgreicher Installation
            os.remove(server_jar)
        except subprocess.CalledProcessError as e:
            print(f"Fehler bei der Forge-Installation: {e}")
            print("Bitte führe die Installation manuell aus mit:")
            print(f"  cd {server_dir} && java -jar {os.path.basename(server_jar)} --installServer")
    
    elif loader == 'neoforge':
        print("Installiere NeoForge Server...")
        # Ausführen des NeoForge-Installers im Server-Verzeichnis
        try:
            subprocess.run(['java', '-jar', server_jar, '--installServer'], 
                          cwd=server_dir, check=True)
            print("NeoForge Server Installation abgeschlossen.")
            # Lösche den Installer nach erfolgreicher Installation
            os.remove(server_jar)
        except subprocess.CalledProcessError as e:
            print(f"Fehler bei der NeoForge-Installation: {e}")
            print("Bitte führe die Installation manuell aus mit:")
            print(f"  cd {server_dir} && java -jar {os.path.basename(server_jar)} --installServer")

def filter_client_mods(mods_dir):
    # Entferne client-only Mods (z.B. optifine, jei, etc.)
    client_mods = ['optifine', 'journeymap', 'jei', 'litematica', 'xaerominimap', 'controlling', 'mouse', 'replaymod']
    for mod in os.listdir(mods_dir):
        if any(name in mod.lower() for name in client_mods):
            print(f"Entferne Client-Mod: {mod}")
            os.remove(os.path.join(mods_dir, mod))

def create_startup_scripts(server_dir, loader, mc_version, loader_version):
    """Erstellt Startskripte für den Server"""
    
    # Erstelle .bat Datei für Windows
    with open(os.path.join(server_dir, "start_server.bat"), "w") as f:
        f.write("@echo off\n")
        f.write("echo Starte Minecraft Server...\n")
        
        if loader == "forge":
            f.write(f'java -Xmx4G -jar forge-{mc_version}-{loader_version}-server.jar nogui\n')
        elif loader == "neoforge":
            f.write(f'java -Xmx4G -jar neoforge-{mc_version}-{loader_version}-server.jar nogui\n')
        elif loader == "fabric":
            f.write(f'java -Xmx4G -jar fabric-server.jar nogui\n')
        
        f.write("pause\n")
    
    # Erstelle eula.txt automatisch
    with open(os.path.join(server_dir, "eula.txt"), "w") as f:
        f.write("#By changing the setting below to TRUE you are indicating your agreement to our EULA (https://aka.ms/MinecraftEULA).\n")
        f.write("eula=false\n")
    
    print("Startskripte erstellt. Bitte ändere 'eula=false' zu 'eula=true' in der eula.txt, um den Server zu starten.")

def download_mods_from_manifest(manifest_path, mods_dir):
    """Lädt alle Mods aus der manifest.json in den mods-Ordner herunter."""
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)
    files = manifest.get('files', [])
    os.makedirs(mods_dir, exist_ok=True)
    for mod in files:
        project_id = mod['projectID']
        file_id = mod['fileID']
        # Curseforge direct download URL
        url = f"https://www.curseforge.com/api/v1/mods/{project_id}/files/{file_id}/download"
        print(f"Lade Mod {project_id}/{file_id} ...")
        dest = os.path.join(mods_dir, f"{project_id}-{file_id}.jar")
        try:
            download_file(url, dest)
            time.sleep(1)  # Etwas warten, um Rate-Limits zu vermeiden
        except Exception as e:
            print(f"Fehler beim Download von {url}: {e}")

def create_server_modpack(modpack_url):
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, "modpack.zip")
        print("Lade Modpack herunter...")
        download_file(modpack_url, zip_path)
        extract_dir = os.path.join(tmpdir, "modpack")
        extract_zip(zip_path, extract_dir)
        loader, mc_version, loader_version = detect_loader(extract_dir)
        print(f"Erkannt: {loader} {mc_version} {loader_version}")
        mods_dir = os.path.join(extract_dir, "mods")
        if os.path.exists(mods_dir):
            filter_client_mods(mods_dir)
        server_dir = os.path.join(os.getcwd(), f"server-{mc_version}-{loader}")
        os.makedirs(server_dir, exist_ok=True)
        shutil.copytree(extract_dir, server_dir, dirs_exist_ok=True)
        server_jar = download_server_jar(loader, mc_version, loader_version, server_dir)

        # Mods aus manifest.json herunterladen
        manifest_path = os.path.join(server_dir, 'manifest.json')
        mods_target_dir = os.path.join(server_dir, 'mods')
        download_mods_from_manifest(manifest_path, mods_target_dir)

        # Kopiere Mods aus overrides/mods (falls vorhanden)
        overrides_mods = os.path.join(server_dir, 'overrides', 'mods')
        if os.path.exists(overrides_mods):
            for modfile in os.listdir(overrides_mods):
                shutil.copy2(os.path.join(overrides_mods, modfile), mods_target_dir)

        # Erstelle Startskripte
        create_startup_scripts(server_dir, loader, mc_version, loader_version)

        print(f"Server Modpack erstellt in: {server_dir}")
        print(f"Server Jar: {server_jar}")
        print(f"Die Server-Dateien sind jetzt bereit für den Transfer zu deinem Server.")
        print(f"Nach dem Transfer ändere die eula.txt zu 'eula=true' und führe dann start_server.bat aus.")

if __name__ == "__main__":
    url = input("Modpack Download-URL (Curseforge ZIP): ").strip()
    create_server_modpack(url)
