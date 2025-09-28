# boot.py - ESP32-S3 DHT WebSocket Monitor 起動スクリプト
# Wi-Fi 接続 + 安全版 NTP 同期
# Thonny IDE対応版

import network, time, sys, gc, socket, struct, machine
from wifi_config import WIFI_SSID, WIFI_PASSWORD, WIFI_HOSTNAME

print("=" * 50)
print("ESP32-S3 DHT Environmental Monitor")
print("Thonny IDE対応版")
print("=" * 50)

# ---- GC ----
gc.collect()
print(f"初期メモリ: {gc.mem_free()} bytes")

# ---- Wi-Fi 接続 ----
def connect_wifi(timeout_s=15):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    try:
        wlan.config(dhcp_hostname=WIFI_HOSTNAME)
    except Exception:
        pass
    if not wlan.isconnected():
        print("Connecting Wi-Fi ...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        t0 = time.ticks_ms()
        while not wlan.isconnected():
            if time.ticks_diff(time.ticks_ms(), t0) > timeout_s * 1000:
                raise OSError("Wi-Fi connect timeout")
            time.sleep_ms(200)
    ip, mask, gw, dns = wlan.ifconfig()
    print("Wi-Fi connected:", ip)
    print("GW:", gw, "DNS:", dns)
    return wlan

# ---- 安全版 NTP ----
_NTP_DELTA = 2208988800
_PKT = bytearray(48); _PKT[0] = 0x1B

def _ntp_once(host, timeout_s=2.5):
    addr = socket.getaddrinfo(host, 123)[0][-1]
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.settimeout(timeout_s)
        s.sendto(_PKT, addr)
        msg = s.recv(48)
        if len(msg) < 48:
            raise OSError("short NTP reply")
        secs = struct.unpack("!I", msg[40:44])[0]
        return secs - _NTP_DELTA
    finally:
        s.close()

def _rtc_set(unix_ts):
    tm = time.gmtime(unix_ts)
    machine.RTC().datetime((tm[0], tm[1], tm[2], tm[6]+1, tm[3], tm[4], tm[5], 0))

def ntp_sync_safe(retries=3, per_try_timeout_s=2.5, servers=None):
    if servers is None:
        wlan = network.WLAN(network.STA_IF)
        ip, mask, gw, dns = wlan.ifconfig()
        servers = [
            "ntp.nict.jp",
            "time.cloudflare.com",
            "pool.ntp.org",
            gw, dns,
            "129.6.15.28",      # NIST
            "162.159.200.1",    # Cloudflare
        ]
    for attempt in range(1, retries+1):
        for host in servers:
            if not host or host == "0.0.0.0":
                continue
            try:
                print(f"Syncing with NTP: {host} (try {attempt}/{retries})")
                unix = _ntp_once(host, timeout_s=per_try_timeout_s)
                if not (946684800 <= unix <= 4102444800):  # 2000-01-01〜2100-01-01
                    raise ValueError("range check failed")
                _rtc_set(unix)
                print("NTP sync successful")
                return True
            except Exception as e:
                print("NTP failed:", e)
                time.sleep_ms(300)
        time.sleep(1)
    print("Warning: NTP sync failed. Boot continues without accurate time.")
    return False

def format_jst_now():
    try:
        utc = time.time()
        jst = utc + 9*3600
        t = time.localtime(jst)
        return "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d} JST".format(*t[:6])
    except Exception:
        return "----/--/-- --:--:-- JST"

# ---- Boot Sequence ----
print("ESP32-S3 Boot Sequence")
print("=====================")

try:
    wlan = connect_wifi()
except Exception as e:
    print("Wi-Fi connect failed:", e)
    sys.exit(1)

ntp_synced = ntp_sync_safe(retries=3, per_try_timeout_s=2.5)

if ntp_synced:
    print("Current", format_jst_now())
else:
    print("Warning: NTP sync failed, timestamps may be inaccurate")

print("Boot sequence completed")
print(f"Ready to start applications on IP: {wlan.ifconfig()[0]}")
