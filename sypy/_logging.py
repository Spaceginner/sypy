import logging
import logging.handlers
import queue


logger = logging.getLogger("sypy")


_logging_queue = queue.Queue()
_queue_handler = logging.handlers.QueueHandler(_logging_queue)
logger.addHandler(_queue_handler)

_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s - %(message)s"))

_queue_listener = logging.handlers.QueueListener(_logging_queue, _handler)
_queue_listener.start()  # TODO make it stoppable, somehow
