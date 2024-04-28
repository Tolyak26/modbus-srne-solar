#!/usr/bin/env python3

from pymodbus.client import ModbusTcpClient
from pymodbus.transaction import ModbusRtuFramer
import argparse
import json

# Ошибки
errorCodes = [
    "Charge MOS short circuit",      # 0
    "Anti-reverse MOS short",        # 1
    "PV panel reversely connected",  # 2
    "PV working point over voltage", # 3
    "PV counter current",            # 4
    "PV input side over-voltage",    # 5
    "PV input side short circuit",   # 6
    "PV input overpower",            # 7
    "Ambient temp too high",         # 8
    "Controller temp too high",      # 9
    "Load over-power/current",       # 10
    "Load short circuit",            # 11
    "Battery undervoltage warning",  # 12
    "Battery overvoltage",           # 13
    "Battery over-discharge"         # 14
]

# Тип заряда
chargeModes = [
    "OFF",              # 0
    "NORMAL",           # 1
    "MPPT",             # 2
    "EQUALIZE",         # 3
    "BOOST",            # 4
    "FLOAT",            # 5
    "CURRENT_LIMITING"  # 6
]

# Вычисление минусовой температуры
def getTemp(temp):
    if(temp/int(128) > 1):
        return -(temp%128)
    return temp

def parse_args():
    global args

    parser = argparse.ArgumentParser(description= "Script for communicate and getting values from a solar controller SRNE SR-ML2420 / ML2430 / ML2440")
    parser.add_argument("ip", help="IP address of a solar controller")
    parser.add_argument("-p", "--tcp_port", dest="tcp_port", help="TCP Port of a solar controller. Default value is 20108", type=int, metavar="TCP_PORT", default=20108)
    parser.add_argument("-u", "--uid", dest="uid", help="Unit ID of a solar controller. Default value is 242", type=int, metavar="UID", default=242)
    parser.add_argument("-a", "--address", dest="address", help="Address for a scanner. Default value is 256", type=int, metavar="ADDRESS", default=256)
    parser.add_argument("-c", "--count", dest="count", help="Values count for a scanner. Default value is 35", type=int, metavar="COUNT", default=35)

    args = parser.parse_args()

def scan():
    result = {}

    modbus = ModbusTcpClient(host=args.ip,port=args.tcp_port,framer=ModbusRtuFramer)

    modbus.connect()

    response = modbus.read_holding_registers(args.address,args.count,args.uid)
    response2 = modbus.read_holding_registers(61440,30,args.uid)

    modeOffset = 32768 if response.registers[32] > 6 else 0
    chargeMode = chargeModes[response.registers[32]-modeOffset]

    errors = "None"
    errorID = response.registers[34]
    if(errorID != 0):
        errors = ""
        count = 0
        while(errorID != 0):
            if(errorID >= pow(2, 15-count)):
                # Если больше одной ошибки, делаем новую строку
                if(count > 0):
                    errors += '\n'
                errors += '- ' + errorCodes[count-1]
                errorID -= pow(2, 15-count)
            count += 1

    result['charge_mode'] = chargeMode
    result['bat_voltage'] = str(round(float(response.registers[1]*0.1), 1))
    result['bat_charge_current'] = str(round(float(response.registers[2]*0.01), 2))
    result['bat_temperature'] = str(getTemp(int(hex(response.registers[3])[-2:], 16)))
    result['bat_soc'] = str(response.registers[0])
    result['bat_charge_ah'] = str(response2.registers[6])
    result['bat_discharge_ah'] = str(response2.registers[7])
    result['load_voltage'] = str(round(float(response.registers[4]*0.1), 1))
    result['load_current'] = str(round(float(response.registers[5]*0.01), 2))
    result['load_power'] = str(response.registers[6])
    result['load_power_consum_kwh'] = str(float(response2.registers[9]*0.001))

    if response.registers[3] < 1000:
        result['device_temperature'] = '0'
    else:
        result['device_temperature'] = str(getTemp(int(hex(response.registers[3])[2:-2], 16)))

    result['panel_voltage'] = str(round(float(response.registers[7]*0.1), 1))
    result['panel_current'] = str(round(float(response.registers[8]*0.01), 2))
    result['panel_power'] = str(response.registers[9])
    result['panel_gener_kwh'] = str(float(response2.registers[8]*0.001))
    result['errors'] = errors

    print(json.dumps(result))

    modbus.close()

if __name__=="__main__":
    try:
        parse_args()
        scan()
    except Exception as e:
        print('Error:',str(e))