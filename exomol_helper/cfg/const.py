"""
Holds constants or extremely simple calculated data
"""

import os
from pathlib import Path

import numpy as np

CHUNK_SIZE = 8196

REPO_ROOT = Path(__file__).parent.parent
REPO_LOCAL = REPO_ROOT / "LOCAL"

EXOMOL_URL_PREFIX : str = "exomol.com/db"
EXOMOL_DATABASE_URL : str = "https://www.exomol.com/db"
EXOMOL_DATABASE_ROOT_URL : str = "https://www.exomol.com/db/exomol.all"
EXOMOL_JSON_DATABASE_ROOT_URL : str = "https://www.exomol.com/db/exomol.all.json"

EXOMOL_API_URL_FMT : str = "https://exomol.com/api/?molecule={}"

EXOMOL_CACHE = Path(os.path.expanduser("~/data/linedata_test_storage/cache"))

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

T_ref                : float    = 296.0                                          # K                    Reference temperature (Kelvin)
P_ref                : float    = 1.0                                            # bar                  Reference pressure (bar)
EXOMOL_T_ref         : float    = 296.0                                          # K                    Reference temperature (Kelvin)
EXOMOL_P_ref         : float    = 1.0                                            # bar                  Reference pressure (bar)

k_B                  : float    = 1.380649E-23                                   # J K^{-1}             Boltzmann constant
k_boltzmann          : float    = 1.380649E-23                                   # J K^{-1}             Boltzmann constant
k_boltzmann_cgs      : float    = 1.380649E-16                                   # erg K^{-1}           Boltzman constant (cgs)

sig_B                : float    = 5.67037E-8                                     # W m^{-2} K^{-4}      Stephan Boltzmann constant

R                    : float    = 8.31446261815324                               # J mol^{-1} K^{-1}    universal gas constant
R_cgs                : float    = 8.31446261815324E7                             # erg mol^{-1} K^{-1}  universal gas constant (cgs)

G                    : float    = 6.67199976E-11                                 # m3 kg^{-1} s^{-2}    universal gravitational constant

eps_LJ               : float    = 59.7*5.67037E-8                                # J                    depth of the Lennard-Jones potential well for H2

H2_c_p               : float    = 14300.0                                        # J K^(-1}             hydrogen specific heat

c_light              : float    = 2.99792458E8                                   # m s^{-1}             Speed of light
c_light_cgs          : float    = 2.99792458E10                                  # cm s^{-1}            Speed of light (cgs)

h_planck             : float    = 6.62607015E-34                                 # J s                  Plancks constant
h_planck_cgs         : float    = 6.62607015E-27                                 # erg s                Plancks constant (cgs)

hbar_planck          : float    = 1.05457182E-34                                 # J s                  Plancks constant divided by 2*PI
hbar_planck_cgs      : float    = h_planck / (2*np.pi)                           # erg s                Plancks constant divided by 2*PI (cgs)

c2                   : float    = c_light * h_planck / k_boltzmann               # m K                  Second radiation constant
c2_cgs               : float    = c_light_cgs * h_planck_cgs / k_boltzmann_cgs   # cm K                 Second radiation constant (cgs)

N_avogadro           : float    = 6.02214129E+23                                 # mol^{-1}             Avogadro's number, number of items in one mole

Dalton               : float    = 1.66053906892E-27                              # kg                   Dalton, 1/12th of mass of a carbon atom (also known as "unified atomic mass unit")
Dalton_cgs           : float    = 1.66053906892E-24                              # g                    Dalton (cgs)

STANDARD_ISOTOPE_ALIASES = {
	'H' : '1H',
	'D' : '2H',
	'O' : '16O',
}

TRANS_STR_FLOAT32_FACTOR = 1E20