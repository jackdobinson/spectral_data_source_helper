

HITRAN_PF_URL_FMT = 'https://www.hitran.org/data/Q/q{global_id}.txt'
HITRAN_160_PAR_FILE_API_URL_FMT = "https://hitran.org/lbl/api?iso_ids_list={global_id}&head=False&fixwidth=0"
HITRAN_API_URL_FMT = "https://hitran.org/lbl/api?iso_ids_list={global_id}&head=False&fixwidth=0&sep=[comma]&request_params={par_list}"


HITRAN_INDEX = None

HITRAN_PF_DATA = None

HITRAN_ISO_ID_FROM_SINGLE_CHAR_MAP = {0:10,'A':11,'B':12}
HITRAN_ISO_ID_TO_SINGLE_CHAR_MAP = dict((v,k) for k,v in HITRAN_ISO_ID_FROM_SINGLE_CHAR_MAP.items())

# Some broadening parameters we get when downloading them are not the correct data (but are surrounded by good data).
# Therefore, use these to detect those cases and set broadening parameters to NANs for the bad lines.
HITRAN_BAD_BROADENER_LINE_STARTS : dict[int,str] = { # global id : tuple of bad starting strings
	85 : (' 51',),
	95 : ('1  ', ' 28'),
	131: (' 23', '   '),
	153: (' 22', '0 02'),
	157: (' 5 ', ' 53'),
}