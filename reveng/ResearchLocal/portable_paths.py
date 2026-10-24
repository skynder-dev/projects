"""Conservative local path budget for the shipped .NET Framework reader.

No registry/policy changes, extended-path prefixes or source renaming. ZIP member
identities remain intact. Count UTF-16 units, as Win32/.NET do, not code points.
"""
from pathlib import Path

def units(value):return len(str(value).encode('utf-16-le','surrogatepass'))//2

def check_files(paths,operation):
 for raw in paths:
  path=Path(raw).absolute()
  excess=max(units(path)-259,max((units(p)-247 for p in path.parents),default=0))
  if excess>0:
   raise ValueError(operation+' stopped before writing: path exceeds the portable .NET Framework limit ('+str(units(path))+' UTF-16 units; file limit259, directory limit247). Choose a shorter Projects/research location or shorten the export name by at least '+str(excess)+' UTF-16 units. Existing source files, archives and previous previews are unchanged. File: '+path.name)
