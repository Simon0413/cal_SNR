import os 
import argparse

parser=argparse.ArgumentParser(description="genSqlite")
        
# add arguments
parser.add_argument("-f","--file",default=" ",type=str,help="file_dir")
parser.add_argument("-s","--sql",default=" ",type=str,help="sql_file")


args=parser.parse_args()
file_dir = args.file
sql_file=args.sql

count = 0

## file_dir = "/home/liuss/msarchive_rst/RATE0100/SC/2014" 
## sql_file = "/home/chenyn/workGG/data/G1_2011_2021.sqlite"
## sql_file = "/home/lianghr/Workspace/Dagangshan/data/rst/rst_2014.sqlite"

for root, dirs, files in os.walk(file_dir):
    for f in files:
        if f.endswith(".mseed"):
            path = os.path.join(root, f)
            os.system(f"../utils/mseedidx -sqlite {sql_file} {path}")
            count += 1 
            if count %100 ==0:
                print("已完成", count, path)
