import ctypes
import numpy as np
from picosdk.ps5000a import ps5000a as ps
import matplotlib.pyplot as plt
from picosdk.functions import adc2mV, assert_pico_ok, mV2adc


class scope:
    def __init__(self):
        """
        Handles interface with the Dll
        
        """

        # Create chandle and status ready for use
        self.chandle = ctypes.c_int16()
        self.status = {}

        self.header="PS5000A_"
        self.open()

    def open(self):
        # Open 5000 series PicoScope
        # Resolution set to 12 Bit
        resolution =ps.PS5000A_DEVICE_RESOLUTION[self.header+"DR_12BIT"]
        # Returns handle to chandle for use in future API functions
        self.status["openunit"] = ps.ps5000aOpenUnit(ctypes.byref(self.chandle), None, resolution)
        try:
            assert_pico_ok(self.status["openunit"])
        except: # PicoNotOkError:

            powerStatus = self.status["openunit"]

            if powerStatus == 286:
                self.status["changePowerSource"] = ps.ps5000aChangePowerSource(self.chandle, powerStatus)
            elif powerStatus == 282:
                self.status["changePowerSource"] = ps.ps5000aChangePowerSource(self.chandle, powerStatus)
            else:
                raise

            assert_pico_ok(self.status["changePowerSource"])
    def close(self):
        self.status["closeunit"] = ps.ps5000aCloseUnit(self.chandle)

    def __del__(self):
        self.close()
        
    def channel(self,channelID: str,range:str,offset=0,coupling="DC"):
        """
        Instantiates the given channel and sets its range, offset and coupling paramaters.
        Note: this is a little clunky as it passes through a few other functions but I blame the DLL interface
        
        Parameters
        ----------
        channelId : char  
            The channel A,B,C,D 
        range : str 
            The voltage range i.e. "2V" valid values depend on scope type
        offset : float?
            The offset voltage in volts
        coupling : str
            "DC" or "AC"
        Returns
        -------
        channel : _Channel
            A channel object to interface with the channel
        """

        return self._Channel(self,channelID,range,offset,coupling)
    class _Channel():
        def __init__(self,parent,channelID: str,range:str,offset,coupling):
            """
            Creates the channel object with access to the parent scope
            For inputs see parent definition of channel
            """
            self.p=parent
            self.channel = ps.PS5000A_CHANNEL[self.p.header+"CHANNEL_"+channelID]
            self.setCh="setCh"+channelID

            self.setParams(range,offset,coupling)

        def setParams(self,range:str,offset,coupling)->None:
            """
            Instantiates the given channel and sets its range, offset and coupling paramaters.
            Note: this is a little clunky as it passes through a few other functions but I blame the DLL interface
            
            Parameters
            ----------
            range : str 
                The voltage range i.e. "2V" valid values depend on scope type
            offset : float?
                The offset voltage in volts
            coupling : str
                "DC" or "AC"
            """
            
            #For error checking this is basically a lookup table, ideally if we could know what threw the error we can print valid keys
            self.coupling_type = ps.PS5000A_COUPLING[self.p.header+coupling]
            self.chRange = ps.PS5000A_RANGE[self.p.header+range]
            
            self.p.status[self.setCh] = ps.ps5000aSetChannel(self.p.chandle, self.channel, 1, self.coupling_type, self.chRange, offset)
            assert_pico_ok(self.p.status[self.setCh])

            self.maxADC = ctypes.c_int16()
            self.p.status["maximumValue"] = ps.ps5000aMaximumValue(self.p.chandle, ctypes.byref(self.maxADC))
            assert_pico_ok(self.p.status["maximumValue"])

        
        def setupTrigger(self,voltage:float,channelID=None)->None:
            """
           Sets the trigger for the channel, if channelID=None trigger of self
        
            Parameters
            ----------
            Voltage: float
                threshold voltage in mV
            channelId : char or None 
                The channel to trigger off A,B,C,D. None for self 
            """
             
            
            # Set up single trigger
            # handle = chandle
            # enabled = 1
            if source ==None:
                source = self.channel
            else:
                source = ps.PS5000A_CHANNEL[self.p.header+"CHANNEL_"+channelID]
            threshold = int(mV2adc(voltage,self.chRange, self.maxADC))
            # direction = PS5000A_RISING = 2
            # delay = 0 s
            # auto Trigger = 1000 ms
            self.p.status["trigger"] = ps.ps5000aSetSimpleTrigger(self.p.chandle, 1, source, threshold, 2, 0, 1000)
            assert_pico_ok(self.p.status["trigger"])

        def getData(self,timebase:int,hsamp: int):
            """
            gets data for the given timebase and number of samples.
        
            Parameters
            ----------
            timebase: int
                See programming guide for full details, as its dependent on bit mode. For most cases is sample period is (timebase-2)/125E6
            hsamp : int 
                The number of samples to get before or after the trigger 
            """
           
            # Set number of pre and post trigger samples to be collected
            preTriggerSamples = hsamp
            postTriggerSamples = hsamp
            maxSamples = preTriggerSamples + postTriggerSamples

            # Get timebase information
            # Warning: When using this example it may not be possible to access all Timebases as all channels are enabled by default when opening the scope.  
            # To access these Timebases, set any unused analogue channels to off.
            # handle = chandle
            #timebase =
            # noSamples = maxSamples
            # pointer to timeIntervalNanoseconds = ctypes.byref(timeIntervalns)
            # pointer to maxSamples = ctypes.byref(returnedMaxSamples)
            # segment index = 0
            timeIntervalns = ctypes.c_float()
            returnedMaxSamples = ctypes.c_int32()
            self.p.status["getTimebase2"] = ps.ps5000aGetTimebase2(self.p.chandle, timebase, maxSamples, ctypes.byref(timeIntervalns), ctypes.byref(returnedMaxSamples), 0)
            assert_pico_ok(self.p.status["getTimebase2"])

            # Run block capture
            # handle = chandle
            # number of pre-trigger samples = preTriggerSamples
            # number of post-trigger samples = PostTriggerSamples
            # timebase = 8 = 80 ns (see Programmer's guide for mre information on timebases)
            # time indisposed ms = None (not needed in the example)
            # segment index = 0
            # lpReady = None (using ps5000aIsReady rather than ps5000aBlockReady)
            # pParameter = None
            self.p.status["runBlock"] = ps.ps5000aRunBlock(self.p.chandle, preTriggerSamples, postTriggerSamples, timebase, None, 0, None, None)
            assert_pico_ok(self.p.status["runBlock"])

            # Check for data collection to finish using ps5000aIsReady
            ready = ctypes.c_int16(0)
            check = ctypes.c_int16(0)
            while ready.value == check.value:
                self.p.status["isReady"] = ps.ps5000aIsReady(self.p.chandle, ctypes.byref(ready))


            # Create buffers ready for assigning pointers for data collection
            bufferAMax = (ctypes.c_int16 * maxSamples)()
            bufferAMin = (ctypes.c_int16 * maxSamples)() # used for downsampling which isn't in the scope of this example
           
            # Set data buffer location for data collection from channel A
            # handle = chandle
            source = self.channel#ps.PS5000A_CHANNEL["PS5000A_CHANNEL_A"]
            # pointer to buffer max = ctypes.byref(bufferAMax)
            # pointer to buffer min = ctypes.byref(bufferAMin)
            # buffer length = maxSamples
            # segment index = 0
            # ratio mode = PS5000A_RATIO_MODE_NONE = 0
            self.p.status["setDataBuffersA"] = ps.ps5000aSetDataBuffers(self.p.chandle, source, ctypes.byref(bufferAMax), ctypes.byref(bufferAMin), maxSamples, 0, 0)
            assert_pico_ok(self.p.status["setDataBuffersA"])

            # create overflow loaction
            overflow = ctypes.c_int16()
            # create converted type maxSamples
            cmaxSamples = ctypes.c_int32(maxSamples)

            # Retried data from scope to buffers assigned above
            # handle = chandle
            # start index = 0
            # pointer to number of samples = ctypes.byref(cmaxSamples)
            # downsample ratio = 0
            # downsample ratio mode = PS5000A_RATIO_MODE_NONE
            # pointer to overflow = ctypes.byref(overflow))
            self.p.status["getValues"] = ps.ps5000aGetValues(self.p.chandle, 0, ctypes.byref(cmaxSamples), 0, 0, 0, ctypes.byref(overflow))
            assert_pico_ok(self.p.status["getValues"])


            # convert ADC counts data to mV
            adc2mVChAMax =  adc2mV(bufferAMax, self.chRange, self.maxADC)
            
            # Create time data
            time = np.linspace(0, (cmaxSamples.value - 1) * timeIntervalns.value, cmaxSamples.value)
            return time,adc2mVChAMax