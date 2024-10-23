import os
import sys
if os.getenv("NUTEST_PATH"):
	LOCALPATH = os.path.join(os.getenv("NUTEST_PATH"), "workflows/acropolis/ahv/platform") # pylint: disable=line-too-long,import-error,relative-import,wrong-import-position
	sys.path.append(LOCALPATH)
