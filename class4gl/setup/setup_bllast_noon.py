# -*- coding: utf-8 -*-
# Read data from BLLAST campaing and convert it to class4gl input

# WARNING!! stupid tab versus space formatting, grrrmmmlmlmlll!  the following command needs to be executed first: 
#    for file in RS_2011????_????_site1_MODEM_CRA.cor ;  do expand -i -t 4 $file > $file.fmt ; done

import pandas as pd
import io
import os
import numpy as np
import datetime as dt
import Pysolar
import sys
import pytz
sys.path.insert(0,'/user/home/gent/vsc422/vsc42247/software/class4gl/class4gl/')
from class4gl import class4gl_input, data_global,class4gl
from interface_multi import stations,stations_iterator, records_iterator,get_record_yaml,get_records


globaldata = data_global()
globaldata.load_datasets(recalc=0)

Rd         = 287.                  # gas constant for dry air [J kg-1 K-1]
cp         = 1005.                 # specific heat of dry air [J kg-1 K-1]
Rv         = 461.5                 # gas constant for moist air [J kg-1 K-1]
epsilon = Rd/Rv # or mv/md


def replace_iter(iterable, search, replace):
    for value in iterable:
        value.replace(search, replace)
        yield value

from class4gl import blh,class4gl_input

# definition of the humpa station
current_station = pd.Series({ "latitude"  : 42.971834,
                  "longitude" : 0.3671169,
                  "name" : "the BLLAST experiment"
                })
current_station.name = 90001





# RS_20110624_1700_site1_MODEM_CRA.cor.fmt
# RS_20110630_1700_site1_MODEM_CRA.cor.fmt
# RS_20110702_1655_site1_MODEM_CRA.cor.fmt
# RS_20110621_0509_site1_MODEM_CRA.cor.fmt

HOUR_FILES = \
{ dt.datetime(2011,6,19,0,0,0,0,pytz.UTC):{'morning':[5,'RS_20110619_0521_site1_MODEM_CRA.cor.fmt'],'afternoon':[11.25,'RS_20110619_1115_site1_MODEM_CRA.cor.fmt']},
 dt.datetime(2011,6,20,0,0,0,0,pytz.UTC):{'morning':[5,'RS_20110620_0515_site1_MODEM_CRA.cor.fmt'],'afternoon':[11.25,'RS_20110620_1115_site1_MODEM_CRA.cor.fmt']},
 dt.datetime(2011,6,25,0,0,0,0,pytz.UTC):{'morning':[5,'RS_20110625_0500_site1_MODEM_CRA.cor.fmt'],'afternoon':[11,'RS_20110625_1100_site1_MODEM_CRA.cor.fmt']},
# dt.datetime(2011,6,26,0,0,0,0,pytz.UTC):{'morning':[5,'RS_20110626_0500_site1_MODEM_CRA.cor.fmt'],'afternoon':[17,'RS_20110626_1700_site1_MODEM_CRA.cor.fmt']},
# dt.datetime(2011,6,27,0,0,0,0,pytz.UTC):{'morning':[5,'RS_20110627_0503_site1_MODEM_CRA.cor.fmt'],'afternoon':[17,'RS_20110627_1700_site1_MODEM_CRA.cor.fmt']},
 dt.datetime(2011,7, 2,0,0,0,0,pytz.UTC):{'morning':[5,'RS_20110702_0501_site1_MODEM_CRA.cor.fmt'],'afternoon':[11,'RS_20110702_1057_site1_MODEM_CRA.cor.fmt']},
# dt.datetime(2011,7, 5,0,0,0,0,pytz.UTC):{'morning':[5,'RS_20110705_0448_site1_MODEM_CRA.cor.fmt'],'afternoon':[17,'RS_20110705_1701_site1_MODEM_CRA.cor.fmt']},
}


#only include the following timeseries in the model output
timeseries_only = \
['Cm', 'Cs', 'G', 'H', 'L', 'LE', 'LEpot', 'LEref', 'LEsoil', 'LEveg', 'Lwin',
 'Lwout', 'Q', 'RH_h', 'Rib', 'Swin', 'Swout', 'T2m', 'dq', 'dtheta',
 'dthetav', 'du', 'dv', 'esat', 'gammaq', 'gammatheta', 'h', 'q', 'qsat',
 'qsurf', 'ra', 'rs', 'theta', 'thetav', 'time', 'u', 'u2m', 'ustar', 'uw',
 'v', 'v2m', 'vw', 'wq', 'wtheta', 'wthetae', 'wthetav', 'wthetae', 'zlcl']

def esat(T):
    return 0.611e3 * np.exp(17.2694 * (T - 273.16) / (T - 35.86))
def efrom_rh100_T(rh100,T):
    return esat(T)*rh100/100.
def qfrom_e_p(e,p):
    return epsilon * e/(p - (1.-epsilon)*e)

def bllast_parser(balloon_file,file_sounding,ldate,hour,c4gli=None):
        #balloon_conv = replace_iter(balloon_file,"°","deg")
        #readlines = [ str(line).replace('°','deg') for line in balloon_file.readlines()]
        #air_balloon = pd.read_fwf( io.StringIO(''.join(readlines)),skiprows=8,skipfooter=15)
        air_balloon_in = pd.read_csv(balloon_file,delimiter='\t',)
                                     #widths=[14]*19,
                                     #skiprows=9,
                                     #skipfooter=15,
                                     #decimal='.',
                                     #header=None,
                                     #names = columns,
                                     #na_values='-----')
        air_balloon_in = air_balloon_in.rename(columns=lambda x: x.strip())
        print(air_balloon_in.columns)
        rowmatches = {
            't':      lambda x: x['TaRad']+273.15,
            #'tv':     lambda x: x['Virt. Temp[C]']+273.15,
            'p':      lambda x: x['Press']*100.,
            'u':      lambda x: x['VHor'] * np.sin((90.-x['VDir'])/180.*np.pi),
            'v':      lambda x: x['VHor'] * np.cos((90.-x['VDir'])/180.*np.pi),
            'z':      lambda x: x['Altitude'] -582.,
            # from virtual temperature to absolute humidity
            'q':      lambda x: qfrom_e_p(efrom_rh100_T(x['UCal'],x['TaRad']+273.15),x['Press']*100.),
        }
        
        air_balloon = pd.DataFrame()
        for varname,lfunction in rowmatches.items():
            air_balloon[varname] = lfunction(air_balloon_in)
        
        rowmatches = {
            'R' :    lambda x: (Rd*(1.-x.q) + Rv*x.q),
            'theta': lambda x: (x['t']) * (x['p'][0]/x['p'])**(x['R']/cp),
            'thetav': lambda x: x.theta  + 0.61 * x.theta * x.q
        }
        
        for varname,lfunction in rowmatches.items():
            air_balloon[varname] = lfunction(air_balloon)
        
        dpars = {}
        dpars['longitude']  = current_station['longitude']
        dpars['latitude']  = current_station['latitude'] 
        
        dpars['STNID'] = current_station.name
        
        
        is_valid = ~np.isnan(air_balloon).any(axis=1) & (air_balloon.z >= 0)
        valid_indices = air_balloon.index[is_valid].values
        
        air_ap_mode='b'
        
        if len(valid_indices) > 0:
            dpars['h'],dpars['h_u'],dpars['h_l'] =\
                blh(air_balloon.z,air_balloon.thetav,air_balloon_in['VHor'])
            dpars['h_b'] = np.max((dpars['h'],10.))
            dpars['h_u'] = np.max((dpars['h_u'],10.)) #upper limit of mixed layer height
            dpars['h_l'] = np.max((dpars['h_l'],10.)) #low limit of mixed layer height
            dpars['h_e'] = np.abs( dpars['h_u'] - dpars['h_l']) # error of mixed-layer height
            dpars['h'] = np.round(dpars['h_'+air_ap_mode],1)
        else:
            dpars['h_u'] =np.nan
            dpars['h_l'] =np.nan
            dpars['h_e'] =np.nan
            dpars['h'] =np.nan
        
        
        
        if ~np.isnan(dpars['h']):
            dpars['Ps'] = air_balloon.p.iloc[valid_indices[0]]
        else:
            dpars['Ps'] = np.nan
        
        if ~np.isnan(dpars['h']):
        
            # determine mixed-layer properties (moisture, potential temperature...) from profile
            
            # ... and those of the mixed layer
            is_valid_below_h = is_valid & (air_balloon.z < dpars['h'])
            valid_indices_below_h =  air_balloon.index[is_valid_below_h].values
            if len(valid_indices) > 1:
                if len(valid_indices_below_h) >= 3.:
                    ml_mean = air_balloon[is_valid_below_h].mean()
                else:
                    ml_mean = air_balloon.iloc[valid_indices[0]:valid_indices[1]].mean()
            elif len(valid_indices) == 1:
                ml_mean = (air_balloon.iloc[0:1]).mean()
            else:
                temp =  pd.DataFrame(air_balloon)
                temp.iloc[0] = np.nan
                ml_mean = temp
                       
            dpars['theta']= ml_mean.theta
            dpars['q']    = ml_mean.q
            dpars['u']    = ml_mean.u
            dpars['v']    = ml_mean.v 
        else:
            dpars['theta'] = np.nan
            dpars['q'] = np.nan
            dpars['u'] = np.nan
            dpars['v'] = np.nan
        
        air_ap_head = air_balloon[0:0] #pd.DataFrame(columns = air_balloon.columns)
        # All other  data points above the mixed-layer fit
        air_ap_tail = air_balloon[air_balloon.z > dpars['h']]





        air_ap_head.z = pd.Series(np.array([2.,dpars['h'],dpars['h']]))
        jump = air_ap_head.iloc[0] * np.nan
        
        
        if air_ap_tail.shape[0] > 1:
        
            # we originally used THTA, but that has another definition than the
            # variable theta that we need which should be the temperature that
            # one would have if brought to surface (NOT reference) pressure.
            for column in ['theta','q','u','v']:
               
               # initialize the profile head with the mixed-layer values
               air_ap_head[column] = ml_mean[column]
               # calculate jump values at mixed-layer height, which will be
               # added to the third datapoint of the profile head
               jump[column] = (air_ap_tail[column].iloc[1]\
                               -\
                               air_ap_tail[column].iloc[0])\
                              /\
                              (air_ap_tail.z.iloc[1]\
                               - air_ap_tail.z.iloc[0])\
                              *\
                              (dpars['h']- air_ap_tail.z.iloc[0])\
                              +\
                              air_ap_tail[column].iloc[0]\
                              -\
                              ml_mean[column] 
               if column == 'theta':
                  # for potential temperature, we need to set a lower limit to
                  # avoid the model to crash
                  jump.theta = np.max((0.1,jump.theta))
        
               air_ap_head[column][2] += jump[column]
        
        air_ap_head.WSPD = np.sqrt(air_ap_head.u**2 +air_ap_head.v**2)


        # filter data so that potential temperature always increases with
        # height 
        cols = []
        for column in air_ap_tail.columns:
            #if column != 'z':
                cols.append(column)

        # only select samples monotonically increasing with height
        air_ap_tail_orig = pd.DataFrame(air_ap_tail)
        air_ap_tail = pd.DataFrame()
        air_ap_tail = air_ap_tail.append(air_ap_tail_orig.iloc[0],ignore_index=True)
        for ibottom in range(1,len(air_ap_tail_orig)):
            if air_ap_tail_orig.iloc[ibottom].z > air_ap_tail.iloc[-1].z +10.:
                air_ap_tail = air_ap_tail.append(air_ap_tail_orig.iloc[ibottom],ignore_index=True)




        # make theta increase strong enough to avoid numerical
        # instability
        air_ap_tail_orig = pd.DataFrame(air_ap_tail)
        air_ap_tail = pd.DataFrame()
        #air_ap_tail = air_ap_tail.append(air_ap_tail_orig.iloc[0],ignore_index=True)
        air_ap_tail = air_ap_tail.append(air_ap_tail_orig.iloc[0],ignore_index=True)
        theta_low = air_ap_head['theta'].iloc[2]
        z_low = air_ap_head['z'].iloc[2]
        ibottom = 0
        for itop in range(0,len(air_ap_tail_orig)):
            theta_mean = air_ap_tail_orig.theta.iloc[ibottom:(itop+1)].mean()
            z_mean =     air_ap_tail_orig.z.iloc[ibottom:(itop+1)].mean()
            if (
                #(z_mean > z_low) and \
                (z_mean > (z_low+10.)) and \
                #(theta_mean > (theta_low+0.2) ) and \
                #(theta_mean > (theta_low+0.2) ) and \
                 (((theta_mean - theta_low)/(z_mean - z_low)) > 0.0001)):

                air_ap_tail = air_ap_tail.append(air_ap_tail_orig.iloc[ibottom:(itop+1)].mean(),ignore_index=True)
                ibottom = itop+1
                theta_low = air_ap_tail.theta.iloc[-1]
                z_low =     air_ap_tail.z.iloc[-1]
            # elif  (itop > len(air_ap_tail_orig)-10):
            #     air_ap_tail = air_ap_tail.append(air_ap_tail_orig.iloc[itop],ignore_index=True)
        
        air_ap = \
            pd.concat((air_ap_head,air_ap_tail)).reset_index().drop(['index'],axis=1)



        # # make theta increase strong enough to avoid numerical
        # # instability
        # air_ap_tail_orig = pd.DataFrame(air_ap_tail)
        # air_ap_tail = pd.DataFrame()
        # #air_ap_tail = air_ap_tail.append(air_ap_tail_orig.iloc[0],ignore_index=True)
        # air_ap_tail = air_ap_tail.append(air_ap_tail_orig.iloc[0],ignore_index=True)
        # theta_low = air_ap_head['theta'].iloc[2]
        # z_low = air_ap_head['z'].iloc[2]
        # ibottom = 0
        # for itop in range(0,len(air_ap_tail_orig)):
        #     theta_mean = air_ap_tail_orig.theta.iloc[ibottom:(itop+1)].mean()
        #     z_mean =     air_ap_tail_orig.z.iloc[ibottom:(itop+1)].mean()
        #     if ((theta_mean > (theta_low+0.2) ) and \
        #          (((theta_mean - theta_low)/(z_mean - z_low)) > 0.001)):

        #         air_ap_tail = air_ap_tail.append(air_ap_tail_orig.iloc[ibottom:(itop+1)].mean(),ignore_index=True)
        #         ibottom = itop+1
        #         theta_low = air_ap_tail.theta.iloc[-1]
        #         z_low =     air_ap_tail.z.iloc[-1]
        #     # elif  (itop > len(air_ap_tail_orig)-10):
        #     #     air_ap_tail = air_ap_tail.append(air_ap_tail_orig.iloc[itop],ignore_index=True)
        # air_ap = \
        #     pd.concat((air_ap_head,air_ap_tail)).reset_index().drop(['index'],axis=1)
        # 
        # # we copy the pressure at ground level from balloon sounding. The
        # # pressure at mixed-layer height will be determined internally by class
        
        rho        = 1.2                   # density of air [kg m-3]
        g          = 9.81                  # gravity acceleration [m s-2]
        
        air_ap['p'].iloc[0] =dpars['Ps'] 
        air_ap['p'].iloc[1] =(dpars['Ps'] - rho * g * dpars['h'])
        air_ap['p'].iloc[2] =(dpars['Ps'] - rho * g * dpars['h'] -0.1)
        
        
        dpars['lat'] = dpars['latitude']
        # this is set to zero because we use local (sun) time as input (as if we were in Greenwhich)
        dpars['lon'] = 0.
        # this is the real longitude that will be used to extract ground data
        
        dpars['ldatetime'] = ldate+dt.timedelta(hours=hour)
        dpars['datetime'] = ldate+dt.timedelta(hours=hour)
        dpars['doy'] = dpars['datetime'].timetuple().tm_yday
        
        dpars['SolarAltitude'] = \
                                Pysolar.GetAltitude(\
                                    dpars['latitude'],\
                                    dpars['longitude'],\
                                    dpars['datetime']\
                                )
        dpars['SolarAzimuth'] =  Pysolar.GetAzimuth(\
                                    dpars['latitude'],\
                                    dpars['longitude'],\
                                    dpars['datetime']\
                                )
        
        
        dpars['lSunrise'], dpars['lSunset'] \
        =  Pysolar.util.GetSunriseSunset(dpars['latitude'],
                                         0.,
                                         dpars['ldatetime'],0.)
        
        # Warning!!! Unfortunatly!!!! WORKAROUND!!!! Even though we actually
        # write local solar time, we need to assign the timezone to UTC (which
        # is WRONG!!!). Otherwise ruby cannot understand it (it always converts
        # tolocal computer time :( ). 
        dpars['lSunrise'] = pytz.utc.localize(dpars['lSunrise'])
        dpars['lSunset'] = pytz.utc.localize(dpars['lSunset'])
        
        # This is the nearest datetime when the sun is up (for class)
        dpars['ldatetime_daylight'] = \
                                np.min(\
                                    (np.max(\
                                        (dpars['ldatetime'],\
                                         dpars['lSunrise']+dt.timedelta(hours=2))\
                                     ),\
                                     dpars['lSunset']\
                                    )\
                                )
        # apply the same time shift for UTC datetime
        dpars['datetime_daylight'] = dpars['datetime'] \
                                    +\
                                    (dpars['ldatetime_daylight']\
                                     -\
                                     dpars['ldatetime'])
        
        print('ldatetime_daylight',dpars['ldatetime_daylight'])
        print('ldatetime',dpars['ldatetime'])
        print('lSunrise',dpars['lSunrise'])
        dpars['day'] = dpars['ldatetime'].day
        
        # We set the starting time to the local sun time, since the model 
        # thinks we are always at the meridian (lon=0). This way the solar
        # radiation is calculated correctly.
        dpars['tstart'] = dpars['ldatetime_daylight'].hour \
                         + \
                         dpars['ldatetime_daylight'].minute/60.\
                         + \
                         dpars['ldatetime_daylight'].second/3600.
        
        print('tstart',dpars['tstart'])
        dpars['sw_lit'] = False
        # convert numpy types to native python data types. This provides
        # cleaner data IO with yaml:
        for key,value in dpars.items():
            if type(value).__module__ == 'numpy':
                dpars[key] = dpars[key].item()
        
                decimals = {'p':0,'t':2,'theta':4, 'z':2, 'q':5, 'u':4, 'v':4}
        # 
                for column,decimal in decimals.items():
                    air_balloon[column] = air_balloon[column].round(decimal)
                    air_ap[column] = air_ap[column].round(decimal)
        
        updateglobal = False
        if c4gli is None:
            c4gli = class4gl_input()
            updateglobal = True
        
        print('updating...')
        print(column)
        c4gli.update(source='bllast',\
                    # pars=pars,
                    pars=dpars,\
                    air_balloon=air_balloon,\
                    air_ap=air_ap)
        if updateglobal:
            c4gli.get_global_input(globaldata)

        # if profile_ini:
        #     c4gli.runtime = 10 * 3600

        c4gli.dump(file_sounding)
        
        # if profile_ini:
        #     c4gl = class4gl(c4gli)
        #     c4gl.run()
        #     c4gl.dump(file_model,\
        #               include_input=True,\
        #               timeseries_only=timeseries_only)
        #     
        #     # This will cash the observations and model tables per station for
        #     # the interface
        # 
        # if profile_ini:
        #     profile_ini=False
        # else:
        #     profile_ini=True
        return c4gli


path_soundings = '/kyukon/data/gent/gvo000/gvo00090/D2D/data/SOUNDINGS/IOPS_NOON/'


file_morning = open(path_soundings+format(current_station.name,'05d')+'_morning.yaml','w') 
for date,pair  in HOUR_FILES.items(): 
    print(pair['morning'])
    humpafn ='/user/data/gent/gvo000/gvo00090/EXT/data/SOUNDINGS/BLLAST/MODEM Radiosoundings/'+pair['morning'][1]
    
    print(humpafn)
    balloon_file = open(humpafn,'r',encoding='latin-1')

    c4gli_morning = bllast_parser(balloon_file,file_morning,date,pair['morning'][0])
    print('c4gli_morning_ldatetime 0',c4gli_morning.pars.ldatetime)
file_morning.close()

file_afternoon = open(path_soundings+format(current_station.name,'05d')+'_afternoon.yaml','w') 
for date,pair  in HOUR_FILES.items(): 
    humpafn ='/user/data/gent/gvo000/gvo00090/EXT/data/SOUNDINGS/BLLAST/MODEM Radiosoundings/'+pair['afternoon'][1]
    balloon_file = open(humpafn,'r',encoding='latin-1')

    c4gli_afternoon = bllast_parser(balloon_file,file_afternoon,date,pair['afternoon'][0])
    print('c4gli_afternoon_ldatetime 0',c4gli_afternoon.pars.ldatetime)
file_afternoon.close()
 

# file_morning = open(path_soundings+format(current_station.name,'05d')+'_morning.yaml','w') 
# for date,pair  in HOUR_FILES.items(): 
#     humpafn ='/kyukon/data/gent/gvo000/gvo00090/EXT/data/SOUNDINGS/HUMPPA/'+pair['morning'][1],
#     balloon_file = open(humpafn,'r',encoding='latin-1')
# 
#     humppa_parser(balloon_file,file_morning,hour,c4gli_morning)
#     print('c4gli_morning_ldatetime 1',c4gli_morning.pars.ldatetime)
# file_morning.close()
# 
# file_afternoon = open(path_soundings+format(current_station.name,'05d')+'_afternoon.yaml','w') 
# for hour in [18]:
#     humpafn ='/kyukon/data/gent/gvo000/gvo00090/EXT/data/SOUNDINGS/HUMPPA/humppa_080610_'+format(hour,"02d")+'00.txt'
#     balloon_file = open(humpafn,'r',encoding='latin-1')
# 
#     humppa_parser(balloon_file,file_afternoon,hour,c4gli_afternoon)
# file_afternoon.close()



# path_model = '/kyukon/data/gent/gvo000/gvo00090/D2D/data/C4GL/HUMPPA/'
# 
# file_model    = open(fnout_model+   format(current_station.name,'05d')+'.yaml','w') 


records_morning = get_records(pd.DataFrame([current_station]),\
                                           path_soundings,\
                                           subset='morning',
                                           refetch_records=True,
                                           )
print('records_morning_ldatetime',records_morning.ldatetime)

records_afternoon = get_records(pd.DataFrame([current_station]),\
                                           path_soundings,\
                                           subset='afternoon',
                                           refetch_records=True,
                                           )

# align afternoon records with noon records, and set same index
records_afternoon.index = records_afternoon.ldatetime.dt.date
records_afternoon = records_afternoon.loc[records_morning.ldatetime.dt.date]
records_afternoon.index = records_morning.index
path_exp = '/kyukon/data/gent/gvo000/gvo00090/D2D/data/C4GL/IOPS_NOON/'

os.system('mkdir -p '+path_exp)
file_morning = open(path_soundings+'/'+format(current_station.name,'05d')+'_morning.yaml')
file_afternoon = open(path_soundings+'/'+format(current_station.name,'05d')+'_afternoon.yaml')
file_ini = open(path_exp+'/'+format(current_station.name,'05d')+'_ini.yaml','w')
file_mod = open(path_exp+'/'+format(current_station.name,'05d')+'_mod.yaml','w')

for (STNID,chunk,index),record_morning in records_morning.iterrows():
    record_afternoon = records_afternoon.loc[(STNID,chunk,index)]

    c4gli_morning = get_record_yaml(file_morning, 
                                    record_morning.index_start, 
                                    record_morning.index_end,
                                    mode='ini')
    #print('c4gli_morning_ldatetime',c4gli_morning.pars.ldatetime)
    
    
    c4gli_afternoon = get_record_yaml(file_afternoon, 
                                      record_afternoon.index_start, 
                                      record_afternoon.index_end,
                                    mode='ini')

    c4gli_morning.update(source='pairs',pars={'runtime' : \
                        int((c4gli_afternoon.pars.datetime_daylight - 
                             c4gli_morning.pars.datetime_daylight).total_seconds())})

    
    c4gli_morning.pars.sw_ac = []
    c4gli_morning.pars.sw_ap = True
    c4gli_morning.pars.sw_lit = False
    c4gli_morning.dump(file_ini)
    
    c4gl = class4gl(c4gli_morning)
    c4gl.run()
    
    c4gl.dump(file_mod,\
              include_input=False,\
              timeseries_only=timeseries_only)
file_ini.close()
file_mod.close()
file_morning.close()
file_afternoon.close()

records_ini = get_records(pd.DataFrame([current_station]),\
                                           path_exp,\
                                           subset='ini',
                                           refetch_records=True,
                                           )
records_mod = get_records(pd.DataFrame([current_station]),\
                                           path_exp,\
                                           subset='mod',
                                           refetch_records=True,
                                           )

records_mod.index = records_ini.index

# align afternoon records with initial records, and set same index
records_afternoon.index = records_afternoon.ldatetime.dt.date
records_afternoon = records_afternoon.loc[records_ini.ldatetime.dt.date]
records_afternoon.index = records_ini.index



# stations_for_iter = stations(path_exp)
# for STNID,station in stations_iterator(stations_for_iter):
#     records_current_station_index = \
#             (records_ini.index.get_level_values('STNID') == STNID)
#     file_current_station_mod = STNID
# 
#     with \
#     open(path_exp+'/'+format(STNID,"05d")+'_ini.yaml','r') as file_station_ini, \
#     open(path_exp+'/'+format(STNID,"05d")+'_mod.yaml','r') as file_station_mod, \
#     open(path_soundings+'/'+format(STNID,"05d")+'_afternoon.yaml','r') as file_station_afternoon:
#         for (STNID,index),record_ini in records_iterator(records_ini):
#             c4gli_ini = get_record_yaml(file_station_ini, 
#                                         record_ini.index_start, 
#                                         record_ini.index_end,
#                                         mode='ini')
#             #print('c4gli_in_ldatetime 3',c4gli_ini.pars.ldatetime)
# 
#             record_mod = records_mod.loc[(STNID,index)]
#             c4gl_mod = get_record_yaml(file_station_mod, 
#                                         record_mod.index_start, 
#                                         record_mod.index_end,
#                                         mode='mod')
#             record_afternoon = records_afternoon.loc[(STNID,index)]
#             c4gl_afternoon = get_record_yaml(file_station_afternoon, 
#                                         record_afternoon.index_start, 
#                                         record_afternoon.index_end,
#                                         mode='ini')


# # select the samples of the afternoon list that correspond to the timing of the
# # morning list
# records_afternoon = records_afternoon.set_index('ldatetime').loc[records_afternoon.ldatetime)]
# records_afternoon.index = recods_morning.index
# 
# 
# # create intersectino index
# index_morning = pd.Index(records_morning.ldatetime.to_date())
# index_afternoon = pd.Index(records_afternoon.ldatetime.to_date())
# 
# for record_morning in records_morning.iterrows():
#     
#     c4gl = class4gl(c4gli)
#     c4gl.run()
#     c4gl.dump(c4glfile,\
#               include_input=True,\
#               timeseries_only=timeseries_only)
# 
# # This will cash the observations and model tables per station for
# # the interface
# 
# records_ini = get_records(pd.DataFrame([current_station]),\
#                                    path_mod,\
#                                    start=0,\
#                                    by=2,\
#                                    subset='ini',
#                                    refetch_records=True,
#                                    )
# records_mod = get_records(pd.DataFrame([current_station]),\
#                                    path_mod,\
#                                    start=1,\
#                                    by=2,\
#                                    subset='mod',
#                                    refetch_records=True,
#                                    )
# records_eval = get_records(pd.DataFrame([current_station]),\
#                                    path_obs,\
#                                    start=1,\
#                                    by=2,\
#                                    subset='eval',
#                                    refetch_records=True,
#                                    )
# 
# 
# # mod_scores = pd.DataFrame(index=mod_records.index)
# # for (STNID,index), current_record_mod in mod_records.iterrows():
# #     print(STNID,index)
# #     current_station = STN
# #     current_record_obs_afternoon = obs_records_afternoon.loc[(STNID,index)]
# #     current_record_obs = obs_records.loc[(STNID,index)]
# # 
# #     record_yaml_mod = get_record_yaml_mod(odirexperiments[keyEXP],\
# #                                           current_station,\
# #                                           current_record_mod,\
# #                                          )
# # 
# #     record_yaml_obs = \
# #             get_record_yaml_obs(odirexperiments[keyEXP],\
# #                                 current_station,\
# #                                 current_record_obs,\
# #                                 suffix='.yaml')
# # 
# #     record_yaml_obs_afternoon = \
# #             get_record_yaml_obs(odir,\
# #                                 current_station,\
# #                                 current_record_obs_afternoon,\
# #                                 suffix='_afternoon.yaml')
# # 
# #     hmax = np.max([record_yaml_obs_afternoon.pars.h,\
# #                    record_yaml_mod.h])
# #     HEIGHTS = {'h':hmax, '2h':2.*hmax, '3000m':3000.}
# #     
# # 
# #     for height,hvalue in HEIGHTS.items():
# # 
# #         lt_obs = (record_yaml_obs_afternoon.air_ap.HAGL < hvalue)
# #         lt_mod = (record_yaml_mod.air_ap.z < hvalue)
# #         try:
# #             mod_scores.at[(STNID,index),'rmse_'+height] = \
# #                 rmse(\
# #                     record_yaml_obs_afternoon.air_ap.theta[lt_obs],\
# #                     np.interp(\
# #                         record_yaml_obs_afternoon.air_ap.HAGL[lt_obs],\
# #                         record_yaml_mod.air_ap.z[lt_mod],\
# #                         record_yaml_mod.air_ap.theta[lt_mod]\
# #                     ))
# #         except ValueError:
# #             mod_scores.at[(STNID,index),'rmse_'+height] = np.nan
# #     # # we calculate these things in the interface itself
# #     # for key in ['q','theta','h']:
# #     #     mod_records.at[(STNID,index),'d'+key+'dt'] = \
# #     #                 (record_yaml_obs.pars.__dict__[key] -  \
# #     #                  record_yaml_mod.__dict__[key]\
# #     #                 )/(record_yaml_obs_afternoon.pars.ldatetime - \
# #     #                    record_yaml_obs.pars.ldatetime).total_seconds()
# # 
# #     #     # the actual time of the initial and evaluation sounding can be 
# #     #     # different, but we consider this as a measurement error for
# #     #     # the starting and end time of the simulation.
# #     #     obs_records_afternoon.at[(STNID,index),'d'+key+'dt'] = \
# #     #                 (record_yaml_obs.pars.__dict__[key] -  \
# #     #                  record_yaml_obs_afternoon.pars.__dict__[key]\
# #     #                 )/(record_yaml_obs_afternoon.pars.ldatetime - \
# #     #                    record_yaml_obs.pars.ldatetime).total_seconds()
# # 
# # mod_scores.to_pickle(odirexperiments[keyEXP]+'/'+format(STNID,'05d')+"_mod_scores.pkl")
# #         
# #                 
# #                 
# # # for EXP,c4glfile in c4glfiles.items():
# # #     c4glfile.close()            
# # 
# # 
# # 
# # 
# # 
# # 
# # 
# # 
# #     
# #     # {'Time[min:sec]': None 
# #     #  'P[hPa]': None, 
# #     #  'T[C]': None, 
# #     #  'U[%]': None, 
# #     #  'Wsp[m/s]': None, 
# #     #  'Wdir[Grd]': None,
# #     #  'Lon[°]', 
# #     #  'Lat[°]', 
# #     #  'Altitude[m]', 'GeoPot[m']', 'MRI',
# #     #        'Unnamed: 11', 'RI', 'Unnamed: 13', 'DewPoint[C]', 'Virt. Temp[C]',
# #     #        'Rs[m/min]D[kg/m3]Azimut[deg]', 'Elevation[deg]', 'Range[m]']
# #     # }
# #     # 
# #     # #pivotrows =
# #     # #{
# # 
# # 
# # 
