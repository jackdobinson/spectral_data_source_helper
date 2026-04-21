import re

C_FMT_STR_WIDTH_PATTERN = re.compile(r'%(\d*)')


def str_to_type(cfmt_str):
	width = int(C_FMT_STR_WIDTH_PATTERN.search(cfmt_str)[1])
	if 's' in cfmt_str:
		#return str
		return f'U{width}'
	elif 'e' in cfmt_str:
		return '<f8'#float
	elif 'f' in cfmt_str:
		return '<f8'#float
	elif 'g' in cfmt_str:
		return '<f8'#floatfloat
	elif 'd' in cfmt_str:
		return '<i8'#int
	else:
		return None

def str_to_width(cfmt_str):
	match = C_FMT_STR_WIDTH_PATTERN.search(cfmt_str)
	return int(match[1])