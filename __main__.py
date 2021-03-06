import logging

from argparse import ArgumentParser
from importlib import import_module

from panic.panic import Panic

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    parser = ArgumentParser(prog='panic')
    parser.add_argument('--host', dest='host', type=str, default='127.0.0.1')
    parser.add_argument('--port', dest='port', type=int, default=8000)
    parser.add_argument('--workers', dest='workers', type=int, default=1, )
    parser.add_argument('--debug', dest='debug', action="store_true")
    parser.add_argument('module')
    args = parser.parse_args()

    try:
        module_parts = args.module.split(".")
        module_name = ".".join(module_parts[:-1])
        app_name = module_parts[-1]

        module = import_module(module_name)
        app = getattr(module, app_name, None)
        if type(app) is not Panic:
            raise ValueError("Module is not a Panic app, it is a {}.  "
                             "Perhaps you meant {}.app?"
                             .format(type(app).__name__, args.module))

        app.run(host=args.host, port=args.port,
                workers=args.workers, debug=args.debug)
    except ImportError:
        logger.error("No module named {} found.\n"
                  "  Example File: project/panic_server.py -> app\n"
                  "  Example Module: project.panic_server.app"
                  .format(module_name))
    except ValueError as e:
        logger.error("{}".format(e))
