import ctypes
from ...Generics import SDRConfiguration
import math
import numpy as np

class SDRUtils():

    bladerfs = {}
    usrps = {}

    defaultsdrconfig = SDRConfiguration(freq =915000000.0, bandwidth = 2000000, chan = 0, hw_tx_gain = 70, hw_rx_gain = 20, sw_tx_gain = -12.0)
    sdrconfig = defaultsdrconfig

    def __init__(self, componentinstancenumber) -> None:
        self.componentinstancenumber = componentinstancenumber
        self.rssi = -90
        tx_rate_for_cca = self.sdrconfig.bandwidth / 1e6
        self.samps_per_est = math.floor(18 * tx_rate_for_cca)
        pass

    def configureSdr(self, type="b200", sdrconfig=None):
        print("Not implemented configureSdr, ", type)


    def get_sdr_power(self,num_samps=1000000, chan=0):
        print("Not implemented get_sdr_power")
        pass

    def start_rx(self, rx_callback, framer):
        print("Not implemented start_rx")
        pass

    def start_sdr_rx(self):
        print("Not implemented start_sdr_rx")
        pass
      
    def stop_sdr_rx(self):
        print("Not implemented stop_sdr_rx")
        pass

    def rx_thread(self):
        print("Not implemented rx_thread")
        pass

    def transmit_samples(self, transmit_buffer):
        print("Not implemented transmit_samples")
        pass

    def finalize_transmit_samples(self):
        pass

    def shutdown(self, error = 0):
        print("Not implemented shutdown")
    

    def ischannelclear(self, threshold=-70, pout=100):
        if self.rssi < threshold:
            return True, self.rssi #TODO: TO BE IMPLEMENTED
        else:
            return False, self.rssi

    def computeRSSI(self, num_samples, buffer, type="sc16"):
        g:float = 0
        if num_samples > 0 :
            if type=="sc16":
                for i in range(num_samples):
                    val:float = math.fabs(buffer[i])/2048.0
                    g += val * val
            else:
                if type=="fc32":
                    realbuf = np.real(buffer)
                    imagbuf = np.imag(buffer)
                    for i in range(num_samples):
                        g += realbuf[i]*realbuf[i] + imagbuf[i]*imagbuf[i]
                else:
                    g=1.0
            g = g / num_samples / 1.0
            self.rssi = 10 * math.log10(math.sqrt(g/(20*2048.0))) - self.sdrconfig.hw_rx_gain
        #print("CHANNEL RSSI = ", g, self.rssi)