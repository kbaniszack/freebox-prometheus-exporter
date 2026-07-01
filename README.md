# Freebox Prometheus Exporter 🚀

Un exportateur Prometheus léger en Python pour surveiller votre **Freebox** (Révolution, Delta, Pop, Ultra, etc.) en temps réel dans **Grafana**.

---

## 📈 Métriques récoltées

* **Ligne & Trafic Global** : 
  * Statut de la connexion (Up/Down).
  * Débits actuels descendant et montant (Bytes/s).
  * Bandes passantes maximales négociées (ADSL/Fibre).
* **Santé de la Box** : 
  * Températures internes (capteurs système et CPU).
  * Vitesse du ventilateur (RPM).
  * Uptime de la box (Secondes).
* **Optique Fibre (FTTH)** :
  * Puissance laser reçue (Rx Power en dBm).
  * Puissance laser transmise (Tx Power en dBm).
* **Ports Physiques (Switch)** :
  * Statut de lien (Up/Down), vitesse de négociation (Mbps) et duplex de chaque port RJ45 à l'arrière.
* **Périphériques connectés (LAN)** :
  * Nombre total d'appareils actifs, répartition Wi-Fi vs Ethernet.
* **Trafic individuel par appareil** :
  * Débits descendant/montant instantanés et volumes totaux transférés pour chaque appareil connecté au réseau.
* **Wi-Fi individuel par appareil** :
  * Force du signal (RSSI en dBm) de chaque appareil sans fil.
  * Vitesse de liaison physique (PHY Link rate en Mbps).
  * Identification de la borne Wi-Fi d'association (Box principale vs Répéteur).

---

## 🛠️ Installation & Premier Lancement

### Étape 1 : Association de sécurité (Obligatoire)

L'API Freebox nécessite une autorisation manuelle la première fois qu'une nouvelle application tente de s'y connecter.

1. Installez les dépendances :
   ```bash
   pip install requests setuptools wheel
   pip install --no-build-isolation freepybox
   ```
2. Créez un script rapide `pair.py` :
   ```python
   from freepybox import Freepybox
   app_desc = {"app_id": "fr.freebox.prometheus-exporter", "app_name": "Freebox Exporter", "app_version": "1.0", "device_name": "Scraper"}
   fbx = Freepybox(app_desc=app_desc, token_file="freebox_token.json")
   fbx.open("192.168.1.254") # Modifiez par l'IP de votre Freebox
   fbx.close()
   ```
3. Lancez-le. **Regardez l'écran physique de votre Freebox** et **appuyez sur la flèche de droite** pour accorder l'accès.
4. Cela génère le fichier `freebox_token.json` requis par l'exportateur.

---

## 🚀 Utilisation

### Mode Local
Lancez simplement l'exportateur :
```bash
python freebox_exporter.py
```

### Mode Docker 🐳
Vous pouvez compiler et lancer le conteneur facilement :

1. Compilez l'image :
   ```bash
   docker build -t freebox-exporter .
   ```
2. Lancez le conteneur (en montant votre fichier de jeton généré à l'étape 1) :
   ```bash
   docker run -d \
     --name freebox-exporter \
     -p 8000:8000 \
     -v $(pwd)/freebox_token.json:/app/freebox_token.json \
     -e FREEBOX_IP="192.168.1.254" \
     freebox-exporter
   ```

---

## 📊 Configuration Grafana

1. Configurez Prometheus pour scraper cet exportateur sur le port `8000` (ex: `http://localhost:8000/metrics`).
2. Importez le tableau de bord prêt à l'emploi `dashboard.json` dans votre instance Grafana (menu **Dashboards** > **New** > **Import**).
3. Le tableau de bord se liera automatiquement à votre source de données Prometheus par défaut.

---

## 📄 Licence
Ce projet est libre de droits. N'hésitez pas à l'adapter et à le publier sur vos dépôts personnels !
