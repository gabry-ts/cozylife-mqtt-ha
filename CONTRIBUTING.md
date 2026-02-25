# Contributing

Contributions are welcome!

## Setup

```bash
git clone https://github.com/gabry-ts/cozylife-mqtt-ha
cd cozylife-mqtt-ha
cp .env.example .env  # if available
docker compose up -d
```

## Workflow

1. Fork the repo
2. Create a feature branch (`git checkout -b feat/my-feature`)
3. Make your changes
4. Test with `docker compose up`
5. Submit a PR

## Code Style

- Python 3 with type hints where practical
- Environment variables for all configuration
- No hardcoded IPs, secrets, or device names
