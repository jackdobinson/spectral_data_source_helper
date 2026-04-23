


import datetime as dt


def delta_str(t_delta : dt.timedelta) -> str:
	return f'{t_delta.days}D {t_delta.seconds//3600}H {(t_delta.seconds %3600)//60}M {t_delta.seconds%60}s {t_delta.microseconds} us'