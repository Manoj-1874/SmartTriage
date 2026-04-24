import sys
import os
sys.path.insert(0, r'e:\Nilal_thiruvila\SmartTriage_Dashboard')
import utils.integrated_dual_brain_risk
print(f'Integrated Risk File: {os.path.abspath(utils.integrated_dual_brain_risk.__file__)}')
with open(utils.integrated_dual_brain_risk.__file__, 'r', encoding='utf-8') as f:
    text = f.read()
    if 'STTABLE' in text: print('Found STTABLE in file!')
    if 'ssaturation' in text: print('Found ssaturation in file!')
    else: print('No ssaturation found in this file.')
