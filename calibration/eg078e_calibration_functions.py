## VLBI FUNCTIONS for eg078 calibration ###
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
from eg078e_calibration_functions import *
ti = time.time()

### Useful scripts called multiple times
def get_tab(uvdata, table):
    # find the number of tables of a certain type
    ver = 0
    for i in range(len(uvdata.tables)) :
        if table in uvdata.tables[i][1] :
            ver = uvdata.tables[i][0]
    print "HIGHEST TABLE OF TYPE", table, "is", ver
    return ver

def tasaver(uvdata,name):
    tasav = AIPSTask('TASAV')
    tasav.indata = uvdata
    tasav.outname = name[:8]
    tasav.go()
    os.system('rm -r eg078e_%s.TASAV' % name[:8])
    fittp = AIPSTask('FITTP')
    fittp.indata = AIPSUVData(name[:8],'TASAV',1,1)
    fittp.dataout = 'PWD:eg078e_%s.TASAV' % name[:8]
    fittp.go()

#step specific scripts
def run_load_sort(pwd,data_prefix,delete,disk):
    ## Load the data into AIPS
    fitld = AIPSTask('FITLD')
    fitld.datain = pwd+data_prefix+'_1_1.IDI'
    fitld.outdisk = disk
    fitld.digicor = -1
    fitld.doconcat = 1
    fitld.outname = data_prefix
    fitld.ncount = 3
    fitld.go()

    #Load the TASAV file which contains the pipelined tables
    fitld = AIPSTask('FITLD')
    fitld.datain = pwd+data_prefix+'_1.tasav.FITS'
    fitld.outdisk = disk
    fitld.digicor = -1
    fitld.outname = 'pipe_TSAV'
    fitld.ncount = 1
    fitld.go()

    #sort the data into time-baseline order
    uvdata = WizAIPSUVData(data_prefix,'UVDATA',disk,1)
    tasav = WizAIPSUVData('pipe_TSAV','TASAV',disk,1)

    uvsrt = AIPSTask('UVSRT')
    uvsrt.indata = uvdata
    uvsrt.outdata = uvdata
    uvsrt.sort = 'TB'
    uvsrt.go()

    dqual = AIPSTask('DQUAL')
    dqual.indata = uvdata
    dqual.fqcenter = -1
    dqual.go()
    if delete == True:
        uvdata.zap()
    uvdata = WizAIPSUVData(data_prefix,'DQUAL',disk,1)

    indxr = AIPSTask('INDXR')
    uvdata.zap_table('CL',1)
    indxr.indata = uvdata
    indxr.cparm[3] = 0.25
    indxr.go()
    if delete == True:
        uvdata.rename(data_prefix,'UVDATA',1)
    else:
        uvdata.rename(data_prefix,'UVDATA',2)

def amplitude_calibration_EVN(uvdata,tasav,disk,refant,sources,snedt_amp):
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
        snplt = AIPSTask('SNPLT')
        snplt.indata = uvdata
        snplt.sources[1] = sources[i]
        snplt.inext = 'SN'
        snplt.invers = get_tab(uvdata,'SN')
        snplt.nplots = 9
        snplt.optype = 'AMP'
        snplt.go()
        os.system('rm amp_cal_'+sources[i]+'.ps')
        lwpla = AIPSTask('LWPLA')
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
    #Interpolate SN1 into CL2
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



def initial_flag(uvdata,tasav,disk,refant):
    tacop = AIPSTask('TACOP')
    tacop.indata = tasav
    tacop.inext = 'FG'
    tacop.invers = 1
    tacop.ncount = 1
    tacop.outdata = uvdata
    tacop.go()
    print 'copied EVN flag file to data, now go manually flag please'

def eg078e_specific_flagging(uvdata,tasav,disk,refant):
    ## Some modifications to CL2 before continuing, some amplitudes are wrong, self_calibration should sort it out!
    ## T6 (ant 1) has IF2 RR at 40 gain where should be 20, seems to only affect 3C345 and DA193...?
    clcor = AIPSTask('CLCOR')
    clcor.indata = uvdata
    clcor.antennas[1] = 1
    clcor.sources[1:] = 'DA193','3C345'
    clcor.eif = 2
    clcor.bif = 2
    clcor.stokes='RR'
    clcor.opcode='GAIN'
    clcor.gainver = get_tab(uvdata,'CL')
    clcor.gainuse = get_tab(uvdata,'CL')
    clcor.clcorprm[1]=0.5
    clcor.go()
    clcor.indata = uvdata
    clcor.sources[1:] = 'DA193','3C345'
    clcor.antennas[1] = 2
    clcor.eif = 2
    clcor.bif = 2
    clcor.stokes='LL'
    clcor.opcode='GAIN'
    clcor.gainver = get_tab(uvdata,'CL')
    clcor.gainuse = get_tab(uvdata,'CL')
    clcor.clcorprm[1]=0.33
    clcor.go()

def instrumental_delay(uvdata,disk,refant,bpass,phase_cal):
    ## first fring is short timerange on DA193 as all telescopes see this source
    fring = AIPSTask('FRING')
    fring.indata = uvdata
    fring.calsour[1:] = bpass
    #fring.timerang[1:] = 0,12,54,32,0,12,59,28
    fring.docalib = 2
    fring.gainuse = 0
    fring.refant = refant
    fring.solint = 5
    fring.aparm[1:] = 3,0
    fring.dparm[9] = 1
    fring.snver = get_tab(uvdata,'SN')+1
    fring.go()

    snplt = AIPSTask('SNPLT')
    snplt.indata = uvdata
    snplt.inext = 'SN'
    snplt.invers = get_tab(uvdata,'SN')
    snplt.nplots = 8
    snplt.optype = 'DELA'
    snplt.go()

    os.system('rm instrumental_delay.ps')
    lwpla = AIPSTask('LWPLA')
    lwpla.indata = uvdata
    lwpla.plver = 1
    lwpla.invers = get_tab(uvdata,'PL')
    lwpla.outfile = 'PWD:instrumental_delay.ps'
    lwpla.go()
    for j in range(get_tab(uvdata,'PL')):
        uvdata.zap_table('PL',j)

    clcal = AIPSTask('CLCAL')
    clcal.indata = uvdata
    clcal.invers = get_tab(uvdata,'SN')
    clcal.snver  = get_tab(uvdata,'SN')
    clcal.gainver = get_tab(uvdata,'CL')
    clcal.gainuse = get_tab(uvdata,'CL')+1
    clcal.interpol = '2PT'
    clcal.dobtween = 1
    clcal.opcode = 'CALI'
    clcal.refant = refant
    clcal.go()


def dodelays(uvdata,disk,refant,bpass,phase_cal):
    fring = AIPSTask('FRING')
    fring.indata = uvdata
    fring.calsour[1:] = bpass
    fring.docalib = 2
    fring.gainuse = get_tab(uvdata,'CL')
    fring.refant = refant
    fring.solint = 1.5
    fring.weightit = 1
    fring.aparm[1:] = 3,0,0,0,1,0,0,0,1
    fring.dparm[1:]= 1,100,50,1,0,0,1
    fring.snver = get_tab(uvdata,'SN')+1
    fring.search[1:]=11,12
    fring.go()

    type_plot=['DELA','RATE','PHAS']
    for i in type_plot:
        snplt = AIPSTask('SNPLT')
        snplt.indata = uvdata
        snplt.inext = 'SN'
        snplt.opcode = 'ALIF'
        snplt.invers = get_tab(uvdata,'SN')
        snplt.nplots = 8
        snplt.optype = i
        snplt.go()

        os.system('rm fringefinder_%s.ps' % i)
        lwpla = AIPSTask('LWPLA')
        lwpla.indata = uvdata
        lwpla.plver = 1
        lwpla.invers = get_tab(uvdata,'PL')
        lwpla.outfile = 'PWD:fringefinder_%s.ps' % i
        lwpla.go()
        for j in range(get_tab(uvdata,'PL')):
            uvdata.zap_table('PL',j)


    fring = AIPSTask('FRING')
    fring.indata = uvdata
    fring.calsour[1] = phase_cal[0]
    print fring.calsour
    fring.docalib = 2
    fring.gainuse = get_tab(uvdata,'CL')
    fring.refant = refant
    fring.solint = 20
    fring.weightit = 1
    fring.aparm[1:] = 3,0,0,0,1,0,0,0,1
    fring.dparm[1:]= 1,200,50,1,0,0,1,5
    fring.snver = get_tab(uvdata,'SN')+1
    fring.search[1:]=11,12
    fring.go()
    fring = AIPSTask('FRING')
    fring.indata = uvdata
    fring.calsour[1] = phase_cal[1]
    fring.dofit[1] = 12
    fring.docalib = 2
    fring.gainuse = get_tab(uvdata,'CL')
    fring.refant = refant
    fring.solint = 5
    fring.weightit = 1
    fring.aparm[1:] = 3,0,0,0,1,0,0,0,1
    fring.dparm[1:]= 1,90,50,1,0,0,1,5
    fring.snver = get_tab(uvdata,'SN')+1
    fring.search[1:]=11,12
    fring.go()
    for i in type_plot:
        snplt = AIPSTask('SNPLT')
        snplt.indata = uvdata
        snplt.inext = 'SN'
        snplt.opcode = 'ALIF'
        snplt.invers = get_tab(uvdata,'SN')
        snplt.nplots = 8
        snplt.optype = i
        snplt.go()

        os.system('rm phase_cals_%s.ps' % i)
        lwpla = AIPSTask('LWPLA')
        lwpla.indata = uvdata
        lwpla.plver = 1
        lwpla.invers = get_tab(uvdata,'PL')
        lwpla.outfile = 'PWD:phase_cals_%s.ps' % i
        lwpla.go()
        for j in range(get_tab(uvdata,'PL')):
            uvdata.zap_table('PL',j)


def applydelays(uvdata,disk,refant,bpass,phase_cal,target):
    ## first apply solutions from phase cal to secondary phase cal & target
    x = get_tab(uvdata,'CL')
    clcal = AIPSTask('CLCAL')
    clcal.indata = uvdata
    clcal.calsour[1] = phase_cal[0]
    clcal.sources[1:] = phase_cal[1], target[0]
    clcal.invers = get_tab(uvdata,'SN')-1
    clcal.snver  = get_tab(uvdata,'SN')-1
    clcal.gainver = x
    clcal.gainuse = x+1
    clcal.doblank = 1
    clcal.dobtween = 1
    clcal.interpol = 'AMBG'
    clcal.opcode = 'CALP'
    clcal.refant = refant
    clcal.go()
    clcal = AIPSTask('CLCAL')
    clcal.indata = uvdata
    clcal.calsour[1] = phase_cal[1]
    clcal.sources[1] = target[0]
    clcal.antennas[1] = 12
    clcal.invers = get_tab(uvdata,'SN')
    clcal.snver  = get_tab(uvdata,'SN')
    clcal.gainver = x
    clcal.gainuse = x+1
    clcal.interpol = 'AMBG'
    clcal.opcode = 'CALP'
    clcal.refant = refant
    clcal.go()

    ### Then apply phase cal to themselves
    clcal = AIPSTask('CLCAL')
    clcal.indata = uvdata
    clcal.calsour[1] = phase_cal[0]
    clcal.sources[1] = phase_cal[0]
    clcal.invers = get_tab(uvdata,'SN')-1
    clcal.snver  = get_tab(uvdata,'SN')-1
    clcal.gainver = x
    clcal.gainuse = x+1
    clcal.interpol = 'SELF'
    clcal.opcode = 'CALP'
    clcal.refant = refant
    clcal.go()
    clcal = AIPSTask('CLCAL')
    clcal.indata = uvdata
    clcal.calsour[1] = phase_cal[1]
    clcal.sources[1] = phase_cal[1]
    clcal.antennas[1] = 12
    clcal.invers = get_tab(uvdata,'SN')
    clcal.snver  = get_tab(uvdata,'SN')
    clcal.gainver = x
    clcal.gainuse = x+1
    clcal.interpol = 'SELF'
    clcal.opcode = 'CALP'
    clcal.refant = refant
    clcal.go()

    ## And finally fringe fitters to themselves
    clcal = AIPSTask('CLCAL')
    clcal.indata = uvdata
    clcal.calsour[1:] = bpass
    clcal.sources[1:] = bpass
    clcal.invers = get_tab(uvdata,'SN')-2
    clcal.snver  = get_tab(uvdata,'SN')-2
    clcal.gainver = x
    clcal.gainuse = x+1
    clcal.interpol = 'SELF'
    clcal.opcode = 'CALP'
    clcal.refant = refant
    clcal.go()

    type_plot=['DELA','RATE','PHAS']
    for i in type_plot:
        snplt = AIPSTask('SNPLT')
        snplt.indata = uvdata
        snplt.inext = 'CL'
        snplt.opcode = 'ALIF'
        snplt.invers = get_tab(uvdata,'CL')
        snplt.nplots = 8
        snplt.optype = i
        snplt.go()

        os.system('rm fringefit_CL_%s.ps' % i)
        lwpla = AIPSTask('LWPLA')
        lwpla.indata = uvdata
        lwpla.plver = 1
        lwpla.invers = get_tab(uvdata,'PL')
        lwpla.outfile = 'PWD:fringefit_CL_%s.ps' % i
        lwpla.go()
        for j in range(get_tab(uvdata,'PL')):
            uvdata.zap_table('PL',j)


def bpass(uvdata,bandpass,refant,disk):
    bpass = AIPSTask('BPASS')
    bpass.indata = uvdata
    bpass.calsour[1:] = bandpass
    bpass.docalib = 2
    bpass.gainuse = get_tab(uvdata,'CL')
    bpass.bpassprm[1:] = 0,0,1,0,0,0,0,0,1,1
    bpass.soltype = 'L1R'
    bpass.bpver = 1
    bpass.go()
    for i in bandpass:
        possm = AIPSTask('POSSM')
        possm.indata = uvdata
        possm.sources[1] = i
        possm.docalib = 2
        possm.gainuse = get_tab(uvdata,'CL')
        possm.doband = 0
        possm.bpver = 1
        possm.codetype = 'A&P'
        possm.nplots = 9
        possm.go()
        os.system('rm pre-bandpass_POSSM_%s.ps' % i)
        lwpla = AIPSTask('LWPLA')
        lwpla.indata = uvdata
        lwpla.plver = 1
        lwpla.invers = get_tab(uvdata,'PL')
        lwpla.outfile = 'PWD:pre-bandpass_POSSM_%s.ps' % i
        lwpla.go()
        for j in range(get_tab(uvdata,'PL')):
            uvdata.zap_table('PL',j)
        possm.doband = 1
        possm.go()
        os.system('rm post-bandpass_POSSM_%s.ps' % i)
        lwpla = AIPSTask('LWPLA')
        lwpla.indata = uvdata
        lwpla.plver = 1
        lwpla.invers = get_tab(uvdata,'PL')
        lwpla.outfile = 'PWD:post-bandpass_POSSM_%s.ps' % i
        lwpla.go()
        for j in range(get_tab(uvdata,'PL')):
            uvdata.zap_table('PL',j)

def primary_calibrator(uvdata,phase_cal,disk,refant):
    ## Derive phases & rates for all other telescopes on first phase cal makes SN8
    fring = AIPSTask('FRING')
    fring.indata = uvdata
    fring.calsour[1] = phase_cal[0]
    fring.docalib = 2
    fring.gainuse = get_tab(uvdata,'CL')
    fring.refant = refant
    fring.doband = 1
    fring.bpver = 1
    fring.solint = 2 # ideally two points per scan now!
    fring.weightit = 1
    fring.aparm[1:] = 3,0,0,0,1,0,0,0,1
    fring.dparm[1:]= 1,100,50,1,0,0,0,2
    fring.snver = get_tab(uvdata,'SN')+1
    fring.search[1:]=11,12
    fring.go()
    ### Derive initial phases and rates for JB on second phase cal makes SN9 (edited with snedt)
    fring = AIPSTask('FRING')
    fring.indata = uvdata
    fring.calsour[1] = phase_cal[1]
    fring.dofit[1] = 12
    fring.docalib = 2
    fring.gainuse = get_tab(uvdata,'CL')
    fring.refant = refant
    fring.solint = 2
    fring.weightit = 1
    fring.aparm[1:] = 3,0,0,0,1,0,0,0,1
    fring.dparm[1:]= 1,100,5,1,0,0,0,2
    fring.snver = get_tab(uvdata,'SN')+1
    fring.search[1:]=11,12
    fring.go()
    optype = ['PHAS','RATE']
    telescope = ['JB','ALL']
    for k in [0,1]:
        for i in optype:
            snplt = AIPSTask('SNPLT')
            snplt.indata = uvdata
            snplt.inext = 'SN'
            snplt.opcode = 'ALIF'
            snplt.invers = get_tab(uvdata,'SN')-k
            snplt.nplots = 8
            snplt.optype = i
            snplt.go()
            print k
            os.system('rm primary_phase_calibrator_%s_%s.ps' % (i ,telescope[k]))
            lwpla = AIPSTask('LWPLA')
            lwpla.indata = uvdata
            lwpla.plver = 1
            lwpla.invers = get_tab(uvdata,'PL')
            lwpla.outfile = 'PWD:primary_phase_calibrator_%s_%s.ps' % (i ,telescope[k])
            lwpla.go()
            for j in range(get_tab(uvdata,'PL')):
                uvdata.zap_table('PL',j)

def primary_calibrator_apply(uvdata,phase_cal,target,disk,refant):
    x = get_tab(uvdata,'CL')
    clcal = AIPSTask('CLCAL')
    clcal.indata = uvdata
    clcal.calsour[1] = phase_cal[0]
    clcal.sources[1:] = phase_cal[1], target[0]
    clcal.invers = get_tab(uvdata,'SN')-1
    clcal.snver  = get_tab(uvdata,'SN')-1
    clcal.gainver = x
    clcal.gainuse = x+1
    clcal.doblank = 1
    clcal.dobtween = 1
    clcal.interpol = 'AMBG'
    clcal.opcode = 'CALP'
    clcal.refant = refant
    clcal.go()
    clcal = AIPSTask('CLCAL')
    clcal.indata = uvdata
    clcal.calsour[1] = phase_cal[1]
    clcal.sources[1] = target[0]
    clcal.antennas[1] = 12
    clcal.invers = get_tab(uvdata,'SN')
    clcal.snver  = get_tab(uvdata,'SN')
    clcal.gainver = x
    clcal.gainuse = x+1
    clcal.interpol = 'AMBG'
    clcal.opcode = 'CALP'
    clcal.refant = refant
    clcal.go()

    ### Then apply phase cal to themselves
    clcal = AIPSTask('CLCAL')
    clcal.indata = uvdata
    clcal.calsour[1] = phase_cal[0]
    clcal.sources[1] = phase_cal[0]
    clcal.invers = get_tab(uvdata,'SN')-1
    clcal.snver  = get_tab(uvdata,'SN')-1
    clcal.gainver = x
    clcal.gainuse = x+1
    clcal.interpol = 'SELF'
    clcal.opcode = 'CALP'
    clcal.refant = refant
    clcal.go()
    clcal = AIPSTask('CLCAL')
    clcal.indata = uvdata
    clcal.calsour[1] = phase_cal[1]
    clcal.sources[1] = phase_cal[1]
    clcal.antennas[1] = 12
    clcal.invers = get_tab(uvdata,'SN')
    clcal.snver  = get_tab(uvdata,'SN')
    clcal.gainver = x
    clcal.gainuse = x+1
    clcal.interpol = 'SELF'
    clcal.opcode = 'CALP'
    clcal.refant = refant
    clcal.go()
