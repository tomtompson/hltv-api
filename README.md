# hltv-api

This project offers an easy-to-use interface for extracting [HLTV](https://www.hltv.org/) data through web scraping, providing a RESTful API built with FastAPI. With this tool, developers can easily pull HLTV data into their applications, websites, or data analysis workflows.

Please be aware that the deployed version is intended for testing purposes and includes rate limiting. For more flexibility and customization, it's recommended to host the service on your own cloud infrastructure.

### API Swagger

https://hltv-json-api.fly.dev/

### Running Locally

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), if you haven't already.

```bash
git clone https://github.com/eupeutro/hltv-api.git
cd hltv-api
uv sync
uv run uvicorn app.main:app
```

Then open http://localhost:8000/

### Running via Docker Compose (recommended)

Includes the API and [FlareSolverr](https://github.com/FlareSolverr/FlareSolverr) for Cloudflare bypass.

```bash
git clone https://github.com/eupeutro/hltv-api.git
cd hltv-api
docker compose up --build
```

Then open http://localhost:8000/

### Running via Docker (standalone)

```bash
git clone https://github.com/eupeutro/hltv-api.git
cd hltv-api
docker build -t hltv-api .
docker run -d -p 8000:8000 hltv-api
```

### Environment Variables

| Variable                  | Description                                                                                            | Default                    |
| ------------------------- | ------------------------------------------------------------------------------------------------------ | -------------------------- |
| `RATE_LIMITING_ENABLE`    | Enable rate limiting for API calls                                                                     | `false`                    |
| `RATE_LIMITING_FREQUENCY` | Delay allowed between each API call. See [slowapi](https://slowapi.readthedocs.io/en/latest/) for more | `2/3seconds`               |
| `FLARESOLVERR_URL`        | FlareSolverr instance URL for Cloudflare bypass                                                        | `http://localhost:8191/v1` |

Create a `.env` file in the project root to override defaults:

```
RATE_LIMITING_ENABLE=false
RATE_LIMITING_FREQUENCY=2/3seconds
FLARESOLVERR_URL=http://localhost:8191/v1
```
