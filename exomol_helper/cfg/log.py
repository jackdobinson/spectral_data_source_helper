
import logging
import datetime as dt
from types import MethodType

logging.basicConfig(format='%(levelname)s :: %(funcName)s :: %(filename)s-%(lineno)d :: %(message)s')
pkg_logger = logging.getLogger(__name__ )
pkg_logger.setLevel(logging.INFO)



progress_lgr = logging.getLogger(__name__+'.__progress')
progress_lgr.propagate = False
progress_lgr.setLevel(logging.INFO)

progress_stream_hdlr = logging.StreamHandler()
progress_stream_hdlr.setLevel(logging.INFO)

#progresss_stream_hdlr_formatter = logging.Formatter('%(levelname)s :: %(funcName)s :: %(filename)s-%(lineno)d :: %(message)s')
progresss_stream_hdlr_formatter = logging.Formatter('%(funcName)s :: PROGRESS :: %(message)s')
progress_stream_hdlr.setFormatter(progresss_stream_hdlr_formatter)
progress_stream_hdlr.terminator = '\r'

progress_lgr.addHandler(progress_stream_hdlr)

# Add attributes to `progress_lgr` so we can log on a time interval
progress_lgr.interval_seconds = 1
progress_lgr.last_log_dt = dt.datetime.now()

def __progress_lgr_is_ready(self):
	if (dt.datetime.now() - self.last_log_dt).total_seconds() > self.interval_seconds:
		return True
	return False
	
progress_lgr.is_ready = MethodType(__progress_lgr_is_ready, progress_lgr)

def __progress_lgr_log(self, *args, **kwargs):
	kwargs['stacklevel'] = kwargs.setdefault('stacklevel',1) + 1
	self.__old_log(*args,**kwargs)
	self.last_log_dt = dt.datetime.now()
progress_lgr.__old_log = progress_lgr.log
progress_lgr.log = MethodType(__progress_lgr_log, progress_lgr)


def __progress_lgr_debug(self, *args, **kwargs):
	kwargs['stacklevel'] = kwargs.setdefault('stacklevel',1) + 1
	self.__old_debug(*args,**kwargs)
	self.last_log_dt = dt.datetime.now()
progress_lgr.__old_debug = progress_lgr.debug
progress_lgr.debug = MethodType(__progress_lgr_debug, progress_lgr)

def __progress_lgr_info(self, *args, **kwargs):
	kwargs['stacklevel'] = kwargs.setdefault('stacklevel',1) + 1
	self.__old_info(*args,**kwargs)
	self.last_log_dt = dt.datetime.now()
progress_lgr.__old_info = progress_lgr.info
progress_lgr.info = MethodType(__progress_lgr_info, progress_lgr)
