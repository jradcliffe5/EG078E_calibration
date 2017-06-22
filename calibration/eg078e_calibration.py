import os, re, time, datetime, sys, math, fnmatch
from os.path import join, getsize
from datetime import date
from collections import deque
import Utilities
from AIPS import AIPS, AIPSDisk
from AIPSTask import AIPSTask, AIPSList
from AIPSData import AIPSUVData, AIPSImage, AIPSCat
from Wizardry.AIPSData import AIPSUVData as WizAIPSUVData
import math, time, datetime
from numpy import *
import itertools, socket, glob
from time import gmtime, strftime, localtime
import eg078e_calibration_functions as eg
ti = time.time()

### inputs ###
data_prefix = 'eg078e'
pwd = '/Users/jackradcliffe/Documents/EG078E_calibration/calibration/'
disk = 1
AIPS.userno = 1000
refant = 3 #Onsala (O8)
bpass = ['DA193','3C345']
phase_cal = ['J1241+602','J1234+619']
target = ['HDFC0155']
snedt_amp = 0

## antenna info
#Array= EVN          Freq=  1594.990000 MHz     Ref.date= 08-MAR-2016
#Ant   1 = T6       BX= -2689955.0734 BY=  5443547.5847 BZ= -1415821.7368
#Ant   2 = WB       BX=   150479.3109 BY= -1916904.2248 BZ=   374432.4865
#Ant   3 = O8       BX=   -58273.1896 BY= -1428761.0198 BZ=   659174.9764
#Ant   4 = MC       BX=   942738.6601 BY= -1908629.9118 BZ=  -240929.8345
#Ant   5 = NT       BX=  1561942.3241 BY= -1866384.3989 BZ=  -884004.4695
#Ant   6 = TR       BX=   460134.8853 BY= -1176822.8367 BZ=   386547.6533
#Ant   7 = SV       BX=   -68710.4359 BY=  -363553.5608 BZ=   839479.9152
#Ant   8 = BD       BX= -1572752.8810 BY=  3608396.3315 BZ=   297181.6294
#Ant   9 = ZC       BX=  1400799.9552 BY=   413769.5117 BZ=  -298574.1928
#Ant  10 = UR       BX=  -259669.4646 BY=  3591767.2449 BZ=  -323425.1693
#Ant  11 = EF       BX=   341961.4694 BY= -2002995.9024 BZ=   209941.7748
#Ant  12 = JB       BX=  -208695.5606 BY= -2393428.8177 BZ=   395996.9676

mysteps = map(int,sys.argv[1:])

sources = bpass + phase_cal + target
print sources
###

thesteps = []
step_title = {1: 'Load, sort, dqual & index the data',
              2: 'Amplitude calibration from EVN pipeline',
              3: 'Flag table from EVN pipeline',
              4: 'Instrumental delay',
              5: 'Fringe fitting',
              6: 'Apply fringe fit solns.',
              7: 'Bandpass calibration',
              8: 'Derive solutions for the primary phase calibrator',
              9: 'Apply rate & phase to primary phase cal + JB'
}
thesteps = []
for i in range(len(step_title)):
		print 'Step ', i+1, step_title[i+1]
print '\n'
try:
	print 'List of steps to be executed ...', mysteps
	thesteps = mysteps
except:
	print 'global variable mysteps not set'

while True:
	for i in range(len(mysteps)):
		print 'Step ', mysteps[i], step_title[mysteps[i]]
	print '\n'
	s = raw_input('Are these the steps you want to conduct (yes or no): ')
	if s == 'yes' or s=='y' or s=='Y':
		break
	if s == 'no' or s=='n':
		sys.exit('Please restate the mysteps parameter')

if (thesteps==[]):
	thesteps = range(0,len(step_title))
	print 'Executing all steps: ', thesteps

mystep = 1

if(mystep in thesteps):
    print 'Step ', mystep, step_title[mystep]
    eg.run_load_sort(pwd=pwd,data_prefix=data_prefix,delete=True,disk=disk)

mystep = 2
uvdata = WizAIPSUVData(data_prefix,'UVDATA',disk,1)
tasav = WizAIPSUVData('pipe_TSAV','TASAV',disk,1)

if(mystep in thesteps):
    print 'Step ', mystep, step_title[mystep]
    eg.amplitude_calibration_EVN(uvdata,tasav,disk,refant,sources,snedt_amp)

mystep = 3
if(mystep in thesteps):
    print 'Step ', mystep, step_title[mystep]
    eg.initial_flag(uvdata,tasav,disk,refant)
    eg.eg078e_specific_flagging(uvdata,tasav,disk,refant)

mystep = 4
if(mystep in thesteps):
    print 'Step ', mystep, step_title[mystep]
    ## Makes SN4
    eg.instrumental_delay(uvdata,disk,refant,bpass,phase_cal)

mystep = 5
if(mystep in thesteps):
    print 'Step ', mystep, step_title[mystep]
    #Makes SN5, 6, 7 and do all for bandpass cals but only delay for primary phase cal and delay for JB on 2nd phs cal
    eg.dodelays(uvdata,disk,refant,bpass,phase_cal)

mystep = 6
if(mystep in thesteps):
    print 'Step ', mystep, step_title[mystep]
    eg.applydelays(uvdata,disk,refant,bpass,phase_cal,target)
    eg.tasaver(uvdata,'DELAYS')

mystep = 7
if(mystep in thesteps):
    print 'Step ', mystep, step_title[mystep]
    eg.bpass(uvdata,bpass,refant,disk)

mystep = 8
if(mystep in thesteps):
    print 'Step ', mystep, step_title[mystep]
    eg.primary_calibrator(uvdata,phase_cal,disk,refant)

mystep = 9
if(mystep in thesteps):
    print 'Step ', mystep, step_title[mystep]
    eg.primary_calibrator_apply(uvdata,phase_cal,target,disk,refant)
    eg.tasaver(uvdata,'PHASE_RATE')

    #Large solution interval fringe fit so that phase IF offsets are removed
#    fring = AIPSTask('FRING')
#    uvdata.zap_table('SN',2)
#    fring.indata = uvdata
#    fring.calsour[1:] = bpass
#    fring.docalib = -1
#    fring.gainuse = 2
#    fring.refant = AMP_refant
#    fring.solint = 10
#    fring.aparm[1:] = 3,0
#    fring.snver = 2
#    fring.go()
