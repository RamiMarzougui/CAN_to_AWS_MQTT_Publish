# import the library
from PCANBasic import *
import time

class CanNwt:
    
    # Sets the PCANHandle (Hardware Channel)
    PcanHandle = PCAN_USBBUS2

    # Sets the bitrate for normal CAN devices
    Bitrate = PCAN_BAUD_1M

    list_time_debug = []  # debug only
    t_prev = 0 #debug only
    

    def __init__(self):
        self.m_objPCANBasic = PCANBasic()
        self.m_objPCANBasic.Initialize(Channel = self.PcanHandle, Btr0Btr1 = self.Bitrate)

    def GetIdString(self,id, msgtype):
        """
        Gets the string representation of the ID of a CAN message

        Parameters:
            id = Id to be parsed
            msgtype = Type flags of the message the Id belong

        Returns:
            Hexadecimal representation of the ID of a CAN message
        """
        if (msgtype & PCAN_MESSAGE_EXTENDED.value) == PCAN_MESSAGE_EXTENDED.value:
            return '%.8Xh' %id
        else:
            return '%.3Xh' %id

    def GetTimeString(self,time):
        """
        Gets the string representation of the timestamp of a CAN message, in milliseconds

        Parameters:
            time = Timestamp in microseconds

        Returns:
            String representing the timestamp in milliseconds
        """
        fTime = time / 1000.0
        return '%.1f' %fTime

    def GetTypeString(self,msgtype):  
        """
        Gets the string representation of the type of a CAN message

        Parameters:
            msgtype = Type of a CAN message

        Returns:
            The type of the CAN message as string
        """
        if (msgtype & PCAN_MESSAGE_STATUS.value) == PCAN_MESSAGE_STATUS.value:
            return 'STATUS'
        
        if (msgtype & PCAN_MESSAGE_ERRFRAME.value) == PCAN_MESSAGE_ERRFRAME.value:
            return 'ERROR'        
        
        if (msgtype & PCAN_MESSAGE_EXTENDED.value) == PCAN_MESSAGE_EXTENDED.value:
            strTemp = 'EXT'
        else:
            strTemp = 'STD'

        if (msgtype & PCAN_MESSAGE_RTR.value) == PCAN_MESSAGE_RTR.value:
            strTemp += '/RTR'
        else:
            if (msgtype > PCAN_MESSAGE_EXTENDED.value):
                strTemp += ' ['
                if (msgtype & PCAN_MESSAGE_FD.value) == PCAN_MESSAGE_FD.value:
                    strTemp += ' FD'
                if (msgtype & PCAN_MESSAGE_BRS.value) == PCAN_MESSAGE_BRS.value:                    
                    strTemp += ' BRS'
                if (msgtype & PCAN_MESSAGE_ESI.value) == PCAN_MESSAGE_ESI.value:
                    strTemp += ' ESI'
                strTemp += ' ]'
                
        return strTemp

    def GetDataString(self,data, msgtype):
        """
        Gets the data of a CAN message as a string

        Parameters:
            data = Array of bytes containing the data to parse
            msgtype = Type flags of the message the data belong

        Returns:
            A string with hexadecimal formatted data bytes of a CAN message
        """
        if (msgtype & PCAN_MESSAGE_RTR.value) == PCAN_MESSAGE_RTR.value:
            return "Remote Request"
        else:
            strTemp = b""
            for x in data:
                strTemp += b'%.2X ' % x
            return str(strTemp).replace("'","",2).replace("b","",1)
        
    def ProcessMessageCan(self,msg,itstimestamp):
        """
        Processes a received CAN message

        Parameters:
            msg = The received PCAN-Basic CAN message
            itstimestamp = Timestamp of the message as TPCANTimestamp structure
        """
        microsTimeStamp = itstimestamp.micros + (1000 * itstimestamp.millis) + (0x100000000 * 1000 * itstimestamp.millis_overflow)

        print("Type: " + self.GetTypeString(msg.MSGTYPE))
        print("ID: " + self.GetIdString(msg.ID, msg.MSGTYPE))
        print("Length: " + str(msg.LEN))
        print("Time: " + self.GetTimeString(microsTimeStamp))
        print("Data: " + self.GetDataString(msg.DATA,msg.MSGTYPE))
        print("----------------------------------------------------------")

    def WriteMessage(self,msg):
        pass
    
    def ReadMessageLog(self):
        # We execute the "Read" function of the PCANBasic   
        read_result = self.m_objPCANBasic.Read(self.PcanHandle)
        if read_result[0] == PCAN_ERROR_OK:
            ## We show the received message
            self.ProcessMessageCan(read_result[1],read_result[2])
        pass
    
    # Get the timestamp in ms
    def GetTime(self,itstimestamp):
        microsTimeStamp = itstimestamp.micros + (1000 * itstimestamp.millis) + (0x100000000 * 1000 * itstimestamp.millis_overflow)
        fTime = microsTimeStamp / 1000.0
        return fTime
    
    # Get the data and put it in a tab
    def GetData(self,data):
        fData=[]
        for octet in data.DATA:
            fData.append(octet)
        return fData

    # Read CAN and create the struct to compress the trame
    def ReadMessage(self):
        trame_can ={}
        # We execute the "Read" function of the PCANBasic   
        read_result = self.m_objPCANBasic.Read(self.PcanHandle)
        #Ceck si une tram a été lue ou non
        if read_result[0] == PCAN_ERROR_OK:
            time_t = 0
            time_t = int(time.time()*1000)
            self.list_time_debug.append(time_t)
            if self.t_prev > time_t:
                print("ERROR TIME ❌")
            self.t_prev = time_t
                

            trame_can={"id":read_result[1].ID,
                            "id_compressed":-1,
                            "dlc":read_result[1].LEN,
                            #time en ms
                            "time": time_t,#int(self.GetTime(read_result[2])), # Eneleve la partie us
                            "priority":0,
                            "sorter":[],
                            "prev_data_hex":[],
                            "data":self.GetData(read_result[1]),
                            "data_hex":[],
                            "data_compressed":[],
                            "data_compressed_hex":[],
                            "cpt_sync":0
                        }
        else :
            trame_can = "Error"
        return trame_can

 