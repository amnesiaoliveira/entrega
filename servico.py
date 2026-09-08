"""Entrada de produção para o serviço Windows (sem depender do uv em execução)."""

import argparse
import logging
import os


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    os.environ["DJANGO_CONFIG_FILE"] = args.config
    os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
    from django.conf import settings
    from waitress import serve

    from config.wsgi import application

    config = settings.PRODUCTION_CONFIG
    logging.basicConfig(level=logging.INFO)
    # HTTPS termina exclusivamente no proxy local; sem confiar em cabeçalhos remotos.
    serve(
        application,
        host="127.0.0.1" if settings.HTTPS_ENABLED else "0.0.0.0",
        port=int(config["PORT"]),
        threads=4,
        url_scheme="https" if settings.HTTPS_ENABLED else "http",
        channel_timeout=60,
    )


if __name__ == "__main__":
    main()
