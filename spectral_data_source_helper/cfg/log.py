
import logging
import logging.handlers
import queue




logging.basicConfig(format='%(levelname)s :: %(funcName)s :: %(filename)s-%(lineno)d :: %(message)s')
pkg_logger = logging.getLogger(__name__ )
pkg_logger.setLevel(logging.INFO)


# Set up progress logging to use a separate thread
q = queue.SimpleQueue()

progress_stream_hdlr = logging.StreamHandler()
progress_stream_hdlr.setLevel(logging.INFO)

#progresss_stream_hdlr_formatter = logging.Formatter('%(levelname)s :: %(funcName)s :: %(filename)s-%(lineno)d :: %(message)s')
#progresss_stream_hdlr_formatter = logging.Formatter('%(funcName)s :: PROGRESS :: %(message)s')
progresss_stream_hdlr_formatter = logging.Formatter('%(message)s')

progress_stream_hdlr.setFormatter(progresss_stream_hdlr_formatter)
progress_stream_hdlr.terminator = '\r'

q_handler = logging.handlers.QueueHandler(q)
q_listener = logging.handlers.QueueListener(q, progress_stream_hdlr)

progress_lgr = logging.getLogger(__name__+'.__progress')
progress_lgr.propagate = False
progress_lgr.setLevel(logging.INFO)

progress_lgr.addHandler(q_handler)

q_listener.start()
