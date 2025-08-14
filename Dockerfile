FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir paho-mqtt

# Copy the bridge script
COPY cozylife_mqtt_bridge.py /app/

# Create non-root user for security
RUN adduser --disabled-password --gecos '' --uid 1000 bridge
USER bridge

# Set environment variables with defaults
ENV DEVICE_IP=10.0.2.77
ENV DEVICE_PORT=5555
ENV MQTT_BROKER=192.168.1.254
ENV MQTT_PORT=32774
ENV DEVICE_NAME=led_letto

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import socket; s=socket.socket(); s.settimeout(5); s.connect(('$DEVICE_IP', int('$DEVICE_PORT'))); s.close()" || exit 1

# Run the bridge
CMD python3 -u cozylife_mqtt_bridge.py