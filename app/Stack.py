import RPi.GPIO as GPIO
import smbus
import time
import bme280
from Adafruit_PCA9685 import PCA9685
from multiprocessing import Process, Manager, Lock

def create_updates():
    retv = {"boards":{}, "find_bme":False}
    for i in range(4): 
        retv["boards"][i] = {}
        for j in range(1,5):
          retv["boards"][i][j] = {"state":0, "updated":0}
    retv['pwm'] = {'clock':{}}
    retv['pwm']['clock']['freq'] = 50
    retv['pwm']['clock']['updated'] = False
    for i in range(16): 
        retv['pwm'][i] = {}
        retv['pwm'][i]['val'] = 0
        retv['pwm'][i]['updated'] = False 
    
    retv['rpi_pwm'] = {}
    for i in range(2): retv['rpi_pwm'][i] ={'value':1,'updated':0}
    return retv





class Stack:
    def __init__(self):
        self.i2c_bus = 1
        self.rpi_pwm_pins = None#[12, 19]
        self.pwm_pins = [12, 19]
        # GPIO.setwarnings(False)
        # GPIO.setmode(GPIO.BOARD)
        # for cnt, pin in enumerate(self.rpi_pwm_pins):
        #     GPIO.setup(pin,GPIO.OUT)
        #     self.rpi_pwm_pins[cnt] = GPIO.PWM(pin,1)
        #     self.rpi_pwm_pins[cnt].start(50)	


        self.bus = smbus.SMBus(self.i2c_bus)
        self.boards = []
        self.bmes   = {}
        manager = Manager()
        self.updates = manager.dict(create_updates())
        self.find_all_boards_()
        self.current_sense = manager.dict(self.get_all_current())
        self.find_all_bme_()
        self.bme_sense     = manager.dict(self.get_all_bme_())
        self.pwm = None
        self.freq = None
        self.setup_pwm_chip_()
        self.set_pwm_freq_(50)
        

        self.flag = manager.Value('b', True)
        self.flag.value = True
        self.proc = Process(target=self.update_)
        self.proc.start()
        print(self.updates['pwm'])
        
    
    #____________________________________________________________________#
    # Only make use of the following functions #
    #____________________________________________________________________#
    def switch(self, board, channel, state):
        updates_key = self.updates["boards"]
        updates_key[board][channel]['state'] = state
        updates_key[board][channel]['updated'] = True
        self.updates["boards"] = updates_key
    
    def get_current_sensor_data(self):
        return dict(self.current_sense)
    
    def get_bme_data(self):
        return dict(self.bme_sense)
    
    def set_pwm_out(self, channel, percentage):
        updates_key = self.updates["pwm"]
        updates_key[channel]['val'] = percentage
        updates_key[channel]['updated'] = True
        self.updates['pwm'] = updates_key
        print(self.updates['pwm'])
    
    def set_pwm_freq(self, freq):
        updates_key = self.updates["pwm"]
        updates_key['clock']['freq'] = freq
        updates_key['clock']['updated'] = True
        self.updates['pwm'] = updates_key
    
    def set_rpi_pwm(self, pin, freq):
        updates_key = self.updates["rpi_pwm"]
        updates_key[pin]['value'] = freq
        updates_key[pin]['updated'] = True
        self.updates["rpi_pwm"] = updates_key

    #____________________________________________________________________#

    def update_(self):
        flag = True
        while(flag):
            if self.rpi_pwm_pins is None:
                GPIO.setwarnings(False)
                GPIO.setmode(GPIO.BOARD)
                self.rpi_pwm_pins = []
                for pin in self.pwm_pins: 
                    GPIO.setup(pin,GPIO.OUT) 
                    self.rpi_pwm_pins.append(GPIO.PWM(pin,1))
                    self.rpi_pwm_pins[-1].start(50)

            retv = self.get_all_current()
            for key in retv:
                sense_key = self.current_sense[key]
                for key2 in retv[key]:
                    sense_key[key2] = retv[key][key2]
                self.current_sense[key] = sense_key

            retv = self.updates.copy()
            updates_key = self.updates['pwm']
            updates_key['clock']['updated'] = False
            for i in range(16): updates_key[i]['updated'] = False
            self.updates['pwm'] = updates_key

            if(retv['pwm']['clock']['updated']):self.set_pwm_freq_(retv['pwm']['clock']['freq'])
            for i in range(16): 
                if(retv['pwm'][i]['updated']):
                    self.set_pwm_(i, retv['pwm'][i]['val'])

            # __________________________________ Motors ________________________________
            retv = self.updates.copy()
            updates_key = self.updates['boards']
            updates_key2 = self.updates['rpi_pwm']
            for key in updates_key2: updates_key2[key]['updated'] = 0
            self.updates['rpi_pwm'] = updates_key2
            for key in updates_key:
                for key2 in updates_key[key]:
                    updates_key[key][key2]['updated'] = 0
            self.updates['boards'] = updates_key

            for key in retv["boards"]:
                for key2 in retv["boards"][key]:
                    if(retv["boards"][key][key2]['updated']): self.switch_(key, key2, retv["boards"][key][key2]['state'])
             
            for cnt in range(2):
                if(retv['rpi_pwm'][cnt]['updated']): 
                    self.rpi_pwm_pins[cnt].ChangeFrequency(retv['rpi_pwm'][cnt]['value'])
                    # self.rpi_pwm_pins[1].ChangeFrequency(retv['rpi_pwm'][cnt]['value'])
                    # change_freq(cnt, retv['rpi_pwm'][cnt]['value'])
                    # pi_pwm.ChangeFrequency(10)
                    # print(cnt, retv['rpi_pwm'][cnt]['value'])
             # ___________________________________________________________________________

            retv = self.get_all_bme_()
            for key in retv:
                sense_key = self.bme_sense[key]
                for key2 in retv[key]:
                    sense_key[key2] = retv[key][key2]
                self.bme_sense[key] = sense_key
            flag = self.flag.value

    def swap_multiplexer_(self, num, channel):
        if(num==1):   address = 0x77
        elif(num==2): address = 0x71
        else :        return False
        if(channel < 0 or channel>7): return False
        value = 1<<channel
        try:
            self.bus.write_byte(address, value)
            return True
        except:
            return False
    
    def find_all_boards_(self):
        address = 0b01000001
        boards  = []
        for i in range(4):
            v = self.swap_multiplexer_(1, 2+i)
            if not(v): continue
            try:
                self.bus.write_byte_data(address, 0x01, 0xF0)
              #  time.sleep(1)
                self.bus.write_byte_data(address, 0x03, 0xF0)
               # time.sleep(1)
                status = self.bus.read_byte_data(address, 0x03)
                #time.sleep(1)
                if(status == 0xF0): boards.append(i)
            except Exception as e:
                print(e)
        self.boards = boards
    
    def switch_(self, board, num, state):
        address = 0b1000001
        if(num<1 or num>4): return False
        if(board in self.boards):
            v = self.swap_multiplexer_(1, 2+board)
            if not(v): return False
            try:
                new_state = self.bus.read_byte_data(address, 0x01)
                mask = 1 << (num-1)
                new_state &= 255-mask
                if(state): new_state |= mask
                self.bus.write_byte_data(address, 0x01, new_state)
                new_state = self.bus.read_byte_data(address, 0x01)
                return True
            except:
                return False
    
    def get_current_sensor(self, board, num):
        if num ==1:  address = 0b1110000
        elif num==2: address = 0b1110011
        elif num==3: address = 0b1111100
        elif num==4: address = 0b1111111
        else: return {'current':-1, 'volt':-1,'watt': -1}
        if(board in self.boards):
            v = self.swap_multiplexer_(1, 2+board)
            if not(v): return -1, -1, -1
            try:
                self.bus.write_byte_data(address, 0x0A, 0b111)
                b1 = self.bus.read_i2c_block_data(address, 0x00, 2)
                a = 22*((b1[0]<<4) + (b1[1]>>4))/(4095)
                b1 = self.bus.read_i2c_block_data(address, 0x02, 2)
                v = 57.3*((b1[0]<<4) + (b1[1]>>4))/4095
                b1 = self.bus.read_i2c_block_data(address, 0x08, 2)
                # t = 0.48*((b1[0]<<1) + (b1[1]>>7)) Max sensor Temperature
                w = a * v
                if(v==0): a=0
                return {'current':a, 'volt':v,'watt': w}
            except:
                return {'current':-1, 'volt':-1,'watt': -1}
    
    def get_all_current(self):
        retv = {}
        for board in self.boards:
            retv[board] = {}
            for i in range(1,5):
                retv[board][i] = self.get_current_sensor(board,i)
        return retv
    
    def find_all_bme_(self):
        for ch1 in range(2):
            self.swap_multiplexer_(1, ch1)
            for ch2 in range(8):
                self.swap_multiplexer_(2, ch2)
                try:
                    retv = bme280.load_calibration_params(self.bus, 0x76)
                    if(retv): self.bmes[(ch1, ch2)] = retv
                except:
                    pass
    
    def get_all_bme_(self):
        retv = {}
        for key in self.bmes:
            self.swap_multiplexer_(1,key[0])
            self.swap_multiplexer_(2,key[1])
            try:
                data = bme280.sample(self.bus, 0x76, self.bmes[key])
                retv[key[0]*8 + key[1]+1] = {'temperature':data.temperature, 'pressure':data.pressure, 'humidity':data.humidity}
            except:
                pass
        return retv

    def setup_pwm_chip_(self):
        if not(self.swap_multiplexer_(1, 6)): return False
        try:
            self.pwm = PCA9685(busnum=self.i2c_bus)
            return True
        except:
            return False
    
    def set_pwm_freq_(self, freq=50):
        if not(self.swap_multiplexer_(1, 6)): return False
        if(self.pwm is None): return False
        try:
            self.pwm.set_pwm_freq(freq)
            self.freq = freq
            return True
        except:
            return False
    
    def set_all_pwm_(self, per):
        if not(self.swap_multiplexer_(1, 6)): return False
        if(per< 0 or per>100):return False
        val = int(4096*(0.0012 + per*0.000008)*self.freq)
        try:
            self.pwm.set_all_pwm(0, val)
            return True
        except:
            return False
    
    def set_pwm_(self, channel, per):
        if not(self.swap_multiplexer_(1, 6)): 
            print("Failed to set PWM: Multiplexer error")
            return False
        if(per< 0 or per>100):
            print("Failed to set PWM: Percentage out of range")
            return False
        val = int(4096*(0.0011 + per*0.000008)*self.freq)
        try:
            self.pwm.set_pwm(channel, 0, val)
            print(f"Sent PWM to channel {channel} with duty cycle {per}%")
            return True
        except:
            print("Failed to set PWM: Exception occurred")
            return False
       
    def stop(self):
        self.flag.value = False
        self.proc.join()

if __name__=="__main__":
    stack = Stack()
    stack.switch(0, 3, 1)
    while(True):
        retv = input("Enter PWM between 0 and 100: ")
        try:
            t = int(retv)
            stack.set_pwm_out(0,t)
            print("update succesful")
        except:
            stack.switch(0, 3, 0)
            stack.stop()
            break
        # print(stack.get_current_sensor_data())
        # print(stack.get_bme_data())