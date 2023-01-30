ps aux|grep farm.py|grep -v grep |awk '{print $2}'|xargs kill -9
nohup python3 farm.py &