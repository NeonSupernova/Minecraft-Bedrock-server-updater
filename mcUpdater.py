#!/usr/bin/python3
import atexit
import os
import shutil
import subprocess
import sys
import time

import requests
from bs4 import BeautifulSoup

serverFolder = 'downloadbedrock'
serverFolderExe = 'bedrock'

difficulty = 'hard'
if len(sys.argv) > 1:
    if sys.argv[1] == 'easy':
        difficulty = 'easy'
    elif sys.argv[1] == 'normal':
        difficulty = 'normal'
    elif sys.argv[1] == 'hard':
        difficulty = 'hard'
    elif sys.argv[1] == 'peaceful':
        difficulty = 'peaceful'

firstRun = False


def initialize():
    # Setup folders
    global firstRun
    if not os.path.isdir(serverFolder):
        print("First run. Creating serverFolder")
        os.makedirs(serverFolder)
        firstRun = True
    if not os.path.isdir(serverFolderExe):
        os.makedirs(serverFolderExe)
        firstRun = True
    # Check serverFolder has only 1 file
    if len(oslistdir()) > 1:
        raise AssertionError("This folder can only have 1 file:" + serverFolder)


def initialize_properties():
    if firstRun:
        setProperties("difficulty", difficulty)  # Default game mode is hard
        setProperties("max-players", str(20))  # Java edition default setting.
        setProperties("content-log-file-enabled", "true")  # Enable log


def get_download_url():
    # get minecraft bedrock server download URL
    m_curl = requests.get('https://www.minecraft.net/en-us/download/server/bedrock').text
    mc_soup = BeautifulSoup(m_curl, 'html.parser')
    for dwbtn in mc_soup.findAll("a", {"class": "btn btn-disabled-outline mt-4 downloadlink"}):
        if dwbtn['data-platform'] == 'serverBedrockLinux':
            return dwbtn['href']


def oslistdir():
    return list(filter((lambda x: x[0] != "."), os.listdir(serverFolder)))


def setProperties(p, v):
    print("Set " + p + " to " + v)
    with open(serverFolderExe + "/server.properties") as spfp:
        sp = spfp.read()
    sp = sp.split("\n")
    for i, setting in enumerate(sp):
        if setting.startswith(p + "="):
            sp[i] = p + "=" + v
    with open(serverFolderExe + "/server.properties", "w") as spfp:
        spfp.write("\n".join(sp))


def startServer():
    print("Starting server...")
    subprocess.call(["tmux", "new", "-d", "-s", "MC_BDRK", "bash"], cwd=serverFolderExe)
    time.sleep(1)
    subprocess.call(["tmux", "send-keys", "-t", "MC_BDRK", "set +e", "Enter"])  # don't bail out of bash script
    subprocess.call(["tmux", "send-keys", "-t", "MC_BDRK",
                     "while true; do ./bedrock_server; echo Server stopped. Restarting in 10 seconds...; sleep 10; done",
                     "Enter"])


def stopServer():
    print("Stopping server...")
    subprocess.call(["tmux", "send-keys", "-t", "MC_BDRK", "stop"])
    time.sleep(1)
    subprocess.call(["tmux", "send-keys", "-t", "MC_BDRK", "Enter"])
    time.sleep(5)
    subprocess.call(["tmux", "send-keys", "-t", "MC_BDRK", "C-c"])
    time.sleep(1)
    subprocess.call(["tmux", "kill-session", "-t", "MC_BDRK"])


atexit.register(stopServer)

initialize()
startServer()
while True:
    try:
        dwurl = get_download_url()
        newVersion = dwurl.split("/")[-1]
        oldVersion = oslistdir()[0] if len(oslistdir()) != 0 else "(No old version found)"
        if oldVersion != newVersion:
            print("New Minecraft version found: " + newVersion)
            print("Start downloading: " + newVersion)
            myfile = requests.get(dwurl)
            open(serverFolder + "/" + newVersion, 'wb').write(myfile.content)
            stopServer()
            if not firstRun:
                print("Remove old version: " + oldVersion)
                try:
                    os.remove(serverFolder + "/" + oldVersion)
                except:
                    pass
                # Backup old server.properties to server.properties.bak
                print("Backing up server properties, whitelist and permissions")
                shutil.move(serverFolderExe + "/server.properties", serverFolderExe + "/server.properties.bak")
                shutil.move(serverFolderExe + "/whitelist.json", serverFolderExe + "/whitelist.json.bak")
                shutil.move(serverFolderExe + "/permissions.json", serverFolderExe + "/permissions.json.bak")
            print("Extracting new server from zip")
            subprocess.call(["unzip", "-o", "-q", serverFolder + "/" + newVersion, "-d", serverFolderExe])
            if firstRun:
                initialize_properties()
            else:
                # Restore server.properties from server.properties.bak
                print("Restoring original server properties, whitelist and permissions")
                shutil.move(serverFolderExe + "/server.properties.bak", serverFolderExe + "/server.properties")
                shutil.move(serverFolderExe + "/whitelist.json.bak", serverFolderExe + "/whitelist.json")
                shutil.move(serverFolderExe + "/permissions.json.bak", serverFolderExe + "/permissions.json")
            startServer()
            firstRun = False
    except Exception as e:
        print(e)
    time.sleep(86400)
