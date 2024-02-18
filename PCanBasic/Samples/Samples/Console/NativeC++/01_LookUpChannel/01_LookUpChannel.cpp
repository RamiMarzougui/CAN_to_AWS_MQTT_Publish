#include "01_LookUpChannel.h" 

LookUpChannel::LookUpChannel()
{
    ShowConfigurationHelp(); // Shows information about this sample
    ShowCurrentConfiguration(); // Shows the current parameters configuration

    std::cout << "Start searching...\n";
    system("PAUSE");
    std::cout << "\n";

    char sParameters[MAX_PATH];
    if (DeviceType != "")
        sprintf_s(sParameters, sizeof(sParameters), "%s=%s", ConvertDefinesToChar((wchar_t*)LOOKUP_DEVICE_TYPE), DeviceType);
    if (DeviceID != "")
    {
        if (sParameters != "")
            sprintf_s(sParameters, sizeof(sParameters), "%s, ", sParameters);
        sprintf_s(sParameters, sizeof(sParameters), "%s%s=%s", sParameters, ConvertDefinesToChar((wchar_t*)LOOKUP_DEVICE_ID), DeviceID);
    }
    if (ControllerNumber != "")
    {
        if (sParameters != "")
            sprintf_s(sParameters, sizeof(sParameters), "%s, ", sParameters);
        sprintf_s(sParameters, sizeof(sParameters), "%s%s=%s", sParameters, ConvertDefinesToChar((wchar_t*)LOOKUP_CONTROLLER_NUMBER), ControllerNumber);
    }
    if (IPAddress != "")
    {
        if (sParameters != "")
            sprintf_s(sParameters, sizeof(sParameters), "%s, ", sParameters);
        sprintf_s(sParameters, sizeof(sParameters), "%s%s=%s", sParameters, ConvertDefinesToChar((wchar_t*)LOOKUP_IP_ADDRESS), IPAddress);
    }

    TPCANHandle handle;
    TPCANStatus stsResult = CAN_LookUpChannel((LPSTR)sParameters, &handle);

    if (stsResult == PCAN_ERROR_OK)
    {

        if (handle != PCAN_NONEBUS)
        {
            UINT32 iFeatures;
            stsResult = CAN_GetValue(handle, PCAN_CHANNEL_FEATURES, &iFeatures, sizeof(UINT32));

            if (stsResult == PCAN_ERROR_OK)
            {
                char buffer[MAX_PATH];
                FormatChannelName(handle, buffer, (iFeatures & FEATURE_FD_CAPABLE) == FEATURE_FD_CAPABLE);
                std::cout << "The channel handle " << buffer << " was found\n";
            }
            else
                std::cout << "There was an issue retrieveing supported channel features\n";
        }
        else
            std::cout << "A handle for these lookup-criteria was not found\n";
    }

    if (stsResult != PCAN_ERROR_OK)
    {
        std::cout << "There was an error looking up the device, are any hardware channels attached?\n";
        ShowStatus(stsResult);
    }

    std::cout << "\n";
    std::cout << "Closing...\n";
    system("PAUSE");
}
LookUpChannel::~LookUpChannel()
{
    CAN_Uninitialize(PCAN_NONEBUS);
}

void LookUpChannel::ShowConfigurationHelp()
{
    std::cout << "=========================================================================================\n";
    std::cout << "|                        PCAN-Basic LookUpChannel Example                                |\n";
    std::cout << "=========================================================================================\n";
    std::cout << "Following parameters are to be adjusted before launching, according to the hardware used |\n";
    std::cout << "                                                                                         |\n";
    std::cout << "* DeviceType: Numeric value that represents a TPCANDevice                                |\n";
    std::cout << "* DeviceID: Numeric value that represents the device identifier                          |\n";
    std::cout << "* ControllerNumber: Numeric value that represents controller number                      |\n";
    std::cout << "* IPAddress: String value that represents a valid Internet Protocol address              |\n";
    std::cout << "                                                                                         |\n";
    std::cout << "For more information see 'LookUp Parameter Definition' within the documentation          |\n";
    std::cout << "=========================================================================================\n";
    std::cout << "\n";
}

void LookUpChannel::ShowCurrentConfiguration()
{
    std::cout << "Parameter values used\n";
    std::cout << "----------------------\n";
    std::cout << "* DeviceType: " << DeviceType << "\n";
    std::cout << "* DeviceID: " << DeviceID << "\n";
    std::cout << "* ControllerNumber: " << ControllerNumber << "\n";
    std::cout << "* IPAddress: " << IPAddress << "\n";
    std::cout << "\n";
}

void LookUpChannel::ShowStatus(TPCANStatus status)
{
    std::cout << "=========================================================================================\n";
    char buffer[MAX_PATH];
    GetFormattedError(status, buffer);
    std::cout << buffer  << "\n";
    std::cout << "=========================================================================================\n";
}

void LookUpChannel::FormatChannelName(TPCANHandle handle, LPSTR buffer, bool isFD)
{
    TPCANDevice devDevice;
    BYTE byChannel;

    // Gets the owner device and channel for a PCAN-Basic handle
    if (handle < 0x100)
    {
        devDevice = (TPCANDevice)(handle >> 4);
        byChannel = (BYTE)(handle & 0xF);
    }
    else
    {
        devDevice = (TPCANDevice)(handle >> 8);
        byChannel = (BYTE)(handle & 0xFF);
    }

    // Constructs the PCAN-Basic Channel name and return it
    char handleBuffer[MAX_PATH];
    GetTPCANHandleName(handle, handleBuffer);
    if (isFD)
        sprintf_s(buffer, MAX_PATH, "%s:FD %d (%Xh)", handleBuffer, byChannel, handle);
    else
        sprintf_s(buffer, MAX_PATH, "%s %d (%Xh)", handleBuffer, byChannel, handle);
}

void LookUpChannel::GetTPCANHandleName(TPCANHandle handle, LPSTR buffer)
{
    strcpy_s(buffer, MAX_PATH, "PCAN_NONE");
    switch (handle)
    {
    case PCAN_PCIBUS1:
    case PCAN_PCIBUS2:
    case PCAN_PCIBUS3:
    case PCAN_PCIBUS4:
    case PCAN_PCIBUS5:
    case PCAN_PCIBUS6:
    case PCAN_PCIBUS7:
    case PCAN_PCIBUS8:
    case PCAN_PCIBUS9:
    case PCAN_PCIBUS10:
    case PCAN_PCIBUS11:
    case PCAN_PCIBUS12:
    case PCAN_PCIBUS13:
    case PCAN_PCIBUS14:
    case PCAN_PCIBUS15:
    case PCAN_PCIBUS16:
        strcpy_s(buffer, MAX_PATH, "PCAN_PCI");
        break;

    case PCAN_USBBUS1:
    case PCAN_USBBUS2:
    case PCAN_USBBUS3:
    case PCAN_USBBUS4:
    case PCAN_USBBUS5:
    case PCAN_USBBUS6:
    case PCAN_USBBUS7:
    case PCAN_USBBUS8:
    case PCAN_USBBUS9:
    case PCAN_USBBUS10:
    case PCAN_USBBUS11:
    case PCAN_USBBUS12:
    case PCAN_USBBUS13:
    case PCAN_USBBUS14:
    case PCAN_USBBUS15:
    case PCAN_USBBUS16:
        strcpy_s(buffer, MAX_PATH, "PCAN_USB");
        break;

    case PCAN_LANBUS1:
    case PCAN_LANBUS2:
    case PCAN_LANBUS3:
    case PCAN_LANBUS4:
    case PCAN_LANBUS5:
    case PCAN_LANBUS6:
    case PCAN_LANBUS7:
    case PCAN_LANBUS8:
    case PCAN_LANBUS9:
    case PCAN_LANBUS10:
    case PCAN_LANBUS11:
    case PCAN_LANBUS12:
    case PCAN_LANBUS13:
    case PCAN_LANBUS14:
    case PCAN_LANBUS15:
    case PCAN_LANBUS16:
        strcpy_s(buffer, MAX_PATH, "PCAN_LAN");
        break;

    default:
        strcpy_s(buffer, MAX_PATH, "UNKNOWN");
        break;
    }
}

void LookUpChannel::GetFormattedError(TPCANStatus error, LPSTR buffer)
{
    // Gets the text using the GetErrorText API function. If the function success, the translated error is returned. 
    // If it fails, a text describing the current error is returned.
    if (CAN_GetErrorText(error, 0x09, buffer) != PCAN_ERROR_OK)
        sprintf_s(buffer, MAX_PATH, "An error occurred. Error-code's text (%Xh) couldn't be retrieved", error);
}

void LookUpChannel::ConvertBitrateToString(TPCANBaudrate bitrate, LPSTR buffer)
{
    switch (bitrate)
    {
    case PCAN_BAUD_1M:
        strcpy_s(buffer, MAX_PATH, "1 MBit/sec");
        break;
    case PCAN_BAUD_800K:
        strcpy_s(buffer, MAX_PATH, "800 kBit/sec");
        break;
    case PCAN_BAUD_500K:
        strcpy_s(buffer, MAX_PATH, "500 kBit/sec");
        break;
    case PCAN_BAUD_250K:
        strcpy_s(buffer, MAX_PATH, "250 kBit/sec");
        break;
    case PCAN_BAUD_125K:
        strcpy_s(buffer, MAX_PATH, "125 kBit/sec");
        break;
    case PCAN_BAUD_100K:
        strcpy_s(buffer, MAX_PATH, "100 kBit/sec");
        break;
    case PCAN_BAUD_95K:
        strcpy_s(buffer, MAX_PATH, "95,238 kBit/sec");
        break;
    case PCAN_BAUD_83K:
        strcpy_s(buffer, MAX_PATH, "83,333 kBit/sec");
        break;
    case PCAN_BAUD_50K:
        strcpy_s(buffer, MAX_PATH, "50 kBit/sec");
        break;
    case PCAN_BAUD_47K:
        strcpy_s(buffer, MAX_PATH, "47,619 kBit/sec");
        break;
    case PCAN_BAUD_33K:
        strcpy_s(buffer, MAX_PATH, "33,333 kBit/sec");
        break;
    case PCAN_BAUD_20K:
        strcpy_s(buffer, MAX_PATH, "20 kBit/sec");
        break;
    case PCAN_BAUD_10K:
        strcpy_s(buffer, MAX_PATH, "10 kBit/sec");
        break;
    case PCAN_BAUD_5K:
        strcpy_s(buffer, MAX_PATH, "5 kBit/sec");
        break;
    default:
        strcpy_s(buffer, MAX_PATH, "Unknown Bitrate");
        break;
    }
}

char* LookUpChannel::ConvertDefinesToChar(wchar_t* define)
{
    // Convert the wchar_t string to a char* string. Record
    // the length of the original string and add 1 to it to
    // account for the terminating null character.
    size_t origsize = wcslen(define) + 1;
    size_t convertedChars = 0;

    // Allocate two bytes in the multibyte output string for every wide
    // character in the input string (including a wide character
    // null). Because a multibyte character can be one or two bytes,
    // you should allot two bytes for each character. Having extra
    // space for the new string is not an error, but having
    // insufficient space is a potential security problem.
    const size_t newsize = origsize * 2;
    // The new string will contain a converted copy of the original
    // string plus the type of string appended to it.
    char* nstring = new char[newsize];

    // Put a copy of the converted string into nstring
    wcstombs_s(&convertedChars, nstring, newsize, define, _TRUNCATE);
    return nstring;
}