# Note: Set PLM to sync mode first followed by device sync
# Commands list: http://www.madreporite.com/insteon/commands.htm

import datetime, time
import calendar
import serial

from astral import Astral
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor


executors = {
    'default': ThreadPoolExecutor(20),
    'processpool': ProcessPoolExecutor(5)
}

sched = BackgroundScheduler(executors=executors)
sched.start()

jobs = []


ser = serial.Serial(
                    port= '/dev/ttyUSB0',
                    baudrate=19200,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    bytesize=serial.EIGHTBITS,
                    timeout=0
                    )

ser.flushInput()
ser.flushOutput()


devices = [{'name': 'House Porch Lights',
            'ontime': 'sunset',
            'ontime_offset': -30,
            'offtime': '23:30',
            'offtime_offset': 0,
            'id': [0x08, 0x2F, 0x5C]},
           {'name': 'Shop Outside Lights',
            'ontime': 'sunset',
            'ontime_offset': -30,
            'offtime': '23:30',
            'offtime_offset': 0,
            'id': [0x38, 0x63, 0xD7]},
           {'name': 'Shed Lights',
            'ontime': 'sunset',
            'ontime_offset': -30,
            'offtime': '23:30',
            'offtime_offset': 0,
            'id': [0x08, 0x2C, 0xD1]},
	       {'name': 'Shop Bench Lights',
	        'ontime': 'sunset',
	        'ontime_offset': -60,
	        'offtime': '23:30',
            'offtime_offset': 0,
	        'id': [0x1A, 0xEE, 0x97]},
           {'name': 'Shop Bench Lights (Weekend)',
            'period': {'Saturday', 'Sunday'},
            'ontime': 'sunset',
            'ontime_offset': -60,
            'offtime': '23:30',
            'offtime_offset': 0,
            'id': [0x1A, 0xEE, 0x97]},
           {'name': 'Landscape Lighting',
            'ontime': 'sunset',
            'ontime_offset': -30,
            'offtime': '23:30',
            'offtime_offset': 0,
            'id': [0x0B, 0xF6, 0xA8]},
#           {'name': 'Kitchen Lights',
#            'ontime': '12:39',
#            'ontime_offset': 0,
#            'offtime': '12:40',
#            'offtime_offset': 0,
#            'id': [0x0B, 0x9D, 0x0F]}
           ]

def sendCommand(device, state, level=0xFF):
    # init
    message = bytearray()
    message.append(0x02) # INSTEON_PLM_START
    message.append(0x62) # INSTEON_STANDARD_MESSAGE

    # device id
    for id_byte in device:
        message.append(id_byte)

    message.append(0x0F) # INSTEON_MESSAGE_FLAG

    device_state = (0x14, 0x12)[state == 'On']
    message.append(device_state) # 0x12 = FAST ON, 0x14 = FAST OFF, 0x19 = STATUS

    message.append(level) # 0x00 = 0%, 0xFF = 100%
    time.sleep(1)

    ser.write(message)
    ser.flush()


def getSolarInfo():
    a = Astral()
    a.solar_depression = 'civil'
    city = a['Seattle']
    timezone = city.timezone
    sun = city.sun(date=datetime.datetime.now())

    return sun


def scheduleAutomation():
    sun_events = getSolarInfo()
    now = datetime.datetime.now()

    # Delete all the old jobs first
    for i in xrange(len(jobs) - 1, -1 , -1):
        jobs[i].remove()
        del jobs[i]

    print(datetime.datetime.now().strftime("%Y-%m-%d %I:%M%p"))

    for index, device in enumerate(devices):
        # Check to see if its a non-recurring daily event
        today_name = calendar.day_name[datetime.datetime.now().weekday()]
        current_time = datetime.datetime.now()

        if 'period' in device.keys():
            if today_name not in device['period']:
                break

        # ontime
        if device['ontime'] == 'sunrise':
            ontime = sun_events['sunrise']
        elif device['ontime'] == 'sunset':
            ontime = sun_events['sunset']
        else:
            HM_ontime = time.strptime(device['ontime'], "%H:%M")
            ontime = now.replace(hour=HM_ontime.tm_hour, minute=HM_ontime.tm_min)
        ontime = ontime + datetime.timedelta(minutes=int(device['ontime_offset']))
        jobs.append(sched.add_job(sendCommand, trigger='cron', hour=ontime.hour, minute=ontime.minute, second=index*2, args=(device['id'], 'On')))
        print(device['name'] + ' ontime: ' + ontime.strftime('%I:%M%p'))

        # offtime
        if device['offtime'] == 'sunrise':
            offtime = sun_events['sunrise']
        elif device['offtime'] == 'sunset':
            offtime = sun_events['sunset']
        else:
            HM_offtime = time.strptime(device['offtime'], "%H:%M")
            offtime = now.replace(hour=HM_offtime.tm_hour, minute=HM_offtime.tm_min)
        offtime = offtime + datetime.timedelta(minutes=int(device['offtime_offset']))
        jobs.append(sched.add_job(sendCommand, trigger='cron', hour=offtime.hour, minute=offtime.minute, second=index*2, args=(device['id'], 'Off')))
        print(device['name'] + ' offtime: ' + offtime.strftime('%I:%M%p'))

        # Check to see if the script has been run between ontime and off time and turn on the device immediately
        if ontime < current_time < offtime:
            sendCommand(device[id], 'On')

def main():
    daily_refresh_job = sched.add_job(scheduleAutomation, trigger='cron', hour=0, minute=0 )
    scheduleAutomation()
    while True:
        time.sleep(2)


if __name__ == "__main__":
    main()
