
# flake8: noqa # flake8 ignores this file
from ...cfg.const import * 

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

# Reference temperature and pressure defined in the [pressure broadening diet](https://doi.org/10.1016/j.jqsrt.2017.01.028) paper.
EXOMOL_T_ref         : float    = 296.0                                          # K                    Exomol Reference temperature (Kelvin)
EXOMOL_P_ref         : float    = 0.986923                                       # atm                  Exomol Reference pressure (atm)
T_ref                : float    = EXOMOL_T_ref/GLOBAL_T_ref                      # K                    Reference temperature (Kelvin)
P_ref                : float    = EXOMOL_P_ref/GLOBAL_P_ref                      # atm                  Reference pressure (atm)