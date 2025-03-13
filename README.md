# Photo Booth 📸

Photo Booth is a fun photo booth application that allows users to capture photos and print them 🖨️. Built with **Python (FastAPI)** for the backend and **React** for the frontend, it brings an interactive and seamless experience to your events.

## Table of Contents 📚

- [Overview 🚀](#overview-)
- [System Requirements 💻](#system-requirements-)
- [Server Setup ⚙️](#server-setup-)
  - [Operating System and Hardware 🖥️](#operating-system-and-hardware-)
  - [Production Installation ✨](#production-installation-)
  - [User Credentials and Account Management 🔑](#user-credentials-and-account-management-)
- [Photo Booth Client Setup 🛠️](#photo-booth-client-setup-)
  - [Installation on Windows 🪟](#installation-on-windows-)
  - [Printer Service Autostart 🚀](#printer-service-autostart-)
  - [Microsoft Edge Kiosk Mode Autostart 🌐](#microsoft-edge-kiosk-mode-autostart-)
- [Development Installation 👩‍💻](#development-installation-)
- [Makefile Commands 📝](#makefile-commands-)

## Overview 🚀

Photo Booth lets you snap photos and print them instantly. Whether for events or personal use, enjoy an integrated experience powered by FastAPI and React.

## System Requirements 💻

### Operating System and Hardware 🖥️

Choose one of the following operating systems:
- **Ubuntu 22** (recommended for ease of setup) 🐧
- **Windows WSL Ubuntu 22**
- **Debian 12**
- **Windows WSL Debian 12**

**Hardware requirements:**
- **64GB free disk space** 💾
- **8GB of RAM** 🧠
- **Nvidia GPU** is recommended for optimal performance (AMD GPUs are not supported). For example, set up an Ubuntu 22 VM on Proxmox with Nvidia GPU passthrough.

## Server Setup ⚙️

### Production Installation ✨

A handy `Makefile` is provided to automate the installation process. The steps below work similarly for all supported OSes.

1. **Update and Install Dependencies:**

   ```sh
   sudo apt update
   sudo apt install git make -y
   ```

2. **Clone the Repository and Run Installation:**

   ```sh
   git clone https://github.com/ITLab-CC/photobooth
   cd photobooth
   make run
   ```

   > **Note:** The installation might take up to **1 hour** depending on your connection and hardware. During the process, the server will reboot to finish installing the Nvidia drivers. After the reboot, simply rerun `make run` to resume the installation 🔄.

### User Credentials and Account Management 🔑

After installation, the server logs will display the usernames and passwords for these accounts:

```
---------------Account---------------
Username: boss
Roles: ['boss']
Password: uOItPy0Khn8XNz3OiNHKBQz.ksMoo+sL
--------------------------------------
---------------Account---------------
Username: photo_booth
Roles: ['photo_booth']
Password: 4K_9*4VU/q.ahgu+v4j,Roi.uUM~fp1j
--------------------------------------
---------------Account---------------
Username: printer
Roles: ['printer']
Password: aYp,xVl4GMRn/d2yP!NIdfLDxFJ.vkSy
--------------------------------------
------------------------------------------------------
All services are running in the background.
The logs are available in the logs/ directory.
------------------------------------------------------
```

If you forget any credentials, use the following commands:
- `make create-admin` – Create a new admin user 👤.
- `make reset-photo-booth` – Reset the photo booth password 🔄.
- `make reset-printer` – Reset the printer password 🔄.

Thats is! Your photo booth server is now set up and ready to use 📸. Now continue with the client.

## Photo Booth Client Setup 🛠️

### Hardware 🖥️

For the client side, we recommend the following hardware (all links provided lead to Amazon):

- **Camera:** [Canon EOS 2000D](https://www.amazon.de/Canon-2000D-Spiegelreflexkamera-Objektiv-18-55/dp/B07B322GL5) 📸
- **Printer:** [DNP Photo Imaging DS 620](https://www.amazon.de/DNP-212620-DS-620-Drucker/dp/B00WIYB5WS) 🖨️
- **TV:** [49" TV](https://www.amazon.de/s?k=50%22+TV) 📺
- **Touchscreen:** [Multi-Touch Infrarot Touch Frame](https://www.amazon.de/Multi-Touch-Infrarot-Rahmen-Screen-Overlay/dp/B07NTF4B7S) 🖱️
- **PC:** [Intel NUC](https://www.amazon.de/s?k=Intel+NUC) 💻

We recommend using **Windows** for setting up the photo booth client because the current camera hardware works best on this platform 🪟.

### Installation on Windows 🪟

1. **Install Git and Python:**
   - Download Git: [https://git-scm.com/download/win](https://git-scm.com/download/win) 🌐
   - Download Python: [https://www.python.org/downloads/](https://www.python.org/downloads/) 🐍

2. **Clone the Repository and Install Dependencies:**

   ```cmd
   git clone https://github.com/ITLab-CC/photobooth
   cd photobooth\printer-service
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables:**

   - Create a `.env` file by copying the provided template:
     
     ```cmd
     copy env.template .env
     ```

   - Open the `.env` file and update the values:

     ```
     PHOTO_BOOTH_BASE_URL="http://123.123.123.123:123"
     PHOTO_BOOTH_USERNAME="user"
     PHOTO_BOOTH_PASSWORD="password"
     ```

   Replace the URL with your server’s domain or IP, and update the printer credentials with those from the server installation 🔐.

### Printer Service Autostart 🚀

Follow these steps to configure Windows to automatically run the printer service at startup:

1. **Create a Batch File:**
   - Open Notepad and paste the following code (adjust the Python path, username, and script name as needed):
     
     ```batch
     @echo off
     python "C:\Users\YOUR_USERNAME\Desktop\photobooth\printer-service\printer_service.py"
     ```
     
   - Save the file as `start_printer_service.bat`.

2. **Add the Batch File to Startup:**
   - Press `Win + R`, type `shell:startup`, and press Enter.
   - Copy the `start_printer_service.bat` file into the Startup folder.

3. **Restart Your Computer:**  
   The printer service will run automatically on login 🔄.

### Microsoft Edge Kiosk Mode Autostart 🌐

To launch Microsoft Edge in kiosk mode automatically at startup:

1. **Create a Batch File:**
   - Open Notepad and paste the following code (update the Edge path and URL as needed):
     
     ```batch
     @echo off
     start "" "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --kiosk "https://photobooth.com/?user=user&password=password" --edge-kiosk-type=fullscreen
     ```

    Dont forget to replace the URL with your server’s domain or IP, and update the photo booth credentials with those from the server installation 🔐.

   - Save the file as `start_kiosk.bat`.

2. **Add the Batch File to Startup:**
   - Press `Win + R`, type `shell:startup`, and press Enter.
   - Copy the `start_kiosk.bat` file into the Startup folder.

3. **Restart Your Computer:**  
   Microsoft Edge will automatically launch in kiosk mode and display your specified website 🖥️.

Thats it! Your photo booth client is now set up and ready to use 📸.

## Development Installation 👩‍💻

For development purposes, run the server without Docker so you can modify the Python code directly. Use:

```sh
make run-dev
```

## Makefile Commands 📝

Below is a summary of the available Makefile commands:

| Command                    | Description                                                        |
|----------------------------|--------------------------------------------------------------------|
| `make run`                 | Run all services in Docker (Production mode). 🚀                   |
| `make run-dev`             | Run all services for development (without Docker). 👩‍💻              |
| `make stop`                | Stop all running services. ⏹️                                        |
| `make clean`               | Remove all generated files, including `.env`, logs, data, and `.venv`. 🧹 |
| `make create-admin`        | Create a new admin user. 👤                                          |
| `make reset-photo-booth`   | Reset the photo booth password. 🔄                                   |
| `make reset-printer`       | Reset the printer password. 🔄                                       |
| `make help`                | Display this help message with available commands. 📖              |
