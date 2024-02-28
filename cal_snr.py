import obspy
from cal_SNR.dbdata import Client
import json
import datetime
import math
import argparse

parser=argparse.ArgumentParser(description="Calculate the SNR of phase signal and noise.")
parser.add_argument("-s","--station",default="./data/test.sta",type=str,help="stations info")
parser.add_argument("-p","--phase_file",default="./data/test.phase",type=str,help="phase catalog")
parser.add_argument("-sql","--sqlite",default="./data/test.sqlite",type=str,help="sqlite file")
parser.add_argument("-tt","--tt_json",default="./data/tt_exmp.json",type=str,help="t_time file")
parser.add_argument("-o","--output",default="./test.snr",type=str,help="output file")

args=parser.parse_args()
sta_file = args.station
pha_file = args.phase_file
sql_file = args.sqlite
tt_file = args.tt_json
out_file = args.output

# reading stations file
def _readStaFile(stationfile):
        stations={}
        file_ = open(stationfile, "r", encoding="utf-8")
        for line in file_.readlines():
            sline = [i for i in line.split(" ") if len(i)>0]
            stations[sline[0]+"."+sline[1]+"."+sline[2]]={"lon":float(sline[3]),
                    "lat": float(sline[4]),
                    "ele": float(sline[5]),
                    "net": sline[0],
                    "sta": sline[1],
                    "num": sline[2]}
        file_.close()
        return stations
print("reading stations file...",end = "")
stations=_readStaFile(sta_file)
print("end.")

# reading phase file
def _readFhaFile(phasefile):
    phas = {}
    with open(pha_file, "r") as f:
        lines = f.readlines()
        event = "event"
        pha = ["phase"]
        for line in lines:
            if line[0] == "#":
                phas[event] = pha
                event = line
                pha = []
            else:
                pha.append(line)
    del phas["event"]
    return phas
print("reading phase file...",end = "")
catalog = _readFhaFile(pha_file)
print("end.")

# function to calculate the SNR
def Cal_SNR(st,ptime,stime,phase):
    count = 0
    sum_SNR = 0
    delay = float(stime-ptime)
    for tr in st:
        count += 1
        if phase == "P":
            signal = tr.copy()
            signal.trim(starttime=ptime, endtime=ptime+delay/4, pad=True, nearest_sample=False, fill_value=0)
        else:
            signal = tr.copy()
            signal.trim(starttime=stime, endtime=stime+delay/4, pad=True, nearest_sample=False, fill_value=0)
        noise = tr.copy()
        noise.trim(starttime=ptime-delay/5-delay/4, endtime=ptime-delay/5, pad=True, nearest_sample=False, fill_value=0)
        snr = ((signal.data ** 2).sum() / len(signal.data)) / ((noise.data ** 2).sum() / len(noise.data))
        snr = 10 * math.log10(snr)
        sum_SNR += snr
    if count == 0:
        return -1
    else:
        return sum_SNR/count

# Converts information from the earthquake catalog into a dictionary
cata_time = {}
for key in catalog.keys():
    event = key.split()[1]
    cata_time[event] = {}
    for val in catalog[key]:
        val = val.split(",")
        sta = val[4].split(".")[0]+val[4].split(".")[1]
        try:
            cata_time[event][sta]["dist"] = float(val[6])
            cata_time[event][sta][val[0]] = float(val[1])
        except:
            cata_time[event][sta] = {}
            cata_time[event][sta]["dist"] = float(val[6])
            cata_time[event][sta][val[0]] = float(val[1])
cleaned = {}
for key, value in cata_time.items():
    if value:
        cleaned[key] = value
cata_time = cleaned

# Read predictive travel time information file
print("reading predict travel time file...",end = "")
with open(tt_file, 'r') as f:
    t_time = json.load(f)
print("end")

print("Start calculating the SNR...")
f = open(out_file,"w")
client = Client(sql_file)
cha = "?H?"
for key in catalog.keys():
    f.writelines(key)
    event = key.split()
    etime = datetime.datetime.strptime(f"{event[3]}-{event[4]}-{event[5]} \
                                       {event[7]}:{event[8]}:{event[9]}.{event[10]}",\
                                        "%Y-%m-%d %H:%M:%S.%f")
    etime = obspy.UTCDateTime(etime.strftime("%Y/%m/%dT%H:%M:%S.%f"))
    for val in catalog[key]:
        phase = val.split(",")
        sta = phase[4]
        if phase[0] == "P":
            ptime = etime + float(val.split(",")[1])
            try:
                stime = etime + cata_time[event[1]][sta.split(".")[0]+sta.split(".")[1]]["S"]
            except:
                stime = etime + t_time[event[1]][sta.split(".")[0]+sta.split(".")[1]]["S"]
        else:
            stime = etime + float(val.split(",")[1])
            try:
                ptime = etime + cata_time[event[1]][sta.split(".")[0]+sta.split(".")[1]]["P"]
            except:
                ptime = etime + t_time[event[1]][sta.split(".")[0]+sta.split(".")[1]]["P"]
        delay = float(stime-ptime)
        try:
            st = client.get_waveforms(stations[sta]["net"],
                    stations[sta]["sta"],
                    stations[sta]["num"], cha, ptime-delay, stime+delay)
            st.detrend(type='demean')
            st.detrend(type='linear')
            st.taper(max_percentage=0.05, max_length=0.5)
            st.filter(type='bandpass', freqmin=1, freqmax=50)
            SNR = Cal_SNR(st,ptime,stime,phase[0])
        except:
            SNR = -1
        f.writelines(val[:-2]+",SNR,"+str(SNR)+"\n")
f.close()
print("end")