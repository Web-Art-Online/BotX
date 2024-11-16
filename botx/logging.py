import colorlog

colorlog.basicConfig(
    format="[%(asctime)s %(log_color)s%(levelname)s%(reset)s] [%(name)s] - %(message)s",
)


def getLogger(id: int):
    logger = colorlog.getLogger(str(id))
    logger.setLevel("DEBUG")
    return logger
