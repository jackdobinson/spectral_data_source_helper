


import datetime as dt


def dt_elapsed_time_str(dt_elapsed_delta : dt.timedelta) -> str:
	parts = (
		dt_elapsed_delta.days,
		dt_elapsed_delta.seconds//3600,
		(dt_elapsed_delta.seconds %3600)//60,
		dt_elapsed_delta.seconds%60,
		dt_elapsed_delta.microseconds
	)
	n_parts = len(parts)
	x_gt_zero = False
	return ' '.join([fmt.format(x) for i, (x, fmt) in enumerate(zip(parts, ('{}D','{:2d}H','{:2d}M','{:2d}s','{}us'))) if ((i == (n_parts-1)) | (x_gt_zero := (x_gt_zero | (x != 0))))])
	
def elapsed_time_str(seconds : float) -> str:
	parts = (
		seconds // 86400,
		(seconds%86400) // 3600,
		(seconds%3600) // 60,
		seconds%60,
	)
	n_parts = len(parts)
	x_gt_zero = False
	return ' '.join([fmt.format(x) for i, (x, fmt) in enumerate(zip(parts, ('{:.0f}D','{:2.0f}H','{:2.0f}M','{:9.6f}s'))) if ((i == (n_parts-1)) | (x_gt_zero := (x_gt_zero | (x != 0))))])
