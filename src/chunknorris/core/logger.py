import logging

logging.basicConfig(
    format="%(asctime)s:%(name)s:%(levelname)s:%(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M",
)

LOGGER = logging.getLogger("ChunkNorris")
