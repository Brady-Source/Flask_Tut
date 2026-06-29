from pstats import Stats
from pathlib import Path

files = sorted(Path(r"C:\Users\dawns\OneDrive\Documents\College\CSCI335 Web Applications Programming\Flask_Tut\profile_dir").glob("*.prof"))

combined = Stats(str(files[0]))
for f in files[1:]:
    combined.add(str(f))

combined.dump_stats(r"C:\Users\dawns\OneDrive\Documents\College\CSCI335 Web Applications Programming\Flask_Tut\profile_dir\combined.prof")