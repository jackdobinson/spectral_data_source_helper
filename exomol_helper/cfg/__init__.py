

from .const import REPO_ROOT, REPO_LOCAL

if REPO_ROOT.is_dir():
	if not REPO_LOCAL.exists():
		REPO_LOCAL.mkdir()