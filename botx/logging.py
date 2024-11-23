import colorlog

colorlog.basicConfig(
    format="[%(asctime)s %(log_color)s%(levelname)s%(reset)s] [%(name)s] - %(message)s",
)


def getLogger(name, level: str):
    logger = colorlog.getLogger(str(name))
    logger.setLevel(level)
    return logger
