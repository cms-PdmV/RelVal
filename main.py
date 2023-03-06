"""
Main module that starts flask web server
"""
import os
import os.path
import logging
import logging.handlers
import argparse
from app import app, set_app


def main():
    """
    Main function: start Flask web server
    """
    parser = argparse.ArgumentParser(description="RelVal Machine")
    parser.add_argument(
        "--mode",
        help="Use production (prod) or development (dev) section of config",
        choices=["prod", "dev"],
        required=True,
    )
    parser.add_argument(
        "--config", default="config.cfg", help="Specify non standard config file name"
    )
    parser.add_argument("--debug", help="Run Flask in debug mode", action="store_true")
    args = vars(parser.parse_args())
    debug = args.get("debug", False)

    # Set Flask app configurations
    host, port, debug = set_app(
        config_path=args.get("config"),
        mode=args.get("mode"),
        debug=debug,
    )

    logger = logging.getLogger()
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        # Do only once, before the reloader
        pid = os.getpid()
        logger.info("PID: %s", pid)
        with open("relval.pid", "w") as pid_file:
            pid_file.write(str(pid))

    logger.info("Starting... Debug: %s, Host: %s, Port: %s", debug, host, port)
    app.run(host=host, port=port, threaded=True, debug=debug)


if __name__ == "__main__":
    main()
