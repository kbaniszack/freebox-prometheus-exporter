import os
import sys
import time
from prometheus_client import start_http_server, Gauge
from freepybox import Freepybox

# --- CONFIGURATION ---
EXPORTER_PORT = int(os.getenv("FREEBOX_EXPORTER_PORT", 8000))
POLLING_INTERVAL = int(os.getenv("FREEBOX_POLLING_INTERVAL", 10))
FREEBOX_IP = os.getenv("FREEBOX_IP", "192.168.1.254")

# Token file location
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
FREEBOX_TOKEN_FILE = os.getenv("FREEBOX_TOKEN_PATH", os.path.join(SCRIPT_DIR, "freebox_token.json"))

# --- PROMETHEUS METRICS ---

# Connection status and bandwidth rates
g_fb_status = Gauge('freebox_connection_status', 'Etat de la connexion (1=up, 0=down)')
g_fb_rate_down = Gauge('freebox_rate_down_bytes', 'Débit descendant actuel (Bytes/s)')
g_fb_rate_up = Gauge('freebox_rate_up_bytes', 'Débit montant actuel (Bytes/s)')
g_fb_bandwidth_down = Gauge('freebox_bandwidth_down_bps', 'Bande passante max descendante (bps)')
g_fb_bandwidth_up = Gauge('freebox_bandwidth_up_bps', 'Bande passante max montante (bps)')

# System health
g_fb_temp_t1 = Gauge('freebox_temp_t1_celsius', 'Température capteur 1 (°C)')
g_fb_temp_cpub = Gauge('freebox_temp_cpub_celsius', 'Température CPU B (°C)')
g_fb_fan_rpm = Gauge('freebox_fan_rpm', 'Vitesse ventilateur (RPM)')
g_fb_uptime = Gauge('freebox_uptime_seconds', 'Uptime système (secondes)')

# Fiber optics FTTH (SFP laser details)
g_fb_ftth_rx_pwr = Gauge('freebox_ftth_rx_power_dbm', 'Puissance optique reçue (dBm)')
g_fb_ftth_tx_pwr = Gauge('freebox_ftth_tx_power_dbm', 'Puissance optique transmise (dBm)')

# LAN devices statistics
g_fb_hosts_active = Gauge('freebox_hosts_active_total', 'Nombre total de périphériques actifs')
g_fb_hosts_wifi = Gauge('freebox_hosts_wifi_active', 'Nombre de périphériques Wi-Fi actifs')
g_fb_hosts_ethernet = Gauge('freebox_hosts_ethernet_active', 'Nombre de périphériques Ethernet actifs')

# Switch Ethernet RJ45 Ports
g_fb_switch_port_link = Gauge('freebox_switch_port_link_status', 'Statut du lien du port switch (1=up, 0=down)', ['port_name', 'port_speed', 'duplex'])

# Downloader tasks and rates
g_fb_downloader_active_tasks = Gauge('freebox_downloader_active_tasks', 'Nombre de téléchargements actifs')
g_fb_downloader_rx_rate = Gauge('freebox_downloader_rx_rate_bytes', 'Débit de téléchargement du downloader (Bytes/s)')
g_fb_downloader_tx_rate = Gauge('freebox_downloader_tx_rate_bytes', 'Débit d\'envoi du downloader (Bytes/s)')

# Per-device network traffic rates and bytes
g_fb_host_rx_rate = Gauge('freebox_host_rx_rate_bytes', 'Débit descendant (Bytes/s)', ['host_name', 'mac_address', 'host_type'])
g_fb_host_tx_rate = Gauge('freebox_host_tx_rate_bytes', 'Débit montant (Bytes/s)', ['host_name', 'mac_address', 'host_type'])
g_fb_host_rx_bytes = Gauge('freebox_host_rx_bytes_total', 'Total octets reçus', ['host_name', 'mac_address', 'host_type'])
g_fb_host_tx_bytes = Gauge('freebox_host_tx_bytes_total', 'Total octets émis', ['host_name', 'mac_address', 'host_type'])

# Per-device Wi-Fi signal and physical link rates
g_fb_host_wifi_signal = Gauge('freebox_host_wifi_signal_dbm', 'Force du signal Wi-Fi (dBm)', ['host_name', 'mac_address', 'ap_type'])
g_fb_host_wifi_phy_rx = Gauge('freebox_host_wifi_phy_rx_rate_mbps', 'Vitesse théorique de liaison descendante (Mbps)', ['host_name', 'mac_address', 'ap_type'])
g_fb_host_wifi_phy_tx = Gauge('freebox_host_wifi_phy_tx_rate_mbps', 'Vitesse théorique de liaison montante (Mbps)', ['host_name', 'mac_address', 'ap_type'])

# Active labels caches for Prometheus garbage collection
active_hosts_labels = set()
active_wifi_labels = set()

# --- DATA ACQUISITION ---

def collect_metrics(fbx):
    global active_hosts_labels, active_wifi_labels
    try:
        fbx.open(FREEBOX_IP)
        
        # 1. Connection metrics
        status = fbx._access.get('connection/')
        if status:
            is_up = 1 if status.get('state') == 'up' else 0
            g_fb_status.set(is_up)
            g_fb_rate_down.set(status.get('rate_down', 0))
            g_fb_rate_up.set(status.get('rate_up', 0))
            g_fb_bandwidth_down.set(status.get('bandwidth_down', 0))
            g_fb_bandwidth_up.set(status.get('bandwidth_up', 0))
        
        # 2. System status
        sys_info = fbx._access.get('system/')
        if sys_info:
            g_fb_temp_t1.set(sys_info.get('temp_t1', 0))
            g_fb_temp_cpub.set(sys_info.get('temp_cpub', 0))
            g_fb_fan_rpm.set(sys_info.get('fan_rpm', 0))
            g_fb_uptime.set(sys_info.get('uptime_val', 0))
            
        # 3. FTTH (Fiber optic SFP details)
        try:
            ftth_info = fbx._access.get('connection/ftth/')
            if ftth_info:
                g_fb_ftth_rx_pwr.set(ftth_info.get('sfp_pwr_rx', 0) / 100.0)
                g_fb_ftth_tx_pwr.set(ftth_info.get('sfp_pwr_tx', 0) / 100.0)
        except:
            pass

        # 4. LAN Hosts and per-device details
        lan_hosts = fbx._access.get('lan/browser/pub/')
        if isinstance(lan_hosts, list):
            active_hosts = [h for h in lan_hosts if h.get('active', False)]
            g_fb_hosts_active.set(len(active_hosts))
            
            wifi_active = 0
            eth_active = 0
            current_hosts_labels = set()
            current_wifi_labels = set()
            
            for h in active_hosts:
                ap = h.get('access_point', {})
                conn_type = ap.get('connectivity_type', '')
                if conn_type == 'wifi':
                    wifi_active += 1
                elif conn_type == 'ethernet':
                    eth_active += 1
                    
                host_name = h.get('primary_name') or h.get('default_name') or h.get('id', 'Inconnu')
                mac = h.get('l2ident', {}).get('id', '')
                host_type = h.get('host_type', 'other')
                
                rx_rate = ap.get('rx_rate', 0)
                tx_rate = ap.get('tx_rate', 0)
                rx_bytes = ap.get('rx_bytes', 0)
                tx_bytes = ap.get('tx_bytes', 0)
                
                label_tuple = (host_name, mac, host_type)
                current_hosts_labels.add(label_tuple)
                
                g_fb_host_rx_rate.labels(host_name=host_name, mac_address=mac, host_type=host_type).set(rx_rate)
                g_fb_host_tx_rate.labels(host_name=host_name, mac_address=mac, host_type=host_type).set(tx_rate)
                g_fb_host_rx_bytes.labels(host_name=host_name, mac_address=mac, host_type=host_type).set(rx_bytes)
                g_fb_host_tx_bytes.labels(host_name=host_name, mac_address=mac, host_type=host_type).set(tx_bytes)
                
                if conn_type == 'wifi':
                    ap_type = ap.get('type', 'gateway')
                    wifi_info = ap.get('wifi_information', {})
                    sig = wifi_info.get('signal', 0)
                    phy_rx = wifi_info.get('phy_rx_rate', 0) / 10.0
                    phy_tx = wifi_info.get('phy_tx_rate', 0) / 10.0
                    
                    wifi_tuple = (host_name, mac, ap_type)
                    current_wifi_labels.add(wifi_tuple)
                    
                    g_fb_host_wifi_signal.labels(host_name=host_name, mac_address=mac, ap_type=ap_type).set(sig)
                    g_fb_host_wifi_phy_rx.labels(host_name=host_name, mac_address=mac, ap_type=ap_type).set(phy_rx)
                    g_fb_host_wifi_phy_tx.labels(host_name=host_name, mac_address=mac, ap_type=ap_type).set(phy_tx)
                    
            g_fb_hosts_wifi.set(wifi_active)
            g_fb_hosts_ethernet.set(eth_active)
            
            # Clean up stale labels
            for label_tuple in list(active_hosts_labels - current_hosts_labels):
                try:
                    g_fb_host_rx_rate.remove(*label_tuple)
                    g_fb_host_tx_rate.remove(*label_tuple)
                    g_fb_host_rx_bytes.remove(*label_tuple)
                    g_fb_host_tx_bytes.remove(*label_tuple)
                except:
                    pass
            for wifi_tuple in list(active_wifi_labels - current_wifi_labels):
                try:
                    g_fb_host_wifi_signal.remove(*wifi_tuple)
                    g_fb_host_wifi_phy_rx.remove(*wifi_tuple)
                    g_fb_host_wifi_phy_tx.remove(*wifi_tuple)
                except:
                    pass
            
            active_hosts_labels = current_hosts_labels
            active_wifi_labels = current_wifi_labels
            
        # 5. Switch Ethernet Status
        try:
            switch_status = fbx._access.get('switch/status/')
            if isinstance(switch_status, list):
                for port in switch_status:
                    name = port.get('name', 'Ethernet')
                    speed = port.get('speed', '0')
                    duplex = port.get('duplex', 'half')
                    is_up = 1 if port.get('link') == 'up' else 0
                    g_fb_switch_port_link.labels(port_name=name, port_speed=speed, duplex=duplex).set(is_up)
        except:
            pass

        # 6. Downloader status
        try:
            dl_stats = fbx._access.get('downloads/stats')
            if dl_stats:
                g_fb_downloader_active_tasks.set(dl_stats.get('nb_tasks_active', 0))
                g_fb_downloader_rx_rate.set(dl_stats.get('rx_rate', 0))
                g_fb_downloader_tx_rate.set(dl_stats.get('tx_rate', 0))
        except:
            pass

        print(f"📦 [Freebox Exporter] Scraped successfully at {time.strftime('%H:%M:%S')}")
    except Exception as e:
        print(f"❌ [Freebox Exporter] Scraping error: {e}")
    finally:
        try:
            fbx.close()
        except:
            pass

# --- MAIN ---

if __name__ == '__main__':
    if not os.path.exists(FREEBOX_TOKEN_FILE):
        print(f"❌ Token file not found at: {FREEBOX_TOKEN_FILE}")
        print("Please run authorization setup first to generate the token.")
        sys.exit(1)

    app_desc = {
        "app_id": "fr.freebox.prometheus-exporter",
        "app_name": "Freebox Exporter",
        "app_version": "1.0",
        "device_name": "Prometheus Scraper"
    }

    fbx = Freepybox(
        app_desc=app_desc,
        token_file=FREEBOX_TOKEN_FILE
    )

    # Start Prometheus HTTP server
    start_http_server(EXPORTER_PORT)
    print(f"📡 Freebox Prometheus Exporter listening on port {EXPORTER_PORT}")

    while True:
        collect_metrics(fbx)
        time.sleep(POLLING_INTERVAL)
