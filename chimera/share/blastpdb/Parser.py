"""
This module used to contain the code for using the
BlastProteinService at RBVI, but that service was
discontinued because NCBI changed the databases to
remove gi references.  The new code is in the
ParserBlastP module now and we import the (mostly)
compatible interface here for some backwards
compatibility.
"""
from ParserBlastP import *
