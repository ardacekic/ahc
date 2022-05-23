# https://www.etsi.org/deliver/etsi_en/300300_300399/300328/02.01.01_60/en_300328v020101p.pdf
#1) Before transmission, the equipment shall perform a Clear Channel Assessment (CCA) check using energy detect. The equipment shall observe the operating channel for the duration of the CCA observation time which shall be not less than 18 μs. The channel shall be considered occupied if the energy level in the channel exceeds the threshold given in step 5 below. If the equipment finds the channel to be clear, it may transmit immediately. See figure 2 below.
#3) The total time during which an equipment has transmissions on a given channel without re-evaluating the availability of that channel, is defined as the Channel Occupancy Time.
# The Channel Occupancy Time shall be in the range 1 ms to 10 ms followed by an Idle Period of at least 5 % of the Channel Occupancy Time used in the equipment for the current Fixed Frame Period.
# The energy detection threshold for the CCA shall be proportional to the transmit power of the transmitter: for a 20 dBm e.i.r.p. transmitter the CCA threshold level (TL) shall be equal to or less than -70 dBm/MHz at the input to the receiver assuming a 0 dBi (receive) antenna assembly. This threshold level (TL) may be corrected for the (receive) antenna assembly gain (G); however, beamforming gain (Y) shall not be taken into account. For power levels less than 20 dBm e.i.r.p. the CCA threshold level may be relaxed to:
#TL = -70 dBm/MHz + 10 × log10 (100 mW / Pout) (Pout in mW e.i.r.p.)


import uhd
import math
from threading import Thread, Lock
import numpy as np
import inspect
import argparse
import inspect
import os
import re
import sys
from .SDRUtils import SDRUtils
from ...Generics import SDRConfiguration


class AhcUhdUtils(SDRUtils):
    
    def __init__(self, componentinstancenumber) -> None:
        super().__init__(componentinstancenumber)
        self.mutex = Lock()
        self.cca = False
        if not bool (self.usrps):
            self.probe_usrps()
      
    
    #defaultusrpconfig = SDRConfiguration(freq =915000000.0, bandwidth = 2000000, chan = 0, hw_tx_gain = 50, hw_rx_gain = 20, sw_tx_gain = -12.0)

    def shutdown(self, error = 0, board = None ):
        pass

    def print_versions(self, device = None ):
        pass

    def probe_usrps(self):
        localusrps = uhd.find( "")
        cnt = 0
        for u in localusrps:
            self.usrps[cnt] = u.to_string()
            print("USRP ", cnt, " is ", self.usrps[cnt])
            cnt = cnt + 1
    

    def configureSdr(self, type="b200", sdrconfig=None):
    
        #self.sdrconfig = sdrconfig
        if sdrconfig == None:
            self.sdrconfig = self.defaultsdrconfig
        else:
            self.sdrconfig = sdrconfig
        #self.devicename = "winslab_b210_" + str(self.componentinstancenumber) #device names are configured properly on devices
        try:
            #print(self.usrps)
            print("SDR my componentinstancenumber is ", int(self.componentinstancenumber))
            self.devicename = self.usrps[int(self.componentinstancenumber)] #get the list of devices online (should be done once!) and match serial to componentinstancenumber
        except Exception as ex:
            self.devicename = "THERE ARE NO USRPS CONNECTED"
            print("Exception while probing usrps ", ex)

        
        self.freq = self.sdrconfig.freq
        self.bandwidth = self.sdrconfig.bandwidth
        self.chan = self.sdrconfig.chan
        self.hw_tx_gain = self.sdrconfig.hw_tx_gain
        self.hw_rx_gain = self.sdrconfig.hw_rx_gain
        self.tx_rate= self.bandwidth
        self.rx_rate= self.bandwidth
        print(f"Configuring {self.devicename}, freq={self.freq}, bandwidth={self.bandwidth}, channel={self.chan}, hw_tx_gain={self.hw_tx_gain}, hw_rx_gain={self.hw_rx_gain}")
        #self.usrp = uhd.usrp.MultiUSRP(f"name={self.devicename}")
        self.usrp = uhd.usrp.MultiUSRP(f"{self.devicename}")
        
        self.usrp.set_rx_bandwidth(self.bandwidth, self.chan)
        self.usrp.set_tx_bandwidth(self.bandwidth, self.chan)
        
        self.usrp.set_rx_freq(self.freq, self.chan)
        self.usrp.set_tx_freq(self.freq, self.chan)
        
        self.usrp.set_rx_bandwidth(self.bandwidth,self.chan)
        self.usrp.set_tx_bandwidth(self.bandwidth,self.chan)
        
        self.usrp.set_rx_rate(self.tx_rate, self.chan)
        self.usrp.set_tx_rate(self.rx_rate, self.chan)
        
        self.usrp.set_rx_gain(self.hw_rx_gain, self.chan)
        self.usrp.set_tx_gain(self.hw_tx_gain, self.chan)

        #self.usrp.set_rx_agc(True, self.chan)
        print("------- USRP(", self.devicename, ") CONFIG --------------------")
        print("------> CHANNEL= ", self.chan)
        print("------> RX-BANDWIDTH= ", self.usrp.get_rx_bandwidth(self.chan))
        print("------> TX-BANDWIDTH= ", self.usrp.get_tx_bandwidth(self.chan))
        print("------> RX-FREQ= ", self.usrp.get_rx_freq(self.chan))
        print("------> TX-FREQ= ", self.usrp.get_tx_freq(self.chan))
        print("------> RX-RATE= ", self.usrp.get_rx_rate(self.chan))
        print("------> TX-RATE= ", self.usrp.get_tx_rate(self.chan))
        print("------> RX-GAIN-NAMES= ", self.usrp.get_rx_gain_names(self.chan))
        print("------> TX-GAIN-NAMES= ", self.usrp.get_tx_gain_names(self.chan))
        print("------> RX-GAIN= ", self.usrp.get_rx_gain(self.chan))
        print("------> TX-GAIN= ", self.usrp.get_tx_gain(self.chan))
        print("------> USRP-INFO= ", self.usrp.get_pp_string())
        #print("------> POWER-RANGE= ", self.usrp.get_rx_power_range())
        

    
        stream_args = uhd.usrp.StreamArgs('fc32', 'sc16')
        stream_args.channels = [self.chan]
        
        self.rx_streamer = self.usrp.get_rx_stream(stream_args)
        self.tx_streamer = self.usrp.get_tx_stream(stream_args)
    
    def get_sdr_power(self,num_samps=1000000, chan=0):
        uhd.dsp.signals.get_usrp_power(self.rx_streamer, num_samps, chan)
        
    
    def ischannelclear_old(self, threshold=-70, pout=100):
        self.cca = True
        cca_threshold = threshold + 10*math.log10(100/pout)
        tx_rate = self.usrp.get_rx_rate(self.chan) / 1e6
        samps_per_est = math.floor(18 * tx_rate)
        #samps_per_est = 10
        power_dbfs = 0
        self.mutex.acquire(1)
        try:
            power_dbfs = uhd.dsp.signals.get_usrp_power(self.rx_streamer, num_samps=int(samps_per_est), chan=self.chan)
        except Exception as e:
            print("Exception in CCA: ", e)
        finally:
            self.mutex.release()
            self.start_sdr_rx()
        #print("Power-dbfs=", power_dbfs)
        self.cca = False
        if (power_dbfs > cca_threshold ):
            #print(power_dbfs)
            return False, power_dbfs
        else:
            return True, power_dbfs
    
    def start_rx(self, rx_callback, framer):
        print(f"start_rx on usrp winslab_b210_{self.componentinstancenumber}")
        self.framer = framer
        self.rx_callback = rx_callback
        self.rx_rate = self.usrp.get_rx_rate()
        self.start_sdr_rx()
        t = Thread(target=self.rx_thread, args=[])
        t.daemon = True
        t.start()
        

    def start_sdr_rx(self):
        stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.start_cont)
        self.rx_streamer.issue_stream_cmd(stream_cmd)
        
    def stop_sdr_rx(self):
        self.rx_streamer.issue_stream_cmd(uhd.types.StreamCMD(uhd.types.StreamMode.stop_cont))
    


    def rx_thread(self):
        print(f"rx_thread on usrp {self.devicename} on node {self.componentinstancenumber}")
        while(self.receiveenabled == True):
            #self.mutex.acquire(1)
            try:
                had_an_overflow = False
                rx_metadata = uhd.types.RXMetadata()
                max_samps_per_packet = self.rx_streamer.get_max_num_samps()
                recv_buffer = np.zeros( max_samps_per_packet, dtype=np.complex64)
                num_rx_samps = self.rx_streamer.recv(recv_buffer, rx_metadata)
                self.rx_callback(num_rx_samps, recv_buffer)
                if num_rx_samps > self.samps_per_est:
                    self.computeRSSI( self.samps_per_est, recv_buffer[:self.samps_per_est],type="fc32")
            except RuntimeError as ex:
                print("Runtime error in receive: %s", ex)
            finally:
                #self.mutex.release()
                pass
            # if rx_metadata.error_code == uhd.types.RXMetadataErrorCode.none:
            #     pass
            # elif rx_metadata.error_code == uhd.types.RXMetadataErrorCode.overflow:
            #     #print("Receiver error: overflow  %s, continuing...", rx_metadata.strerror())
            #     pass
            # elif rx_metadata.error_code == uhd.types.RXMetadataErrorCode.late:
            #     #print("Receiver error: late %s, continuing...", rx_metadata.strerror())
            #     pass
            # elif rx_metadata.error_code == uhd.types.RXMetadataErrorCode.timeout:
            #     print("Receiver error:timeout  %s, continuing...", rx_metadata.strerror())
            #     pass
            # else:
            #     print("Receiver error: %s", rx_metadata.strerror())
        print("Will not read samples from the channel any more...")           
        
    def finalize_transmit_samples(self):   
        tx_metadata = uhd.types.TXMetadata() 
        tx_metadata.end_of_burst = True
        tx_metadata.start_of_burst = False
        tx_metadata.has_time_spec = False
        num_tx_samps = self.tx_streamer.send(np.zeros((1, 0), dtype=np.complex64), tx_metadata)
        return num_tx_samps
        
    def transmit_samples(self, transmit_buffer):
        #print("Transmit")
        tx_metadata = uhd.types.TXMetadata()
        tx_metadata.has_time_spec = False
        tx_metadata.start_of_burst = False
        tx_metadata.end_of_burst = False
        num_tx_samps = self.tx_streamer.send(transmit_buffer, tx_metadata)
        return num_tx_samps