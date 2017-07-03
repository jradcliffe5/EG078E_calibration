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

##### Example ParselTongue script for use with AIPS
##### Usage in command line: ParselTongue ParselTongue_example.py <mysteps>

### inputs ###
data_prefix = 'eg078e' ## file prefix (only if you have file with same name)
pwd = '/Users/jackradcliffe/Documents/EG078E_calibration/calibration/' ## current working directory (for outputs like plots etc)
disk = 1 ## AIPS disk
AIPS.userno = 1000 ## AIPS usernumber
refant = 3 #Reference antenna (should be largest antenna or closest to centre of array)
bpass = ['DA193','3C345'] ## Bandpass calibrators (solve for Amp vs. frequency)
phase_cal = ['J1241+602','J1234+619'] ## Phase calibrators (solve for phase vs time)
target = ['HDFC0155'] ## Target field
delete = False ## delete intermediate files
snedt_amp = 0
##############

mysteps = map(int,sys.argv[1:])

sources = bpass + phase_cal + target ## combine all sources together for some tasks
print sources
###

thesteps = []
### Add to this everytime you make a new calibration step
## and use these three lines to start the step (changing mystep=x)
#  mystep = 1
## if(mystep in thesteps):
##     print 'Step ', mystep, step_title[mystep]


step_title = {1: 'Load, sort, dqual & index the data',
              2: 'Amplitude calibration from EVN pipeline',
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
## e.g. this step will load data in directory /Users/jackradcliffe/Documents/EG078E_calibration/calibration/ called eg078e_1_1.IDI'
if(mystep in thesteps):
    print 'Step ', mystep, step_title[mystep]
    ## FITLD loads data
    fitld = AIPSTask('FITLD') ## initilise task first (same name as in AIPS)
    fitld.datain = pwd+data_prefix+'_1_1.IDI' ## set inputs, same as in AIPS!
    fitld.outdisk = disk
    fitld.digicor = -1
    fitld.doconcat = 1
    fitld.outname = data_prefix
    fitld.ncount = 3
    fitld.go() ## <taskname>.go() will run task with inputs above

    #sort the data into time-baseline order
    uvdata = WizAIPSUVData(data_prefix,'UVDATA',disk,1) ## Parseltongue has these special variables
    ### which hold the names of data. It is of the form WizAIPSUVData(name,class,disk,seq) look at AIPS catalogue using command pcat

    ## Uvsrt sorts it in time-baseline order
    uvsrt = AIPSTask('UVSRT')
    uvsrt.indata = uvdata ##special input of <taskname>.indata is equivalent to the AIPS getn <num> command but you use the WizAIPSUVData type i.e. uvdata in this case
    uvsrt.outdata = uvdata ## same as above but AIPS command geton <num>
    uvsrt.sort = 'TB'
    uvsrt.go()

    ## dont worry about this
    dqual = AIPSTask('DQUAL')
    dqual.indata = uvdata
    dqual.fqcenter = -1
    dqual.go()
    if delete == True:
        uvdata.zap() ### zap command deletes files in AIPS so be careful! e.g. this one will delete WizAIPSUVData(data_prefix,'UVDATA',disk,1)
    uvdata = WizAIPSUVData(data_prefix,'DQUAL',disk,1) ## redefined as DQUAL makes another copy

    ## Index the data to make sure tables are in order
    indxr = AIPSTask('INDXR')
    uvdata.zap_table('CL',1) ## Zap_table command deletes table. Command is of form .zap_table(<table type>,<table number>) and this one deletes the calibration table (CL) number 1 as we want indxr to make a new one with a different time intervals (indxr.cparm[3] = 0.25)
    indxr.indata = uvdata
    indxr.cparm[3] = 0.25
    ## Some AIPS variables have multiple inputs so need to be a python list or an AIPS list. BUT AIPS in 1 indexed and python is 0 indexed therefore the first value in a list needs to be None. Aips has special ways of doing this as follows e.g. if i want to set cparm 1 2 and 3 all to 0.25 i can either do:
    # indxr.cparm[1:] = 0.25,0.25,0.25
    # indxr.cparm = AIPSList([0.25,0.25,0.25])
    indxr.go()
    if delete == True:
        uvdata.rename(data_prefix,'UVDATA',1)
    else:
        uvdata.rename(data_prefix,'UVDATA',2)


mystep = 2 ## initialise step 2 if the input command was ParselTongue ParselTongue_example.py 2
uvdata = WizAIPSUVData(data_prefix,'UVDATA',disk,1)

## This step is for EVN telescope ONLY!!! Just showing as more examples
if(mystep in thesteps):
    print 'Step ', mystep, step_title[mystep]
    if snedt_amp == 0:
        uvdata.zap_table('SN',1)
        tacop = AIPSTask('TACOP')
        tacop.indata = tasav
        tacop.inext = 'SN'
        tacop.invers = 1
        tacop.ncount = 1
        tacop.outdata = uvdata
        tacop.go()

    for i in range(len(sources)):
        snplt = AIPSTask('SNPLT') ## SNPLT is great for plotting calibration solutions! USE IT ALOT! :)
        snplt.indata = uvdata
        snplt.sources[1] = sources[i]
        snplt.inext = 'SN'
        snplt.invers = get_tab(uvdata,'SN') ##EXTREMELY USEFUL: function get_tab(<data>,<table type>) will get the number of the highest table i.e. newest table created! See the function at the top of this script!
        snplt.nplots = 9
        snplt.optype = 'AMP'
        snplt.go()
        os.system('rm amp_cal_'+sources[i]+'.ps')
        lwpla = AIPSTask('LWPLA') ## LWPLA outputs the PL tables (with plots made by snplt to the current working directory) This example will plot PL tables per source to the file names amp_cal_'+sources[i]+'.ps' and then delete the PL tables and do SNPLT on the next source and output again etc.
        lwpla.indata = uvdata
        lwpla.plver = 1
        lwpla.invers = get_tab(uvdata,'PL')
        lwpla.outfile = 'PWD:amp_cal_'+sources[i]+'.ps'
        lwpla.go()
        for j in range(get_tab(uvdata,'PL')):
            uvdata.zap_table('PL',j)

    while True:
        s = raw_input('Is the sn table ok? ')
        if s == 'yes' or s=='y' or s=='Y':
            break
        if s == 'no' or s=='n':
            sys.exit('Use SNEDT to change tables please and change snedt_amp input to 1:')
    #Interpolate SN1 into CL2 ## KEEP TRACK OF WHAT TABLES HAVE WHAT!
    uvdata.zap_table('CL',2)
    clcal = AIPSTask('CLCAL')
    clcal.indata = uvdata
    clcal.invers = get_tab(uvdata,'SN')
    clcal.snver  = get_tab(uvdata,'SN')
    clcal.gainver = get_tab(uvdata,'CL')
    clcal.gainuse = get_tab(uvdata,'SN')+1
    clcal.interpol = '2PT'
    clcal.dobtween = -1
    clcal.refant = refant
    clcal.go()



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
