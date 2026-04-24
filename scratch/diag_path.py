import sys
import os
from utils.integrated_dual_brain_risk import IntegratedDualBrainRisk

print("Python Path:", sys.path)
import utils.integrated_dual_brain_risk as idbr
print("IDBR File:", idbr.__file__)

# Read the file content directly from where it's imported
with open(idbr.__file__, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()
    if "STABLE" in content: print("Found STABLE")
    if "STTABLE" in content: print("Found STTABLE")
    if "saturation" in content: print("Found saturation")
    if "ssaturation" in content: print("Found ssaturation")
