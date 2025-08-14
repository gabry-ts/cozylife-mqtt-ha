#!/usr/bin/env python3
import socket
import json
import time
import threading
import paho.mqtt.client as mqtt
import sys
import signal

class CozylifeMQTTBridge:
    def __init__(self, device_ip="10.0.2.77", device_port=5555, 
                 mqtt_broker="192.168.1.254", mqtt_port=32774):
        self.device_ip = device_ip
        self.device_port = device_port
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        
        # Home Assistant MQTT Discovery topics
        self.device_id = "led_letto"
        self.discovery_prefix = "homeassistant"
        self.node_id = "cozylife_bridge"
        
        # Topics
        self.state_topic = f"{self.discovery_prefix}/light/{self.device_id}/state"
        self.command_topic = f"{self.discovery_prefix}/light/{self.device_id}/set"
        self.brightness_state_topic = f"{self.discovery_prefix}/light/{self.device_id}/brightness"
        self.brightness_command_topic = f"{self.discovery_prefix}/light/{self.device_id}/brightness/set"
        self.hs_state_topic = f"{self.discovery_prefix}/light/{self.device_id}/hs"
        self.hs_command_topic = f"{self.discovery_prefix}/light/{self.device_id}/hs/set"
        self.color_temp_state_topic = f"{self.discovery_prefix}/light/{self.device_id}/color_temp"
        self.color_temp_command_topic = f"{self.discovery_prefix}/light/{self.device_id}/color_temp/set"
        self.color_mode_state_topic = f"{self.discovery_prefix}/light/{self.device_id}/color_mode"
        self.availability_topic = f"{self.discovery_prefix}/light/{self.device_id}/availability"
        self.config_topic = f"{self.discovery_prefix}/light/{self.device_id}/config"
        
        # MQTT client setup with API v2
        self.mqtt_client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_message = self.on_mqtt_message
        self.mqtt_client.will_set(self.availability_topic, "offline", retain=True)
        
        self.running = False
        self.last_state = None
        
    def send_cozylife_command(self, cmd_type, data=None):
        """Send command to Cozylife device"""
        sn = str(int(time.time() * 1000))
        
        if cmd_type == 2:  # QUERY
            message = {"pv": 0, "cmd": 2, "sn": sn, "msg": {"attr": [0]}}
        elif cmd_type == 3:  # SET
            if data:
                attrs = list(map(int, data.keys()))
                message = {"pv": 0, "cmd": 3, "sn": sn, "msg": {"attr": attrs, "data": data}}
            else:
                return None
        else:
            return None
        
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            s.connect((self.device_ip, self.device_port))
            
            payload = json.dumps(message, separators=(',', ':')) + "\r\n"
            s.send(payload.encode('utf-8'))
            
            response = s.recv(1024)
            s.close()
            
            if response:
                return json.loads(response.decode('utf-8').strip())
        except Exception as e:
            print(f"[ERROR] Device communication: {e}")
            return None
    
    def on_mqtt_connect(self, client, userdata, flags, reason_code, properties):
        """Callback for MQTT connection"""
        if reason_code == 0:
            print(f"[MQTT] Connected to broker at {self.mqtt_broker}:{self.mqtt_port}")
            
            # Subscribe to command topics
            client.subscribe(self.command_topic)
            client.subscribe(self.brightness_command_topic)
            client.subscribe(self.hs_command_topic)
            client.subscribe(self.color_temp_command_topic)
            print(f"[MQTT] Subscribed to command topics")
            
            # Send online status
            client.publish(self.availability_topic, "online", retain=True)
            
            # Send discovery config
            self.send_discovery_config()
            
            # Initial state query
            self.query_and_publish_state()
        else:
            print(f"[MQTT] Connection failed with code {reason_code}")
    
    def send_discovery_config(self):
        """Send MQTT discovery configuration for Home Assistant"""
        config = {
            "name": "LED Letto",
            "unique_id": "cozylife_led_letto",
            "object_id": "led_letto",  # This creates entity_id: light.led_letto
            "state_topic": self.state_topic,
            "command_topic": self.command_topic,
            "brightness_state_topic": self.brightness_state_topic,
            "brightness_command_topic": self.brightness_command_topic,
            "brightness_scale": 255,  # HA uses 0-255 scale
            "hs_state_topic": self.hs_state_topic,
            "hs_command_topic": self.hs_command_topic,
            "color_temp_state_topic": self.color_temp_state_topic,
            "color_temp_command_topic": self.color_temp_command_topic,
            "color_mode_state_topic": self.color_mode_state_topic,
            "min_mireds": 153,  # 6500K
            "max_mireds": 370,  # 2700K
            "supported_color_modes": ["hs", "color_temp"],
            "payload_on": "ON",
            "payload_off": "OFF",
            "availability_topic": self.availability_topic,
            "availability_mode": "latest",
            "optimistic": False,
            "device": {
                "identifiers": [f"cozylife_{self.device_id}"],
                "name": "LED Letto",
                "model": "Cozylife Smart Light",
                "manufacturer": "Cozylife",
                "sw_version": "1.0"
            }
        }
        
        self.mqtt_client.publish(self.config_topic, json.dumps(config), retain=True)
        print(f"[MQTT] Sent discovery config")
    
    def on_mqtt_message(self, client, userdata, msg):
        """Handle incoming MQTT messages"""
        topic = msg.topic
        payload = msg.payload.decode('utf-8')
        
        print(f"[MQTT] Received: {topic} = {payload}")
        
        if topic == self.command_topic:
            # Handle ON/OFF commands
            if payload == "ON":
                result = self.send_cozylife_command(3, {"1": 255})
                if result and result.get("res") == 0:
                    print("[Device] Light turned ON")
                    time.sleep(0.5)  # Small delay to ensure state is updated
                    self.query_and_publish_state()
            elif payload == "OFF":
                result = self.send_cozylife_command(3, {"1": 0})
                if result and result.get("res") == 0:
                    print("[Device] Light turned OFF")
                    time.sleep(0.5)
                    self.query_and_publish_state()
        
        elif topic == self.brightness_command_topic:
            # Handle brightness commands (HA sends 0-255, Cozylife uses 0-1000)
            try:
                brightness_ha = int(payload)
                brightness_ha = max(0, min(255, brightness_ha))  # Clamp to 0-255
                
                # Replica conversione originale: payload['4'] = brightness * 4
                brightness_cozy = brightness_ha * 4
                
                # Turn on with brightness
                result = self.send_cozylife_command(3, {"1": 255, "4": brightness_cozy})
                if result and result.get("res") == 0:
                    print(f"[Device] Brightness set to {brightness_ha} (Cozy: {brightness_cozy})")
                    time.sleep(0.5)
                    self.query_and_publish_state()
            except ValueError:
                print(f"[ERROR] Invalid brightness value: {payload}")
        
        elif topic == self.hs_command_topic:
            # Handle HS commands (format: "H,S" where H:0-360, S:0-100)
            # Replica esatta dell'integrazione originale
            try:
                h, s = map(float, payload.split(','))
                
                # Esattamente come nell'integrazione originale (linee 181-182)
                payload_data = {
                    "1": 255,  # ON
                    "5": int(h),      # Hue: diretto 0-360
                    "6": int(s * 10)  # Saturation: 0-100 -> 0-1000
                }
                # NOTA: L'integrazione originale NON imposta il mode=1 per i colori!
                
                result = self.send_cozylife_command(3, payload_data)
                if result and result.get("res") == 0:
                    print(f"[Device] HS set to H:{h}° S:{s}% -> Cozy H:{int(h)} S:{int(s*10)}")
                    time.sleep(0.5)
                    self.query_and_publish_state()
            except Exception as e:
                print(f"[ERROR] Invalid HS value: {payload} - {e}")
        
        elif topic == self.color_temp_command_topic:
            # Handle color temperature commands (mireds from HA)
            try:
                mireds = int(payload)
                # Replica conversione dell'integrazione originale (linea 186)
                # payload['3'] = 1000 - colortemp * 2
                temp_cozy = 1000 - mireds * 2
                temp_cozy = max(0, min(1000, temp_cozy))
                
                # Set white mode and temperature
                result = self.send_cozylife_command(3, {
                    "1": 255,  # ON
                    "2": 0,    # White mode
                    "3": temp_cozy
                })
                if result and result.get("res") == 0:
                    print(f"[Device] Color temp set to {mireds} mireds (Cozy: {temp_cozy})")
                    time.sleep(0.5)
                    self.query_and_publish_state()
            except ValueError:
                print(f"[ERROR] Invalid color temp value: {payload}")
    
    def query_and_publish_state(self):
        """Query device state and publish to MQTT"""
        response = self.send_cozylife_command(2)
        
        if response and "msg" in response and "data" in response["msg"]:
            data = response["msg"]["data"]
            
            # Get state (attribute 1: 0=off, >0=on)
            is_on = data.get("1", 0) > 0
            state = "ON" if is_on else "OFF"
            
            # Get mode (attribute 2: 0=white, 1=color)
            mode = data.get("2", 0)
            
            # Get brightness (attribute 4: scala 0-4000 nell'integrazione originale!)
            brightness_cozy = data.get("4", 1000)
            # Replica conversione originale: brightness = int(state['4'] / 4)
            brightness_ha = int(brightness_cozy / 4)  # Cozylife usa scala 0-4000, HA 0-255
            
            # Publish state
            self.mqtt_client.publish(self.state_topic, state, retain=True)
            
            if is_on:
                # Publish brightness
                self.mqtt_client.publish(self.brightness_state_topic, str(brightness_ha), retain=True)
                
                if mode == 1:  # Color mode
                    # Replica lettura HS dell'integrazione originale (linea 132)
                    hue = int(data.get("5", 0))  # 0-360
                    sat = int(data.get("6", 1000) / 10)  # 0-1000 -> 0-100
                    
                    self.mqtt_client.publish(self.hs_state_topic, f"{hue},{sat}", retain=True)
                    self.mqtt_client.publish(self.color_mode_state_topic, "hs", retain=True)
                    print(f"[State] Light: {state}, H:{hue}° S:{sat}%, Brightness: {brightness_ha}")
                    
                else:  # White mode
                    # Replica conversione temperatura dell'integrazione originale (linea 135)
                    temp_cozy = data.get("3", 500)
                    # color_temp = 500 - int(state['3'] / 2)
                    mireds = 500 - int(temp_cozy / 2)
                    self.mqtt_client.publish(self.color_temp_state_topic, str(mireds), retain=True)
                    self.mqtt_client.publish(self.color_mode_state_topic, "color_temp", retain=True)
                    print(f"[State] Light: {state}, Temp: {mireds} mireds, Brightness: {brightness_ha}")
            else:
                print(f"[State] Light: {state}")
            
            self.last_state = (state, brightness_ha, mode)
    
    def poll_device(self):
        """Periodically poll device state"""
        while self.running:
            try:
                self.query_and_publish_state()
            except Exception as e:
                print(f"[ERROR] Polling failed: {e}")
            
            # Poll every 30 seconds
            for _ in range(30):
                if not self.running:
                    break
                time.sleep(1)
    
    def start(self):
        """Start the bridge"""
        self.running = True
        
        # Connect to MQTT
        print(f"[MQTT] Connecting to {self.mqtt_broker}:{self.mqtt_port}...")
        try:
            self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port, 60)
        except Exception as e:
            print(f"[ERROR] Failed to connect to MQTT: {e}")
            return
        
        # Start MQTT loop in background
        self.mqtt_client.loop_start()
        
        # Start polling thread
        poll_thread = threading.Thread(target=self.poll_device)
        poll_thread.daemon = True
        poll_thread.start()
        
        print("[Bridge] Started successfully!")
        print(f"[Bridge] Device: {self.device_ip}:{self.device_port}")
        print(f"[Bridge] MQTT: {self.mqtt_broker}:{self.mqtt_port}")
        print(f"[Bridge] Entity ID in HA: light.led_letto")
        print("[Bridge] Press Ctrl+C to stop")
        
        # Keep running
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
    
    def rgb_to_hsv(self, r, g, b):
        """Convert RGB (0-255) to HSV (H: 0-360, S: 0-1, V: 0-255)"""
        r, g, b = r/255.0, g/255.0, b/255.0
        mx = max(r, g, b)
        mn = min(r, g, b)
        df = mx - mn
        
        if mx == mn:
            h = 0
        elif mx == r:
            h = (60 * ((g-b)/df) + 360) % 360
        elif mx == g:
            h = (60 * ((b-r)/df) + 120) % 360
        elif mx == b:
            h = (60 * ((r-g)/df) + 240) % 360
        
        s = 0 if mx == 0 else df/mx
        v = mx * 255
        
        return h, s, v
    
    def hsv_to_rgb(self, h, s, v):
        """Convert HSV (H: 0-360, S: 0-1, V: 0-255) to RGB (0-255)"""
        h = h / 60
        s = s
        v = v / 255.0
        
        c = v * s
        x = c * (1 - abs((h % 2) - 1))
        m = v - c
        
        if 0 <= h < 1:
            r, g, b = c, x, 0
        elif 1 <= h < 2:
            r, g, b = x, c, 0
        elif 2 <= h < 3:
            r, g, b = 0, c, x
        elif 3 <= h < 4:
            r, g, b = 0, x, c
        elif 4 <= h < 5:
            r, g, b = x, 0, c
        else:
            r, g, b = c, 0, x
        
        return int((r+m)*255), int((g+m)*255), int((b+m)*255)
    
    def stop(self):
        """Stop the bridge"""
        print("\n[Bridge] Stopping...")
        self.running = False
        
        # Send offline status
        self.mqtt_client.publish(self.availability_topic, "offline", retain=True)
        
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()
        print("[Bridge] Stopped.")

def signal_handler(sig, frame):
    """Handle Ctrl+C"""
    sys.exit(0)

if __name__ == "__main__":
    import os
    
    # Setup signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Get configuration from environment variables
    device_ip = os.getenv('DEVICE_IP', '10.0.2.77')
    device_port = int(os.getenv('DEVICE_PORT', '5555'))
    mqtt_broker = os.getenv('MQTT_BROKER', '192.168.1.254')
    mqtt_port = int(os.getenv('MQTT_PORT', '32774'))
    
    print(f"[Config] Device: {device_ip}:{device_port}")
    print(f"[Config] MQTT: {mqtt_broker}:{mqtt_port}")
    
    # Create and start bridge
    bridge = CozylifeMQTTBridge(
        device_ip=device_ip,
        device_port=device_port,
        mqtt_broker=mqtt_broker,
        mqtt_port=mqtt_port
    )
    
    bridge.start()