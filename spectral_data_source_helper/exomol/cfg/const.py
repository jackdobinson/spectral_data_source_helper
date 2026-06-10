


EXOMOL_URL_PREFIX : str = "exomol.com/db"
EXOMOL_DATABASE_URL : str = "https://www.exomol.com/db"
EXOMOL_DATABASE_ROOT_URL : str = "https://www.exomol.com/db/exomol.all"
EXOMOL_JSON_DATABASE_ROOT_URL : str = "https://www.exomol.com/db/exomol.all.json"

EXOMOL_API_URL_FMT : str = "https://exomol.com/api/?molecule={}"

EXOMOL_API_EXTERNAL_URL_STARTS = (
	'exomol.comhttp://',
	'exomol.comhttps://',
	'exomol.comftp://',
)

EXOMOL_API_INTERNAL_URL_START = 'exomol.com/db/'

EXOMOL_STATE_FILE_ENDINGS = (
	'.states',
	'.states.bz2',
)

EXOMOL_TRANSITION_FILE_ENDINGS = (
	'.trans',
	'.trans.bz2',
)

EXOMOL_T_ref         : float    = 296.0                                          # K                    Reference temperature (Kelvin)
EXOMOL_P_ref         : float    = 1.0                                            # bar                  Reference pressure (bar)