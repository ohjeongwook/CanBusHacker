/**
 * CAN BUS
 *
 * Copyright (c) 2010 Sukkin Pang All rights reserved.
 */

#ifndef canbus__h
#define canbus__h

#include <inttypes.h>

#define CANSPEED_125 	7		// CAN speed at 125 kbps
#define CANSPEED_250  	3		// CAN speed at 250 kbps
#define CANSPEED_500	1		// CAN speed at 500 kbps


#define ENGINE_COOLANT_TEMP 0x05
#define ENGINE_RPM          0x0C
#define VEHICLE_SPEED       0x0D
#define MAF_SENSOR          0x10
#define O2_VOLTAGE          0x14
#define THROTTLE			0x11

#define PID_REQUEST         0x7DF
#define PID_REPLY			0x7E8

class CanbusClass
{
  public:

	CanbusClass();
    char init(unsigned char);
	char message_tx(unsigned int ID, unsigned char *buffer);
	unsigned int message_rx(unsigned char *buffer);
	bool raw_message_rx(uint16_t &id, int8_t &rtr, uint8_t &length, unsigned char *raw_buffer, unsigned char *buffer);
	char ecu_req(unsigned char pid,  char *buffer);
private:
	
};
extern CanbusClass Canbus;
//extern tCAN message;

#endif
