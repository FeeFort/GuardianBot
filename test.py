import datetime

now = datetime.datetime.now()
time_now = datetime.time(now.hour, now.minute)
time_n = datetime.time(18)
print(time_now)
print(time_n)