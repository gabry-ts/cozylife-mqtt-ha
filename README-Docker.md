# Cozylife MQTT Bridge - Docker

Questo container Docker crea un bridge MQTT per dispositivi Cozylife, permettendo l'integrazione con Home Assistant tramite MQTT Discovery.

## Avvio rapido

### Con Docker Compose (consigliato)

1. Modifica il file `docker-compose.yml` con i tuoi parametri:
   ```yaml
   environment:
     - DEVICE_IP=10.0.2.77        # IP del tuo dispositivo Cozylife
     - DEVICE_PORT=5555           # Porta del dispositivo (default: 5555)
     - MQTT_BROKER=192.168.1.254  # IP del tuo broker MQTT
     - MQTT_PORT=32774            # Porta del broker MQTT
     - DEVICE_NAME=led_letto      # Nome entità in HA
   ```

2. Avvia il servizio:
   ```bash
   docker-compose up -d
   ```

3. Verifica i log:
   ```bash
   docker-compose logs -f cozylife-mqtt-bridge
   ```

### Con Docker run

```bash
docker run -d \
  --name cozylife-mqtt-bridge \
  --network host \
  --restart unless-stopped \
  -e DEVICE_IP=10.0.2.77 \
  -e DEVICE_PORT=5555 \
  -e MQTT_BROKER=192.168.1.254 \
  -e MQTT_PORT=32774 \
  -e DEVICE_NAME=led_letto \
  cozylife-mqtt-bridge:latest
```

## Variabili d'ambiente

| Variabile | Default | Descrizione |
|-----------|---------|-------------|
| `DEVICE_IP` | `10.0.2.77` | Indirizzo IP del dispositivo Cozylife |
| `DEVICE_PORT` | `5555` | Porta TCP del dispositivo |
| `MQTT_BROKER` | `192.168.1.254` | Indirizzo IP del broker MQTT |
| `MQTT_PORT` | `32774` | Porta del broker MQTT |
| `DEVICE_NAME` | `led_letto` | Nome per l'entità in Home Assistant |

## Home Assistant

Dopo l'avvio del container, il dispositivo apparirà automaticamente in Home Assistant come `light.{DEVICE_NAME}` con supporto per:

- ✅ ON/OFF
- ✅ Controllo luminosità
- ✅ Selezione colori (HSV)
- ✅ Temperatura colore (bianco caldo/freddo)

## Risoluzione problemi

### Container non si avvia
- Verifica che i parametri IP siano corretti
- Controlla che il dispositivo Cozylife sia raggiungibile: `ping DEVICE_IP`
- Verifica la connettività al broker MQTT

### Dispositivo non appare in HA
- Controlla che MQTT Discovery sia abilitato in HA
- Verifica i log del container: `docker logs cozylife-mqtt-bridge`
- Riavvia Home Assistant se necessario

### Controllo salute
Il container include un health check che verifica la connettività al dispositivo ogni 30 secondi.

```bash
# Verifica stato
docker ps
# Stato del container dovrebbe essere "healthy"
```

## Build personalizzata

```bash
# Build dell'immagine
docker build -t cozylife-mqtt-bridge:latest .

# Push su registry (opzionale)
docker tag cozylife-mqtt-bridge:latest your-registry/cozylife-mqtt-bridge:latest
docker push your-registry/cozylife-mqtt-bridge:latest
```

## Supporto multi-dispositivo

Per più dispositivi Cozylife, crea più servizi nel `docker-compose.yml`:

```yaml
version: '3.8'
services:
  cozylife-letto:
    build: .
    environment:
      - DEVICE_IP=10.0.2.77
      - DEVICE_NAME=led_letto
      # ... altri parametri
  
  cozylife-salotto:
    build: .
    environment:
      - DEVICE_IP=10.0.2.78
      - DEVICE_NAME=led_salotto
      # ... altri parametri
```