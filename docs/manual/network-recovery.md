# Network Recovery

If a WiFi configuration change leaves a device unreachable — wrong static IP, wrong gateway, wrong subnet, the wrong network selected as default — you can recover it without reflashing. This page covers four methods, in order of preference.

!!! warning "When to use this page"
    Symptoms: the GenMaster web UI doesn't load, SSH times out, ping gets no response, or GenMaster can't reach GenSlave after a network change. Before reaching for the SD card, try the methods below in order.

## Method 1 — Local console (preferred)

Plug a monitor and keyboard into the affected Pi, log in, and use `nmtui` — NetworkManager's curses UI. Works on both GenMaster (Pi 5) and GenSlave (Pi Zero 2W), and is the safest path because you can see exactly what you're changing before you commit.

### Pi 5 (GenMaster)

You need:

- HDMI cable (the Pi 5 uses a full-size HDMI port — most monitors will work directly)
- USB keyboard

### Pi Zero 2W (GenSlave)

The Pi Zero 2W is more awkward — most people don't keep these adapters around:

- **mini-HDMI to HDMI** adapter (the Pi Zero has a mini-HDMI port, not full-size)
- **micro-USB OTG** adapter (so you can plug a USB-A keyboard into the data port)
- USB keyboard

!!! tip "Keep the adapters with the Pi"
    For unattended Pi Zero deployments, tape a small zip-loc with the adapters to the enclosure. The day you need them is the day you really need them.

### Recovery steps

Once you have a console:

1. Log in with your normal account (`pi` or whatever you set up).
2. Run:

    ```bash
    sudo nmtui
    ```

3. Choose **Edit a connection** to fix a misconfigured profile, or **Activate a connection** to switch back to a working one.
4. To delete the bad profile entirely, choose **Edit a connection → ⟨name⟩ → Delete**.
5. After saving, run:

    ```bash
    sudo systemctl restart NetworkManager
    ```

6. Check the IP came back:

    ```bash
    ip addr show wlan0
    ```

## Method 2 — `nmcli` one-liners

If you'd rather not deal with the curses UI, the same operations are available as direct commands. Useful when you can console in but don't want to navigate menus.

### List saved profiles

```bash
nmcli connection show
```

### Switch a profile back from static to DHCP

```bash
sudo nmcli connection modify "<profile-name>" \
    ipv4.method auto \
    ipv4.addresses "" \
    ipv4.gateway "" \
    ipv4.dns ""
sudo nmcli connection up "<profile-name>"
```

### Change just the static IP / gateway

```bash
sudo nmcli connection modify "<profile-name>" \
    ipv4.method manual \
    ipv4.addresses 192.168.1.50/24 \
    ipv4.gateway 192.168.1.1 \
    ipv4.dns "1.1.1.1 8.8.8.8"
sudo nmcli connection up "<profile-name>"
```

### Delete a saved profile entirely

```bash
sudo nmcli connection delete "<profile-name>"
```

### Force a re-scan and reconnect

```bash
sudo nmcli device wifi rescan
sudo nmcli device connect wlan0
```

## Method 3 — SD card surgery

If you can't get a console (no spare monitor / no HDMI adapter / Pi is in an inconvenient location), pop the SD card into another machine and edit the NetworkManager profile directly.

!!! danger "Power off cleanly"
    Pull power only after the Pi has actually shut down (`sudo shutdown -h now`), or after at least 30 seconds with no activity LED. Yanking power on a running Pi can corrupt the filesystem and turn a network problem into a re-flash.

### From a Linux or macOS machine

1. Power off the Pi, remove the SD card, insert it into your computer.
2. Mount the **rootfs** partition (the larger ext4 partition — Linux mounts it automatically; on macOS you'll need [extFS for Mac](https://www.paragon-software.com/home/extfs-mac/) or similar).
3. Navigate to:

    ```
    /etc/NetworkManager/system-connections/
    ```

4. Each saved network is a `<ssid>.nmconnection` text file. To remove the broken one, delete that file. To fix it, edit the `[ipv4]` section:

    ```ini
    [ipv4]
    method=auto         # change "manual" → "auto" to switch back to DHCP
    # OR for static:
    method=manual
    address1=192.168.1.50/24,192.168.1.1
    dns=1.1.1.1;8.8.8.8;
    ```

5. Save, unmount, return the SD card to the Pi, and boot.

### From a Windows machine

Windows can't read ext4 natively. Either install an ext4 driver (e.g. [WSL2 with `wsl --mount`](https://learn.microsoft.com/en-us/windows/wsl/wsl2-mount-disk), or [Linux File Systems for Windows](https://www.paragon-software.com/home/linuxfs-windows/)), or do the edit from another Linux/macOS machine.

## Method 4 — Ethernet fallback (Pi 5 only)

The Pi 5 has built-in Ethernet. If WiFi is broken, you can plug it directly into a switch or router and reach it that way.

1. Connect the Ethernet cable.
2. Find its DHCP-assigned IP from your router's admin page.
3. SSH in and use Methods 1 or 2 above to fix WiFi.
4. When WiFi is back, unplug Ethernet.

The Pi Zero 2W has no Ethernet port, so this method doesn't apply to GenSlave.

## Prevention checklist

Before you save a static-IP configuration, double-check:

- [ ] **CIDR is correct.** `/24` = 255.255.255.0 (most home networks). `/16` = 255.255.0.0. `/23` = 255.255.254.0. Don't guess — match what your router shows for its LAN.
- [ ] **Gateway is on the same subnet** as the static address. If your IP is `192.168.1.50/24`, the gateway should be `192.168.1.x`.
- [ ] **Gateway is reachable.** From the device's current network, run `ping <new-gateway-ip>` first.
- [ ] **DNS is reachable.** `8.8.8.8` (Google) and `1.1.1.1` (Cloudflare) are safe defaults if you don't know your local DNS server.
- [ ] **GenMaster and GenSlave end up on the same subnet** if you intend to use the local link rather than Tailscale. The Add Network dialog will warn you if they wouldn't be — pay attention to that warning.
- [ ] **Test with `auto_connect=false` first.** Add the network, manually connect to verify it works, then re-edit the profile to enable auto-connect.

## See also

- [GenSlave manual page](genslave.md)
- [System page](system.md)
- [Troubleshooting](../TROUBLESHOOTING.md)
